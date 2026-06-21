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
import sys, os, textwrap
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

# Layout: "   What it is:  value" — labels left-aligned, values aligned at one column.
# Wrapped continuation lines hang-indent to the value column so a wrap never
# collapses the visual organization.
#
# _WIDTH is deliberately conservative (not the 80-col default): the script's
# output is shown inside June's TUI, whose visible width is narrower than the
# raw terminal. If a line exceeds that visible width, the TUI re-wraps it at
# column 0 and the hanging indent is destroyed. 66 leaves margin for a narrow
# window. Determinism over cleverness — a fixed width renders the same everywhere.
_BASE = "   "
_LABEL_W = 11          # width of the widest label ("What it is:")
_VALUE_COL = len(_BASE) + _LABEL_W + 2   # column where values start (16)
_WIDTH = 66            # total line width (incl. the indent)


def _wrap(label, value):
    """Render 'label:  value', wrapping the whole line at _WIDTH with
    continuation lines hanging under the value column."""
    prefix = f"{_BASE}{label:<{_LABEL_W}}  "
    cont = " " * _VALUE_COL
    return textwrap.wrap(value, width=_WIDTH, initial_indent=prefix,
                         subsequent_indent=cont, break_on_hyphens=False,
                         break_long_words=False) or [prefix.rstrip()]


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
        return "●", "active"

def _is_done(stream):
    return _sel(_props(stream), "engagement") == "Done"

def _is_later(stream):
    return _sel(_props(stream), "engagement") == "Backburner"

def _stream_order(stream):
    """Soft-sequence override. Read by name — key is auto-generated.
    Streams sharing a number are parallel within their depth tier.
    Optional: when absent, parallel is the default."""
    by_name = {p.get("name"): p for p in stream.get("properties", [])}
    return (by_name.get("Stream order") or {}).get("number")

def _dep_ids(stream):
    """IDs of streams this stream hard-depends on — must be done before this one starts."""
    by_name = {p.get("name"): p for p in stream.get("properties", [])}
    raw = (by_name.get("Depends on") or {}).get("objects") or []
    return _id_list(raw)

def _arc_rationale(stream):
    """Plain-language reasoning for why this stream sits where it does in the arc.
    Written by the AI when proposing ordering; editable by June; shown in render_stream."""
    by_name = {p.get("name"): p for p in stream.get("properties", [])}
    return (by_name.get("Arc position rationale") or {}).get("text")


# ---------------------------------------------------------------------------
# Structured context parsing
# ---------------------------------------------------------------------------

def _parse_context(ctx):
    """Parse the structured format from gsdo_context.

    Looks for lines starting with:
      what it is —
      the arc   —   (optional; active streams)
      next step —

    Returns (what_it_is, the_arc, next_step); a missing line returns None.
    Splits only on the FIRST em-dash, so the value may contain its own dashes.
    """
    if not ctx:
        return None, None, None
    what_it_is = the_arc = next_step = None
    for line in ctx.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("what it is"):
            what_it_is = stripped.split("—", 1)[-1].strip() if "—" in stripped else None
        elif low.startswith("the arc"):
            the_arc = stripped.split("—", 1)[-1].strip() if "—" in stripped else None
        elif low.startswith("next step"):
            next_step = stripped.split("—", 1)[-1].strip() if "—" in stripped else None
    return what_it_is, the_arc, next_step

def _is_structured(ctx):
    what_it_is, _the_arc, next_step = _parse_context(ctx)
    return bool(what_it_is or next_step)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _header(stream):
    """The stream's title line: '● ACTIVE  Stream name'."""
    circle, label = _engagement_label(stream)
    return f"{circle} {label:<6}  {stream['name']}"

def _detail_lines(stream, tasks):
    """What it is (one line) + the arc (computed from ordered steps).

    No separate Next step line: the arc's → already points to where we are.
    See docs/map_design.md.
    """
    lines = []
    what_it_is, _arc_ignored, _next_ignored = _parse_context(_txt(_props(stream), "gsdo_context"))
    if what_it_is:
        lines += _wrap("What it is:", what_it_is)
    lines += _arc_lines(stream, tasks)
    return lines


