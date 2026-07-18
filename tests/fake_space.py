"""An in-memory stand-in for the live Anytype space, installed at the TRANSPORT seam.

Used by `tests/test_api_write.py` and by the manual curl run that drives the real server. The seam
is `anytype_test.call` (every write module imports it by value, so each importer is patched by
name) plus the four `gsdo_anytype` lookups. Nothing above the transport is mocked — `gsdo_objects`,
`api_write`, `api_tree` and `task_actions` all run their real code, including the dedup guard, the
link-kind guard, guard #3 and every read-back.

Object and property shapes are copied from a live read (2026-07-18): properties carry `name` and
`format` inline, a select reads back as `{"select": {"id", "name"}}`, an objects-relation as bare
id STRINGS under `"objects"`, and `archived` is a top-level bool.
"""
import copy

SPACE = "space-fake"

TYPE_KEYS = {"Goal": "gsdo_goal", "Project": "gsdo_project", "Task": "task",
             "Recurring": "gsdo_recurring", "Strategy": "gsdo_strategy"}

# name -> (key, format, [options])
PROPS = {
    "Goal engagement": ("gsdo_goal_engagement", "select", ["Backburner", "Open", "Steady", "Sprint"]),
    "Goal status": ("gsdo_goal_status", "select", ["Active", "Parked", "Achieved"]),
    "Horizon": ("gsdo_horizon", "select", ["Chapter", "Milestone", "Ongoing"]),
    "Reaching for": ("gsdo_reaching", "text", None),
    "Resolution condition": ("gsdo_resolution", "text", None),
    "Barriers": ("gsdo_barriers", "text", None),
    "Description": ("gsdo_description", "text", None),
    "Context": ("gsdo_context", "text", None),
    "Affective": ("gsdo_affective", "text", None),
    "Access notes": ("gsdo_access_notes", "text", None),
    "Blocked on": ("gsdo_blocked_on", "text", None),
    "Relevant docs": ("gsdo_docs", "text", None),
    "Engagement": ("engagement", "select",
                   ["Backburner", "Open", "Steady", "Needs Clarifying", "Done"]),
    "Project status": ("gsdo_project_status", "select", ["Active", "Parked", "Inactive"]),
    "Side": ("gsdo_side", "select", ["Work", "Daily life", "Fun / hobby", "Wellbeing"]),
    "Deadline": ("gsdo_deadline", "date", None),
    "Block chunk min": ("gsdo_block_chunk_min", "number", None),
    "Is workstream": ("is_workstream", "checkbox", None),
    "Task status": ("gsdo_task_status", "select",
                    ["Ready", "Active", "Blocked", "In Design", "Parked", "Done"]),
    "Due date": ("due_date", "date", None),
    "Scheduled": ("scheduled", "date", None),
    "Duration min": ("gsdo_duration_min", "number", None),
    "AI autonomous": ("gsdo_ai_autonomous", "checkbox", None),
    "Needs clarifying": ("gsdo_needs_clarifying", "checkbox", None),
    "Done": ("done", "checkbox", None),
    "Access conditions": ("gsdo_access_conditions", "multi_select",
                          ["Requires-talking-to-a-person", "Can-be-done-lying-down",
                           "Involves-leaving-house", "Requires-deep-thinking",
                           "Involves-bureaucracy", "Induces-pain"]),
    "Interval unit": ("interval_unit", "select", ["day", "week", "month", "as_needed"]),
    "Interval count": ("gsdo_interval_count", "number", None),
    "Day of week": ("gsdo_day_of_week", "multi_select", ["Mon", "Tue", "Wed", "Thu", "Fri"]),
    "Day of month": ("gsdo_day_of_month", "number", None),
    "Time of day": ("gsdo_time_of_day", "text", None),
    "Active": ("gsdo_active", "checkbox", None),
    "Applies when": ("gsdo_applies_when", "select", ["Always", "Low energy", "Stuck"]),
    "Strategy status": ("gsdo_strategy_status", "select", ["Active", "Retired"]),
    "What for": ("gsdo_what_for", "text", None),
    "Linked Projects": ("linked_projects", "objects", None),
    "Project link": ("gsdo_project_link", "objects", None),
    "Parent project": ("gsdo_parent_project", "objects", None),
    "Goal link": ("gsdo_goal_link", "objects", None),
}

_BY_KEY = {k: (n, f, o) for n, (k, f, o) in PROPS.items()}


def prop_meta(name_or_key):
    if name_or_key in PROPS:
        name = name_or_key
        key, fmt, opts = PROPS[name]
    elif name_or_key in _BY_KEY:
        name, fmt, opts = _BY_KEY[name_or_key]
        key = name_or_key
    else:
        return None
    return {"id": f"prop-{key}", "key": key, "name": name, "format": fmt,
            "tags": [{"id": f"tag-{key}-{o}", "name": o} for o in (opts or [])]}


def _type_block(type_name):
    return {"id": f"type-{TYPE_KEYS[type_name]}", "key": TYPE_KEYS[type_name],
            "name": type_name, "properties": [
                {"key": k, "name": n, "format": f} for n, (k, f, _) in PROPS.items()]}


def obj(oid, type_name, name, **vals):
    """A live-shaped object. `vals` are keyed by property DISPLAY name."""
    o = {"id": oid, "object": "object", "name": name, "archived": False,
         "type": _type_block(type_name), "properties": []}
    for pname, v in vals.items():
        _set_prop(o, pname, v)
    return o


