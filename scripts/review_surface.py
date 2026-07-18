#!/usr/bin/env python3
"""Build June's review-and-reorganize surface — a single self-contained HTML file
rendered from the LIVE Anytype space, so it never drifts from what's actually there.

Why this exists: raw Anytype shows a flat wall of titles and hides every relation, which
makes the data impossible for June to read or clean up. This renders the real structure
(Goal > Project > Subproject > Task) as a collapsible tree where every field is an
editable, correctly-typed control (dropdowns for selects, checkboxes for booleans,
date pickers for dates). She reviews, reorganizes, and leaves notes; the page tracks
every change as a diff and exports it. Applying the diff back to Anytype is a separate
step (Claude parses the export and writes with read-back).

The page is a LOCAL file only (her data carries health/financial detail) — never publish it.

Usage:  python3 scripts/review_surface.py [OUTPUT_PATH]
        default output: docs/controlled_drift_tree.html
Rerun any time to pull a fresh copy from live data.
"""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as ga

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TEMPLATE_PATH = os.path.join(HERE, "surface_template.html")
DEFAULT_OUT = os.path.join(REPO, "docs", "controlled_drift_tree.html")

# ---- system/structural fields hidden from the surface (matched by display name) ----
SKIP_NAMES = {"Created by", "Creation date", "Last opened date", "Last modified date",
              "Last modified by", "Last modified", "Backlinks", "Links", "Tag", "Assignee",
              "Status", "Added date", "Last opened", "Icon", "Foreground projects",
              "Goal link", "Parent project", "Linked Projects", "Project link"}
# display order; anything unlisted sorts to the end
PRIORITY = ["Task status", "Project status", "Goal status", "Engagement", "Goal engagement",
            "Side", "Done", "Due date", "Scheduled", "Deadline", "Horizon",
            "Interval unit", "Interval count", "Day of week", "Time of day", "Day of month",
            "Frequency",
            "Context", "Description", "Affective", "Reaching for", "Resolution condition",
            "Barriers", "Blocked on", "Needs clarifying", "Duration min",
            "Duration source", "Access conditions", "Access notes", "AI autonomous",
            "Depends on", "Relevant docs", "Arc position rationale", "Engagement notes",
            "Last surfaced"]
# the field she changes most, surfaced as an inline dropdown on the collapsed row
PRIMARY = {"Goal": "Goal engagement", "Project": "Engagement", "Task": "Task status",
           "Recurring": "Interval unit"}


