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
    Returns {"goal": obj|None, "goals": [obj,...], "projects": [obj,...], "binding": dict} or None.

    Handles both single-goal format (binds_to.goal) and multi-goal format (binds_to.goals).
    "goal" in the return dict is the first goal (for backwards compatibility); "goals" is all of them.
    """
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
    # Support both "goal" (single) and "goals" (multi-goal) formats
    if bt.get("goal"):
        goals = [g_obj for g_obj in [fetch(bt["goal"])] if g_obj]
    elif bt.get("goals"):
        goals = [g_obj for g_obj in (fetch(r) for r in bt["goals"]) if g_obj]
    else:
        goals = []
    goal = goals[0] if goals else None
    projects = [p for p in (fetch(r) for r in bt.get("projects", [])) if p]
    return {"goal": goal, "goals": goals, "projects": projects, "binding": b}


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


_CLAUDE_MD_MARKER = "## Controlled Drift binding"


def _write_claude_md(folder, project_name, goal_name=None):
    """Write or replace the Controlled Drift section in CLAUDE.md.

    Replaces an existing section rather than skipping it, so re-running
    bind refreshes stale agent instructions when the schema changes.
    """
    path = os.path.join(os.path.abspath(folder), "CLAUDE.md")
    goal_str = f" (Goal: {goal_name})" if goal_name else ""
    body = "\n".join([
        f"Bound to → Project: **{project_name}**{goal_str}.",
        "Capture any task/commitment mention here to Anytype under this project by default.",
        "The `drift` skill is active — orient, capture, weed, plan. June never names a function.",
        "Marker: `.gsdot` in this directory.",
        "",
        "**When creating a work stream (sub-project) here:**",
        "- Set `Depends on` (objects) for hard dependencies only — streams that genuinely",
        "  cannot start until another is done. Parallel is the default; leave unset when",
        "  there is no real dependency. The AI can propose candidates from context.",
        "- Write `Arc position rationale` (text) — full plain sentences (not a one-liner)",
        "  explaining where this stream sits in the project arc and why. Guard #6: June needs",
        "  to understand the reasoning, not just see the result. Stored here so it persists",
        "  across sessions without being re-derived.",
    ])

    def _build(before, after=""):
        sep = "\n\n" if before else ""
        tail = ("\n" + after.lstrip("\n")) if after else ""
        return before + sep + _CLAUDE_MD_MARKER + "\n\n" + body + "\n" + tail

    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        if _CLAUDE_MD_MARKER in content:
            # Replace existing section — re-running updates stale content
            idx = content.index(_CLAUDE_MD_MARKER)
            before = content[:idx].rstrip()
            rest = content[idx:]
            nxt = rest.find("\n## ", 1)
            after = "" if nxt == -1 else rest[nxt:]
            with open(path, "w") as f:
                f.write(_build(before, after))
        else:
            with open(path, "a") as f:
                f.write("\n\n" + _CLAUDE_MD_MARKER + "\n\n" + body + "\n")
    else:
        with open(path, "w") as f:
            f.write(_build(""))


def init_binding(folder, project_name, goal_id=None, goal_name=None,
                 goal_ids=None, goal_names=None,
                 parent_project_id=None, project_context=None, note=None):
    """Set up the Project (create if absent, idempotent) and write the marker.

    Supports single goal (goal_id + goal_name) or multiple goals (goal_ids + goal_names lists).
    goal_ids/goal_names take precedence if both are provided.

    Auto-detects a parent .gsdot (walking up from folder's parent) and sets
    Parent project on the new Project — no question asked, mirrors filesystem
    containment. Pass parent_project_id explicitly to override.

    Confirms with a live read-back before dinging (the operating guard).

    IMPORTANT: Always call this function for binding creation. Never write inline Python
    to create the .gsdot directly — this function handles read-back, CLAUDE.md, and ding.
    If this function doesn't support your case, surface the gap rather than working around it.
    """
    sid = g.get_space_id()

    # Normalize goal args — multi-goal takes precedence
    if goal_ids:
        _goal_ids = list(goal_ids)
        _goal_names = list(goal_names) if goal_names else [""] * len(_goal_ids)
    elif goal_id:
        _goal_ids = [goal_id]
        _goal_names = [goal_name or ""]
    else:
        _goal_ids = []
        _goal_names = []

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
        if _goal_ids:
            props["Goal link"] = _goal_ids
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
    if len(_goal_ids) == 1:
        binds_to["goal"] = {"id": _goal_ids[0], "name": _goal_names[0]}
    elif len(_goal_ids) > 1:
        binds_to["goals"] = [{"id": gid, "name": gname}
                              for gid, gname in zip(_goal_ids, _goal_names)]
    marker = {"system": "Controlled Drift", "binds_to": binds_to}
    if note:
        marker["note"] = note
    marker_path = os.path.join(os.path.abspath(folder), MARKER)
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)
        f.write("\n")
    print(f"  [marker] {marker_path}")

    # 4b. write or update CLAUDE.md at the folder root
    goal_name_display = " + ".join(n for n in _goal_names if n) or None
    _write_claude_md(folder, project_name, goal_name_display)
    print(f"  [claude.md] updated at {os.path.join(os.path.abspath(folder), 'CLAUDE.md')}")

    # 4. confirm + ding (only now)
    notify.ding()
    return {"project_id": pid, "marker_path": marker_path}


def repair_binding(folder):
    """Check a .gsdot binding for known issues and fix what can be fixed automatically.

    Checks:
    - .gsdot exists and is valid JSON
    - goals/goal field is readable by load_context()
    - CLAUDE.md has the Controlled Drift binding section
    - Project IDs in .gsdot resolve in Anytype

    Fixes automatically: missing CLAUDE.md section.
    Reports but does not auto-fix: missing/unresolvable project IDs (need init_binding re-run).
    """
    folder = os.path.abspath(folder)
    marker_path = find_marker(folder)
    if not marker_path:
        print(f"[error] no .gsdot found from {folder}")
        return

    print(f"[check] binding: {marker_path}")

    # 1. Parse .gsdot
    try:
        with open(marker_path) as f:
            marker = json.load(f)
    except Exception as e:
        print(f"[error] .gsdot is not valid JSON: {e}")
        return

    bt = marker.get("binds_to", {})

    # 2. Check goals
    if bt.get("goals"):
        print(f"[ok]    goals (multi): {[g.get('name') for g in bt['goals']]}")
    elif bt.get("goal"):
        print(f"[ok]    goal (single): {bt['goal'].get('name')}")
    else:
        print("[warn]  no goal or goals field — binding has no goal context")

    # 3. Check projects resolve in Anytype
    sid = g.get_space_id()
    for proj in bt.get("projects", []):
        pid, pname = proj.get("id"), proj.get("name")
        try:
            obj = call("GET", f"/spaces/{sid}/objects/{pid}")[1].get("object", {})
            if obj.get("name") == pname:
                print(f"[ok]    project resolves: {pname}")
            else:
                print(f"[warn]  project ID {pid[:12]} resolves to {obj.get('name')!r}, expected {pname!r}")
        except Exception as e:
            print(f"[error] project ID {pid[:12] if pid else '(none)'} did not resolve: {e}")

    # 4. Check + repair CLAUDE.md
    claude_path = os.path.join(os.path.dirname(marker_path), "CLAUDE.md")
    if os.path.isfile(claude_path):
        with open(claude_path) as f:
            content = f.read()
        if _CLAUDE_MD_MARKER in content:
            print(f"[ok]    CLAUDE.md has Controlled Drift binding section")
        else:
            print(f"[fix]   CLAUDE.md missing binding section — writing it now")
            projects = bt.get("projects", [])
            pname = projects[0]["name"] if projects else "(unknown project)"
            goals = bt.get("goals", []) or ([bt["goal"]] if bt.get("goal") else [])
            goal_display = " + ".join(g.get("name", "") for g in goals) or None
            _write_claude_md(os.path.dirname(marker_path), pname, goal_display)
            print(f"[ok]    CLAUDE.md binding section written")
    else:
        print(f"[fix]   no CLAUDE.md found — creating it")
        projects = bt.get("projects", [])
        pname = projects[0]["name"] if projects else "(unknown project)"
        goals = bt.get("goals", []) or ([bt["goal"]] if bt.get("goal") else [])
        goal_display = " + ".join(g.get("name", "") for g in goals) or None
        _write_claude_md(os.path.dirname(marker_path), pname, goal_display)
        print(f"[ok]    CLAUDE.md created")

    print("[done]  repair check complete")


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

    p_repair = sub.add_parser("repair", help="check binding for issues and fix what can be fixed automatically")
    p_repair.add_argument("folder", nargs="?", default=None)

    args = ap.parse_args()
    if args.cmd == "show":
        ctx = load_context(args.folder)
        if not ctx:
            print(f"no {MARKER} binding found from {os.path.abspath(args.folder or os.getcwd())}")
        else:
            b = ctx["binding"]
            print(f"binding: {b['_marker_path']}")
            if ctx["goals"]:
                for g_obj in ctx["goals"]:
                    print(f"  goal:    {g_obj.get('name')}")
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
    elif args.cmd == "repair":
        repair_binding(args.folder or os.getcwd())
    else:
        ap.print_help()
