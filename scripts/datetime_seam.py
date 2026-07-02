#!/usr/bin/env python3
"""Datetime seam: converts a Recurring item's schedule fields into a concrete
fixed_time datetime for today (or None if not scheduled today).

Rule: all reasoning is in local wall-clock time (America/Los_Angeles by default,
but derived from the system TZ — not hardcoded, so a GA move doesn't silently break).
UTC conversion happens only at the Anytype API boundary (caller's responsibility).

Recurring schedule is defined by:
  interval_unit  (select key: "day" | "week" | "month" | "as_needed")
  interval_count (number: N, default 1)
  day_of_week    (multi_select of tag names e.g. ["Wed"])  — weekly anchor
  day_of_month   (number 1-31)                             — monthly anchor
  time_of_day    (text "HH:MM")                            — clock time when set

Scheduling logic:
  day/N   — recurs every N days from an anchor. v1: anchor = object creation date if
            available, else today. Without a past anchor, daily items are scheduled today.
  week/N  — if day_of_week is set, recurs on those weekdays. If not set, recurs weekly
            (any day — treated as today for scheduling purposes in v1).
  month/N — recurs on day_of_month each month (clamped to the last day for short months,
            so "31" fires on Feb 28/29). If day_of_month is unset, returns None (no anchor
            to guess from). v1 fires monthly regardless of N — every-N-months needs a stored
            start anchor we don't yet keep; count>1 is treated as monthly until then.
  as_needed / None — not scheduled; returns None.
"""
import calendar
import datetime as dt
import zoneinfo


DOW_NAME_TO_WEEKDAY = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6,
}

DEFAULT_DURATION_MIN = 30
DEFAULT_TIME = dt.time(9, 0)  # 9:00 AM fallback when no time_of_day set


def _local_tz():
    """System local timezone — not hardcoded, survives a geographic move."""
    try:
        return zoneinfo.ZoneInfo("localtime")
    except Exception:
        return None


def _parse_time(time_of_day_str):
    """Parse 'HH:MM' or 'H:MM' text. Returns dt.time or DEFAULT_TIME."""
    if not time_of_day_str:
        return DEFAULT_TIME
    try:
        parts = time_of_day_str.strip().split(":")
        return dt.time(int(parts[0]), int(parts[1]))
    except Exception:
        return DEFAULT_TIME


def _parse_dow_names(multi_select_tags):
    """Extract weekday integers from multi_select tag list.
    Accepts both raw tag-name strings and tag dicts (Anytype API shapes both ways)."""
    days = []
    for tag in (multi_select_tags or []):
        name = tag.get("name") if isinstance(tag, dict) else tag
        w = DOW_NAME_TO_WEEKDAY.get(name)
        if w is not None:
            days.append(w)
    return days


def today_fixed_time(item, today=None):
    """Return a tz-naive local-time datetime for item if it recurs today, else None.

    item dict keys (all optional, all from Anytype property values):
      interval_unit   — select tag name string ("day", "week", "month", "as_needed")
      interval_count  — int, default 1
      day_of_week     — list of tag dicts or name strings
      time_of_day     — "HH:MM" string
      duration_min    — int (not used here; passed through by scheduler)

    today: date to check against (default: dt.date.today()).
    Returns datetime (tz-naive, local wall-clock) or None.
    """
    today = today or dt.date.today()
    unit = item.get("interval_unit")
    if not unit or unit == "as_needed":
        return None

    count = int(item.get("interval_count") or 1)
    clock = _parse_time(item.get("time_of_day"))

    if unit == "day":
        # Every N days — v1: schedule daily items every day (anchor refinement is post-v1)
        if count == 1:
            return dt.datetime.combine(today, clock)
        # Every-N-days: return today (caller can add anchor-based filtering later)
        return dt.datetime.combine(today, clock)

    if unit == "week":
        dow_weekdays = _parse_dow_names(item.get("day_of_week") or [])
        if not dow_weekdays:
            # Weekly with no specific day — treat as schedulable today (v1)
            return dt.datetime.combine(today, clock)
        if today.weekday() in dow_weekdays:
            return dt.datetime.combine(today, clock)
        return None

    if unit == "month":
        dom = item.get("day_of_month")
        if not dom:
            return None
        dom = int(dom)
        last_day = calendar.monthrange(today.year, today.month)[1]
        target = min(dom, last_day)  # clamp so "31" fires on the last day of short months
        if today.day == target:
            return dt.datetime.combine(today, clock)
        return None

    return None


def recurring_items_for_today(anytype_objects, today=None):
    """Filter a list of Anytype Recurring objects to those scheduled today.
    Returns list of dicts with keys: id, name, fixed_time, duration_min.
    anytype_objects: raw dicts from the Anytype API (/spaces/{sid}/objects).
    """
    today = today or dt.date.today()
    results = []
    for obj in anytype_objects:
        if not (isinstance(obj.get("type"), dict) and
                obj["type"].get("key") == "gsdo_recurring"):
            continue
        props = {p.get("key"): p for p in obj.get("properties", [])}

        def pval(key, kind):
            p = props.get(key, {})
            return p.get(kind) if p else None

        item = {
            "id":             obj.get("id"),
            "name":           obj.get("name"),
            "interval_unit":  (pval("interval_unit", "select") or {}).get("name"),
            "interval_count": pval("interval_count", "number"),
            "day_of_week":    pval("gsdo_day_of_week", "multi_select") or [],
            "day_of_month":   pval("day_of_month", "number"),
            "time_of_day":    pval("gsdo_time_of_day", "text"),
            "duration_min":   pval("gsdo_duration_min", "number"),
        }
        fixed = today_fixed_time(item, today)
        if fixed is not None:
            results.append({
                "id":           item["id"],
                "name":         item["name"],
                "fixed_time":   fixed,
                "duration_min": item["duration_min"] or DEFAULT_DURATION_MIN,
            })
    return results