# Step icons — uniform marker on every step of the arc.
_ICON_DONE = "✓"     # finished step
_ICON_HERE = "→"     # the step we're on now (also the "next" — no separate field)
_ICON_TODO = "☐"     # future step, not started

def _arc_lines(stream, tasks):
    """The arc: the stream's ordered steps, each marked done / here / todo.

    'Here' is the first not-done step; everything after it is todo. This is the
    deterministic 'where are we in it, what's left' view. Reads real step data —
    never hand-composed.
    """
    steps = _steps_for(stream["id"], tasks)
    if not steps:
        return []
    out = ["   The arc:"]
    here_marked = False
    for s in steps:
        if s["done"]:
            icon = _ICON_DONE
        elif not here_marked:
            icon = _ICON_HERE
            here_marked = True
        else:
            icon = _ICON_TODO
        out.append(f"      {icon} {s['name']}")
    return out


# ---------------------------------------------------------------------------
# Stream ordering — dependency-vs-sequence (parallel default)
# ---------------------------------------------------------------------------

def _topo_sort_streams(streams):
    """Sort streams with hard-dependency enforcement; parallel is the default.

    Returns (sorted_streams, depths) where depths maps stream_id → int.
    Depth 0 = no deps within this set; depth N = max(dep depths) + 1.
    Streams at the same depth have no ordering relationship — they are parallel.
    Within a depth tier, Stream order provides soft sequencing when present;
    when absent, streams sort by name (all remain parallel).

    Cycles in the dependency graph are broken gracefully: the cycle node is
    treated as depth 0 so rendering never crashes.
    """
    stream_ids = {s["id"] for s in streams}
    by_id = {s["id"]: s for s in streams}
    depths: dict = {}

    def _get_depth(sid, visiting=frozenset()):
        if sid in depths:
            return depths[sid]
        if sid in visiting:          # cycle — treat as root
            depths[sid] = 0
            return 0
        local_deps = [d for d in _dep_ids(by_id[sid]) if d in stream_ids]
        depths[sid] = (0 if not local_deps
                       else max(_get_depth(d, visiting | {sid}) for d in local_deps) + 1)
        return depths[sid]

    for s in streams:
        _get_depth(s["id"])

    def _sort_key(s):
        depth = depths.get(s["id"], 0)
        later = _is_later(s)     # active (False) sorts before later (True) at same depth
        order = _stream_order(s)
        return (depth, later, float("inf") if order is None else order, s["name"])

    return sorted(streams, key=_sort_key), depths


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
        by_name = {p.get("name"): p for p in o.get("properties", [])}
        # Task status lives under "Task status" (key gsdo_task_status), not "status".
        status_sel = (by_name.get("Task status") or {}).get("select") or {}
        status = status_sel.get("name") if isinstance(status_sel, dict) else None
        # The arc needs DONE steps too (to show ✓), so we keep done tasks here —
        # unlike the daily plan, which filters them out.
        done = (status == "Done") or bool((props.get("done") or {}).get("checkbox"))
        # linked_projects format is "objects" (plural); entries are object IDs
        # (sometimes dicts) — match streams by ID, not name.
        linked_ids = _id_list((props.get("linked_projects") or {}).get("objects"))
        # Step order read by NAME ("Step order") — its key is auto-generated.
        order = (by_name.get("Step order") or {}).get("number")
        tasks.append({"id": o["id"], "name": o.get("name", ""), "linked_ids": linked_ids,
                      "status": status, "done": done, "order": order})
    return goals, projects, tasks


def _id_list(raw):
    """Normalize an objects-relation value to a list of id strings."""
    out = []
    for x in raw or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict) and x.get("id"):
            out.append(x["id"])
    return out


