#!/usr/bin/env python3
"""Read-only render of the active Focus Period for the overlay's Today tab (Phase 6, Task 2/6A).

June's stated keystone: SEE the focus configuration she authored, folded into Today. This is a
*rendering*, not a stored copy (addendum §"How June sees and edits it") — build_period_view reads
live fields every call and assembles a plain-language JSON payload the client lays out. Deterministic,
no LLM: it reads the same every time from stored fields.

Plain words, never encode (access frame): no glyphs, no <pre>, no orient_map-style symbol soup — the
client renders accessible layout from this JSON. Affect is never flattened (guard #3): `intent` and
`availability_note` travel as full free text, not compressed into scalars.

Scope: read-only. Authoring/editing is Task 3/4. This module never writes to Anytype.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import daily_plan as dp
import focus_period as fp

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _fmt_day(d, weekday=False):
    """'Jun 29' or (weekday=True) 'Mon Jun 29'. Plain words — no encoding."""
    if not isinstance(d, dt.date):
        return ""
    base = f"{_MONTHS[d.month]} {d.day}"
    return f"{_WEEKDAYS[d.weekday()]} {base}" if weekday else base


def _fmt_range(start, end, weekday=False):
    """A date range with an en-dash: 'Jun 29 – Jul 6' / 'Mon Jun 29 – Mon Jul 6'.
    Degrades gracefully if one end is missing (the loader only returns periods with both,
    but never assume)."""
    s, e = _fmt_day(start, weekday), _fmt_day(end, weekday)
    if s and e:
        return f"{s} – {e}"
    return s or e


def build_period_view(period_ctx, today):
    """Pure assembly — the tested unit. Reads the already-loaded period context and returns a
    plain JSON render payload. `period_ctx` is what daily_plan.load_active_items produces:
    {"period": <dict|None>, "is_off": bool, "in_window": bool}. The period dict already has
    `foreground` resolved to current project names (rename-safe) by the load path.

    `availability_active` is computed here from (period, today) via the canonical
    focus_period.in_availability_window helper — not read from the ctx's precomputed in_window —
    so this function depends only on the inputs it is handed (no hidden coupling) and `today` is
    load-bearing. Single source of truth for the window logic stays in focus_period.

    Returns {"active": False} when there is no active period — an honest empty state, never a
    fabricated one (the client shows "no focus period set")."""
    period = (period_ctx or {}).get("period")
    if not period:
        return {"active": False}

    start, end = period.get("start"), period.get("end")
    return {
        "active": True,
        "name": period.get("name") or "",
        # two formats: collapsed header is compact (no weekday); the expanded card carries weekday
        "date_range": _fmt_range(start, end, weekday=False),
        "date_range_full": _fmt_range(start, end, weekday=True),
        "intent": period.get("intent") or "",
        "foreground": list(period.get("foreground") or []),
        "availability_note": period.get("availability_note") or "",
        # drives the collapsed "Now" alert — only when today is inside the availability window
        "availability_active": fp.in_availability_window(period, today),
    }


def render_period():
    """Self-contained entry point the server calls (mirrors orient_map.render_map). Does the one
    full fetch load_active_items already performs, then assembles the payload. Read-only."""
    sid = g.get_space_id()
    *_, period_ctx = dp.load_active_items(sid)
    return build_period_view(period_ctx, dt.date.today())


if __name__ == "__main__":
    import json
    print(json.dumps(render_period(), indent=2, default=str))
