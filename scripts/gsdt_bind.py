#!/usr/bin/env python3
"""Directory-level binding for Controlled Drift (AI_LAYER_SPEC.md §8h).

The drift skill is global but location-blind. A binding marker file ties a
folder to a slice of the Anytype graph (a Goal and/or Project) so that *being
in that folder* auto-contextualizes the system: capture lands pre-aligned, the
weeding alignment step starts from the right cluster, planning is scoped.

Marker format (.gsdot):
  {"system": "Controlled Drift",
   "binds_to": {"goal": {"id": "...", "name": "Material survival"},
                "projects": [{"id": "...", "name": "..."}]}}

Two halves:
  - WORKFLOW: `init_binding(...)` sets up the Project (creates or links it) AND
    integrates the folder (writes the marker, confirms with read-back + ding).
    Auto-detects a parent .gsdot and sets parent_project on the new Project.
  - CODE: `read_binding()` / `load_context()` resolve the nearest marker on
    startup and hand back the bound slice for an instance to pre-load.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import gsdo_anytype as g
import gsdo_objects as o
import notify

MARKER = ".gsdot"


# ---- CODE half: resolve a folder -> its bound slice ----

def find_marker(start_dir=None):
    """Walk up from start_dir (default cwd) to find the nearest MARKER file."""
    d = os.path.abspath(start_dir or os.getcwd())
    while True:
        candidate = os.path.join(d, MARKER)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def read_binding(start_dir=None):
    """Return the parsed marker dict for the nearest binding, or None."""
    path = find_marker(start_dir)
    if not path:
        return None
    with open(path) as f:
        b = json.load(f)
    b["_marker_path"] = path
    return b


def load_context(start_dir=None):
    """Resolve the bound Goal/Projects live from Anytype (the slice to pre-load).
    Returns {"goal": obj|None, "projects": [obj,...], "binding": dict} or None."""
    b = read_binding(start_dir)
    if not b:
        return None
    sid = g.get_space_id()

    def fetch(ref):
        oid = ref.get("id")
        if not oid:
            return None
        return call("GET", f"/spaces/{sid}/objects/{oid}")[1].get("object")

    bt = b.get("binds_to", {})
    goal = fetch(bt["goal"]) if bt.get("goal") else None
    projects = [p for p in (fetch(r) for r in bt.get("projects", [])) if p]
    return {"goal": goal, "projects": projects, "binding": b}


# ---- WORKFLOW half: set up a Project + integrate the folder ----

def _existing_project(name):
    sid = g.get_space_id()
    pkey = (g.find_type("Project") or {}).get("key")
    for obj in g.fetch_all_objects(sid):
        ot = obj.get("type"); ot = ot.get("key") if isinstance(ot, dict) else ot
        if obj.get("name") == name and (pkey is None or ot == pkey):
            return obj.get("id")
    return None


def _detect_parent_project_id(folder):
    """Walk up from dirname(folder) to find a parent .gsdot; return its first project id."""
    parent_dir = os.path.dirname(os.path.abspath(folder))
    parent_binding = read_binding(parent_dir)
    if not parent_binding:
        return None
    projects = parent_binding.get("binds_to", {}).get("projects", [])
    return projects[0]["id"] if projects else None


def init_binding(folder, project_name, goal_id=None, goal_name=None,
                 parent_project_id=None, project_context=None, note=None):
    """Set up the Project (create if absent, idempotent) and write the marker.

    Auto-detects a parent .gsdot (walking up from folder's parent) and sets
    Parent project on the new Project — no question asked, mirrors filesystem
    containment. Pass parent_project_id explicitly to override.

    Confirms with a live read-back before dinging (the operating guard).
    """
    sid = g.get_space_id()

    # Auto-detect parent if not provided
    if parent_project_id is None:
        parent_project_id = _detect_parent_project_id(folder)
        if parent_project_id:
            print(f"  [parent] detected parent project {parent_project_id[:12]}")

    # 1. set up the Project (create or reuse)
    pid = _existing_project(project_name)
    if pid:
        print(f"  [reuse] Project {project_name!r} ({pid[:12]})")
    else:
        props = {"Engagement": "Steady"}
        if goal_id:
            props["Goal link"] = [goal_id]
        if parent_project_id:
            props["Parent project"] = [parent_project_id]
        if project_context:
            props["Context"] = project_context
        pid = o.create("Project", project_name, properties=props)
        print(f"  [new]   Project {project_name!r} -> {pid[:12]}")

    # 2. READ-BACK — prove it persisted before we claim success
    obj = call("GET", f"/spaces/{sid}/objects/{pid}")[1].get("object", {})
    if obj.get("name") != project_name:
        raise RuntimeError(f"read-back FAILED for Project {project_name!r}: {obj}")

    # 3. integrate the folder — write the marker
    binds_to = {"projects": [{"id": pid, "name": project_name}]}
    if goal_id:
        binds_to["goal"] = {"id": goal_id, "name": goal_name}
    marker = {"system": "Controlled Drift", "binds_to": binds_to}
    if note:
        marker["note"] = note
    marker_path = os.path.join(os.path.abspath(folder), MARKER)
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)
        f.write("\n")
    print(f"  [marker] {marker_path}")

    # 4. confirm + ding (only now)
    notify.ding()
    return {"project_id": pid, "marker_path": marker_path}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Controlled Drift directory binding")
    sub = ap.add_subparsers(dest="cmd")

    p_show = sub.add_parser("show", help="show the binding resolved from a folder")
    p_show.add_argument("folder", nargs="?", default=None)

    p_init = sub.add_parser("init", help="set up a Project + write the marker")
    p_init.add_argument("folder")
    p_init.add_argument("--project", required=True)
    p_init.add_argument("--goal-id", default=None)
    p_init.add_argument("--goal-name", default=None)
    p_init.add_argument("--parent-project-id", default=None)
    p_init.add_argument("--context", default=None)
    p_init.add_argument("--note", default=None)

    args = ap.parse_args()
    if args.cmd == "show":
        ctx = load_context(args.folder)
        if not ctx:
            print(f"no {MARKER} binding found from {os.path.abspath(args.folder or os.getcwd())}")
        else:
            b = ctx["binding"]
            print(f"binding: {b['_marker_path']}")
            if ctx["goal"]:
                print(f"  goal:    {ctx['goal'].get('name')}")
            for p in ctx["projects"]:
                print(f"  project: {p.get('name')}")
            if b.get("note"):
                print(f"  note:    {b['note']}")
    elif args.cmd == "init":
        init_binding(args.folder, args.project, goal_id=args.goal_id,
                     goal_name=args.goal_name,
                     parent_project_id=args.parent_project_id,
                     project_context=args.context, note=args.note)
        print("[done] binding set up")
    else:
        ap.print_help()
