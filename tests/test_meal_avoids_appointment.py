"""A meal is a SOFT anchor — a suggestion — and must yield to a HARD fixed-time commitment.

Live bug, 2026-07-20: a 13:29 refresh ceils the day's start to 13:30, so the learned-lunch rule
(start + 30 min) computed lunch at 14:00 — exactly a real 14:00 appointment. The scheduler places
every anchor at its own fixed_time with no anchor-vs-anchor check, so the two overlapped and her
plan showed "Lunch 14:00–14:30" sitting on top of "SF LGBT Center Drop-In 14:00–15:00".

An appointment is the fixed thing; the meal is the movable one. The meal must step off it.
Pure-logic: no Anytype.
"""
import datetime as dt
import daily_plan as dp


def _appt(hour, minute=0, dur=60, name="SF LGBT Center Drop-In"):
    return {"id": "APT", "name": name,
            "fixed_time": dt.datetime(2026, 7, 20, hour, minute), "duration_min": dur}


def test_lunch_does_not_land_on_an_appointment():
    # Start 13:30 -> the learned-lunch rule wants 14:00, which is the appointment. It must move.
    start = dt.datetime(2026, 7, 20, 13, 30)
    meals = dp.default_meal_anchors([_appt(14, 0, 60)], start)
    assert len(meals) == 1
    lunch = meals[0]
    lunch_start = lunch["fixed_time"]
    lunch_end = lunch_start + dt.timedelta(minutes=lunch["duration_min"])
    appt_start = dt.datetime(2026, 7, 20, 14, 0)
    appt_end = dt.datetime(2026, 7, 20, 15, 0)
    # No overlap: lunch ends by the appointment start, or begins at/after its end.
    assert lunch_end <= appt_start or lunch_start >= appt_end, \
        f"lunch {lunch_start:%H:%M}-{lunch_end:%H:%M} overlaps appt {appt_start:%H:%M}-{appt_end:%H:%M}"


def test_lunch_pushed_past_the_appointment_lands_at_its_end():
    # The concrete expectation: lunch yields to just after the commitment.
    start = dt.datetime(2026, 7, 20, 13, 30)
    meals = dp.default_meal_anchors([_appt(14, 0, 60)], start)
    assert meals[0]["fixed_time"] == dt.datetime(2026, 7, 20, 15, 0)


def test_lunch_is_untouched_when_it_does_not_collide():
    # Appointment at 10:00; a 13:30 start still puts lunch at 14:00, well clear of it.
    start = dt.datetime(2026, 7, 20, 13, 30)
    meals = dp.default_meal_anchors([_appt(10, 0, 60)], start)
    assert meals[0]["fixed_time"] == dt.datetime(2026, 7, 20, 14, 0)


def test_no_appointment_leaves_the_ordinary_lunch_time():
    start = dt.datetime(2026, 7, 20, 13, 30)
    meals = dp.default_meal_anchors([], start)
    assert meals[0]["fixed_time"] == dt.datetime(2026, 7, 20, 14, 0)
