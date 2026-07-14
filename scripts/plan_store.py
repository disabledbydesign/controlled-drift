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
            "payload": None,
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


def _iter_items(plan):
    """Every schedulable item in a cached plan, across BOTH shapes: a clock day keeps rows under
    blocks[]; a fragmented/priority day keeps them in a flat items[] list with no blocks. Iterating
    only blocks[] was the mark-done-doesn't-stick bug on fragmented days — the Anytype write landed
    but the cache never changed, so reopening showed the task unchecked."""
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            yield item
    for item in plan.get("items", []):
        yield item


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
    for item in _iter_items(plan):
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


def is_recurring_item(task_id):
    """True if the cached plan carries this id on a RECURRING anchor row (a chore/appointment,
    flagged `recurring` by blocks_from_scheduled). The completion endpoint reads this to route a
    chore checkoff to a local 'done for today' (cache flip) instead of an Anytype Task-status write
    — Recurring objects have no Task status and they recur, so writing done-forever would be wrong."""
    plan = load_plan()
    if plan is None:
        return False
    for item in _iter_items(plan):
        if item.get("id") == task_id and item.get("recurring"):
            return True
    return False


def mark_item_undone(task_id):
    """Undo a checkoff in the cache (the mis-tap fix): set done=False on every cached plan
    item with this task id, so reopening the overlay shows it un-checked again. Mirror of
    mark_item_done; preserves generated_at (a toggle is not a regeneration)."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for item in _iter_items(plan):
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


def _remove_rows(pred):
    """Shared core of the "not today" removals: drop every cached-plan row matching `pred` from
    TODAY'S view only. Cache-only on purpose — no Anytype write, no status change, no reschedule.
    The rows just leave the current list; the next generation rebuilds from Anytype and they return
    as candidates with the exact status they had. Clock times of the remaining rows are left as they
    are (a gap, not a re-solve — a hide, not a re-plan). Works across both shapes (blocks[] clock day
    / flat items[] fragmented day). Preserves generated_at (not a regeneration).

    Returns (plan, removed) where `removed` is the list of removed row dicts — empty if nothing
    matched. Returns (None, []) if there's no cache at all.
    """
    plan = load_plan()
    if plan is None:
        return None, []
    removed = []
    for block in plan.get("blocks", []):
        kept = []
        for it in block.get("items", []):
            (removed if pred(it) else kept).append(it)
        block["items"] = kept
    flat = plan.get("items")
    if isinstance(flat, list):
        kept = []
        for it in flat:
            (removed if pred(it) else kept).append(it)
        plan["items"] = kept
    if removed:
        _persist_plan(plan)
    return plan, removed


def remove_item(task_id):
    """"Not today" on a single task — drop its row(s) from today's cached list by task id."""
    return _remove_rows(lambda it: it.get("id") == task_id)


def remove_block(project_id):
    """"Not today" on a work-block — drop every cached row of that block-work project (they carry
    `project_id`). Same cache-only contract as remove_item: the project's tasks keep their status
    and return on the next generation (a matching recent deferral keeps the block out for the
    recency window)."""
    return _remove_rows(lambda it: it.get("project_id") == project_id)


def _persist_plan(plan):
    """Atomically rewrite the cached plan (the overlay never reads a half-written file)."""
    path = _plan_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(plan, f, indent=2)
    os.replace(tmp, path)


def is_block_item(project_id):
    """True if the cached plan carries a BLOCK row for this project_id (blocks_from_scheduled
    tags block rows with block=True + project_id). The completion endpoint routes a block check
    to a local 'worked on it today' (chunk_log + cache flip) — NEVER an Anytype done-write; a
    block must never finish the underlying project (display_grain_design.md decision 3)."""
    plan = load_plan()
    if plan is None:
        return False
    for item in _iter_items(plan):
        if item.get("block") and item.get("project_id") == project_id:
            return True
    return False


