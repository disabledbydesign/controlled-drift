import datetime as dt, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import datetime_seam as ds


def test_active_as_needed_is_due_every_day():
    item = {"interval_unit": "as_needed", "active": True}
    for d in (dt.date(2026, 7, 17), dt.date(2026, 7, 18), dt.date(2026, 8, 1)):
        due, _ = ds.today_fixed_time(item, d)
        assert due is True


def test_inactive_as_needed_is_never_due():
    due, _ = ds.today_fixed_time({"interval_unit": "as_needed", "active": False}, dt.date(2026, 7, 17))
    assert due is False
    due2, _ = ds.today_fixed_time({"interval_unit": "as_needed"}, dt.date(2026, 7, 17))  # absent = off
    assert due2 is False


def test_scheduled_recurring_ignores_active():
    # a daily task is due regardless of active; active must not perturb scheduled units
    due, _ = ds.today_fixed_time({"interval_unit": "day", "active": False}, dt.date(2026, 7, 17))
    assert due is True


def test_unset_interval_stays_off_even_if_active():
    # never-configured (no unit) is the surface-list's concern, not this feature
    due, _ = ds.today_fixed_time({"interval_unit": None, "active": True}, dt.date(2026, 7, 17))
    assert due is False
