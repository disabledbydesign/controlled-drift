#!/usr/bin/env python3
"""Deterministic resolution of a Focus Period. Pure functions — no Anytype writes.

The Focus Period holds the short-term time layer + overrides June authors. Python
resolves every calendar FACT here (is today off, is today in the availability window,
which projects are foreground). The situated MEANING (intent, availability_note) is
carried as free text for the LLM to read — never flattened into a fact. See
docs/focus_configuration_addendum.md.

The type key is 'focus_period' (bare, like 'task') — Anytype generated it; verified live
2026-07-02. NOT 'gsdo_focus_period' — a wrong constant here would silently filter out every
period, so it is confirmed against the live space, not guessed.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

FOCUS_PERIOD_TYPE_KEY = "focus_period"
_DAY_OFF_DEFAULTS = {"weekly_off": ["Sat", "Sun"]}
_WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# --- reading Anytype property values by display name -------------------------

def _by_name(obj):
    return {p.get("name"): p for p in obj.get("properties", [])}


def _date(props, name):
    p = props.get(name) or {}
    v = p.get("date")
    if not v:
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def _text(props, name):
    p = props.get(name) or {}
    return p.get("text") or ""


def _parse_date_list(props, name):
    """A small structured list of ISO dates from a text field. Deterministic (not NL):
    accepts a JSON array OR a comma-separated list; keeps only well-formed ISO dates.
    Returns (dates, had_error) — had_error surfaces a malformed value to June (never silent)."""
    raw = _text(props, name).strip()
    if not raw:
        return [], False
    values = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            values = [str(x).strip() for x in parsed]
    except (json.JSONDecodeError, TypeError):
        values = None
    if values is None:
        values = [tok.strip() for tok in raw.split(",")]
    out, had_error = [], False
    for v in values:
        if not v:
            continue
        try:
            dt.date.fromisoformat(v[:10])
            out.append(v[:10])
        except ValueError:
            had_error = True
    return out, had_error


def _objects_pairs(props, name):
    """Return [(id, name-or-None), ...] for an objects relation — KEEP the id (rename-safe).
    Anytype returns this relation as a list of id STRINGS on read-back (verified live
    2026-07-02); other shapes may give dicts. Handle both. The name is resolved from the
    live projects list later (the load path), since the string-id form carries no name."""
    p = props.get(name) or {}
    objs = p.get("objects") or []
    out = []
    for o in objs:
        if isinstance(o, dict) and o.get("id"):
            out.append((o["id"], o.get("name")))
        elif isinstance(o, str) and o:
            out.append((o, None))
    return out


def parse_focus_period(obj):
    props = _by_name(obj)
    sel = (props.get("Output format") or {}).get("select") or {}
    days_off, off_err = _parse_date_list(props, "Days off")
    days_on, on_err = _parse_date_list(props, "Days on")
    return {
        "id": obj.get("id"),
        "name": obj.get("name"),
        "start": _date(props, "Period start"),
        "end": _date(props, "Period end"),
        "intent": _text(props, "Intent"),
        "availability_start": _date(props, "Availability start"),
        "availability_end": _date(props, "Availability end"),
        "availability_note": _text(props, "Availability note"),
        "days_off": days_off,
        "days_on": days_on,
        "days_off_error": off_err or on_err,   # surface a bad list to June, never silent
        "output_format": (sel.get("name") if isinstance(sel, dict) else sel) or "Auto",
        "workday_start": _text(props, "Workday start") or None,
        "workday_end": _text(props, "Workday end") or None,
        # id/name pairs — the load path resolves ids -> current names against live projects
        "foreground_pairs": _objects_pairs(props, "Foreground projects"),
        "paused_pairs": _objects_pairs(props, "Paused projects"),
    }


def parse_hhmm(s, default=(18, 0)):
    """Parse 'HH:MM' -> (hour, minute). Used for the Workday-start / Workday-end overrides.

    Returns `default` on anything unparseable rather than raising: a typo in one clock field
    should cost that field's override, not the whole day's plan. The default is a parameter
    because the two bounds fall back to different times — end to 18:00, start to 10:00 — and a
    start silently falling back to 18:00 would produce an empty day.
    """
    try:
        h, m = str(s).strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
        return default
    except (AttributeError, ValueError):
        return default


# --- loading the active period + resolving calendar facts -------------------

def load_active_focus_period(objects, today=None):
    """The Focus Period whose [start, end] contains today (inclusive), else None.
    If several match, the one with the latest start wins (deterministic tiebreak)."""
    today = today or dt.date.today()
    candidates = []
    for obj in objects:
        t = obj.get("type")
        tkey = t.get("key") if isinstance(t, dict) else t
        if tkey != FOCUS_PERIOD_TYPE_KEY:
            continue
        p = parse_focus_period(obj)
        if p["start"] and p["end"] and p["start"] <= today <= p["end"]:
            candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p["start"])


def load_day_off_defaults():
    """The global weekly day-off default from settings.json; ['Sat','Sun'] if absent/malformed."""
    try:
        with open(cd_paths.config_file("settings.json")) as f:
            data = json.load(f)
        wk = data.get("weekly_off")
        return wk if isinstance(wk, list) and wk else list(_DAY_OFF_DEFAULTS["weekly_off"])
    except (FileNotFoundError, json.JSONDecodeError):
        return list(_DAY_OFF_DEFAULTS["weekly_off"])


def is_day_off(period, weekly_off, today):
    """Precedence: an explicit days_on date forces a WORK day; an explicit days_off date
    forces OFF; otherwise fall back to the weekly default. A None period = weekly default only."""
    iso = today.isoformat()
    if period:
        if iso in (period.get("days_on") or []):
            return False
        if iso in (period.get("days_off") or []):
            return True
    return _WEEKDAY_ABBR[today.weekday()] in (weekly_off or [])


def in_availability_window(period, today):
    if not period:
        return False
    s, e = period.get("availability_start"), period.get("availability_end")
    return bool(s and e and s <= today <= e)


def resolve_output_shape(period, in_window):
    """'clock' or 'priority', from STRUCTURED inputs only (no NL scanning). Explicit
    Output format wins; on Auto (or no period), priority iff in an availability window.
    The capacity nuance is the model's to read from free text, not Python's to scan."""
    fmt = (period or {}).get("output_format", "Auto")
    if fmt == "Priority list":
        return "priority"
    if fmt == "Clock schedule":
        return "clock"
    return "priority" if in_window else "clock"
