#!/usr/bin/env python3
"""Deterministic Orient map renderer.

Reads stored fields from Anytype — no LLM, no composition at render time.
The map is stable because the data is stable.

Each work stream stores two plain-language lines in gsdo_context:

    what it is — [one sentence: what this stream is, in plain words]
    next step  — [the single clear next move]

The renderer shows them like this (active stream):

    ● ACTIVE  Finish the daily-plan pipeline

       What it is:  takes a messy brain-dump and hands you back a real day
       Next step:   build the planning half — pick what matters, fit it to your day

       Tasks:
         · ...

A "later" stream shows just its name + What it is (no next step, no tasks).
A finished stream drops to the "Finished:" section, name only.

Register rules for what gets stored (enforced at entry, see SKILL.md):
  plain language · one sentence per line · no filenames · no jargon ·
  no coded status words. Written so June reads it at a glance.

Engagement drives the circle:
  Steady / Sprint / Hyperfixation / unset  →  ● ACTIVE
  Backburner                               →  ○ later
  Done                                     →  Finished section

IMPORTANT: this output is column-aligned monospace. Whoever shows it to June
MUST show it inside a code block, or the alignment collapses into mush.

Usage:
  python3 scripts/orient_map.py "Build Controlled Drift"
  python3 scripts/orient_map.py "Build Controlled Drift" --stream "stream name"
  python3 scripts/orient_map.py "Build Controlled Drift" --missing
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g


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
    """Parse the two-line structured format from gsdo_context.

    Looks for lines starting with:
      what it is —
      next step  —

    Returns (what_it_is, next_step); a missing line returns None.
    Splits only on the FIRST em-dash, so the value may contain its own dashes.
    """
    if not ctx:
        return None, None
    what_it_is = next_step = None
    for line in ctx.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("what it is"):
            what_it_is = stripped.split("—", 1)[-1].strip() if "—" in stripped else None
        elif low.startswith("next step"):
            next_step = stripped.split("—", 1)[-1].strip() if "—" in stripped else None
    return what_it_is, next_step

def _is_structured(ctx):
    what_it_is, next_step = _parse_context(ctx)
    return bool(what_it_is or next_step)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _header(stream):
    """The stream's title line: '● ACTIVE  Stream name'."""
    circle, label = _engagement_label(stream)
    return f"{circle} {label:<6}  {stream['name']}"

def _detail_lines(stream, tasks):
    """The indented What it is / Next step / Tasks block for an active stream."""
    lines = []
    ctx = _txt(_props(stream), "gsdo_context")
    what_it_is, next_step = _parse_context(ctx)

    if what_it_is:
        lines.append(f"   What it is:  {what_it_is}")
    if next_step:
        lines.append(f"   Next step:   {next_step}")

    stream_tasks = _tasks_for(stream["name"], tasks)
    if stream_tasks:
        if lines:
            lines.append("")
        lines.append("   Tasks:")
        for t in stream_tasks:
            flag = "  (needs clarifying)" if t["status"] == "Needs Clarifying" else ""
            lines.append(f"     · {t['name']}{flag}")

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

    lines.append(f"WORK STREAMS — {proj['name']}:")
    lines.append("")

    if not streams:
        lines.append("  No work streams yet.")
        return "\n".join(lines).rstrip()

    # Active streams — full detail + tasks
    for s in active:
        lines.append(_header(s))
        detail = _detail_lines(s, tasks)
        if detail:
            lines.append("")
            lines.extend(detail)
        lines.append("")

    # Later streams — name + What it is only
    for s in later:
        lines.append(_header(s))
        what_it_is, _ = _parse_context(_txt(_props(s), "gsdo_context"))
        if what_it_is:
            lines.append(f"   What it is:  {what_it_is}")
        lines.append("")

    # Finished — name only
    if done:
        lines.append("Finished:")
        for s in done:
            lines.append(f"   {s['name']}")

    return "\n".join(lines).rstrip()


def render_stream(stream_name):
    """Show one work stream in full — detail plus any sub-streams."""
    goals, projects, tasks = _load()
    s = next((o for o in projects if o.get("name") == stream_name), None)
    if s is None:
        return f"(no work stream named {stream_name!r} found)"

    lines = [_header(s)]
    detail = _detail_lines(s, tasks)
    if detail:
        lines.append("")
        lines.extend(detail)

    sid_val = s["id"]
    sub = [o for o in projects
           if sid_val in _objs(_props(o), "gsdo_parent_project")]
    sub_active = [x for x in sub if not _is_done(x) and not _is_later(x)]
    sub_done = [x for x in sub if _is_done(x)]

    if sub_active:
        lines.append("")
        lines.append("   Inside this stream:")
        for x in sub_active:
            lines.append(f"     {_header(x)}")
    if sub_done:
        lines.append("")
        lines.append("   Finished:")
        for x in sub_done:
            lines.append(f"     {x['name']}")

    return "\n".join(lines)


def missing_descriptions(project_name):
    """Return names of active work streams that need the structured description pass.

    A stream needs a pass if it has no context, or context not in the
    two-line format (what it is / next step). Done streams are excluded.
    """
    _, projects, _ = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    pid = proj["id"]
    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")
               and not _is_done(o)]
    return [s["name"] for s in streams
            if not _is_structured(_txt(_props(s), "gsdo_context"))]


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
