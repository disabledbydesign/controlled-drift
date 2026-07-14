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

IMPORTANT: the skeleton map (`--skeleton`) is column-aligned monospace. Whoever
shows it to June MUST show it inside a code block, or the alignment collapses.

TWO AUDIENCES, TWO RENDERERS (2026-07-13):
  - render_map_agent() — the CLI DEFAULT. A full, labeled, per-stream dump of every
    stored field + per-task status, for an AGENT asked to orient / assess what's open.
    June never runs this script herself, so the default serves the agent, not her.
  - render_map() / render_stream() — the JUNE-FACING register: terse, plain-language,
    one line per field, monospace (the "skeleton" view). Reached via `--skeleton` on
    the CLI, and imported directly by the drift skill for her operating flow (unchanged).

Usage:
  python3 scripts/orient_map.py "Build Controlled Drift"              # agent dump (default)
  python3 scripts/orient_map.py "Build Controlled Drift" --skeleton   # June's terse map
  python3 scripts/orient_map.py "Build Controlled Drift" --skeleton --stream "stream name"
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

def _any_field(o, label):
    """Read any field by its DISPLAY NAME regardless of format (used by render_map_agent,
    which needs every stored field, not just the handful render_map's June-facing register
    surfaces). Robust to Anytype-auto-generated keys the rest of this file works around by
    name (Engagement, Side, Arc position rationale, ...) — this generalizes that pattern to
    any field rather than hand-listing keys one at a time."""
    for p in o.get("properties", []):
        if p.get("name") != label:
            continue
        if "select" in p:
            v = p["select"]
            return v.get("name") if isinstance(v, dict) else v
        if "multi_select" in p:
            return [x.get("name") if isinstance(x, dict) else x for x in (p.get("multi_select") or [])]
        if "objects" in p:
            return p.get("objects") or []
        for k in ("text", "number", "date", "checkbox"):
            if k in p:
                return p[k]
    return None


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

def _is_workstream_own(stream):
    """This project's own Is-workstream checkbox (key is predictable: is_workstream)."""
    return bool(_props(stream).get("is_workstream", {}).get("checkbox"))

def _is_workstream(stream, all_projects, _by_id=None):
    """A workstream is never rendered inline as a project/subproject (June, 2026-07-13,
    docs/map_design.md). Own checkbox wins; otherwise inherited from the nearest ancestor
    that has it set — same walk-up-the-Parent-project-chain mechanism as Side inheritance
    in scripts/daily_plan.py, so a newly nested sub-workstream needs no hand-tagging."""
    if _by_id is None:
        _by_id = {p["id"]: p for p in all_projects}
    seen, cur = set(), stream
    while True:
        if _is_workstream_own(cur):
            return True
        parents = _objs(_props(cur), "gsdo_parent_project")
        if not parents or cur["id"] in seen:
            return False
        seen.add(cur["id"])
        cur = _by_id.get(parents[0])
        if cur is None:
            return False

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

def _children_of(parent_id, all_projects):
    """Return all NON-workstream projects whose Parent project includes parent_id.

    Workstreams are excluded here (not just filtered at the top of render_map) so every
    consumer of this function — render_map, render_stream, _all_sub_projects — inherits
    the same rule automatically: a workstream never appears inline in the project tree,
    at any depth. See docs/map_design.md."""
    return [p for p in all_projects
            if parent_id in _objs(_props(p), "gsdo_parent_project")
            and not _is_workstream(p, all_projects)]


def _workstream_descendants(parent_id, all_projects):
    """All workstream-tagged (including inherited) projects anywhere under parent_id,
    for the compact summary section — deliberately terse (names only, no arc/detail),
    so it reads as a structurally different kind of list, not more streams to parse."""
    direct = [p for p in all_projects
              if parent_id in _objs(_props(p), "gsdo_parent_project")]
    out = [p for p in direct if _is_workstream(p, all_projects)]
    for child in direct:
        out.extend(_workstream_descendants(child["id"], all_projects))
    return out


