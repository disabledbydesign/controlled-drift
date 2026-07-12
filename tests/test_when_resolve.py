# tests/test_when_resolve.py — pure logic, no network.
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from when_resolve import resolve_when, is_scheduled_for_today_or_earlier as ok

MON = dt.date(2026, 7, 13)  # a Monday


def test_today():        assert resolve_when("today", MON) == (MON.isoformat(), True, False)
def test_tomorrow():     assert resolve_when("tomorrow", MON) == ("2026-07-14", False, False)
def test_next_weekday(): assert resolve_when("thursday", MON) == ("2026-07-16", False, False)
def test_same_weekday_is_next_week(): assert resolve_when("monday", MON) == ("2026-07-20", False, False)
def test_iso_passthrough():  assert resolve_when("2026-08-01", MON) == ("2026-08-01", False, False)
def test_someday_parked(): assert resolve_when("someday", MON) == (None, False, True)
def test_blank_none():   assert resolve_when("", MON) == (None, False, False) and resolve_when(None, MON) == (None, False, False)
def test_unknown_none(): assert resolve_when("whenever the vibe hits", MON) == (None, False, False)


# eligibility predicate (imported by the selection thread):
def test_undated_eligible():  assert ok(None, MON) is True and ok("", MON) is True
def test_today_eligible():    assert ok("2026-07-13", MON) is True
def test_overdue_eligible():  assert ok("2026-07-01", MON) is True
def test_future_excluded():   assert ok("2026-07-16", MON) is False
def test_datetime_tz_form():  assert ok("2026-07-16T00:00:00Z", MON) is False and ok("2026-07-13T00:00:00Z", MON) is True
