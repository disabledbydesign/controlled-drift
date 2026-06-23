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
            "payload": (
                "Capacity is low today. Please reframe the plan: shorter sessions, "
                "lower-stakes tasks first, rest built in. Keep the time-block format. "
                "Re-explain the ordering logic for a low-energy day."
            ),
        },
        {
            "id": "quick-wins",
            "label": "Quick wins first",
            "payload": (
                "Reorder to lead with quick wins — shorter tasks I can finish fast to "
                "build momentum for the harder work later. Explain why this order works "
                "for today."
            ),
        },
        {
            "id": "stuck",
            "label": "I'm stuck",
            "payload": (
                "I'm stuck and can't start. Offer one very small, concrete first step I "
                "can take right now — something doable in five minutes. Hold everything "
                "else. Don't ask me to decide anything."
            ),
        },
        # "add" focuses the open text field instead of generating — no payload.
        {"id": "add", "label": "Add something", "payload": None},
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


# --- actions (variable button schema) ---------------------------------------

def load_actions():
    """Return the button schema, seeding the default on first run."""
    try:
        with open(_actions_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _ensure_dir()
        with open(_actions_path(), "w") as f:
            json.dump(_DEFAULT_ACTIONS, f, indent=2)
        return _DEFAULT_ACTIONS


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