def _append_flat_streams(lines, active_sorted, tasks, depths):
    """Render active/later streams as a flat topo-ordered list (no groupings)."""
    groups = []
    i, n = 0, len(active_sorted)
    while i < n:
        s = active_sorted[i]
        cur_depth = depths.get(s["id"], 0)
        cur_order = _stream_order(s)
        j = i + 1
        while j < n:
            d2 = depths.get(active_sorted[j]["id"], 0)
            o2 = _stream_order(active_sorted[j])
            if d2 != cur_depth or o2 != cur_order:
                break
            j += 1
        groups.append((cur_depth, cur_order, active_sorted[i:j]))
        i = j

    multi_group = len(groups) > 1

    for _depth, cur_order, group in groups:
        # Show "running alongside" when multiple streams are in this group AND either:
        # (a) there are multiple groups (some sequential structure to distinguish from), or
        # (b) an explicit Stream order was set (user chose to group them explicitly).
        if len(group) > 1 and (multi_group or cur_order is not None):
            lines.append("  — running alongside —")
        for s in group:
            lines.append(_header(s))
            if _is_later(s):
                what_it_is, _, _ = _parse_context(_txt(_props(s), "gsdo_context"))
                if what_it_is:
                    lines += _wrap("What it is:", what_it_is)
            else:
                detail = _detail_lines(s, tasks)
                if detail:
                    lines.append("")
                    lines.extend(detail)
            lines.append("")


def _append_grouped_streams(lines, active_sorted, grouping_ids, all_projects, tasks):
    """Render streams with grouping structure.

    Groupings (sub-projects that have their own children) appear as section
    headers; their children are shown indented inside them. Leaf streams at
    the top level render normally alongside grouping sections.
    """
    for s in active_sorted:
        lines.append(_header(s))
        if s["id"] in grouping_ids:
            # Section: show children inside the grouping
            children = _children_of(s["id"], all_projects)
            children_sorted, _ = _topo_sort_streams(children)
            done_ch = [c for c in children_sorted if _is_done(c)]
            active_ch = [c for c in children_sorted if not _is_done(c)]
            lines.append("")
            if done_ch:
                cnames = " · ".join(c["name"] for c in done_ch)
                lines.append(f"     ✓ {cnames}")
                lines.append("")
            for c in active_ch:
                lines.append("  " + _header(c))
                if _is_later(c):
                    what_it_is, _, _ = _parse_context(_txt(_props(c), "gsdo_context"))
                    if what_it_is:
                        for ln in _wrap("What it is:", what_it_is):
                            lines.append("  " + ln)
                else:
                    what_it_is, _, _ = _parse_context(_txt(_props(c), "gsdo_context"))
                    if what_it_is:
                        lines.append("")
                        for ln in _wrap("What it is:", what_it_is):
                            lines.append("  " + ln)
                    arc = _arc_lines(c, tasks)
                    if arc:
                        lines.append("")
                        for ln in arc:
                            lines.append("  " + ln)
                lines.append("")
        else:
            # Leaf stream at top level — render normally
            if _is_later(s):
                what_it_is, _, _ = _parse_context(_txt(_props(s), "gsdo_context"))
                if what_it_is:
                    lines += _wrap("What it is:", what_it_is)
            else:
                detail = _detail_lines(s, tasks)
                if detail:
                    lines.append("")
                    lines.extend(detail)
            lines.append("")