def mark_block_chunked(project_id, chunked=True):
    """Flip did_chunk_today on every cached block row for this project, so reopening the overlay
    shows the chunk-check state without a regeneration. The DURABLE record is chunk_log; this is
    only the cache mirror (like mark_item_done for a task). Returns the updated plan or None."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for item in _iter_items(plan):
        if item.get("block") and item.get("project_id") == project_id:
            item["did_chunk_today"] = chunked
            changed = True
    if changed:
        _persist_plan(plan)
    return plan


def set_block_chunk(project_id, minutes):
    """Update the cached block row's chunk length so the overlay reflects June's new value
    immediately. The DURABLE write (Anytype Project field + event log) is block_duration; the
    re-timed slot follows on the next generation. Returns the updated plan or None."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for item in _iter_items(plan):
        if item.get("block") and item.get("project_id") == project_id:
            item["chunk_min"] = minutes
            changed = True
    if changed:
        _persist_plan(plan)
    return plan


def set_item_duration(item_id, minutes):
    """Update the cached duration_min on every plan row carrying this Anytype id (a real task or
    recurring), so the overlay reflects June's new length immediately. The durable write is on
    the object itself (task_actions.set_task_duration). Returns the updated plan or None."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for item in _iter_items(plan):
        if item.get("id") == item_id:
            item["duration_min"] = minutes
            changed = True
    if changed:
        _persist_plan(plan)
    return plan


# --- tap-to-place move (deterministic — no LLM, no regeneration) -------------
# June moves a task by TAPPING WHERE IT GOES: the overlay shows tap-targets at every later
# spot in the visible plan, and the tapped spot arrives here as (target_block, position).
# The clock times then RE-FLOW automatically: pure first-fit arithmetic over the cached
# plan's existing durations. This never touches plan_generate/daily_plan and never writes
# to Anytype. It is a day-of adjustment to what's on screen, NOT a stored preference: the
# next generation rebuilds the plan from Anytype and the move is gone (overlay copy says
# so — nothing here promises persistence).

_DEFAULT_ITEM_MIN = 30  # fallback duration when an item's current time doesn't parse


def _hhmm_to_min(s):
    """'13:30' -> 810, or None if it isn't an HH:MM string."""
    try:
        h, m = str(s).strip().split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _min_to_hhmm(n):
    n %= 24 * 60
    return f"{n // 60:02d}:{n % 60:02d}"


def _range_bounds(s):
    """'09:00 – 10:30' -> (540, 630). A single time or unparseable text -> (start_or_None, None).
    Splits on the en-dash, the separator every generated time range uses."""
    if not s:
        return None, None
    parts = [p.strip() for p in str(s).split("–")]
    start = _hhmm_to_min(parts[0]) if parts else None
    end = _hhmm_to_min(parts[1]) if len(parts) > 1 else None
    return start, end


def _reflow_block(block):
    """Recompute every item's clock time in this block, in order — the automatic time
    recalculation June asked for. Each item KEEPS its existing duration (or 30 min if its
    current time doesn't parse); item N starts where item N-1 ends; the walk starts at the
    block's own start time (or the first item's, if the block has none). If nothing gives a
    start time, the times are left exactly as they are — an honest no-op, never invented.
    If the durations run past the block's labelled end, the times run past it too: the
    arithmetic tells the truth rather than squeezing tasks to fit."""
    items = block.get("items", [])
    if not items:
        return
    cursor, _ = _range_bounds(block.get("time"))
    if cursor is None:
        cursor, _ = _range_bounds(items[0].get("time"))
    if cursor is None:
        return
    for item in items:
        s, e = _range_bounds(item.get("time"))
        dur = (e - s) if (s is not None and e is not None and e > s) else _DEFAULT_ITEM_MIN
        item["time"] = f"{_min_to_hhmm(cursor)} – {_min_to_hhmm(cursor + dur)}"
        cursor += dur


