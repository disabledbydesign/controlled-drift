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

def create_object(type_key, name, body=None, properties=None):
    """Low-level: create an object of type_key. properties: {prop_name_or_key: value}."""
    sid = g.get_space_id()
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
