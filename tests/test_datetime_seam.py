# tests/test_datetime_seam.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from datetime_seam import today_fixed_time, recurring_items_for_today


def test_monthly_fires_on_anchor_day():
    item = {"interval_unit": "month", "interval_count": 1, "day_of_month": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) == (True, None)


def test_monthly_silent_on_other_days():
    item = {"interval_unit": "month", "day_of_month": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 2)) == (False, None)


def test_monthly_clamps_to_last_day_of_short_month():
    # "31" should fire on Feb 28 (2026 is not a leap year), not vanish
    item = {"interval_unit": "month", "day_of_month": 31}
    assert today_fixed_time(item, dt.date(2026, 2, 28)) == (True, None)
    assert today_fixed_time(item, dt.date(2026, 2, 27)) == (False, None)


def test_monthly_without_anchor_returns_not_due():
    # no day_of_month → no anchor to guess from
    item = {"interval_unit": "month", "interval_count": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) == (False, None)


def test_monthly_respects_time_of_day():
    item = {"interval_unit": "month", "day_of_month": 1, "time_of_day": "14:30"}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) == (True, dt.time(14, 30))


def test_daily_due_with_no_time_of_day_carries_no_fabricated_clock():
    # 2026-07-17: no more 9am default — due today, no time preference.
    item = {"interval_unit": "day", "interval_count": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 17)) == (True, None)


def test_weekly_no_day_set_is_due_with_no_time():
    item = {"interval_unit": "week"}
    assert today_fixed_time(item, dt.date(2026, 7, 17)) == (True, None)


def test_weekly_specific_day_due_only_that_weekday():
    item = {"interval_unit": "week", "day_of_week": ["Fri"], "time_of_day": "08:00"}
    assert today_fixed_time(item, dt.date(2026, 7, 17)) == (True, dt.time(8, 0))  # a Friday
    assert today_fixed_time(item, dt.date(2026, 7, 16)) == (False, dt.time(8, 0))  # a Thursday


def test_as_needed_never_due():
    item = {"interval_unit": "as_needed", "time_of_day": "09:00"}
    assert today_fixed_time(item, dt.date(2026, 7, 17)) == (False, dt.time(9, 0))


def test_unparseable_time_of_day_is_no_time_not_a_default():
    item = {"interval_unit": "day", "time_of_day": "garbage"}
    assert today_fixed_time(item, dt.date(2026, 7, 17)) == (True, None)


# --- recurring_items_for_today: fixed_time is None for a due-but-timeless item -----------

def _obj(name, interval_unit, time_of_day=None, duration_min=None, **extra):
    props = [{"key": "interval_unit", "select": {"name": interval_unit}}]
    if time_of_day is not None:
        props.append({"key": "gsdo_time_of_day", "text": time_of_day})
    if duration_min is not None:
        props.append({"key": "gsdo_duration_min", "number": duration_min})
    for k, v in extra.items():
        props.append({"key": k, **v})
    return {"id": f"id-{name}", "name": name, "type": {"key": "gsdo_recurring"},
            "properties": props}


def test_recurring_items_for_today_untimed_chore_has_none_fixed_time():
    objs = [_obj("Do the dishes", "day", duration_min=20)]
    results = recurring_items_for_today(objs, dt.date(2026, 7, 17))
    assert len(results) == 1
    assert results[0]["fixed_time"] is None
    assert results[0]["duration_min"] == 20
    assert results[0]["name"] == "Do the dishes"


def test_recurring_items_for_today_timed_item_keeps_real_fixed_time():
    objs = [_obj("Take meds", "day", time_of_day="20:00", duration_min=5)]
    results = recurring_items_for_today(objs, dt.date(2026, 7, 17))
    assert results[0]["fixed_time"] == dt.datetime(2026, 7, 17, 20, 0)


def test_recurring_items_for_today_as_needed_excluded():
    objs = [_obj("Deep clean fridge", "as_needed")]
    assert recurring_items_for_today(objs, dt.date(2026, 7, 17)) == []


def test_recurring_items_for_today_active_as_needed_included_and_flagged():
    # Exercises the REAL property-read path (pval("active", "checkbox")) through the actual
    # Anytype-shaped object, not a hand-built item dict — proves the real key is wired, not just
    # today_fixed_time's branching logic in isolation.
    objs = [_obj("Clean the fridge", "as_needed", active={"checkbox": True})]
    results = recurring_items_for_today(objs, dt.date(2026, 7, 17))
    assert len(results) == 1
    assert results[0]["name"] == "Clean the fridge"
    assert results[0]["as_needed"] is True
