"""Checking off an ARC STEP must stick in the cached plan, the same way every other row does.

An arc step is a real Anytype task nested inside a work block's `arc` list, each carrying its
own id (verified against June's live plan 2026-07-19). `POST /api/complete` already routes a
step id correctly: `complete_task_row` falls past is_as_needed / is_recurring / is_block_item
and lands on `task_actions.complete_task`, which writes it done in Anytype.

But `mark_item_done` then flips the CACHE, and `_iter_items` only ever walked
blocks[].items[], items[] and appointments[] — never into an item's `arc`. So the Anytype write
landed and the cached plan never changed: reopening the surface showed the step unchecked
again. That is precisely the bug `_iter_items`' own docstring describes twice already, for
fragmented days and for appointments, arriving a third time by a third route.

`grep -n "arc" scripts/plan_store.py` returned nothing at all before this change — that is how
the gap was found.

The state values mirror `model/plan.ts`'s `toggleArcStep` exactly, so the plan the server hands
back and the plan the surface optimistically drew are the same plan:
    complete   -> "done", and a following "ahead" step is promoted to "here"
    uncomplete -> "ahead"

All file paths are redirected into tmp_path, so tests never touch June's real
~/.controlled-drift/ data.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_store


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))


BLOCK_ID = "bafyproj"
STEP_1 = "bafystep1"
STEP_2 = "bafystep2"
STEP_3 = "bafystep3"


def _plan(states=("done", "here", "ahead")):
    """A priority-shaped plan holding one block with a three-step arc — the live shape."""
    return {
        "shape": "priority",
        "woven_frame": "Today.",
        "items": [
            {
                "block": True,
                "project_id": BLOCK_ID,
                "task": "Work on Life admin",
                "chunk_min": 45,
                "arc": [
                    {"text": "Back up dotfiles", "state": states[0], "id": STEP_1},
                    {"text": "Cancel food stamps", "state": states[1], "id": STEP_2},
                    {"text": "Decide about the card offer", "state": states[2], "id": STEP_3},
                ],
            }
        ],
    }


def _arc(plan):
    return [s["state"] for s in plan["items"][0]["arc"]]


def test_completing_a_step_marks_it_done_in_the_cache(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(), source="test")

    plan_store.mark_item_done(STEP_2)

    # Read from DISK, not from the return value — a reload is what this is protecting.
    assert _arc(plan_store.load_plan())[1] == "done"


def test_completing_the_current_step_advances_the_next_one(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(), source="test")

    plan_store.mark_item_done(STEP_2)

    # Same rule as `toggleArcStep` in the surface, so the two never render a different arc.
    assert _arc(plan_store.load_plan()) == ["done", "done", "here"]


def test_completing_a_step_does_not_advance_a_step_that_is_already_here(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(("ahead", "here", "here")), source="test")

    plan_store.mark_item_done(STEP_2)

    # Only an "ahead" step is promoted. A step already marked "here" is left alone — the live
    # plan really does carry several "here" steps at once (`plan_generate._mark_here`).
    assert _arc(plan_store.load_plan()) == ["ahead", "done", "here"]


def test_reopening_a_step_sends_it_back_to_ahead(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(("done", "done", "here")), source="test")

    plan_store.mark_item_undone(STEP_2)

    assert _arc(plan_store.load_plan()) == ["done", "ahead", "here"]


def test_completing_a_step_leaves_the_block_row_alone(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(), source="test")

    plan_store.mark_item_done(STEP_2)

    # A step is one task. The block above it must not be marked done or chunked by this —
    # `display_grain_design.md` §REVISION §B: a block returns tomorrow.
    item = plan_store.load_plan()["items"][0]
    assert item.get("done") is not True
    assert item.get("did_chunk_today") is not True


def test_a_step_id_is_not_treated_as_a_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan(), source="test")

    # `complete_task_row` dispatches on this. If a step id matched, checking a step would log a
    # work chunk against the project instead of completing her task.
    assert plan_store.is_block_item(STEP_2) is False
    assert plan_store.is_block_item(BLOCK_ID) is True


def test_marking_a_top_level_row_still_works(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan = _plan()
    plan["items"].append({"id": "bafytask", "task": "Take out the bins"})
    plan_store.save_plan(plan, source="test")

    plan_store.mark_item_done("bafytask")

    # The arc walk is an addition, not a replacement — the ordinary row path is untouched.
    assert plan_store.load_plan()["items"][1]["done"] is True