def _write_plan(plan):
    """Atomic persist of an in-place plan mutation (same discipline as save_plan/mark_item_done:
    the overlay never reads a half-written plan). Deliberately does NOT re-stamp
    generated_at/source — a move is not a regeneration."""
    path = _plan_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(plan, f, indent=2)
    os.replace(tmp, path)


def move_item_later(task_id, target_block_index, position=None):
    """Move one scheduled task LATER in the cached clock-shape plan and re-flow the times.

    `position` is the item's FINAL index in the destination block's item list (the tap-target
    the overlay showed); None appends to the end of the destination block. A move within the
    SAME block needs a position strictly greater than the item's current index; any other
    destination must be a strictly later block. Both affected blocks are re-flowed so every
    item shows a real recomputed time.

    Returns the updated plan dict. Raises:
      LookupError — no cached plan; no clock-shape blocks (fragmented days reorder via
                    move_priority_item_later instead); or no scheduled item with task_id.
      ValueError  — block/position out of range, or the destination is not strictly later.
    """
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    blocks = plan.get("blocks")
    if not blocks:
        raise LookupError("plan has no time-blocks — use move_priority_item_later for a "
                          "fragmented (priority-shape) day")
    if not (0 <= target_block_index < len(blocks)):
        raise ValueError(f"target block {target_block_index} out of range (0..{len(blocks) - 1})")

    src_index = src_pos = None
    for bi, block in enumerate(blocks):
        for pos, item in enumerate(block.get("items", [])):
            if item.get("id") == task_id:
                src_index, src_pos = bi, pos
                break
        if src_index is not None:
            break
    if src_index is None:
        raise LookupError(f"no scheduled item with id {task_id!r} to move")
    if target_block_index < src_index:
        raise ValueError("can only move a task later")

    # Validate the landing spot BEFORE mutating anything.
    if target_block_index == src_index:
        n = len(blocks[src_index]["items"])
        # Same block: the final index must be strictly later than where it is now.
        if position is None or not (src_pos < position <= n - 1):
            raise ValueError("a move within its own part of the day must land at a later spot")
    else:
        n = len(blocks[target_block_index].get("items", []))
        if position is None:
            position = n                      # append (the block-end tap-target)
        elif not (0 <= position <= n):
            raise ValueError(f"position {position} out of range for that part of the day (0..{n})")

    src_item = blocks[src_index]["items"].pop(src_pos)
    # After the pop, inserting at `position` puts the item at exactly that final index —
    # including the same-block case (everything after src_pos shifted down by one).
    blocks[target_block_index].setdefault("items", []).insert(position, src_item)

    _reflow_block(blocks[src_index])
    if target_block_index != src_index:
        _reflow_block(blocks[target_block_index])

    _write_plan(plan)
    return plan


def move_priority_item_later(task_id, position):
    """Move one item LATER in a fragmented-day (priority-shape) plan. `position` is the item's
    FINAL index in the flat list (the tap-target the overlay showed). Pure position change —
    priority items carry no clock times, so there is nothing to re-flow. Same honesty rule as
    move_item_later: a day-of adjustment to the cache; the next generation replaces it.
    Preserves generated_at/source.

    Raises LookupError (no cached plan / no priority list / id absent) and ValueError
    (position not strictly later, or out of range)."""
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    items = plan.get("items")
    if not items:
        raise LookupError("plan has no priority list to reorder (a clock-shape day moves via "
                          "move_item_later)")
    src_pos = next((i for i, it in enumerate(items) if it.get("id") == task_id), None)
    if src_pos is None:
        raise LookupError(f"no item with id {task_id!r} to move")
    if not (src_pos < position <= len(items) - 1):
        raise ValueError("can only move a task to a later spot in the list")
    item = items.pop(src_pos)
    items.insert(position, item)   # after the pop, inserting at `position` = final index
    _write_plan(plan)
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