def render_map(project_name):
    """Render the full map for a parent project.

    When direct sub-projects have their own children (groupings), the map
    renders them as phase sections with streams inside — mirroring the
    repo's organizational structure. Without groupings, streams render flat.
    """
    goals, projects, tasks = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return f"(no project named {project_name!r} found)"

    pid = proj["id"]
    pprops = _props(proj)
    goal_ids = _objs(pprops, "gsdo_goal_link")
    goal = next((o for o in goals if o["id"] in goal_ids), None)

    # Workstreams — never shown inline in the tree below (docs/map_design.md, 2026-07-13).
    # Computed up front so the "no [real] work streams" message can be worded honestly: a
    # project can be ALL workstreams (e.g. Build Controlled Drift) and still have plenty to
    # show — saying "no work streams yet" right above a list of 12 of them read as a bug
    # (June, 2026-07-13), which it was.
    workstreams = sorted(_workstream_descendants(pid, projects), key=lambda s: s["name"])

    # Direct sub-projects (groupings or leaf streams) — workstreams excluded, see _children_of
    all_direct = _children_of(pid, projects)

    # Detect groupings: direct children that have their own children
    grouping_ids = {s["id"] for s in all_direct if _children_of(s["id"], projects)}

    # Include done items in topo sort so active items depending on them get
    # correct depth values. Split for display after.
    all_sorted, depths = _topo_sort_streams(all_direct)
    done_sorted = [s for s in all_sorted if _is_done(s)]
    active_sorted = [s for s in all_sorted if not _is_done(s)]

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

    lines.append(f"  {proj['name']}")
    lines.append("")

    def _finish():
        # Deliberately terse section: names only, no circle/arc/detail, so it reads as a
        # structurally different kind of list rather than more streams to parse.
        if workstreams:
            lines.append(f"  ⚙ Workstreams ({len(workstreams)}) — dev/research threads:")
            for w in workstreams:
                lines.append(f"       {w['name']}")
            lines.append("")
        return "\n".join(lines).rstrip()

    if not all_direct:
        lines.append("  No project-level work streams yet." if workstreams
                      else "  No work streams yet.")
        return _finish()

    # Compact trajectory line: done phases/streams (what's behind you)
    if done_sorted:
        names = " · ".join(s["name"] for s in done_sorted)
        lines.append(f"  ✓ {names}")
        lines.append("")

    if not active_sorted:
        if not done_sorted:
            lines.append("  No project-level work streams yet." if workstreams
                          else "  No work streams yet.")
        return _finish()

    if grouping_ids:
        _append_grouped_streams(lines, active_sorted, grouping_ids, projects, tasks)
    else:
        _append_flat_streams(lines, active_sorted, tasks, depths)

    return _finish()


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
    # _children_of, not a raw parent-project scan — workstreams are excluded there so this
    # inherits the same rule as render_map (2026-07-13).
    sub = _children_of(sid_val, projects)
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

    workstreams = sorted(_workstream_descendants(sid_val, projects), key=lambda w: w["name"])
    if workstreams:
        lines.append("")
        lines.append(f"   ⚙ Workstreams ({len(workstreams)}) — dev/research threads:")
        for w in workstreams:
            lines.append(f"       {w['name']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent-facing renderer (the DEFAULT — June never runs this script herself,
# 2026-07-13). render_map/render_stream above are the June-facing register:
# terse, plain-language, one line per field, monospace-aligned for her TUI, and
# they deliberately DISCARD most stored fields. That's useless to an agent asked
# to "orient and figure out what's open" — it needs every field, clearly labeled,
# with per-task status. This renderer is that: completeness over calm. Workstreams
# are shown inline here (clearly typed) rather than hidden — the hide-workstreams
# rule is a June-facing UI concern; an agent orienting needs the whole picture.
# ---------------------------------------------------------------------------

# Fields dumped per type in the agent view, by DISPLAY NAME (read via _any_field,
# which tolerates Anytype's auto-generated keys). "always" fields print even when
# empty (their absence is signal — an unset Engagement means the daily plan can't
# gate on it); "if_set" fields print only when populated, to keep the dump scannable.
_AGENT_FIELDS = {
    "gsdo_goal": {
        "always": ["Horizon", "Goal engagement", "Goal status"],
        "if_set": ["Reaching for", "Resolution condition", "Barriers", "Context"],
    },
    "gsdo_project": {
        "always": ["Engagement", "Side", "Project status"],
        "if_set": ["Deadline", "Reaching for", "Description", "Affective", "Barriers",
                   "Engagement notes", "Arc position rationale", "Depends on", "Context"],
    },
    "task": {
        "always": ["Task status"],
        "if_set": ["Done", "Due date", "Scheduled", "Duration min", "Affective",
                   "Access conditions", "Blocked on", "Needs clarifying", "Context"],
    },
    "gsdo_recurring": {
        "always": ["Interval unit"],
        "if_set": ["Interval count", "Day of week", "Day of month", "Time of day",
                   "Has target", "Target", "Duration min", "Context"],
    },
}


def _agent_fmt_val(v, name_by_id=None):
    """One-line rendering of any field value for the agent dump; resolves object ids
    to names when a lookup is provided (so 'Depends on' reads as titles, not ids)."""
    if v is None or v == "" or v == []:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        parts = []
        for x in v:
            if isinstance(x, dict):
                xid = x.get("id") or x.get("object") or x.get("target")
                parts.append((name_by_id or {}).get(xid, x.get("name") or xid or "?"))
            elif name_by_id and x in name_by_id:
                parts.append(name_by_id[x])
            else:
                parts.append(str(x))
        return ", ".join(p for p in parts if p) or "—"
    return str(v).replace("\n", " ⏎ ")


def _agent_fields_block(obj, tkey, indent, name_by_id):
    """The labeled field lines for one object (goal/project/task/recurring)."""
    spec = _AGENT_FIELDS.get(tkey, {})
    lines = []
    for label in spec.get("always", []):
        lines.append(f"{indent}  {label}: {_agent_fmt_val(_any_field(obj, label), name_by_id)}")
    for label in spec.get("if_set", []):
        v = _any_field(obj, label)
        if v not in (None, "", [], False):
            lines.append(f"{indent}  {label}: {_agent_fmt_val(v, name_by_id)}")
    return lines


def render_map_agent(project_name):
    """DEFAULT output. Full, labeled, per-stream field dump for an agent orienting in
    the repo — 'what's open, what to work on, what's blocked.' Deterministic; live read."""
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    projects = [o for o in objs if _tkey(o) == "gsdo_project"]
    goals = [o for o in objs if _tkey(o) == "gsdo_goal"]
    tasks = [o for o in objs if _tkey(o) == "task"]
    recurrings = [o for o in objs if _tkey(o) == "gsdo_recurring"]
    name_by_id = {o["id"]: o.get("name") for o in objs}

    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return f"(no project named {project_name!r} found)"

    proj_by_id = {p["id"]: p for p in projects}

    def _linked(children_objs, parent_id, link_key):
        out = []
        for o in children_objs:
            if parent_id in _id_list(_objs(_props(o), link_key)):
                out.append(o)
        return out

    def _task_line(t, indent):
        status = _any_field(t, "Task status") or ("Done" if _any_field(t, "Done") else "—")
        head = f"{indent}  · [{status}] {t.get('name','')}"
        extra = []
        for label in ("Blocked on", "Due date", "Duration min", "Affective", "Access conditions",
                      "Needs clarifying"):
            v = _any_field(t, label)
            if v not in (None, "", [], False):
                extra.append(f"{label}={_agent_fmt_val(v)}")
        if extra:
            head += "  (" + "; ".join(extra) + ")"
        return head

    out = []

    def emit_project(p, indent, label):
        pid = p["id"]
        is_ws = _is_workstream(p, projects, proj_by_id)
        kind = "WORKSTREAM" if is_ws else label
        out.append(f"{indent}{kind}  {p.get('name','')}   #{pid[-6:]}")
        out.extend(_agent_fields_block(p, "gsdo_project", indent, name_by_id))
        # tasks
        my_tasks = _linked(tasks, pid, "linked_projects")
        if my_tasks:
            out.append(f"{indent}  Tasks ({len(my_tasks)}):")
            for t in sorted(my_tasks, key=lambda x: (x.get("name") or "")):
                out.append(_task_line(t, indent))
        # recurring
        my_rec = _linked(recurrings, pid, "gsdo_project_link")
        if my_rec:
            out.append(f"{indent}  Recurring ({len(my_rec)}):")
            for r in sorted(my_rec, key=lambda x: (x.get("name") or "")):
                iv = _agent_fmt_val(_any_field(r, "Interval unit"))
                cnt = _any_field(r, "Interval count")
                cadence = f"every {cnt} {iv}" if cnt and iv != "—" else iv
                out.append(f"{indent}  · ↻ {r.get('name','')}  ({cadence})")
        # children (real subprojects + nested workstreams), recursed
        for c in sorted(_linked(projects, pid, "gsdo_parent_project"),
                        key=lambda x: (x.get("name") or "")):
            out.append("")
            emit_project(c, indent + "    ", "SUBPROJECT")

    # Goal header
    goal_ids = _objs(_props(proj), "gsdo_goal_link")
    goal = next((o for o in goals if o["id"] in goal_ids), None)
    out.append("=" * 70)
    out.append(f"AGENT ORIENTATION — {project_name}")
    out.append("Live read from Anytype; deterministic (no LLM). Every stored field shown.")
    out.append("=" * 70)
    out.append("")
    if goal:
        out.append(f"GOAL  {goal.get('name','')}   #{goal['id'][-6:]}")
        out.extend(_agent_fields_block(goal, "gsdo_goal", "", name_by_id))
        out.append("")
    emit_project(proj, "", "PROJECT")
    return "\n".join(out).rstrip()


def _all_sub_projects(parent_id, all_projects):
    """Recursively collect all projects in the subtree under parent_id.

    Includes groupings (sub-projects with children) and their leaf streams.
    Depth-first; does not deduplicate (the graph is a tree so no cycles expected).
    """
    direct = [p for p in all_projects
              if parent_id in _objs(_props(p), "gsdo_parent_project")]
    out = list(direct)
    for child in direct:
        out.extend(_all_sub_projects(child["id"], all_projects))
    return out


def missing_descriptions(project_name):
    """Return names of active work streams that need the structured description pass.

    A stream needs a pass if it has no context, or context not in the
    two-line format (what it is / next step). Done streams are excluded.
    Checks all streams in the subtree (including streams nested under groupings).
    """
    _, projects, _ = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    streams = [s for s in _all_sub_projects(proj["id"], projects) if not _is_done(s)]
    return [s["name"] for s in streams
            if not _is_structured(_txt(_props(s), "gsdo_context"))]


def gap_streams(project_name):
    """Like missing_descriptions, but returns full dicts so the fix-up pass can
    update each stream in place without re-querying every object one by one.

    Returns [{id, name, context, engagement}] for active streams that need a pass.
    Checks all streams in the subtree (including streams nested under groupings).
    """
    _, projects, _ = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return []
    out = []
    for s in _all_sub_projects(proj["id"], projects):
        if _is_done(s):
            continue
        ctx = _txt(_props(s), "gsdo_context")
        if not _is_structured(ctx):
            out.append({"id": s["id"], "name": s["name"], "context": ctx,
                        "engagement": _sel(_props(s), "engagement")})
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Orient renderer. DEFAULT = agent-facing full field dump (June never "
                    "runs this herself, 2026-07-13). Use --june for her terse TUI map.")
    ap.add_argument("project", nargs="?", default="Build Controlled Drift")
    ap.add_argument("--june", action="store_true",
                    help="June-facing terse map (plain language, one line per field, monospace)")
    ap.add_argument("--stream", default=None, help="open one work stream by name (June-facing)")
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
    elif args.june:
        print(render_map(args.project))
    else:
        print(render_map_agent(args.project))
