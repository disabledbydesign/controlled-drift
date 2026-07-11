# tests/test_period_view.py — pure-function tests for the read-only "see my week" payload.
# build_period_view takes an already-loaded period_ctx (no Anytype), so these run offline and
# leave nothing in June's real space.
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from period_view import build_period_view, _fmt_day, _fmt_range


def _ctx(period):
    # in_window is intentionally NOT set here: build_period_view computes the window from
    # (period, today) itself now, so the tests exercise the real logic instead of a hand-set bool.
    return {"period": period, "is_off": False}


def _period(**over):
    p = {
        "name": "Week of Jun 29 — recover, jobs, caregiving",
        "start": dt.date(2026, 6, 29),
        "end": dt.date(2026, 7, 6),
        "intent": "Jobs are the survival focus this stretch.",
        "availability_note": "Caregiving Sat–Mon — fragmented time, survival-first.",
        "availability_start": dt.date(2026, 7, 4),   # caregiving window Sat–Mon
        "availability_end": dt.date(2026, 7, 6),
        "foreground": ["Academic positions", "Industry positions"],
    }
    p.update(over)
    return p


# --- date formatters ---------------------------------------------------------

def test_fmt_day_compact_and_weekday():
    d = dt.date(2026, 6, 29)  # a Monday
    assert _fmt_day(d) == "Jun 29"
    assert _fmt_day(d, weekday=True) == "Mon Jun 29"


def test_fmt_range_compact_vs_weekday_cross_month():
    s, e = dt.date(2026, 6, 29), dt.date(2026, 7, 6)  # Mon -> Mon, crosses the month
    assert _fmt_range(s, e) == "Jun 29 – Jul 6"
    assert _fmt_range(s, e, weekday=True) == "Mon Jun 29 – Mon Jul 6"


def test_fmt_range_degrades_when_one_end_missing():
    assert _fmt_range(dt.date(2026, 6, 29), None) == "Jun 29"
    assert _fmt_range(None, None) == ""


# --- build_period_view -------------------------------------------------------

def test_no_active_period_is_honest_empty():
    assert build_period_view(_ctx(None), dt.date(2026, 7, 11)) == {"active": False}
    # a None/empty ctx must not blow up either
    assert build_period_view(None, dt.date(2026, 7, 11)) == {"active": False}


def test_active_period_full_payload():
    # today = Jul 4 → inside the caregiving window → availability_active True
    out = build_period_view(_ctx(_period()), dt.date(2026, 7, 4))
    assert out["active"] is True
    assert out["name"].startswith("Week of Jun 29")
    assert out["date_range"] == "Jun 29 – Jul 6"          # collapsed: no weekday
    assert out["date_range_full"] == "Mon Jun 29 – Mon Jul 6"  # expanded card: weekday
    assert out["intent"] == "Jobs are the survival focus this stretch."
    assert out["foreground"] == ["Academic positions", "Industry positions"]
    assert out["availability_note"].startswith("Caregiving")
    assert out["availability_active"] is True


def test_availability_active_computed_from_today():
    p = _period()
    # today = Jun 30 → the period is active but today is BEFORE the caregiving window
    outside = build_period_view(_ctx(p), dt.date(2026, 6, 30))
    assert outside["availability_active"] is False
    # the note itself still travels (shown in the card); only the "Now" alert is gated
    assert outside["availability_note"].startswith("Caregiving")
    # today = Jul 5 → inside the window
    inside = build_period_view(_ctx(p), dt.date(2026, 7, 5))
    assert inside["availability_active"] is True


def test_empty_intent_and_foreground_are_safe():
    out = build_period_view(_ctx(_period(intent="", foreground=[])), dt.date(2026, 7, 1))
    assert out["intent"] == ""
    assert out["foreground"] == []
    # missing keys entirely must also be tolerated (no KeyError)
    bare = build_period_view(_ctx({"start": dt.date(2026, 6, 29), "end": dt.date(2026, 7, 6)}),
                             dt.date(2026, 7, 1))
    assert bare["active"] is True
    assert bare["name"] == "" and bare["intent"] == "" and bare["foreground"] == []
    assert bare["availability_note"] == "" and bare["availability_active"] is False
