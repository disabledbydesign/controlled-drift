#!/usr/bin/env python3
"""User-local cache + config for the Controlled Drift overlay.

Two files live in ~/.controlled-drift/ (outside the repo — user data, never committed):

  current_plan.json   the last generated daily plan the overlay displays. Written by
                      plan_generate (morning push, refresh, negotiate); read by the
                      server's GET /api/plan. Shape:
                        {woven_frame, blocks[], still_here[], generated_at, source}

  actions.json        the VARIABLE button schema (the both-and: presets are structured
                      correction-capture AND freetext signals what presets are missing).
                      Buttons are config, not hardcoded, so the set can grow/shrink as
                      usage patterns emerge — without code edits. Read by GET /api/actions.

Why a cache at all: the overlay must show a plan the instant June opens it (the EF point —
it comes to her). Generation needs an LLM call; the cache decouples "display" (instant,
no LLM) from "generate" (slower, on the morning push or a button). The plan is the data;
the cache is where it rests between generations.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths

# Paths resolve through cd_paths at call time (default ~/.controlled-drift/), so the test
# sandbox redirect (CD_CONFIG_DIR) deterministically keeps test runs out of real data.
def _plan_path():
    return cd_paths.config_file("current_plan.json")

def _actions_path():
    return cd_paths.config_file("actions.json")

# Seed for the variable button schema. Each preset carries the negotiation payload
# (the instruction sent to the LLM). "add" has no payload — it focuses the textarea.
# Register is permission-granting, never imperative (SYNTHESIS design DNA).
# These are a STARTING set, not a fixed one — Slice 3's learning loop grows them from
# freetext-request patterns June approves.
_DEFAULT_ACTIONS = {
    "version": 1,
    "presets": [
        {
            "id": "low-energy",
            "label": "Low energy today",
            # operation="generate": triggers a fresh plan generation with the capacity flag,
            # so the LLM selects from the full task list (prioritizing Can-be-done-lying-down
            # tasks) rather than reordering what's already on screen.
            "operation": "generate",
            "capacity_flag": "low-energy",
            "payload": (
                "Capacity is low today. Please reframe the plan: shorter sessions, "
                "lower-stakes tasks first, rest built in. Keep the time-block format. "
                "Re-explain the ordering logic for a low-energy day."
            ),
        },
        {
            "id": "quick-wins",
            "label": "Quick wins first",
            "operation": "reorder",
            "payload": (
                "Reorder to lead with quick wins — shorter tasks I can finish fast to "
                "build momentum for the harder work later. Explain why this order works "
                "for today."
            ),
        },
        {
            "id": "stuck",
            "label": "I'm stuck",
            "operation": "reorder",
            "payload": (
                "I'm stuck and can't start. Offer one very small, concrete first step I "
                "can take right now — something doable in five minutes. Hold everything "
                "else. Don't ask me to decide anything."
            ),
        },
        {
            "id": "add",
            "label": "+ Add",
            # UI-only: the server returns the current plan synchronously; the overlay
            # uses this to focus the Add tab textarea rather than starting a generation.
            "operation": "reorder",
        },
    ],
}


def _ensure_dir():
    os.makedirs(cd_paths.config_dir(), exist_ok=True)


# --- current plan -----------------------------------------------------------

def save_plan(plan, source="generate"):
    """Persist a generated plan. `plan` is the structured dict the overlay reads.

    Stamps generated_at + source so the overlay (and any future learning) can tell a
    fresh morning plan from a renegotiated one.
    """
    _ensure_dir()
    record = dict(plan)
    record["generated_at"] = dt.datetime.now().isoformat()
    record["source"] = source
    path = _plan_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, path)  # atomic — the overlay never reads a half-written plan
    return record


def load_plan():
    """Return the cached plan dict, or None if nothing has been generated yet.

    None is a real answer (Slice-1 first run, or a failed generation) — the server
    surfaces it honestly as an empty state, never a fabricated plan.
    """
    try:
        with open(_plan_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def mark_item_done(task_id):
    """Flip done=true on every cached plan item carrying this Anytype task id, so reopening
    the overlay shows it checked WITHOUT a regeneration (closing a task must not cost an LLM
    call). Returns the updated plan, or None if there's no cache / no matching item.

    Preserves generated_at + source deliberately — a checkoff is not a new generation, and
    re-stamping would make a mark-done masquerade as a fresh morning plan.
    """
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            if item.get("id") == task_id:
                item["done"] = True
                changed = True
    if changed:
        path = _plan_path()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(plan, f, indent=2)
        os.replace(tmp, path)  # atomic — the overlay never reads a half-written plan
    return plan


def mark_item_undone(task_id):
    """Undo a checkoff in the cache (the mis-tap fix): set done=False on every cached plan
    item with this task id, so reopening the overlay shows it un-checked again. Mirror of
    mark_item_done; preserves generated_at (a toggle is not a regeneration)."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            if item.get("id") == task_id and item.get("done"):
                item["done"] = False
                changed = True
    if changed:
        path = _plan_path()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(plan, f, indent=2)
        os.replace(tmp, path)
    return plan


