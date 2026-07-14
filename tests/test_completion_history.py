"""The plan/completion-history foundation (2026-07-13): a durable record of what was on each
day's plan (plan_snapshot_log, already existed) joined with what June actually finished
(completion_log, new). This is the record rollover, the neglect-repurpose, and completion-based
learning all read. Also pins the fragmented-day mark-done fix that shares the same code path."""
import datetime as dt
import plan_snapshot_log as psl
import completion_log as cl
import plan_store


def test_iter_items_covers_both_plan_shapes():
    # The fix: a clock day keeps rows in blocks[]; a fragmented day in a flat items[]. Iterating
    # only blocks[] was the mark-done-doesn't-stick bug.
    from plan_store import _iter_items
    clock = {"blocks": [{"items": [{"id": "a"}, {"id": "b"}]}]}
    frag = {"items": [{"id": "c"}, {"id": "d"}]}
    both = {"blocks": [{"items": [{"id": "a"}]}], "items": [{"id": "c"}]}
    assert {it["id"] for it in _iter_items(clock)} == {"a", "b"}
    assert {it["id"] for it in _iter_items(frag)} == {"c", "d"}
    assert {it["id"] for it in _iter_items(both)} == {"a", "c"}


def test_mark_done_sticks_on_fragmented_priority_day(cd_sandbox):
    # The live bug: on a fragmented (priority-shape) day the checkoff wrote to Anytype but never
    # reached the cache, so reopening the overlay showed the task unchecked again.
    plan = {"shape": "priority", "header": "when you get time", "still_here": [],
            "items": [{"id": "p1", "task": "Frag task", "done": False}]}
    plan_store.save_plan(plan, source="test")
    plan_store.mark_item_done("p1")
    assert next(it for it in plan_store.load_plan()["items"] if it["id"] == "p1")["done"] is True
    plan_store.mark_item_undone("p1")
    assert next(it for it in plan_store.load_plan()["items"] if it["id"] == "p1")["done"] is False


def test_completion_log_nets_done_then_undone(cd_sandbox):
    cl.log_completion("t1", "Task one")
    cl.log_completion("t2", "Task two")
    cl.log_uncompletion("t1")                        # mis-tap: t1 undone the same day
    assert cl.completed_ids_on(dt.date.today()) == {"t2"}     # t1 netted out, t2 stands


def test_undone_on_uses_the_latest_snapshot_of_the_day(cd_sandbox):
    # A renegotiation writes a fresh snapshot for the same day; undone_on must read the LATEST one,
    # so a task June dropped in the renegotiated plan is no longer a rollover candidate tomorrow.
    today = dt.date.today()
    psl.log_plan_snapshot({"blocks": [{"items": [{"id": "x", "task": "X"}, {"id": "y", "task": "Y"}]}]},
                          source="morning")
    psl.log_plan_snapshot({"blocks": [{"items": [{"id": "x", "task": "X"}]}]}, source="freetext")  # Y dropped
    undone = psl.undone_on(today)
    assert {u["id"] for u in undone} == {"x"}    # Y is gone from the latest plan → not carried


def test_undone_on_joins_planned_and_completed(cd_sandbox):
    plan = {"shape": "clock", "blocks": [{"label": "M", "items": [
        {"id": "u1", "task": "Undone task"},
        {"id": "d1", "task": "Done task"},
        {"task": "Lunch"},                            # id-less anchor — not a real task
    ]}]}
    psl.log_plan_snapshot(plan, source="test")        # stamps today
    cl.log_completion("d1", "Done task")             # completed today
    undone = psl.undone_on(dt.date.today())
    assert {u["id"] for u in undone} == {"u1"}        # planned + not done; d1 done; Lunch not a task
    assert undone[0]["name"] == "Undone task"
