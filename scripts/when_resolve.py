#!/usr/bin/env python3
"""Anchor a free-text 'when' (from the capture LLM) to a concrete date, and answer whether a
scheduled date makes a task eligible for today. Python owns the date so 'Thursday' becomes a real
day and can't drift. The eligibility predicate is imported by the selection thread (it owns where
it's called — load_active_items); this module just provides the pure rule."""
import datetime as dt
from datetime_seam import DOW_NAME_TO_WEEKDAY  # {"Mon":0,...,"Sun":6}

_PARKED = {"someday", "eventually", "later", "whenever", "no rush", "sometime", "no date"}
_DOW = {"monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu",
        "friday": "Fri", "saturday": "Sat", "sunday": "Sun"}


def _as_date(v):
    if not v:
        return None
    s = str(v).strip()
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        try:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def resolve_when(when_text, today):
    """(scheduled_iso|None, is_today, is_parked). Blank/unknown -> (None, False, False)."""
    if not when_text:
        return (None, False, False)
    w = str(when_text).strip().lower()
    if w in _PARKED:                       return (None, False, True)
    if w in ("today", "now", "tonight"):   return (today.isoformat(), True, False)
    if w == "tomorrow":                    return ((today + dt.timedelta(days=1)).isoformat(), False, False)
    d = _as_date(w)
    if d is not None:                      return (d.isoformat(), d == today, False)
    if w in _DOW:
        delta = (DOW_NAME_TO_WEEKDAY[_DOW[w]] - today.weekday()) % 7 or 7
        return ((today + dt.timedelta(days=delta)).isoformat(), False, False)
    return (None, False, False)


def is_scheduled_for_today_or_earlier(scheduled_iso, today=None):
    """True if a task is eligible for today's plan by its Scheduled date: undated or dated
    today-or-earlier. A strictly future date returns False (held off today). Selection-thread import.
    Tolerant of Anytype's datetime/tz round-trip form (e.g. '2026-07-16T00:00:00Z')."""
    today = today or dt.date.today()
    d = _as_date(scheduled_iso)
    return True if d is None else d <= today
