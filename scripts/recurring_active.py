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
