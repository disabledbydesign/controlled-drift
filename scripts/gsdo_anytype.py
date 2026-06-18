#!/usr/bin/env python3
"""Idempotent Anytype schema helpers for GSDO. Built on the verified call() in anytype_test.py.
Confirmed in Task 1 against live OpenAPI (2026-06-17):
  - select-option tags path: /spaces/{sid}/properties/{pid}/tags
    (GET returns {"data": [...tags...], "pagination": {...}};
     POST {"name": opt, "color": <color>} creates a tag — color is required per OpenAPI schema,
     valid values: grey|yellow|orange|red|pink|purple|blue|ice|teal|lime; default "grey")
  - type property-list field: "properties"
    (confirmed from GET /spaces/{sid}/types?limit=100 -> task type keys include "properties",
     value is list of {object, id, key, name, format} dicts)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call

_SID = None
def get_space_id():
    global _SID
    if _SID is None:
        _SID = call("GET", "/spaces")[1]["data"][0]["id"]
    return _SID

def find_type(key_or_name):
    sid = get_space_id()
    data = call("GET", f"/spaces/{sid}/types?limit=100")[1].get("data", [])
    return next((t for t in data if t.get("key") == key_or_name or t.get("name") == key_or_name), None)

def find_property(key_or_name):
    sid = get_space_id()
    data = call("GET", f"/spaces/{sid}/properties?limit=200")[1].get("data", [])
    return next((p for p in data if p.get("key") == key_or_name or p.get("name") == key_or_name), None)

def ensure_property(name, fmt, options=None):
    existing = find_property(name)
    if existing:
        key = existing.get("key")
    else:
        st, b = call("POST", f"/spaces/{get_space_id()}/properties", {"name": name, "format": fmt})
        if st not in (200, 201):
            raise RuntimeError(f"create property {name} failed: {st} {b}")
        key = b["property"]["key"]
    if options and fmt in ("select", "multi_select"):
        ensure_select_options(key, options)
    return key

def ensure_select_options(property_key, options, color="grey"):
    sid = get_space_id()
    prop = find_property(property_key)
    if prop is None:
        raise ValueError(f"ensure_select_options: property {property_key!r} not found")
    pid = prop["id"]
    # Confirmed path: /spaces/{sid}/properties/{pid}/tags
    # color is required by the API (CreateTagRequest schema); defaults to "grey"
    existing = {t.get("name") for t in call("GET", f"/spaces/{sid}/properties/{pid}/tags")[1].get("data", [])}
    for opt in options:
        if opt not in existing:
            st, b = call("POST", f"/spaces/{sid}/properties/{pid}/tags", {"name": opt, "color": color})
            if st not in (200, 201):
                raise RuntimeError(f"create tag {opt} on {property_key} failed: {st} {b}")

def link_properties_to_type(type_id, property_keys):
    sid = get_space_id()
    t = call("GET", f"/spaces/{sid}/types/{type_id}")[1].get("type", {})
    # Confirmed field: "properties" lists a type's linked properties
    current = {p.get("key") for p in t.get("properties", [])}
    to_add = [{"key": k} for k in property_keys if k not in current]
    if to_add:
        merged = t.get("properties", []) + to_add
        st, b = call("PATCH", f"/spaces/{sid}/types/{type_id}",
                     {"properties": merged})
        if st not in (200, 201):
            raise RuntimeError(f"link properties to type {type_id} failed: {st} {b}")

def fetch_all_objects(sid, page_size=100):
    """Paginate through all objects in the space. Returns the full list."""
    objects = []
    offset = 0
    while True:
        _, body = call("GET", f"/spaces/{sid}/objects?limit={page_size}&offset={offset}")
        batch = body.get("data", []) if isinstance(body, dict) else []
        objects.extend(batch)
        if not (isinstance(body, dict) and body.get("pagination", {}).get("has_more")):
            break
        offset += page_size
    return objects

def ensure_type(name, plural, property_keys, layout="basic"):
    existing = find_type(name)
    if existing:
        type_id, key = existing["id"], existing.get("key")
    else:
        st, b = call("POST", f"/spaces/{get_space_id()}/types",
                     {"name": name, "plural_name": plural, "layout": layout})
        if st not in (200, 201):
            raise RuntimeError(f"create type {name} failed: {st} {b}")
        type_id, key = b["type"]["id"], b["type"]["key"]
    link_properties_to_type(type_id, property_keys)
    return key
