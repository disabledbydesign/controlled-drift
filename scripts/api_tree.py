#!/usr/bin/env python3
"""The payload behind `GET /api/tree` — June's real object graph, in the shape the new
surface's Review tab consumes.

The new UI (`app/`) currently runs entirely on `app/src/fixtures/tree.ts`. That fixture is the
CONTRACT: `{id, level, type, title, vals, children}`, levels GOAL / PROJECT / SUBPROJECT /
WORKSTREAM / TASK / RECURRING, plus flat STRATEGY nodes. This module returns the same shape
built from the live space.

Three things here are load-bearing and easy to get wrong:

1. **Nothing may silently vanish.** Every Goal / Project / Task / Recurring / Strategy object in
   the space appears exactly once in the payload, and `_check_no_omission` RAISES if that is not
   true. In a pure Goal→Project→Task tree an unfiled task renders NOWHERE — it silently does not
   exist. Capture and weeding produce unfiled objects constantly, so the rooted tree alone is a
   lossy view of the space. Hence `orphans` (below), which follows the categories
   `review_surface.py:234-247` already established rather than inventing new ones.

   ⚠ One category is WIDER here than in `review_surface`: a project whose `Goal link` points at
   an id that is not in the space (deleted or archived goal) is treated as goal-less. In
   `review_surface` such a project has a non-None `proj_goal` and matches no rendered goal, so it
   is rendered nowhere at all — a real silent-vanish path in the surface being retired.

2. **Tri-state is expressed by key presence** (backend spec §4, contract §2.2). A key absent from
   `vals` means "inherit from the nearest ancestor that sets it"; a key present, even as `''`,
   means an explicit own value. So this NEVER emits a placeholder for an unset field. Anytype
   cooperates: it omits properties that were never written (verified live — 129 of 166 Tasks carry
   `Context` at all), so a property that comes back as `""` was written and then cleared, and is
   correctly reported as explicit-empty.

3. **`level` is not `type`** (backend spec §5). Subproject, Workstream and Project are all the
   Anytype type `Project`. Workstream is `is_workstream`, inherited down the parent chain — the
   same rule `review_surface.is_ws` and `orient_map._is_workstream` apply. Subproject vs Project
   is nesting depth. The UI needs the finer `level` to pick the right control set.

The valKey ↔ Anytype-property mapping is NOT duplicated here: it is `api_schema.PROPERTY_FOR`,
inverted. One definition, so a field that gains a control in the schema endpoint is round-tripped
by the tree endpoint without a second edit.

Reading only. Nothing here writes to Anytype.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import intentionally_none
import api_schema

# The five GSDO types. Everything else live in the space (Page, Bookmark, Note, Focus Period) is
# deliberately outside this graph — reported in `counts.excluded` rather than dropped quietly.
GSDO_TYPES = ("Goal", "Project", "Task", "Recurring", "Strategy")

# Object-reference properties that build the hierarchy. ⚠ These read back as bare id STRINGS
# under "objects" (not "object") — the bug that once made every task→project link read empty.
LINK_TASK_PROJECT = "linked_projects"
LINK_RECURRING_PROJECT = "gsdo_project_link"
LINK_PARENT_PROJECT = "gsdo_parent_project"
LINK_GOAL = "gsdo_goal_link"

# Fields the UI drives with dedicated controls rather than the generic schema form, so they are
# absent from `api_schema.PROPERTY_FOR` but must still round-trip (contract §2.2).
#   TASK.done      -> the row checkbox; `toggleDone` also flips `status`.
#   RECURRING.paused -> the in-my-plan toggle. ⚠ POLARITY: Anytype stores `Active`
#     (default true, spec §3); the UI fixture stores the INVERSE, `paused` (contract Q6/Q3).
#     Emitted as `paused` because that is what the fixture and `isInactive()` read. Only emitted
#     when `Active` is explicitly present, so an untouched Recurring inherits "not paused".
EXTRA_PROPERTY_FOR = {
    "TASK": {"done": "Done"},
    "RECURRING": {"paused": "Active"},
}
INVERTED_VALS = {("RECURRING", "paused")}


def _type_name(o):
    t = o.get("type")
    return t.get("name") if isinstance(t, dict) else t


def _prop_name(o, p):
    """Display name of a property on an object, falling back to the type's declaration."""
    if p.get("name"):
        return p["name"]
    t = o.get("type") or {}
    for tp in t.get("properties", []) or []:
        if tp.get("key") == p.get("key"):
            return tp.get("name")
    return None


def _ids(v):
    """Normalize an objects-relation value to a list of ids. Handles the bare-string form."""
    if not v:
        return []
    if not isinstance(v, list):
        v = [v]
    out = []
    for x in v:
        out.append(x if isinstance(x, str)
                   else (x.get("id") or x.get("object") or x.get("target")))
    return [i for i in out if i]


def _link(o, key):
    for p in o.get("properties", []):
        if p.get("key") == key and "objects" in p:
            return _ids(p["objects"])
    return []


