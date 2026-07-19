"""The stored duration REACHES the plan row — on both plan shapes, for task and recurring rows.

Why this file exists: tests/test_task_duration.py asserts only the WRITE. A field can be written
correctly to Anytype and never read back onto the row June actually sees, and a write-only suite
cannot see that. Live symptom (2026-07-19): "Do the dishes" carries gsdo_duration_min = 20,
GET /api/tree returns 20, and GET /api/plan returned the same task with no duration field at all —
so the Today tab offered "set duration" for a duration she had already given it. 158 objects in
her space carry a duration; none reached the Today tab.

Every assertion here is on the READ side, and POSITIVE — it names the value that must arrive.

Two things these tests deliberately hold apart:

  * A BLOCK row's chunk length ("how long I work on this project in a sitting") and a TASK row's
    own duration ("how long this specific thing takes") are different facts about different
    things. They must not collapse into one field.
  * An ABSENT duration must arrive absent. Nothing here may invent a number for a task that has
    none stored — a confident wrong number is worse than a blank, because the UI cannot then
    offer an honest unset state. Block rows survive on both shapes and always did; that is why
    this defect outlived several reviews, so the task and recurring rows are checked explicitly.
"""
import datetime as dt

import pytest

import daily_plan as dp
import plan_generate as pg


START = dt.datetime(2026, 7, 19, 10, 0)
END = dt.datetime(2026, 7, 19, 18, 0)


@pytest.fixture(autouse=True)
def _no_real_chunk_log(monkeypatch):
    """Never read June's real chunk_log data file from a test."""
    monkeypatch.setattr(dp.chunk_log, "chunked_today_ids", lambda *a, **k: set())


def _clock_plan(items):
    return {"shape": "clock", "woven_frame": "f", "still_here": [],
            "blocks": [{"label": "Morning", "time": "10:00 – 12:00", "framing": "fresh",
                        "items": list(items)}]}


def _priority_plan(items):
    return {"shape": "priority", "woven_frame": "f", "still_here": [], "items": list(items)}


def _rows(plan):
    """Every rendered row, both shapes."""
    if plan.get("blocks"):
        return [it for b in plan["blocks"] for it in b["items"]]
    return list(plan.get("items", []))


def _row_named(plan, name):
    for it in _rows(plan):
        if (it.get("task") or it.get("name")) == name:
            return it
    raise AssertionError(f"no row named {name!r} in {[r.get('task') or r.get('name') for r in _rows(plan)]}")


def _resolve_priority(plan, tasks):
    """Run the priority-shape post-LLM path exactly as generate_plan/reorder run it."""
    ref_map = {f"t{i}": t["id"] for i, t in enumerate(tasks)}
    pg._resolve_ids(plan, ref_map, tasks, all_tasks=tasks)
    pg._retime_clock_plan(plan, tasks, all_anchors=[], start_time=START, end_time=END)
    plan["items"] = pg._group_block_project_items(plan.get("items", []))
    return plan


# --------------------------------------------------------------------------
# Clock shape (blocks_from_scheduled is the row assembler)
# --------------------------------------------------------------------------

def test_clock_task_row_carries_the_stored_duration():
    tasks = [{"id": "a", "name": "Do the dishes", "duration_min": 20}]
    plan = _clock_plan([{"time": "x", "task": "Do the dishes", "project": None,
                         "interstitial": False, "id": "a"}])
    pg._retime_clock_plan(plan, tasks, all_anchors=[], start_time=START, end_time=END)
    assert _row_named(plan, "Do the dishes")["duration_min"] == 20


def test_clock_recurring_row_carries_the_stored_duration():
    # A due-but-timeless Recurring chore composed by the model like any task.
    tasks = [{"id": "r1", "name": "Take out recycling", "duration_min": 15,
              "is_recurring": True}]
    plan = _clock_plan([{"time": "x", "task": "Take out recycling", "project": None,
                         "interstitial": False, "id": "r1"}])
    pg._resolve_ids(plan, {"t0": "r1"}, tasks, all_tasks=tasks)
    pg._retime_clock_plan(plan, tasks, all_anchors=[], start_time=START, end_time=END)
    row = _row_named(plan, "Take out recycling")
    assert row["recurring"] is True          # it really is the recurring row, not a plain task
    assert row["duration_min"] == 15


def test_clock_recurring_ANCHOR_row_carries_the_stored_duration():
    # The other recurring row kind: a fixed-time anchor Python re-adds itself.
    anchor = {"id": "r2", "name": "Feed the cat", "duration_min": 10,
              "fixed_time": dt.datetime(2026, 7, 19, 11, 0)}
    scheduled = dp.build_schedule([], [anchor], start_time=START, end_time=END)
    blocks = dp.blocks_from_scheduled(scheduled)
    row = [it for b in blocks for it in b["items"] if it["task"] == "Feed the cat"][0]
    assert row["recurring"] is True
    assert row["duration_min"] == 10


