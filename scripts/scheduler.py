#!/usr/bin/env python3
"""Deterministic clock-time scheduler. The LLM proposes ORDER; this places items in TIME.
Spec §1: 'LLMs cannot reliably know the current time or do duration arithmetic.'"""
import datetime as dt

DEFAULT_DURATION_MIN = 30

def _dur(item):
    return item.get("duration_min") or DEFAULT_DURATION_MIN

def schedule(items, start):
    """items: list of {"name", "duration_min", "fixed_time": datetime|None, ...}. start: datetime.
    Fixed-time items are anchors placed at their clock time; flexible items flow around them.
    Returns each item (copied) with start_time/end_time added."""
    anchors = sorted(
        ({**it, "start_time": it["fixed_time"],
          "end_time": it["fixed_time"] + dt.timedelta(minutes=_dur(it))}
         for it in items if it.get("fixed_time") is not None),
        key=lambda a: a["start_time"])
    flexible = [it for it in items if it.get("fixed_time") is None]

    out = []
    cursor = start
    fi = 0
    for anchor in anchors:
        # place flexible items that fully fit before this anchor begins
        while fi < len(flexible):
            end = cursor + dt.timedelta(minutes=_dur(flexible[fi]))
            if end <= anchor["start_time"]:
                placed = dict(flexible[fi]); placed["start_time"] = cursor; placed["end_time"] = end
                out.append(placed); cursor = end; fi += 1
            else:
                break
        out.append(anchor)
        cursor = max(cursor, anchor["end_time"])
    # remaining flexible items after the last anchor
    while fi < len(flexible):
        end = cursor + dt.timedelta(minutes=_dur(flexible[fi]))
        placed = dict(flexible[fi]); placed["start_time"] = cursor; placed["end_time"] = end
        out.append(placed); cursor = end; fi += 1
    return out