def _set_prop(o, pname, value):
    meta = prop_meta(pname)
    if meta is None:
        raise KeyError(f"fake_space: unknown property {pname!r}")
    entry = {"object": "property", "id": meta["id"], "key": meta["key"],
             "name": meta["name"], "format": meta["format"]}
    fmt = meta["format"]
    if fmt == "select":
        entry["select"] = {"id": f"tag-{meta['key']}-{value}", "name": value}
    elif fmt == "multi_select":
        entry["multi_select"] = [{"id": f"tag-{meta['key']}-{v}", "name": v} for v in value]
    elif fmt == "objects":
        entry["objects"] = list(value)
    elif fmt == "checkbox":
        entry["checkbox"] = bool(value)
    elif fmt == "number":
        entry["number"] = value
    elif fmt == "date":
        entry["date"] = value
    else:
        entry["text"] = value
    o["properties"] = [p for p in o["properties"] if p.get("key") != meta["key"]] + [entry]


class FakeSpace:
    """The store plus a recorded call log. `calls` is what read-back tests assert against."""

    def __init__(self, objects):
        self.objects = {o["id"]: copy.deepcopy(o) for o in objects}
        self.calls = []
        self.next_id = 1
        #: Set to True to simulate a write that Anytype accepts (200) and does not persist —
        #: the exact failure the read-back discipline exists to catch.
        self.swallow_writes = False

    # --- the transport ------------------------------------------------------
    def call(self, method, path, body=None):
        self.calls.append((method, path))
        parts = [p for p in path.split("?")[0].split("/") if p]
        # /spaces/{sid}/objects[/{id}]
        if len(parts) >= 3 and parts[0] == "spaces" and parts[2] == "objects":
            oid = parts[3] if len(parts) > 3 else None
            if method == "GET" and oid:
                o = self.objects.get(oid)
                return (200, {"object": copy.deepcopy(o)}) if o else (404, {"error": "not found"})
            if method == "POST" and not oid:
                return self._create(body)
            if method == "PATCH" and oid:
                return self._patch(oid, body)
            if method == "DELETE" and oid:
                if oid not in self.objects:
                    return 404, {"error": "not found"}
                self.objects[oid]["archived"] = True
                return 204, ""
        if len(parts) >= 5 and parts[2] == "properties" and parts[4] == "tags":
            meta = prop_meta(parts[3].replace("prop-", ""))
            return 200, {"data": meta["tags"] if meta else []}
        raise AssertionError(f"fake_space: unexpected {method} {path}")

    def _type_name_of_key(self, key):
        return next((n for n, k in TYPE_KEYS.items() if k == key), None)

    def _create(self, body):
        tname = self._type_name_of_key(body["type_key"])
        if tname is None:
            return 400, {"error": f"unknown type_key {body.get('type_key')!r}"}
        oid = f"new-{self.next_id}"
        self.next_id += 1
        o = obj(oid, tname, body.get("name") or "")
        self.objects[oid] = o
        if not self.swallow_writes:
            self._apply(oid, body.get("properties") or [])
        return 201, {"object": copy.deepcopy(o)}

    def _patch(self, oid, body):
        if oid not in self.objects:
            return 404, {"error": "not found"}
        if self.swallow_writes:
            return 200, {"object": copy.deepcopy(self.objects[oid])}
        if body.get("name") is not None:
            self.objects[oid]["name"] = body["name"]
        if body.get("type_key") is not None:
            # In-place type change, copied from live behaviour probed 2026-07-18: the object keeps
            # its id AND every property value, including values for properties the new type does
            # not link. Only the `type` block is replaced.
            tname = self._type_name_of_key(body["type_key"])
            if tname is None:
                return 400, {"error": f"unknown type_key {body['type_key']!r}"}
            self.objects[oid]["type"] = _type_block(tname)
        self._apply(oid, body.get("properties") or [])
        return 200, {"object": copy.deepcopy(self.objects[oid])}

    def _apply(self, oid, props):
        o = self.objects[oid]
        for p in props:
            meta = prop_meta(p["key"])
            fmt = meta["format"]
            if fmt == "select":
                name = next((t["name"] for t in meta["tags"] if t["id"] == p["select"]), None)
                _set_prop(o, meta["name"], name)
            elif fmt == "multi_select":
                names = [t["name"] for t in meta["tags"] if t["id"] in (p["multi_select"] or [])]
                _set_prop(o, meta["name"], names)
            elif fmt == "objects":
                _set_prop(o, meta["name"], p["objects"])
            elif fmt == "checkbox":
                _set_prop(o, meta["name"], p["checkbox"])
            elif fmt == "number":
                _set_prop(o, meta["name"], p["number"])
            elif fmt == "date":
                _set_prop(o, meta["name"], p["date"])
            else:
                _set_prop(o, meta["name"], p["text"])

    def all_objects(self, sid=None, page_size=None):
        return [copy.deepcopy(o) for o in self.objects.values() if not o.get("archived")]


#: Every module that imported `call` by value and therefore holds its own reference.
_CALL_HOLDERS = ("gsdo_objects", "api_write", "task_actions", "recurring_active")


def install(space, setattr_fn):
    """Point the transport and the four `gsdo_anytype` lookups at `space`.

    `setattr_fn(module, name, value)` is `monkeypatch.setattr` under pytest, or a plain setattr in
    the standalone curl harness — so one installer serves both.
    """
    import importlib
    import gsdo_anytype as g
    for mod_name in _CALL_HOLDERS:
        mod = importlib.import_module(mod_name)
        setattr_fn(mod, "call", space.call)
    setattr_fn(g, "get_space_id", lambda: SPACE)
    setattr_fn(g, "fetch_all_objects", space.all_objects)
    setattr_fn(g, "find_property", prop_meta)
    setattr_fn(g, "find_type", lambda n: ({"key": TYPE_KEYS[n], "name": n}
                                          if n in TYPE_KEYS else None))
    return space