def test_clock_row_with_no_stored_duration_arrives_absent():
    # Nothing stored -> the row must say so honestly, so the UI can show an unset state.
    # A cold-start default presented as a value June chose is the defect, not the fix.
    tasks = [{"id": "a", "name": "Call the pharmacy", "duration_min": None}]
    plan = _clock_plan([{"time": "x", "task": "Call the pharmacy", "project": None,
                         "interstitial": False, "id": "a"}])
    pg._retime_clock_plan(plan, tasks, all_anchors=[], start_time=START, end_time=END)
    assert _row_named(plan, "Call the pharmacy").get("duration_min") is None


def test_clock_meal_and_break_rows_carry_no_duration():
    # Meals and breaks are Python-owned defaults, not durations June set on an object. They have
    # no id and no edit affordance; surfacing their default length as a stored duration would be
    # the same fabrication this work removes.
    meal = {"id": None, "name": "Lunch", "duration_min": 45,
            "fixed_time": dt.datetime(2026, 7, 19, 12, 0), "_default_anchor": True}
    scheduled = dp.build_schedule([], [meal], start_time=START, end_time=END)
    blocks = dp.blocks_from_scheduled(scheduled)
    row = [it for b in blocks for it in b["items"] if it["task"] == "Lunch"][0]
    assert row.get("duration_min") is None


def test_clock_block_chunk_and_task_duration_stay_distinct():
    # Two rows, two different facts, in one day: a block says "how long I work on this project in
    # a sitting" (chunk_min), a plain task says "how long this specific thing takes"
    # (duration_min). Neither may take the other's number.
    tasks = [{"id": "a", "name": "Draft the intro", "duration_min": 25},
             {"id": "b", "name": "Do the dishes", "duration_min": 20}]
    plan = _clock_plan([
        {"time": "x", "task": "Draft the intro", "project": "Manuscript",
         "interstitial": False, "id": "a",
         "block_project": True, "project_id": "p1", "arc": [], "chunk_min": 90},
        {"time": "x", "task": "Do the dishes", "project": None,
         "interstitial": False, "id": "b"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[], start_time=START, end_time=END)
    # The block-work task folds under one "Work on Manuscript" block carrying the chunk length.
    block = _row_named(plan, "Work on Manuscript")
    assert block["chunk_min"] == 90
    assert block["absorbed_ids"] == ["a"]        # the real task is still resolvable underneath
    # The plain task keeps its own stored duration, untouched by the block beside it.
    assert _row_named(plan, "Do the dishes")["duration_min"] == 20


# --------------------------------------------------------------------------
# Priority shape (flat items; _retime_clock_plan is a no-op here)
# --------------------------------------------------------------------------

def test_priority_task_row_carries_the_stored_duration():
    tasks = [{"id": "a", "name": "Do the dishes", "duration_min": 20}]
    plan = _priority_plan([{"task": "Do the dishes", "project": None,
                            "interstitial": False, "ref": "t0"}])
    _resolve_priority(plan, tasks)
    assert _row_named(plan, "Do the dishes")["duration_min"] == 20


def test_priority_recurring_row_carries_the_stored_duration():
    tasks = [{"id": "r1", "name": "Take out recycling", "duration_min": 15,
              "is_recurring": True}]
    plan = _priority_plan([{"task": "Take out recycling", "project": None,
                            "interstitial": False, "ref": "t0"}])
    _resolve_priority(plan, tasks)
    row = _row_named(plan, "Take out recycling")
    assert row["recurring"] is True
    assert row["duration_min"] == 15


def test_priority_row_with_no_stored_duration_arrives_absent():
    tasks = [{"id": "a", "name": "Call the pharmacy", "duration_min": None}]
    plan = _priority_plan([{"task": "Call the pharmacy", "project": None,
                            "interstitial": False, "ref": "t0"}])
    _resolve_priority(plan, tasks)
    assert _row_named(plan, "Call the pharmacy").get("duration_min") is None


def test_priority_block_chunk_and_task_duration_stay_distinct():
    tasks = [{"id": "a", "name": "Draft the intro", "duration_min": 25,
              "linked_projects": ["Manuscript"],
              "block_project": True, "project_id": "p1", "arc": [], "chunk_min": 90}]
    plan = _priority_plan([{"task": "Draft the intro", "project": "Manuscript",
                            "interstitial": False, "ref": "t0"}])
    _resolve_priority(plan, tasks)
    block = _row_named(plan, "Work on Manuscript")
    assert block["chunk_min"] == 90
    assert block["duration_min"] == 90        # the chunk, allocated once — not the task's 25
