#!/usr/bin/env python3
"""Deterministic Orient map renderer.

Reads stored fields from Anytype — no LLM, no composition at render time.
The map is stable because the data is stable.

Each work stream has three stored description lines:

    what it's doing — [the purpose of this stream]
    where we are    — [current status]
    where it goes   — [next direction]

These are written once (by the Orient function when it helps set up a stream)
and read back verbatim every time. If a stream doesn't have the structured
format yet, its raw context is shown and it's flagged as needing a pass.

Visual format:

    ● ACTIVE   Stream name
               what it's doing — ...
               where we are    — ...
               where it goes   — ...

    ○ later    Stream name
               what it's doing — ...

Engagement drives the ●/○ label:
  Steady / Sprint / Hyperfixation / unset  →  ● ACTIVE
  Backburner                               →  ○ later
  Done                                     →  shown in Finished section, no detail

Usage:
  python3 scripts/orient_map.py "Build Controlled Drift"
  python3 scripts/orient_map.py "Build Controlled Drift" --stream "stream name"
  python3 scripts/orient_map.py "Build Controlled Drift" --missing
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

# Column where the stream name starts (after "  ● ACTIVE   ")
_NAME_COL = 14


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Engagement → display label
# ---------------------------------------------------------------------------

def _engagement_label(stream):
    """Return (circle, label_text) for a stream based on its Engagement field."""
    eng = _sel(_props(stream), "engagement")
    if eng == "Done":
        return "✓", "done"
    elif eng == "Backburner":
        return "○", "later"
    else:
        return "●", "ACTIVE"

def _is_done(stream):
    return _sel(_props(stream), "engagement") == "Done"

def _is_later(stream):
    return _sel(_props(stream), "engagement") == "Backburner"


# ---------------------------------------------------------------------------
# Structured context parsing
# ---------------------------------------------------------------------------

def _parse_context(ctx):
    """Parse the three-line structured format from gsdo_context.

    Looks for lines starting with:
      what it's doing —
      where we are    —
      where it goes   —

    Returns (doing, here, nxt). Any missing line returns None.
    If none of the three labels are found, returns (None, None, None) —
    indicating unstructured context that needs a pass.
    """
    if not ctx:
        return None, None, None
    doing = here = nxt = None
    for line in ctx.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("what it's doing"):
            doing = stripped.split("—", 1)[-1].strip() if "—" in stripped else stripped
        elif low.startswith("where we are"):
            here = stripped.split("—", 1)[-1].strip() if "—" in stripped else stripped
        elif low.startswith("where it goes"):
            nxt = stripped.split("—", 1)[-1].strip() if "—" in stripped else stripped
    return doing, here, nxt

def _is_structured(ctx):
    doing, here, nxt = _parse_context(ctx)
    return bool(doing or here or nxt)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _stream_block(stream, show_detail=True):
    """Render one stream as a block of lines."""
    circle, label = _engagement_label(stream)
    sp = _props(stream)
    ctx = _txt(sp, "gsdo_context")

    # Header line: "  ● ACTIVE   Stream name"
    prefix = f"  {circle} {label}"
    pad = " " * max(1, _NAME_COL - len(prefix))
    header = f"{prefix}{pad}{stream['name']}"

    lines = [header]

    if not show_detail:
        return lines

    desc_indent = " " * _NAME_COL

    doing, here, nxt = _parse_context(ctx)

    if doing or here or nxt:
        if doing:
            lines.append(f"{desc_indent}what it's doing — {doing}")
        if here:
            lines.append(f"{desc_indent}where we are    — {here}")
        if nxt:
            lines.append(f"{desc_indent}where it goes   — {nxt}")
    # Unstructured context is not shown in the map — it's noise until the
    # structured pass runs. missing_descriptions() will flag it.

    return lines


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load():
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    goals = [o for o in objs if _tkey(o) == "gsdo_goal"]
    projects = [o for o in objs if _tkey(o) == "gsdo_project"]
    tasks = []
    for o in objs:
        if _tkey(o) != "task":
            continue
        props = {p.get("key"): p for p in o.get("properties", [])}
        status_sel = (props.get("status") or {}).get("select") or {}
        status = status_sel.get("name") if isinstance(status_sel, dict) else None
        if status not in (None, "Active", "Needs Clarifying"):
            continue
        if (props.get("done") or {}).get("checkbox"):
            continue
        # linked_projects uses "object" (singular) — returns list of {id, name} dicts
        linked_raw = (props.get("linked_projects") or {}).get("object") or []
        linked = [lp.get("name") for lp in linked_raw
                  if isinstance(lp, dict) and lp.get("name")]
        tasks.append({"id": o["id"], "name": o.get("name", ""), "linked": linked,
                      "status": status})
    return goals, projects, tasks


def _tasks_for(stream_name, tasks):
    """Return tasks whose linked_projects includes this stream's name."""
    return [t for t in tasks if stream_name in t["linked"]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_map(project_name):
    """Render the full map for a parent project."""
    goals, projects, tasks = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return f"(no project named {project_name!r} found)"

    pid = proj["id"]
    pprops = _props(proj)
    goal_ids = _objs(pprops, "gsdo_goal_link")
    goal = next((o for o in goals if o["id"] in goal_ids), None)

    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")]

    active = [s for s in streams if not _is_done(s) and not _is_later(s)]
    later = [s for s in streams if _is_later(s)]
    done = [s for s in streams if _is_done(s)]

    lines = []

    # Goal header
    if goal:
        gp = _props(goal)
        hz = _sel(gp, "gsdo_horizon")
        rf = _txt(gp, "gsdo_reaching_for_(text)")
        hz_str = f"  ({hz.lower()})" if hz else ""
        lines.append(f"GOAL:  {goal['name']}{hz_str}")
        if rf:
            lines.append(f"       {rf}")
        lines.append("")

    lines.append(f"WORK STREAMS — the work of {proj['name']}:")
    lines.append("")

    if not streams:
        lines.append("  No work streams yet.")
    else:
        task_indent = " " * (_NAME_COL + 2)
        for s in active:
            lines.extend(_stream_block(s))
            # Show tasks under ACTIVE streams — this is the "what's in here right now"
            stream_tasks = _tasks_for(s["name"], tasks)
            if stream_tasks:
                lines.append(f"{task_indent}Tasks:")
                for t in stream_tasks:
                    flag = " (needs clarifying)" if t["status"] == "Needs Clarifying" else ""
                    lines.append(f"{task_indent}  · {t['name']}{flag}")
            lines.append("")
        for s in later:
            lines.extend(_stream_block(s))
            lines.append("")
        if done:
            lines.append("Finished:")
            for s in done:
                lines.extend(_stream_block(s, show_detail=False))

    return "\n".join(lines).rstrip()


def render_stream(stream_name):
    """Show one work stream in full — description plus any sub-streams."""
    goals, projects, tasks = _load()
    s = next((o for o in projects if o.get("name") == stream_name), None)
    if s is None:
        return f"(no work stream named {stream_name!r} found)"

    sid_val = s["id"]
    sub = [o for o in projects
           if sid_val in _objs(_props(o), "gsdo_parent_project")]
    sub_active = [x for x in sub if not _is_done(x) and not _is_later(x)]
    sub_later = [x for x in sub if _is_later(x)]
    sub_done = [x for x in sub if _is_done(x)]

    lines = _stream_block(s)

    if sub_active or sub_later:
        lines.append("")
        lines.append("  Inside this stream:")
        for x in sub_active:
            lines.extend("    " + l for l in _stream_block(x))
            lines.append("")
        for x in sub_later:
            lines.extend("    " + l for l in _stream_block(x))
            lines.append("")

    if sub_done:
        lines.append("  Finished:")
        for x in sub_done:
            lines.extend("    " + l for l in _stream_block(x, show_detail=False))

    return "\n".join(lines)


def missing_descriptions(project_name):
    """Return names of active work streams that need the structured description pass.

    A stream needs a pass if it has no context, or context that doesn't use
    the three-line format (what it's doing / where we are / where it goes).
    Done streams are excluded — they're finished.
    """
    _, projects, _ = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    pid = proj["id"]
    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")
               and not _is_done(o)]
    result = []
    for s in streams:
        ctx = _txt(_props(s), "gsdo_context")
        if not ctx or not _is_structured(ctx):
            result.append(s["name"])
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Deterministic Orient map renderer")
    ap.add_argument("project", nargs="?", default="Build Controlled Drift")
    ap.add_argument("--stream", default=None, help="open one work stream by name")
    ap.add_argument("--missing", action="store_true",
                    help="list streams that need the structured description pass")
    args = ap.parse_args()

    if args.missing:
        names = missing_descriptions(args.project)
        if names:
            print(f"Streams needing structured description ({args.project!r}):")
            for n in names:
                print(f"  {n}")
        else:
            print("All active streams have structured descriptions.")
    elif args.stream:
        print(render_stream(args.stream))
    else:
        print(render_map(args.project))