def _steps_for(stream_id, tasks):
    """The stream's steps (tasks linked to it by id), ordered by Step order then name.

    Tasks with no Step order sort last (kept stable by name) so a stream that
    hasn't been ordered yet still renders sensibly.
    """
    steps = [t for t in tasks if stream_id in t["linked_ids"]]
    steps.sort(key=lambda t: (t["order"] is None, t["order"] if t["order"] is not None else 0,
                              t["name"]))
    return steps


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

    # Include done streams in the topo sort so active streams that depended on them
    # get correct depth values. Split for display: done streams show as a compact
    # trajectory line (✓ name · name) at the top; active streams render below.
    all_streams = [o for o in projects if pid in _objs(_props(o), "gsdo_parent_project")]
    all_sorted, depths = _topo_sort_streams(all_streams)
    done_sorted = [s for s in all_sorted if _is_done(s)]
    sorted_streams = [s for s in all_sorted if not _is_done(s)]

    lines = []

    # Goal header
    if goal:
        gp = _props(goal)
        hz = _sel(gp, "gsdo_horizon")
        rf = _txt(gp, "gsdo_reaching_for_(text)")
        hz_str = f"  ({hz.lower()})" if hz else ""
        lines.append(f"GOAL:  {goal['name']}{hz_str}")
        if rf:
            for piece in textwrap.wrap(rf, width=_WIDTH - 7) or [""]:
                lines.append(f"       {piece}")
        lines.append("")

    lines.append(f"THE ARC — {proj['name']}:")
    lines.append("")

    if done_sorted:
        names = " · ".join(s["name"] for s in done_sorted)
        lines.append(f"  ✓ {names}")
        lines.append("")

    if not sorted_streams:
        if not done_sorted:
            lines.append("  No work streams yet.")
        return "\n".join(lines).rstrip()

    # Build groups: consecutive streams at the same depth + same Stream order are parallel.
    groups = []
    i, n = 0, len(sorted_streams)
    while i < n:
        s = sorted_streams[i]
        cur_depth = depths.get(s["id"], 0)
        cur_order = _stream_order(s)
        j = i + 1
        while j < n:
            d2 = depths.get(sorted_streams[j]["id"], 0)
            o2 = _stream_order(sorted_streams[j])
            if d2 != cur_depth or o2 != cur_order:
                break
            j += 1
        groups.append((cur_depth, cur_order, sorted_streams[i:j]))
        i = j

    multi_group = len(groups) > 1

    for _depth, cur_order, group in groups:
        # Show "running alongside" when multiple streams are in this group AND either:
        # (a) there are multiple groups (some sequential structure to distinguish from), or
        # (b) an explicit Stream order was set (user chose to group them explicitly).
        # When everything is parallel by default (single group, no explicit order), the
        # separator adds no information and is omitted.
        if len(group) > 1 and (multi_group or cur_order is not None):
            lines.append("  — running alongside —")
        for s in group:
            lines.append(_header(s))
            if _is_later(s):
                # later stream — name + What it is only
                what_it_is, _, _ = _parse_context(_txt(_props(s), "gsdo_context"))
                if what_it_is:
                    lines += _wrap("What it is:", what_it_is)
            else:
                # active stream — What it is + its step-arc
                detail = _detail_lines(s, tasks)
                if detail:
                    lines.append("")
                    lines.extend(detail)
            lines.append("")

    return "\n".join(lines).rstrip()


def render_stream(stream_name):
    """Show one work stream in full — detail plus any sub-streams."""
    goals, projects, tasks = _load()
    s = next((o for o in projects if o.get("name") == stream_name), None)
    if s is None:
        return f"(no work stream named {stream_name!r} found)"

    lines = [_header(s)]
    rationale = _arc_rationale(s)
    if rationale:
        lines.append("")
        lines += _wrap("Why here:", rationale)
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


def gap_streams(project_name):
    """Like missing_descriptions, but returns full dicts so the fix-up pass can
    update each stream in place without re-querying every object one by one.

    Returns [{id, name, context, engagement}] for active streams that need a pass.
    """
    _, projects, _ = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    pid = proj["id"]
    out = []
    for s in projects:
        if pid not in _objs(_props(s), "gsdo_parent_project") or _is_done(s):
            continue
        ctx = _txt(_props(s), "gsdo_context")
        if not _is_structured(ctx):
            out.append({"id": s["id"], "name": s["name"], "context": ctx,
                        "engagement": _sel(_props(s), "engagement")})
    return out


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
