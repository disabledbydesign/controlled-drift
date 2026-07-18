#!/usr/bin/env python3
"""The SINGLE writer of a Recurring's `Active` flag (as-needed on/off). Completion, Add, Focus, and June's
tick-list all funnel here — no path re-implements the write/read-back/log. A neutral leaf module so
`capture_generate` can call it without the `server → capture_generate` import cycle."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
import reactivation_log
from anytype_test import call


def _get_object(rid):
    # same GET as capture_generate._get_object:325-330 — inlined so this module imports no caller.
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{rid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read Recurring {rid!r}: {st} {b}")
    return b["object"]


def _active_of(obj):
    by_name = {p.get("name"): p for p in obj.get("properties", [])}
    return (by_name.get("Active") or {}).get("checkbox")


def as_needed_objects(objects):
    """Recurring objects whose Interval unit is as_needed, from a raw Anytype objects list —
    REGARDLESS of current Active state. An OFF one is exactly the reactivation target (Decision
    4: 'match her words to her existing as-needed tasks'), so this must never filter by Active —
    a caller that only wants active/inactive ones filters the returned list itself. The single
    shared source for every reactivation entry point's grounding/matching (Add-box weeding,
    Focus-Period authoring) — previously duplicated per-caller, which let one caller's grounding
    context silently diverge from another's (Task 6 review finding, 2026-07-17: the Focus-Period
    authoring prompt's task grounding came from daily_plan.load_active_items' 'due today' filter,
    which for an as_needed item IS its Active state — so an OFF task could never be named for
    reactivation through that path at all)."""
    out = []
    for o in objects:
        t = o.get("type")
        tk = t.get("key") if isinstance(t, dict) else t
        if tk != "gsdo_recurring":
            continue
        props = {p.get("key"): p for p in o.get("properties", [])}
        unit = (props.get("interval_unit") or {}).get("select") or {}
        if unit.get("name") == "as_needed":
            out.append(o)
    return out


def set_recurring_active(rid, active):
    """Read Active's PRE-state, write the new value, read it BACK BY DISPLAY NAME to prove it persisted,
    then log the (old → new) toggle. `active` is a bool; returns the new state. Reads its own before-state
    so the log no-ops correctly on a real re-tap — callers pass no `old`."""
    before = _get_object(rid)
    old = _active_of(before)
    gsdo_objects.update(rid, properties={"Active": active})
    after = _get_object(rid)
    got = _active_of(after)
    if bool(got) != bool(active):
        raise RuntimeError(f"Active read-back mismatch for {rid!r}: wrote {active!r}, got {got!r}")
    reactivation_log.log_change(rid, after.get("name"), bool(old), bool(active))
    return bool(active)
