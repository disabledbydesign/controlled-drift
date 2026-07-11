#!/usr/bin/env python3
"""v1 chat-authoring seam for a Focus Period: create the object AND capture June's raw
words as learning signal in one call — so config authoring/corrections are logged from
day one, before the overlay authoring UI (Phase 6) exists.

Authoring is speak -> structure -> confirm (NOT auto-generated content): June says her
week, an instance structures it into fields, she confirms. The caller must resolve any
project names -> ids before passing `properties` (the write side of gsdo_objects.create
formats an `objects` relation as a list of ids; the read side hands back id/name pairs).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import gsdo_objects
import signal_log


def resolve_project_names_to_ids(names, objects=None):
    """Resolve project display-names -> Anytype ids for the Foreground/Paused relations.

    The write side of a Focus Period needs ids (the objects relation is a list of ids);
    June speaks names. Raises on an unknown name — never silently drops a project she named.
    `objects` may be passed (already-fetched) for testing; otherwise fetched live.

    Payload recipe (what author_focus_period's `properties` looks like):
      {"Period start": "2026-06-30", "Period end": "2026-07-06", "Intent": "...",
       "Availability start"/"Availability end": ISO date, "Availability note": "...",
       "Days off"/"Days on": "2026-07-03, 2026-07-04",  # CSV or JSON array
       "Output format": "Auto"|"Clock schedule"|"Priority list", "Workday end": "22:00",
       "Foreground projects": [<id>, ...], "Paused projects": [<id>, ...]}
    """
    if objects is None:
        objects = g.fetch_all_objects(g.get_space_id())
    by_name = {}
    for o in objects:
        t = o.get("type")
        tk = t.get("key") if isinstance(t, dict) else t
        if tk == "gsdo_project" and o.get("name"):
            by_name[o["name"]] = o["id"]
    ids = []
    for n in names:
        if n not in by_name:
            raise ValueError(f"project {n!r} not found — can't foreground/pause it")
        ids.append(by_name[n])
    return ids


def author_focus_period(raw_text, name, properties, source="config_authoring"):
    """Create a Focus Period and log June's raw words as signal. Returns the new object id.
    source='config_correction' when editing an existing period's framing."""
    oid = gsdo_objects.create("Focus Period", name, properties=properties)
    signal_log.log_signal(raw_text, source=source,
                          reference={"kind": "focus_period", "id": oid, "name": name})
    return oid


def update_focus_period(object_id, raw_text, name, properties, source="config_correction"):
    """Update an existing Focus Period IN PLACE (v1 choice — the period object is short-lived;
    archive-on-lapse is Phase 8) and log June's words as a correction signal. Returns object_id.
    The caller resolves project names -> ids first, same as the create path."""
    gsdo_objects.update(object_id, name=name, properties=properties)
    signal_log.log_signal(raw_text, source=source,
                          reference={"kind": "focus_period", "id": object_id, "name": name})
    return object_id
