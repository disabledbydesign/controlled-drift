#!/usr/bin/env python3
"""Create Anytype objects from confirmed weeding output. The deterministic write layer:
the LLM (Claude) produces the validated proposal; this turns each confirmed item into an
Anytype object, resolving property names->keys, formatting each value by the property's
format, and resolving select/multi_select option names->tag ids.

Value shapes confirmed empirically against the live API (2026-06-17):
  text->{"text":v} number->{"number":v} checkbox->{"checkbox":bool}
  date->{"date":"YYYY-MM-DD"|ISO} select->{"select":tag_id}
  multi_select->{"multi_select":[tag_id,...]} objects->{"objects":[obj_id,...]}
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import gsdo_anytype as g

def _tag_id(prop, option_name):
    sid = g.get_space_id()
    tags = call("GET", f"/spaces/{sid}/properties/{prop['id']}/tags")[1].get("data", [])
    t = next((x for x in tags if x.get("name") == option_name), None)
    if t is None:
        opts = [x.get("name") for x in tags]
        raise ValueError(f"option {option_name!r} not found on {prop.get('name')!r} (have {opts})")
    return t["id"]

def _value_field(prop, value):
    fmt, key = prop.get("format"), prop.get("key")
    if fmt == "text":         return {"key": key, "text": value}
    if fmt == "number":       return {"key": key, "number": value}
    if fmt == "checkbox":     return {"key": key, "checkbox": bool(value)}
    if fmt == "date":         return {"key": key, "date": value}
    if fmt == "select":       return {"key": key, "select": _tag_id(prop, value)}
    if fmt == "multi_select": return {"key": key, "multi_select": [_tag_id(prop, v) for v in value]}
    if fmt == "objects":      return {"key": key, "objects": value if isinstance(value, list) else [value]}
    raise ValueError(f"unsupported format {fmt!r} for property {prop.get('name')!r}")

def _norm_name(s):
    """Normalize a name for exact-duplicate matching: whitespace-collapsed, case-folded."""
    import re
    return re.sub(r"\s+", " ", (s or "").strip().lower())

# --- shared link-KIND guard --------------------------------------------------
# The data-model rule: a Task's / Recurring's project link may only point at a Project, and a
# Project's Goal link only at a Goal. This enforcement lived ONLY in the overlay's capture path
# (capture_generate, keyed on the P#/G# link tokens), so MCP writes and drift-skill writes
# bypassed it entirely and COULD link a Task to a Goal — type-mismatched, corrupt data. Moving
# the rule here, into the shared write layer every writer goes through, means it can't drift by
# path. Same outcome the overlay chose: a wrong-kind link is DROPPED (no link beats a mismatched
# one), never raised — so a legitimate UNLINKED create is untouched and only a corrupt link is
# refused, nothing more.
#
# Keyed by the type_key being created; the value maps each link property (by display NAME, since
# every real caller passes display names — see CLAUDE.md and capture_generate) to the type_key
# the link must resolve to.
_LINK_KIND = {
    "task":           {"Linked Projects": "gsdo_project"},
    "gsdo_recurring": {"Project link":    "gsdo_project"},
    "gsdo_project":   {"Goal link":       "gsdo_goal"},
}

def _object_type_key(sid, oid):
    """The type key of an existing object, or None if it can't be read. Best-effort by design: a
    link we CAN'T verify is left alone — we only ever drop a link we can positively prove is
    wrong-kind, because refusing an unverifiable link could break a legitimate write."""
    try:
        st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    except Exception:
        return None
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        return None
    return b.get("object", {}).get("type", {}).get("key")

def guard_link_kinds(sid, type_key, properties):
    """Return a copy of `properties` with any positively-wrong-kind link value dropped. Warns on
    each drop (never silent — a dropped link is signal). All ids on a link dropped -> that link
    property is removed entirely, so the object is created with no link rather than a bad one
    (the overlay's exact choice). Only link props for this type are inspected; everything else
    passes through untouched, so unlinked and non-link creates are unaffected."""
    rules = _LINK_KIND.get(type_key)
    if not rules or not properties:
        return properties
    out = dict(properties)
    for prop_name, expected_key in rules.items():
        if prop_name not in out:
            continue
        val = out[prop_name]
        if not val:
            continue
        ids = val if isinstance(val, list) else [val]
        kept = []
        for oid in ids:
            actual = _object_type_key(sid, oid)
            if actual is not None and actual != expected_key:
                print(f"[gsdo_objects] refusing wrong-kind link on {prop_name!r}: {oid} is a "
                      f"{actual!r}, expected a {expected_key!r} — dropped (no link beats a bad one)",
                      file=sys.stderr)
                continue
            kept.append(oid)
        if kept:
            out[prop_name] = kept if isinstance(val, list) else kept[0]
        else:
            del out[prop_name]   # every id was wrong-kind -> create with no link at all
    return out

def find_existing(type_key, name):
    """Id of an existing object of the SAME type with the same normalized name, or None.

    Exact match only (case/whitespace-insensitive) — a near-miss name still creates. A false
    dedup (silently reusing the wrong object) is worse than a rare true duplicate, so this
    only catches the unambiguous case: literally the same name, same type.
    """
    sid = g.get_space_id()
    target = _norm_name(name)
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") == type_key and _norm_name(o.get("name")) == target:
            return o["id"]
    return None

def create_object(type_key, name, body=None, properties=None):
    """Low-level: create an object of type_key. properties: {prop_name_or_key: value}.

    Dedup guard (added 2026-07-02): before creating, checks for an existing object of the same
    type with the same normalized name and returns its id instead of creating a new one.
    Confirmed empirically (2026-07-02) that neither this function nor the live Anytype API
    deduped by name on their own — two creates with an identical name produced two distinct
    objects. That gap meant the memory pass's content-hash state file was the ONLY guard against
    a repeat create; if it were ever lost or deleted, a re-run had nothing to stop it recreating
    everything (the exact Strategy-triplication failure this system already hit once for real).
    This makes gsdo_objects.create the actual "one source of truth" dedup backstop the daily
    memory pass plan assumed already existed.
    """
    sid = g.get_space_id()
    existing_id = find_existing(type_key, name)
    if existing_id:
        return existing_id
    # Shared link-KIND guard: drop any wrong-kind link (Task->Goal, etc.) before writing, so every
    # writer — MCP, drift skill, overlay — inherits the rule that used to live only in the overlay.
    properties = guard_link_kinds(sid, type_key, properties)
    props = []
    for pname, value in (properties or {}).items():
        if value is None:
            continue
        prop = g.find_property(pname)
        if prop is None:
            raise ValueError(f"create_object: property {pname!r} not found")
        props.append(_value_field(prop, value))
    payload = {"type_key": type_key, "name": name}
    if body:
        payload["body"] = body
    if props:
        payload["properties"] = props
    st, b = call("POST", f"/spaces/{sid}/objects", payload)
    if st not in (200, 201):
        raise RuntimeError(f"create_object {name!r} failed: {st} {b}")
    return b["object"]["id"]

def create(type_name, name, body=None, properties=None):
    """Create by friendly type NAME (e.g. 'Task','Goal','Recurring','Strategy','Note')."""
    t = g.find_type(type_name)
    if t is None:
        raise ValueError(f"create: type {type_name!r} not found")
    return create_object(t.get("key"), name, body=body, properties=properties)

def update(object_id, name=None, properties=None):
    """Update an existing object's name and/or properties.

    properties: {prop_name_or_key: value} — resolved + formatted the same way as
    create (select option names -> tag ids, etc.). Use this instead of hand-rolling
    PATCH calls: it handles the value-shape resolution that raw select writes get wrong.

    Examples:
      update(stream_id, name="Finish the daily-plan pipeline")
      update(stream_id, properties={"Context": "what it is — ...\\nnext step — ..."})
      update(stream_id, properties={"Engagement": "Done"})   # resolves "Done" -> tag id
    """
    sid = g.get_space_id()
    payload = {}
    if name is not None:
        payload["name"] = name
    props = []
    for pname, value in (properties or {}).items():
        if value is None:
            continue
        prop = g.find_property(pname)
        if prop is None:
            raise ValueError(f"update: property {pname!r} not found")
        props.append(_value_field(prop, value))
    if props:
        payload["properties"] = props
    if not payload:
        raise ValueError("update: nothing to change (pass name and/or properties)")
    st, b = call("PATCH", f"/spaces/{sid}/objects/{object_id}", payload)
    if st not in (200, 201):
        raise RuntimeError(f"update {object_id!r} failed: {st} {b}")
    return b.get("object", {}).get("id", object_id)
