#!/usr/bin/env python3
"""Deterministic Orient map renderer.

Reads stored fields from Anytype and formats them — no LLM, no interpretation.
The map is stable because the data is stable, not because an instance nailed the
register.

What the map shows:
  - Goal header (name + reaching_for)
  - All work streams under the parent project, each with its stored context
    (gsdo_context field) as the description
  - Non-finished streams first; streams marked Done in a plain "Finished:" section

What the map does NOT do:
  - Encode status as symbols or one-word codes
  - Filter based on an Engagement value (Done is the only structural distinction)
  - Compose or interpret anything — it shows what is stored

If a stream has no context yet, it shows just the name. That is a signal for the
Orient function to offer to help write the description — not a display problem to
pad over.

Usage:
  python3 scripts/orient_map.py "Build Controlled Drift"
  python3 scripts/orient_map.py "Build Controlled Drift" --stream "a stream name"
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g


def _props(o):
    return {p.get("key"): p for p in o.get("properties", [])}

def _sel(props, key):
    v = props.get(key) or {}
    s = v.get("select") if isinstance(v, dict) else None
    return s.get("name") if isinstance(s, dict) and s else None

def _txt(props, key):
    v = props.get(key) or {}
    return v.get("text") if isinstance(v, dict) else None

def _objs(props, key):
    v = props.get(key) or {}
    return (v.get("objects") or []) if isinstance(v, dict) else []

def _tkey(o):
    t = o.get("type")
    return t.get("key") if isinstance(t, dict) else t

def _is_done(stream):
    return _sel(_props(stream), "engagement") == "Done"


def _load():
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    goals = [o for o in objs if _tkey(o) == "gsdo_goal"]
    projects = [o for o in objs if _tkey(o) == "gsdo_project"]
    return goals, projects


def render_map(project_name):
    """Render the full map for a parent project — all work streams with descriptions."""
    goals, projects = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return f"(no project named {project_name!r} found)"
    pid = proj["id"]
    pprops = _props(proj)
    goal_ids = _objs(pprops, "gsdo_goal_link")
    goal = next((o for o in goals if o["id"] in goal_ids), None)

    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")]

    current = [s for s in streams if not _is_done(s)]
    finished = [s for s in streams if _is_done(s)]

    lines = []

    if goal:
        gp = _props(goal)
        rf = _txt(gp, "gsdo_reaching_for_(text)")
        lines.append(f"Goal: {goal['name']}")
        if rf:
            lines.append(f"  {rf}")
        lines.append("")

    lines.append(f"Work streams — {proj['name']}:")
    lines.append("")

    if not streams:
        lines.append("  No work streams yet.")
    else:
        for s in current:
            sp = _props(s)
            ctx = _txt(sp, "gsdo_context")
            lines.append(s["name"])
            if ctx:
                lines.append(f"  {ctx}")
            lines.append("")

        if finished:
            lines.append("Finished:")
            for s in finished:
                sp = _props(s)
                ctx = _txt(sp, "gsdo_context")
                lines.append(f"  {s['name']}")
                if ctx:
                    lines.append(f"    {ctx}")
            lines.append("")

    return "\n".join(lines).strip()


def render_stream(stream_name):
    """Show one work stream in full — its description plus any sub-streams."""
    goals, projects = _load()
    s = next((o for o in projects if o.get("name") == stream_name), None)
    if s is None:
        return f"(no work stream named {stream_name!r} found)"

    sp = _props(s)
    ctx = _txt(sp, "gsdo_context")
    sid_val = s["id"]

    sub = [o for o in projects
           if sid_val in _objs(_props(o), "gsdo_parent_project")]
    sub_current = [x for x in sub if not _is_done(x)]
    sub_finished = [x for x in sub if _is_done(x)]

    lines = [s["name"]]
    if ctx:
        lines.append("")
        lines.append(ctx)

    if sub_current:
        lines.append("")
        lines.append("Inside this stream:")
        for x in sub_current:
            xp = _props(x)
            xctx = _txt(xp, "gsdo_context")
            lines.append(f"  {x['name']}")
            if xctx:
                lines.append(f"    {xctx}")

    if sub_finished:
        lines.append("")
        lines.append("Finished:")
        for x in sub_finished:
            lines.append(f"  {x['name']}")

    return "\n".join(lines)


def missing_descriptions(project_name):
    """Return names of work streams that have no stored context — signals for the
    Orient function to offer to help write them."""
    _, projects = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    pid = proj["id"]
    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")
               and not _is_done(o)]
    return [s["name"] for s in streams
            if not _txt(_props(s), "gsdo_context")]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Deterministic Orient map renderer")
    ap.add_argument("project", nargs="?", default="Build Controlled Drift")
    ap.add_argument("--stream", default=None, help="open one work stream by name")
    ap.add_argument("--missing", action="store_true",
                    help="list streams with no stored description")
    args = ap.parse_args()

    if args.missing:
        names = missing_descriptions(args.project)
        if names:
            print(f"Work streams with no description yet ({args.project!r}):")
            for n in names:
                print(f"  {n}")
        else:
            print("All work streams have descriptions.")
    elif args.stream:
        print(render_stream(args.stream))
    else:
        print(render_map(args.project))