def build(out_path=None):
    """Regenerate the surface HTML from live Anytype. Returns the output path.
    Importable so the local server (surface_serve.py) can trigger a rebuild."""
    out_path = out_path or DEFAULT_OUT
    sid = ga.get_space_id()
    objs = ga.fetch_all_objects(sid)
    byid = {o["id"]: o for o in objs}

    def tname(o):
        t = o.get("type"); return t.get("name") if isinstance(t, dict) else t
    def norm_ids(v):
        out = []
        if not v: return out
        if not isinstance(v, list): v = [v]
        for x in v:
            out.append(x if isinstance(x, str) else (x.get("id") or x.get("object") or x.get("target")))
        return [i for i in out if i]
    def short(oid): return oid[-6:]
    def objfield(o, key):
        p = next((p for p in o.get("properties", []) if p.get("key") == key), None)
        return norm_ids(p["objects"]) if p and "objects" in p else []
    def prio(name): return (PRIORITY.index(name) if name in PRIORITY else len(PRIORITY), name)

    # cache each type's property list; read select options once per property
    tprops = {t: ga.find_type(t).get("properties", []) for t in ("Goal", "Project", "Task", "Recurring")}
    def name_for(typ, key):
        for p in tprops.get(typ, []):
            if p.get("key") == key: return p.get("name")
        return None
    def tag_options(pid):
        _, b = ga.call("GET", "/spaces/%s/properties/%s/tags" % (sid, pid))
        return [t.get("name") for t in b.get("data", [])]

    def type_meta(typ):
        meta = {}
        for p in tprops[typ]:
            name, fmt = p.get("name"), p.get("format")
            if name in SKIP_NAMES: continue
            entry = {"format": fmt}
            if fmt in ("select", "multi_select"):
                entry["options"] = tag_options(p["id"])
            meta[name] = entry
        return meta
    fieldmeta = {t: type_meta(t) for t in ("Goal", "Project", "Task", "Recurring")}

    def render_val(p):
        for fk in ("text", "number", "url", "email", "phone"):
            if fk in p: return p[fk]
        if "checkbox" in p: return "yes" if p["checkbox"] else "no"
        if "select" in p:
            s = p["select"]; return s.get("name") if isinstance(s, dict) else s
        if "multi_select" in p:
            return ", ".join(x.get("name") for x in p["multi_select"] if isinstance(x, dict)) or None
        if "date" in p: return p["date"]
        if "objects" in p:
            nm = [byid.get(i, {}).get("name", "?") for i in norm_ids(p["objects"])]
            return ", ".join(n for n in nm if n) or None
        return None

    def fields_of(o, skip=None):
        typ = tname(o); meta = fieldmeta.get(typ, {})
        byname = {}
        for p in o.get("properties", []):
            nm = name_for(typ, p.get("key")) or p.get("name")
            if nm: byname[nm] = p
        out = []
        for name, m in meta.items():
            if skip and name == skip: continue
            p = byname.get(name)
            val = render_val(p) if p else None
            out.append({"name": name, "value": "" if val is None else str(val), "format": m["format"]})
        out.sort(key=lambda d: prio(d["name"]))
        return out

    def primary_of(o):
        typ = tname(o); field = PRIMARY.get(typ)
        if not field: return None
        val = ""
        for pr in o.get("properties", []):
            if name_for(typ, pr.get("key")) == field and "select" in pr:
                s = pr["select"]; val = s.get("name") if isinstance(s, dict) else (s or ""); break
        return {"field": field, "value": val or ""}

    goals = [o for o in objs if tname(o) == "Goal"]
    projects = [o for o in objs if tname(o) == "Project"]
    tasks = [o for o in objs if tname(o) == "Task"]
    recurrings = [o for o in objs if tname(o) == "Recurring"]

    tasks_by_proj = {}; orphan_tasks = []
    for t in tasks:
        pids = objfield(t, "linked_projects")
        if pids and pids[0] in byid: tasks_by_proj.setdefault(pids[0], []).append(t)
        else: orphan_tasks.append(t)
    # Recurring items (June, 2026-07-13: "I need to be able to see recurring tasks") — same
    # attach-by-linked-project pattern as tasks; a Recurring links via gsdo_project_link.
    recurring_by_proj = {}; orphan_recurrings = []
    for r in recurrings:
        pids = objfield(r, "gsdo_project_link")
        if pids and pids[0] in byid: recurring_by_proj.setdefault(pids[0], []).append(r)
        else: orphan_recurrings.append(r)
    children = {}; top = []
    for p in projects:
        par = objfield(p, "gsdo_parent_project")
        if par and par[0] in byid: children.setdefault(par[0], []).append(p)
        else: top.append(p)
    def proj_goal(p):
        g = objfield(p, "gsdo_goal_link"); return g[0] if g else None

    # ---- workstreams: never rendered inline as a project/subproject (June, 2026-07-13,
    # docs/map_design.md, "Workstreams are never rendered as projects/subprojects").
    # A workstream is an internal dev/research thread (e.g. "Route prioritization and
    # task breakdown" under Build Controlled Drift). Own checkbox wins; otherwise a
    # project inherits `true` from its nearest ancestor that has it set — same
    # walk-up-the-Parent-project-chain mechanism as Side inheritance in daily_plan.py,
    # and the same rule scripts/orient_map.py already applies to the text map.
    projects_by_id = {p["id"]: p for p in projects}

    def own_workstream(p):
        for pr in p.get("properties", []):
            if pr.get("key") == "is_workstream":
                return bool(pr.get("checkbox"))
        return False

    _ws_cache = {}
    def is_ws(p):
        pid = p["id"]
        if pid in _ws_cache: return _ws_cache[pid]
        _ws_cache[pid] = False  # cycle guard
        if own_workstream(p):
            result = True
        else:
            par = objfield(p, "gsdo_parent_project")
            parent = projects_by_id.get(par[0]) if par else None
            result = is_ws(parent) if parent is not None else False
        _ws_cache[pid] = result
        return result

    def base(o, level):
        prim = primary_of(o)
        return {"id": short(o["id"]), "fullId": o["id"], "type": tname(o), "level": level,
                "title": (o.get("name", "") or "").strip(), "primary": prim,
                "fields": fields_of(o, skip=prim["field"] if prim else None), "children": []}
    def node_task(t): return base(t, "TASK")
    def node_recurring(r): return base(r, "RECURRING")
    def node_proj(p, level="PROJECT"):
        """A workstream-tagged project is rendered through this SAME function (level=
        "WORKSTREAM" instead of "PROJECT"/"SUBPROJECT") — fully functional: editable
        title, fields, Move/Note/Delete, its own tasks and further-nested workstreams —
        just placed in `n["workstreams"]` instead of `n["children"]` so the frontend can
        group it under a visually distinct, separately-collapsible section rather than
        interleaving it with real projects/subprojects (June, 2026-07-13, docs/map_design.md).
        Corrected same day: a first pass made workstream entries name-only and read-only,
        which defeated the surface's whole purpose — June needs to WORK on this data,
        including moving tasks into their correct workstream. Any child of a workstream is
        itself guaranteed a workstream by inheritance, so `real_children` is naturally empty
        when called recursively for a workstream node — nesting falls out of this one function
        with no special-casing needed."""
        n = base(p, level)
        real_children = [c for c in children.get(p["id"], []) if not is_ws(c)]
        ws_children = [c for c in children.get(p["id"], []) if is_ws(c)]
        n["children"] = [node_proj(c, "SUBPROJECT") for c in real_children] + \
                        [node_task(t) for t in tasks_by_proj.get(p["id"], [])] + \
                        [node_recurring(r) for r in recurring_by_proj.get(p["id"], [])]
        if ws_children:
            n["workstreams"] = sorted([node_proj(c, "WORKSTREAM") for c in ws_children],
                                       key=lambda w: w["title"])
        return n
    def node_goal(g):
        n = base(g, "GOAL")
        n["children"] = [node_proj(p) for p in top_real if proj_goal(p) == g["id"]]
        return n

    # Top-level projects, split real vs. workstream (workstream-grain projects are marked
    # nested under a container per the spec, so a top-level workstream is an edge case —
    # handled below rather than assumed impossible).
    top_real = [p for p in top if not is_ws(p)]
    top_ws = [p for p in top if is_ws(p)]

    tree = [node_goal(g) for g in goals]
    nogoal = [p for p in top_real if proj_goal(p) is None]
    if nogoal:
        tree.append({"id": None, "fullId": None, "type": "GROUP", "level": "GROUP",
                     "title": "⚠ NO GOAL YET — projects not linked to a goal",
                     "primary": None, "fields": [], "children": [node_proj(p) for p in nogoal]})
    if orphan_tasks:
        tree.append({"id": None, "fullId": None, "type": "GROUP", "level": "GROUP",
                     "title": "⚠ NO PROJECT — orphan tasks", "primary": None,
                     "fields": [], "children": [node_task(t) for t in orphan_tasks]})
    if orphan_recurrings:
        tree.append({"id": None, "fullId": None, "type": "GROUP", "level": "GROUP",
                     "title": "⚠ NO PROJECT — orphan recurring items", "primary": None,
                     "fields": [], "children": [node_recurring(r) for r in orphan_recurrings]})
    if top_ws:
        # Unexpected shape (a workstream with no parent project at all) but handled so
        # nothing silently vanishes — still a fully functional WORKSTREAM node, same as
        # any nested case, just grouped here since it has no real ancestor to nest under.
        tree.append({"id": None, "fullId": None, "type": "GROUP", "level": "GROUP",
                     "title": "⚙ Workstreams with no parent project", "primary": None,
                     "fields": [], "children": [],
                     "workstreams": sorted([node_proj(p, "WORKSTREAM") for p in top_ws],
                                            key=lambda w: w["title"])})

    # Note: the flat "PARENTS" list (every goal/project in one array) that used to feed the
    # Move dropdown is gone (2026-07-13) — the Move picker now builds its hierarchy directly
    # from `tree` in JS (buildMoveTree/renderMoveTree in surface_template.html), since a flat
    # list of 60+ items was unusable as a dropdown.

    def js(o): return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    html = (template.replace("/*__DATA__*/", js(tree))
                    .replace("/*__FIELDMETA__*/", js(fieldmeta)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    ws_count = sum(1 for p in projects if is_ws(p))
    print("Wrote %s" % out_path)
    print("  goals=%d  projects=%d  tasks=%d  recurring=%d  orphan-tasks=%d  orphan-recurring=%d"
          "  goalless-top-projects=%d  workstream-projects=%d"
          % (len(goals), len(projects), len(tasks), len(recurrings), len(orphan_tasks),
             len(orphan_recurrings), len(nogoal), ws_count))
    print("  open it with:  open %s" % out_path)
    return out_path


def main():
    build(sys.argv[1] if len(sys.argv) > 1 else None)


if __name__ == "__main__":
    main()
