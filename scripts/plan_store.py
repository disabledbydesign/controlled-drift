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
            # June's own instruction, 2026-07-18: "prioritize household chores and life admin
            # tasks". The button existed in the mockup with NO preset behind it, so it flashed a
            # message and changed nothing. `reorder` rather than `generate` — this reshapes
            # today's plan, it does not ask for a new one.
            "id": "life-admin",
            "label": "Life admin & household",
            "operation": "reorder",
            "payload": (
                "Reorder to lead with household chores and life admin — cleaning, errands, "
                "paperwork, the administrative things that pile up. Explain why this order "
                "works for today."
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
    but the cache never changed, so reopening showed the task unchecked. Also covers appointments[]
    (2026-07-17, daily_plan.format_appointments) — today's real timed anchors, present on every
    plan regardless of shape; without walking it here, checking one off would route through
    is_recurring_item correctly (its id is real) but the cache flip in mark_item_done would never
    find the row to update, so it'd un-check itself the moment the overlay re-rendered."""
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            yield item
    for item in plan.get("items", []):
        yield item
    for item in plan.get("appointments", []):
        yield item


def _mark_arc_step(plan, task_id, done):
    """Flip the state of the ARC STEP carrying this task id, wherever it is nested.

    A work block's `arc` holds the project's own tasks as ordered steps, each with a REAL
    Anytype task id (grain.project_arc). `_iter_items` walks blocks[].items[], items[] and
    appointments[] — it does NOT descend into an item's `arc`, so before this a step checkoff
    wrote to Anytype and the cache never changed: reopening showed the step un-checked again.
    That is the same mark-done-doesn't-stick bug `_iter_items`' docstring already records twice
    (fragmented days, then appointments), arriving a third time by a third route.

    The state values MIRROR `model/plan.ts`'s `toggleArcStep` exactly, so the plan the server
    hands back and the plan the surface drew optimistically are the same plan — otherwise
    adopting the server's answer would visibly undo her tap:

        done=True  -> "done", and the step immediately after it is promoted "ahead" -> "here"
        done=False -> "ahead"

    Only an "ahead" step is promoted. The live plan really does carry several "here" steps at
    once (plan_generate._mark_here), and re-deriving the whole arc here would fight that.

    Returns True if anything changed.
    """
    changed = False
    for item in _iter_items(plan):
        arc = item.get("arc")
        if not isinstance(arc, list):
            continue
        for i, step in enumerate(arc):
            if not isinstance(step, dict) or step.get("id") != task_id:
                continue
            if not done:
                if step.get("state") != "ahead":
                    step["state"] = "ahead"
                    changed = True
                continue
            was_here = step.get("state") == "here"
            if step.get("state") != "done":
                step["state"] = "done"
                changed = True
            # The advance: only when the checked step was the current one, and only if the
            # next step is still waiting.
            nxt = arc[i + 1] if i + 1 < len(arc) else None
            if was_here and isinstance(nxt, dict) and nxt.get("state") == "ahead":
                nxt["state"] = "here"
                changed = True
    return changed


def mark_item_done(task_id):
    """Flip done=true on every cached plan item carrying this Anytype task id, so reopening
    the overlay shows it checked WITHOUT a regeneration (closing a task must not cost an LLM
    call). Returns the updated plan, or None if there's no cache / no matching item.

    Also marks a nested ARC STEP with this id — see `_mark_arc_step`.

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
    if _mark_arc_step(plan, task_id, True):
        changed = True
    if changed:
        path = _plan_path()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(plan, f, indent=2)
        os.replace(tmp, path)  # atomic — the overlay never reads a half-written plan
    return plan


def item_name(task_id):
    """The display name of the cached plan row carrying this id (its 'task'/'name' field),
    or None if there's no cache / no match. The completion route uses this to name a recurring
    or as-needed 'done for today' for completion_log — a real task gets its name from the Anytype
    read-back, but a recurring checkoff is cache-only, so the name comes from here."""
    plan = load_plan()
    if plan is None:
        return None
    for item in _iter_items(plan):
        if item.get("id") == task_id:
            return item.get("task") or item.get("name")
    return None


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


def is_as_needed_item(task_id):
    """True if the cached plan carries this id on a row flagged `as_needed` (an active as-needed
    task, marked in daily_plan). The completion endpoint reads this BEFORE is_recurring_item to
    route a checkoff to a real Active=false write (done-until-asked-again) instead of the
    cache-only 'done for today' a scheduled recurring gets."""
    plan = load_plan()
    if plan is None:
        return False
    for item in _iter_items(plan):
        if item.get("id") == task_id and item.get("as_needed"):
            return True
    return False


def mark_item_undone(task_id):
    """Undo a checkoff in the cache (the mis-tap fix): set done=False on every cached plan
    item with this task id, so reopening the overlay shows it un-checked again. Mirror of
    mark_item_done; preserves generated_at (a toggle is not a regeneration).

    Also reopens a nested ARC STEP with this id — see `_mark_arc_step`."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    for item in _iter_items(plan):
        if item.get("id") == task_id and item.get("done"):
            item["done"] = False
            changed = True
    if _mark_arc_step(plan, task_id, False):
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
    recurring), so the overlay reflects June's new length immediately, and re-flow the clock
    times of any block(s) that carry it — otherwise the number changes but the displayed
    schedule doesn't (2026-07-15 friction: a duration change had "no impact on the daily plan
    schedule"). A fragmented/priority day has no clock times to reflow; updating duration_min
    there is the whole fix. The durable write is on the object itself
    (task_actions.set_task_duration). Returns the updated plan or None."""
    plan = load_plan()
    if plan is None:
        return None
    changed = False
    touched_blocks = []
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            if item.get("id") == item_id:
                item["duration_min"] = minutes
                changed = True
                if block not in touched_blocks:
                    touched_blocks.append(block)
    for item in plan.get("items", []):
        if item.get("id") == item_id:
            item["duration_min"] = minutes
            changed = True
    for block in touched_blocks:
        _reflow_block(block)
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
    recalculation June asked for. Each item's slot length is its duration_min when the row
    carries a positive one — that's the number she just set explicitly, and it must win
    (2026-07-15 friction: reflow used to re-derive duration only from the OLD time range,
    so a duration edit never showed up in the schedule); otherwise the existing time range's
    span, or 30 min if neither parses. Item N starts where item N-1 ends; the walk starts at
    the block's own start time (or the first item's, if the block has none). If nothing gives
    a start time, the times are left exactly as they are — an honest no-op, never invented.
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
        dur = item.get("duration_min")
        if not isinstance(dur, (int, float)) or dur <= 0:
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


def move_item(task_id, target_block_index, position=None):
    """Move one scheduled task to ANY spot in the cached clock-shape plan — earlier or later —
    and re-flow the times.

    Direction is not constrained: June asked to be able to move things earlier as well as
    later, so the destination may be an earlier block, a later block, or an earlier/later spot
    within the item's own block. (The original later-only rule came from the one-way "push it
    back" gesture the first overlay offered; it was never a property of the data.)

    `position` is the item's FINAL index in the destination block's item list (the tap-target
    the overlay showed). None means "append": the end of a different block, or the last spot of
    its own block. Both affected blocks are re-flowed from their existing durations, so every
    item shows a real recomputed time whichever way the item travelled.

    Returns the updated plan dict. Raises:
      LookupError — no cached plan; no clock-shape blocks (fragmented days reorder via
                    move_priority_item instead); or no scheduled item with task_id.
      ValueError  — block/position out of range, or the destination is where the item already
                    is (a no-op is reported, never silently swallowed).
    """
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    blocks = plan.get("blocks")
    if not blocks:
        raise LookupError("plan has no time-blocks — use move_priority_item for a "
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

    # Validate the landing spot BEFORE mutating anything.
    if target_block_index == src_index:
        n = len(blocks[src_index]["items"])
        # Same block: the item is popped and re-inserted, so the final index runs 0..n-1.
        if position is None:
            position = n - 1                  # append (the block-end tap-target)
        elif not (0 <= position <= n - 1):
            raise ValueError(f"position {position} out of range for that part of the day "
                             f"(0..{n - 1})")
        if position == src_pos:
            raise ValueError("that task is already in that spot — nothing to move")
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


def move_priority_item(task_id, position):
    """Move one item UP OR DOWN the ranked list of a fragmented-day (priority-shape) plan.
    `position` is the item's FINAL index in the flat list (the tap-target the overlay showed);
    it may be above or below where the item sits now. Pure position change — priority items
    carry no clock times, so there is nothing to re-flow. Same honesty rule as move_item: a
    day-of adjustment to the cache; the next generation replaces it. Preserves
    generated_at/source.

    Raises LookupError (no cached plan / no priority list / id absent) and ValueError
    (position out of range, or already the item's current spot)."""
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    items = plan.get("items")
    if not items:
        raise LookupError("plan has no priority list to reorder (a clock-shape day moves via "
                          "move_item)")
    src_pos = next((i for i, it in enumerate(items) if it.get("id") == task_id), None)
    if src_pos is None:
        raise LookupError(f"no item with id {task_id!r} to move")
    if not (0 <= position <= len(items) - 1):
        raise ValueError(f"position {position} out of range for the list "
                         f"(0..{len(items) - 1})")
    if position == src_pos:
        raise ValueError("that task is already in that spot — nothing to move")
    item = items.pop(src_pos)
    items.insert(position, item)   # after the pop, inserting at `position` = final index
    # A move rewrites the plan's OWN order, so a manual ranking saved by set_priority_order is
    # now stale. Keeping it would leave it governing the display and make the move she just made
    # look like it did not take — the worse of the two surprises. The move wins.
    plan.pop("priority_order", None)
    _write_plan(plan)
    return plan


def set_priority_order(order):
    """Persist June's OWN ranking of a fragmented-day (priority-shape) list.

    `order` is the complete list of item ids in the order she put them in. Stored on the cached
    plan under `priority_order`; the surface reads it back on load, so a reordering survives a
    reload instead of dying with the tab (June's decision 2026-07-19, closing
    docs/api_contract_v2.md §6 Q1).

    ── KEYED BY OBJECT ID, NEVER BY SLOT POSITION ──────────────────────────────
    A regenerated plan reassigns slots, so an index-keyed ranking silently reattaches to
    whatever now sits at that index. Commit b721103 moved block state off slot keys for exactly
    this reason and `chunked` carried the same bug before it.

    ── WHAT A REGENERATION DOES TO IT — the decision, stated ────────────────────
    Nothing explicit: the ranking lives INSIDE the plan record, and `save_plan` writes a fresh
    record, so a regeneration drops it and the generator's order stands. That is deliberate and
    conservative. A regenerated plan is a fresh ranking over possibly different items, and
    reapplying her ordering across it would silently govern a set she never ordered — the
    failure mode the id-keying above exists to prevent, arriving by a second route. The
    alternative (carry it over, merging by id) is a real option and is FLAGGED FOR JUNE rather
    than decided here.

    ── WHY NOT A NEW .jsonl ────────────────────────────────────────────────────
    This is per-plan state, the same family as the moves, deferrals and chunk flags this module
    already holds. `scripts/data/` has thirteen .jsonl files and the rule is to widen what
    exists rather than add a fourteenth.

    Raises LookupError (no cached plan / not a priority-shape plan) and ValueError (the order
    does not name exactly the plan's items, once each).
    """
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to rank")
    items = plan.get("items")
    if not items:
        raise LookupError("plan has no priority list to rank (a clock-shape day orders its rows "
                          "under blocks[])")

    order = [str(i) for i in order]
    if len(set(order)) != len(order):
        raise ValueError("that order names the same task twice — one row, one rank")

    # ⚠ A BLOCK ROW HAS NO `id` — its id lives in `project_id`. Verified against June's real
    # fragmented-day plan 2026-07-19, where three of seven rows were blocks with `id` absent.
    # `api/adapt.ts` reads `it.id ?? it.project_id` for exactly this reason and the surface then
    # sends a block's project_id as its id, so reading `id` alone here disagreed with every id
    # the client can possibly send. It also put `None` in this list, which made the refusal path
    # raise TypeError out of `sorted()` instead of naming the offending id.
    #
    # Found by POSTing to the running server, NOT by a test — the fixture gave every row an
    # `id`, so it could not see this. Same class as the block-id bug `adapt.ts` records.
    known = [it.get("id") or it.get("project_id") for it in items]
    if not all(known):
        raise ValueError("that plan has a row with no id, so it cannot be ranked")
    if set(order) != set(known):
        unknown = sorted(set(order) - set(known))
        missing = sorted(set(known) - set(order))
        raise ValueError(
            "that order does not match the plan's list"
            + (f"; not in the plan: {unknown}" if unknown else "")
            + (f"; left out of the order: {missing}" if missing else ""))

    plan["priority_order"] = order
    _write_plan(plan)      # deliberately does NOT re-stamp generated_at — a reorder is not a
    return plan            # regeneration, and the surface reports the plan's age from that stamp


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
    # Add presets that exist in the defaults but not on disk. Without this a NEW button can
    # never reach an existing install — the loop above only backfills FIELDS on ids already
    # present, so `life-admin` was in the defaults and absent from June's live file, and the
    # button went on flashing a message with nothing behind it.
    # ⚠ Tradeoff, stated: this means a preset cannot be removed by deleting it from the file,
    # because it would be restored on the next load. There is no delete UI today, so nothing
    # can express that intent yet; when one exists this needs a tombstone rather than a silent
    # re-add.
    on_disk = {p.get("id") for p in data.get("presets", [])}
    for pid, default in defaults_by_id.items():
        if pid not in on_disk:
            data.setdefault("presets", []).append(dict(default))
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
