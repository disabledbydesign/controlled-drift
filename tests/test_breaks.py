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
