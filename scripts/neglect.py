#!/usr/bin/env python3
"""Neglect-resurfacing: active items not surfaced in N days. Makes the daily plan's
'still here, not today' reassurance HONEST (§9 item 6) — re-surfacing must be real."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call

def find_neglected(items, now, days=3):
    """Pure. items: list of {"last_surfaced": datetime|None, ...}. Returns the neglected ones."""
    cutoff = now - dt.timedelta(days=days)
    out = []
    for it in items:
        ls = it.get("last_surfaced")
        if ls is None or ls < cutoff:
            out.append(it)
    return out

# Only these object types are surfaceable work (plan note 1: active Tasks + Projects).
# Without this filter, query_neglected would read every page/note in the space and
# report all of them (no last_surfaced) as neglected.
SURFACEABLE_TYPE_KEYS = {"task", "gsdo_project"}

def _parse_date(raw):
    """Anytype serializes dates as ISO-8601 with a trailing 'Z' (e.g. '2026-06-15T16:39:41Z')
    — confirmed empirically against the live API. fromisoformat yields a tz-AWARE datetime,
    which cannot be compared against a naive datetime.now(); drop the tz so day-granularity
    neglect compares cleanly (the UTC/local offset is immaterial at a multi-day window)."""
    if not raw:
        return None
    s = raw.replace("Z", "+00:00") if isinstance(raw, str) and raw.endswith("Z") else raw
    d = dt.datetime.fromisoformat(s)
    return d.replace(tzinfo=None) if d.tzinfo is not None else d

def query_neglected(days=3, now=None):
    """Live wrapper: read active Tasks + Projects from Anytype, return the neglected ones.
    Reads the 'GSDO Last surfaced' (date) property; None when never surfaced.
    NOTE: limit=200 (no pagination yet) — fine for v1; add pagination before wiring into
    the daily-plan pipeline if the space exceeds ~200 objects."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    surfaced = g.find_property("Last surfaced")
    if surfaced is None:
        raise RuntimeError("query_neglected: 'Last surfaced' property not found "
                           "(run build_task.py first) — refusing to report all items as neglected")
    surfaced_key = surfaced.get("key")
    data = call("GET", f"/spaces/{sid}/objects?limit=200")[1].get("data", [])
    items = []
    for o in data:
        t = o.get("type")
        tkey = t.get("key") if isinstance(t, dict) else t
        if tkey not in SURFACEABLE_TYPE_KEYS:
            continue
        pv = {p.get("key"): p for p in o.get("properties", [])}
        ls = _parse_date(pv.get(surfaced_key, {}).get("date"))
        items.append({"name": o.get("name"), "id": o.get("id"), "last_surfaced": ls})
    return find_neglected(items, now, days=days)
