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

def query_neglected(days=3, now=None):
    """Live wrapper: read active Tasks from Anytype, return the neglected ones.
    Reads the 'GSDO Last surfaced' (date) property; None when never surfaced."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    surfaced_key = (g.find_property("GSDO Last surfaced") or {}).get("key")
    data = call("GET", f"/spaces/{sid}/objects?limit=200")[1].get("data", [])
    items = []
    for o in data:
        pv = {p.get("key"): p for p in o.get("properties", [])}
        raw = pv.get(surfaced_key, {}).get("date") if surfaced_key else None
        ls = dt.datetime.fromisoformat(raw) if raw else None
        items.append({"name": o.get("name"), "id": o.get("id"), "last_surfaced": ls})
    return find_neglected(items, now, days=days)