def _value(p):
    """The typed value of one property, or `_UNSET` when the property carries no value.

    Types are preserved rather than stringified: number stays a number, checkbox a bool,
    multi_select an ARRAY of option names. The fixture hand-wrote some of these loosely
    (`blockMin:'60'`, `access:'Involves-leaving-house'`); per the 2026-07-17 fixture-extraction
    note those looser forms are NOT the contract — the API returns the real types.
    """
    fmt = p.get("format")
    if fmt == "text" and "text" in p:
        return p["text"] or ""
    if fmt == "number" and "number" in p:
        return p["number"]
    if fmt == "checkbox" and "checkbox" in p:
        return bool(p["checkbox"])
    if fmt == "date" and "date" in p:
        return p["date"]
    if fmt == "select" and "select" in p:
        s = p["select"]
        return (s.get("name") if isinstance(s, dict) else s) or _UNSET
    if fmt == "multi_select" and "multi_select" in p:
        opts = [x.get("name") if isinstance(x, dict) else x for x in (p["multi_select"] or [])]
        return [x for x in opts if x]
    if fmt in ("url", "email", "phone") and fmt in p:
        return p[fmt] or ""
    return _UNSET


class _Unset:
    def __repr__(self):
        return "<unset>"


_UNSET = _Unset()


def _vals_map(level):
    """{Anytype display name: valKey} for one UI level — `api_schema.PROPERTY_FOR` inverted."""
    out = {}
    for val_key, prop in api_schema.PROPERTY_FOR.get(level, {}).items():
        out.setdefault(prop, val_key)
    for val_key, prop in EXTRA_PROPERTY_FOR.get(level, {}).items():
        out[prop] = val_key
    return out


def _vals(o, level):
    """The `vals` bag: ONLY the keys this object actually sets. See tri-state note in the docstring.

    ⚠ The tri-state note's claim that "Anytype cooperates" holds for TEXT and nothing else. It was
    verified against a text property (`Context`) and is FALSE for a multi_select, where writing an
    empty value deletes the property outright — so `access` set-here-and-empty and `access` never
    touched come back identically. `intentionally_none` carries that distinction in its own
    property; this is where it is folded back in, so every reader downstream sees the tri-state
    the resolver expects without knowing the marker exists.
    """
    wanted = _vals_map(level)
    out = {}
    marker = None
    for p in o.get("properties", []):
        name = _prop_name(o, p)
        if name == intentionally_none.PROPERTY:
            v = _value(p)
            marker = None if isinstance(v, _Unset) else v
            continue        # never a `vals` key of its own — it is plumbing, not a field
        key = wanted.get(name)
        if key is None:
            continue
        v = _value(p)
        if isinstance(v, _Unset):
            continue
        if (level, key) in INVERTED_VALS:
            v = not bool(v)
        out[key] = v

    # A marked field is PRESENT and empty — "intentionally none". Emitted only when the field is
    # not otherwise set, so a real value always wins over a stale marker rather than being hidden
    # by one.
    for key in intentionally_none.marked_keys(marker):
        if key in wanted.values() and key not in out:
            out[key] = [] if key == "access" else ""
    return out


def build_tree():
    """The `GET /api/tree` body. Reads the live space; never writes."""
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    return build_tree_from(objs)


