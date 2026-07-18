#!/usr/bin/env python3
"""Datetime seam: decides whether a Recurring item is due today, and separately, whether
it has a real clock time.

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
            so "31" fires on Feb 28/29). If day_of_month is unset, not due (no anchor to
            guess from). v1 fires monthly regardless of N — every-N-months needs a stored
            start anchor we don't yet keep; count>1 is treated as monthly until then.
  as_needed / None — not scheduled automatically; browsable on the Map instead
            (orient_map.py lists every Recurring under its linked project regardless
            of schedule — an as-needed item is there for June to pull up, not on autopilot).

DUE vs. TIMED (2026-07-17 — see today_fixed_time's docstring): whether an item recurs today
and whether it has a real clock time are independent questions. A recurring item due today
with no time_of_day set has no clock preference at all — it is NOT given a fabricated one.
`recurring_items_for_today` returns it with `fixed_time: None`; the caller
(daily_plan.load_active_items) routes a None-fixed_time item into the same composable task
pool the LLM places freely, instead of the fixed-time anchor pipeline.
"""
import calendar
import datetime as dt
import zoneinfo


DOW_NAME_TO_WEEKDAY = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6,
}

DEFAULT_DURATION_MIN = 30


def _local_tz():
    """System local timezone — not hardcoded, survives a geographic move."""
    try:
        return zoneinfo.ZoneInfo("localtime")
    except Exception:
        return None


def _parse_time(time_of_day_str):
    """Parse 'HH:MM' or 'H:MM' text. Returns dt.time, or None if unset/unparseable.

    No fallback default (changed 2026-07-17): a recurring item with no stated time has no
    clock preference — it should never be handed a fabricated one. The earlier 9am default
    made every timeless chore (dishes, kitchen, toilet) a fake anchor that was immediately
    "overdue" on generation (plans rarely start before 10am) and got demoted + shoved behind
    every real task the LLM had already placed — structurally losing the scheduling race
    every day (June, 2026-07-17: "the clock time is getting in the way"). The LLM is meant
    to place a no-time chore wherever it fits, same as any other task; see
    recurring_items_for_today / daily_plan.load_active_items for the split."""
    if not time_of_day_str:
        return None
    try:
        parts = time_of_day_str.strip().split(":")
        return dt.time(int(parts[0]), int(parts[1]))
    except Exception:
        return None


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
    """Return (due, clock) for item today.

      due   — True if the item recurs today, from interval math ALONE — never touches
              whether a clock time is set. An every-day chore is due every day whether or
              not it has a time_of_day.
      clock — dt.time if item has an explicit, parseable time_of_day; else None. A None
              clock is not "unscheduled" — it means "due today, no time preference," which
              the caller folds into the composable task pool instead of the anchor pipeline
              (daily_plan.load_active_items). Only a genuinely time-bound recurring item
              (a real time_of_day) stays a true clock anchor.

    item dict keys (all optional, all from Anytype property values):
      interval_unit   — select tag name string ("day", "week", "month", "as_needed")
      interval_count  — int, default 1
      day_of_week     — list of tag dicts or name strings
      time_of_day     — "HH:MM" string
      duration_min    — int (not used here; passed through by scheduler)
      active          — bool; only consumed when interval_unit == "as_needed" (surfaces every
                        day while True; ignored by every scheduled unit)

    today: date to check against (default: dt.date.today()).
    """
    today = today or dt.date.today()
    unit = item.get("interval_unit")
    clock = _parse_time(item.get("time_of_day"))
    if unit == "as_needed":
        # An as-needed task is off until asked-for. When Active, it is "due" every day until June
        # completes it (which writes Active=false) — it keeps resurfacing. (June, 2026-07-17.)
        return bool(item.get("active")), clock
    if not unit:
        return False, clock   # never-configured stays off — not this feature (the surface list's)

    if unit == "day":
        # Every N days — v1: schedule daily items every day (anchor refinement is post-v1)
        return True, clock

    if unit == "week":
        dow_weekdays = _parse_dow_names(item.get("day_of_week") or [])
        if not dow_weekdays:
            # Weekly with no specific day — treat as schedulable today (v1)
            return True, clock
        return (today.weekday() in dow_weekdays), clock

    if unit == "month":
        dom = item.get("day_of_month")
        if not dom:
            return False, clock
        dom = int(dom)
        last_day = calendar.monthrange(today.year, today.month)[1]
        target = min(dom, last_day)  # clamp so "31" fires on the last day of short months
        return (today.day == target), clock

    return False, clock


def recurring_items_for_today(anytype_objects, today=None):
    """Filter a list of Anytype Recurring objects to those due today.
    Returns list of dicts with keys: id, name, fixed_time (datetime, or None if no
    time_of_day is set — see today_fixed_time), duration_min.
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
            "active":         bool(pval("active", "checkbox")),   # real key confirmed in Task 1 (bare, not gsdo_active)
        }
        due, clock = today_fixed_time(item, today)
        if not due:
            continue
        results.append({
            "id":           item["id"],
            "name":         item["name"],
            "fixed_time":   dt.datetime.combine(today, clock) if clock else None,
            "duration_min": item["duration_min"] or DEFAULT_DURATION_MIN,
            "as_needed":    item["interval_unit"] == "as_needed",   # routes completion in Task 4
        })
    return results
