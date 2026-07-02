# tests/test_datetime_seam.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from datetime_seam import today_fixed_time


def test_monthly_fires_on_anchor_day():
    item = {"interval_unit": "month", "interval_count": 1, "day_of_month": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) == dt.datetime(2026, 7, 1, 9, 0)


def test_monthly_silent_on_other_days():
    item = {"interval_unit": "month", "day_of_month": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 2)) is None


def test_monthly_clamps_to_last_day_of_short_month():
    # "31" should fire on Feb 28 (2026 is not a leap year), not vanish
    item = {"interval_unit": "month", "day_of_month": 31}
    assert today_fixed_time(item, dt.date(2026, 2, 28)) == dt.datetime(2026, 2, 28, 9, 0)
    assert today_fixed_time(item, dt.date(2026, 2, 27)) is None


def test_monthly_without_anchor_returns_none():
    # no day_of_month → no anchor to guess from
    item = {"interval_unit": "month", "interval_count": 1}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) is None


def test_monthly_respects_time_of_day():
    item = {"interval_unit": "month", "day_of_month": 1, "time_of_day": "14:30"}
    assert today_fixed_time(item, dt.date(2026, 7, 1)) == dt.datetime(2026, 7, 1, 14, 30)