def build_tree_from(objs):
    """The pure half — the graph assembly, given already-fetched objects. Testable without a space."""
    by_id = {o["id"]: o for o in objs}
    of_type = {t: [o for o in objs if _type_name(o) == t] for t in GSDO_TYPES}

    goals = of_type["Goal"]
    projects = of_type["Project"]
    projects_by_id = {p["id"]: p for p in projects}
    goals_by_id = {o["id"]: o for o in goals}

    # --- workstream inheritance: own checkbox wins, else inherit from the nearest ancestor ----
    def _own_ws(p):
        for pr in p.get("properties", []):
            if pr.get("key") == "is_workstream":
                return bool(pr.get("checkbox"))
        return False

    ws_cache = {}

    def is_ws(p):
        pid = p["id"]
        if pid in ws_cache:
            return ws_cache[pid]
        ws_cache[pid] = False  # cycle guard
        if _own_ws(p):
            result = True
        else:
            par = _link(p, LINK_PARENT_PROJECT)
            parent = projects_by_id.get(par[0]) if par else None
            result = is_ws(parent) if parent is not None else False
        ws_cache[pid] = result
        return result

    def parent_of(p):
        par = _link(p, LINK_PARENT_PROJECT)
        return projects_by_id.get(par[0]) if par else None

    def level_of(p):
        if is_ws(p):
            return "WORKSTREAM"
        return "SUBPROJECT" if parent_of(p) is not None else "PROJECT"

    # --- attach tasks / recurrings / child projects -------------------------------------------
    tasks_by_project, orphan_tasks = {}, []
    for t in of_type["Task"]:
        pids = _link(t, LINK_TASK_PROJECT)
        if pids and pids[0] in projects_by_id:
            tasks_by_project.setdefault(pids[0], []).append(t)
        else:
            orphan_tasks.append(t)

    recurring_by_project, orphan_recurring = {}, []
    for r in of_type["Recurring"]:
        pids = _link(r, LINK_RECURRING_PROJECT)
        if pids and pids[0] in projects_by_id:
            recurring_by_project.setdefault(pids[0], []).append(r)
        else:
            orphan_recurring.append(r)

    children_of, rooted_projects = {}, []
    for p in projects:
        parent = parent_of(p)
        if parent is not None:
            children_of.setdefault(parent["id"], []).append(p)
        else:
            rooted_projects.append(p)

    def goal_of(p):
        gids = _link(p, LINK_GOAL)
        # Wider than review_surface on purpose: an unresolvable goal id counts as no goal,
        # otherwise the project renders under no goal AND in no bucket. See docstring.
        return next((i for i in gids if i in goals_by_id), None)

    # --- node construction ---------------------------------------------------------------------
    seen = set()

    def node(o, level, type_name, children=()):
        seen.add(o["id"])
        return {"id": o["id"], "level": level, "type": type_name,
                "title": (o.get("name") or "").strip(),
                "vals": _vals(o, level), "children": list(children)}

    def by_title(nodes):
        return sorted(nodes, key=lambda n: n["title"].lower())

    def project_node(p):
        lvl = level_of(p)
        kids = children_of.get(p["id"], [])
        child_nodes = by_title([project_node(c) for c in kids])
        child_nodes += by_title([node(t, "TASK", "Task")
                                 for t in tasks_by_project.get(p["id"], [])])
        child_nodes += by_title([node(r, "RECURRING", "Recurring")
                                 for r in recurring_by_project.get(p["id"], [])])
        return node(p, lvl, "Project", child_nodes)

    goal_children = {}
    for p in rooted_projects:
        if is_ws(p):
            continue  # a parentless workstream has no goal home; it goes in its own bucket
        gid = goal_of(p)
        if gid is not None:
            goal_children.setdefault(gid, []).append(p)

    nodes = by_title([
        node(gl, "GOAL", "Goal",
             by_title([project_node(p) for p in goal_children.get(gl["id"], [])]))
        for gl in goals
    ])

    strategies = by_title([node(s, "STRATEGY", "Strategy") for s in of_type["Strategy"]])

    # --- orphan buckets — the anti-vanishing affordance -----------------------------------------
    goalless = [p for p in rooted_projects if not is_ws(p) and goal_of(p) is None]
    parentless_ws = [p for p in rooted_projects if is_ws(p)]

    orphans = {
        # Keys are stable ids; `label` is the June-facing heading, kept verbatim from the
        # surface being retired so the wording she already reads does not change.
        "projects_without_goal": {
            "label": "⚠ NO GOAL YET — projects not linked to a goal",
            "nodes": by_title([project_node(p) for p in goalless])},
        "orphan_tasks": {
            "label": "⚠ NO PROJECT — orphan tasks",
            "nodes": by_title([node(t, "TASK", "Task") for t in orphan_tasks])},
        "orphan_recurring": {
            "label": "⚠ NO PROJECT — orphan recurring items",
            "nodes": by_title([node(r, "RECURRING", "Recurring") for r in orphan_recurring])},
        "parentless_workstreams": {
            "label": "⚙ Workstreams with no parent project",
            "nodes": by_title([project_node(p) for p in parentless_ws])},
    }

    counts = {
        "objects_fetched": len(objs),
        "by_type": {t: len(of_type[t]) for t in GSDO_TYPES},
        "excluded": len(objs) - sum(len(of_type[t]) for t in GSDO_TYPES),
        "in_tree": _count(nodes),
        "in_orphans": {k: _count(v["nodes"]) for k, v in orphans.items()},
        "strategies": len(strategies),
        "workstreams": sum(1 for p in projects if is_ws(p)),
    }

    _check_no_omission(objs, seen)
    return {"nodes": nodes, "strategies": strategies, "orphans": orphans, "counts": counts}


def _count(nodes):
    return sum(1 + _count(n["children"]) for n in nodes)


def _check_no_omission(objs, seen):
    """Raise if any GSDO object failed to land somewhere in the payload.

    Silent omission is this project's most expensive recurring failure, and it is exactly what an
    orphan bucket exists to prevent — so the guarantee is enforced, not documented. A 500 that
    names the missing objects is strictly better than a tree that quietly lost them.
    """
    expected = {o["id"] for o in objs if _type_name(o) in GSDO_TYPES}
    missing = expected - seen
    if missing:
        names = ", ".join(sorted(next(o.get("name", "?") for o in objs if o["id"] == i)
                                 for i in list(missing)[:10]))
        raise RuntimeError(
            f"api_tree: {len(missing)} object(s) would be dropped from the tree "
            f"and every orphan bucket: {names}")
    extra = seen - expected
    if extra:
        raise RuntimeError(f"api_tree: {len(extra)} object(s) emitted more than once or unknown")


if __name__ == "__main__":
    import json
    print(json.dumps(build_tree(), indent=2, ensure_ascii=False))
