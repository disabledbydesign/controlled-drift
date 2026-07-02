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
import gsdo_objects
import signal_log


def author_focus_period(raw_text, name, properties, source="config_authoring"):
    """Create a Focus Period and log June's raw words as signal. Returns the new object id.
    source='config_correction' when editing an existing period's framing."""
    oid = gsdo_objects.create("Focus Period", name, properties=properties)
    signal_log.log_signal(raw_text, source=source,
                          reference={"kind": "focus_period", "id": oid, "name": name})
    return oid