# --- generation status (for async generate-and-poll) ------------------------
# A long generation (the LLM call) no longer blocks the HTTP request — the server kicks it
# off in the background and the overlay polls this status. Lives in its own small file so a
# status write never races a plan write.
def _status_path():
    return cd_paths.config_file("gen_status.json")


def get_gen_status():
    """Current generation state: {state: 'idle'|'running'|'error', updated_at, [error]}.
    'idle' is the honest default (nothing has run, or the last run finished)."""
    try:
        with open(_status_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"state": "idle"}


def set_gen_status(state, error=None):
    """Record generation state. `state` in {'running','idle','error'}; `error` on failure."""
    _ensure_dir()
    rec = {"state": state, "updated_at": dt.datetime.now().isoformat()}
    if error:
        rec["error"] = error
    path = _status_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, path)
    return rec


# --- actions (variable button schema) ---------------------------------------

def load_actions():
    """Return the button schema, seeding the default on first run.

    Also migrates an existing on-disk actions.json that is missing `operation` / `capacity_flag`
    fields (added when intent-routing landed). Presets are merged by id from _DEFAULT_ACTIONS so
    new fields propagate without requiring a manual file delete.
    """
    try:
        with open(_actions_path()) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = None

    if data is None:
        _ensure_dir()
        with open(_actions_path(), "w") as f:
            json.dump(_DEFAULT_ACTIONS, f, indent=2)
        return _DEFAULT_ACTIONS

    # Migrate: if any preset is missing `operation`, merge from _DEFAULT_ACTIONS by id.
    defaults_by_id = {p["id"]: p for p in _DEFAULT_ACTIONS["presets"]}
    changed = False
    for preset in data.get("presets", []):
        pid = preset.get("id")
        if pid in defaults_by_id and "operation" not in preset:
            preset["operation"] = defaults_by_id[pid]["operation"]
            if "capacity_flag" in defaults_by_id[pid]:
                preset["capacity_flag"] = defaults_by_id[pid]["capacity_flag"]
            changed = True
    if changed:
        with open(_actions_path(), "w") as f:
            json.dump(data, f, indent=2)
    return data


def find_preset(action_id):
    """Look up one preset by id; None if it's not in the schema."""
    for p in load_actions().get("presets", []):
        if p.get("id") == action_id:
            return p
    return None


if __name__ == "__main__":
    # Quick self-check: seed actions, show paths + current state.
    acts = load_actions()
    plan = load_plan()
    print(f"config dir : {cd_paths.config_dir()}")
    print(f"actions    : {len(acts.get('presets', []))} presets -> {_actions_path()}")
    print(f"plan cached: {'yes' if plan else 'no (none generated yet)'} -> {_plan_path()}")
