"""Break-block insertion (Strategy: regular breaks every ~2h of focused work).

Breaks are real short blocks the scheduler places — not a worded nudge — and they
only land after an extended stretch of actual work. Things that are already breaks
(lunch, walks, naps) reset the counter, so a break never piles onto them.
Pure-logic: no Anytype.
"""
import datetime as dt
import daily_plan as dp

START = dt.datetime(2026, 7, 2, 9, 0)


def _task(name, dur):
    return {"name": name, "duration_min": dur}


def _breaks(sched):
    return [it for it in sched if it.get("_break")]


def test_no_break_on_a_short_day():
    sched = dp.build_schedule([_task("A", 30), _task("B", 30)], [], START)
    assert _breaks(sched) == []


def test_break_after_two_hours_of_work():
    sched = dp.build_schedule([_task("A", 60), _task("B", 60), _task("C", 60)], [], START)
    brks = _breaks(sched)
    assert len(brks) == 1
    assert brks[0]["start_time"] == dt.datetime(2026, 7, 2, 11, 0)  # after 2h from 09:00


def test_never_ends_the_day_on_a_break():
    # exactly 2h of work, nothing after → no dangling break
    sched = dp.build_schedule([_task("A", 60), _task("B", 60)], [], START)
    assert _breaks(sched) == []


def test_break_does_not_land_on_lunch():
    lunch = {"name": "Lunch", "duration_min": 45,
             "fixed_time": dt.datetime(2026, 7, 2, 12, 0), "_default_anchor": True}
    work = [_task(f"W{i}", 30) for i in range(8)]   # 4h of work around lunch
    sched = dp.build_schedule(work, [lunch], START)
    lunch_item = next(it for it in sched if it["name"] == "Lunch")
    for b in _breaks(sched):
        gap_min = (b["start_time"] - lunch_item["end_time"]).total_seconds() / 60
        # lunch resets the counter → no break in the ~2h right after lunch
        assert not (0 <= gap_min < 90), f"break too soon after lunch: {gap_min} min"


def test_a_walk_counts_as_a_break_and_resets():
    # 2h of work then a walk → the walk serves as the break; no separate break stacked on it
    items = [_task("A", 60), _task("B", 60),
             {"name": "Go on a walk", "duration_min": 30},
             _task("C", 60), _task("D", 60)]
    sched = dp.build_schedule(items, [], START)
    walk = next(it for it in sched if "walk" in it["name"].lower())
    for b in _breaks(sched):
        gap_min = (b["start_time"] - walk["end_time"]).total_seconds() / 60
        assert not (0 <= gap_min < 90)


def test_is_rest_item():
    assert dp._is_rest_item({"name": "Lunch", "_default_anchor": True})
    assert dp._is_rest_item({"name": "Go on a long walk"})
    assert dp._is_rest_item({"name": "Break — stand", "_break": True})
    assert not dp._is_rest_item({"name": "Draft cover letter"})


def test_break_block_shape():
    sched = dp.build_schedule([_task("A", 90), _task("B", 60), _task("C", 60)], [], START)
    brk = next(it for it in sched if it.get("_break"))
    assert brk["duration_min"] == dp.BREAK_DURATION_MIN
    assert "break" in brk["name"].lower()


# --- errand runs: a break never splits two adjacent leaving-house items (2026-07-17) ---------
# REGRESSION, live-caught 2026-07-16T12:20:03: "Mail contestation..." and "Print out (at
# Kinkos)..." were already adjacent in the LLM's own composed order, but a "stand, stretch,
# move" break got wedged between them purely because accumulated work crossed BREAK_WORK_MIN
# right at that point -- _compute_break_anchors had no notion the two neighbors were the same
# errand run. Mirrors the real incident's shape: two Involves-leaving-house items straddling
# the 120-minute threshold, more work after so it's not an end-of-day edge case.

def _errand(name, dur):
    return {"name": name, "duration_min": dur, "access": ["Involves-leaving-house"]}


def test_shares_batch_tag():
    assert dp._shares_batch_tag(_errand("A", 10), _errand("B", 10)) is True
    assert dp._shares_batch_tag(_errand("A", 10), _task("B", 10)) is False
    assert dp._shares_batch_tag(_task("A", 10), _task("B", 10)) is False


def test_break_never_splits_two_adjacent_errands():
    items = [_task("Warm up work", 90),      # cum 90
             _errand("Errand 1", 30),        # cum 120 -- crosses BREAK_WORK_MIN right here
             _errand("Errand 2", 20),        # adjacent errand -- must not be split off
             _task("Wind down work", 30)]    # more work after, so a break isn't end-of-day
    sched = dp.build_schedule(items, [], START)
    e1 = next(it for it in sched if it["name"] == "Errand 1")
    e2 = next(it for it in sched if it["name"] == "Errand 2")
    assert e1["end_time"] == e2["start_time"], "the two errands must stay adjacent"
    assert not any(b["start_time"] == e1["end_time"] for b in _breaks(sched)), \
        "a break must not land between the two errands"
    # the deferred stretch still counts -- a break still lands, just at the cluster's far edge
    assert len(_breaks(sched)) == 1
