#!/usr/bin/env python3
"""Neglect: two named cohorts, sharing one staleness core (16-day default horizon).

TWO COHORTS (split 2026-07-13 — June ratified). The original code resurfaced Backburner/
unset projects on a "not surfaced in N days" timer and called that "neglect." It ran
backwards: a project June actually cares about and is actively pursuing (Engagement Steady/
Sprint/Hyperfixation) surfaces a move EVERY DAY via one-move-per-thread selection, so
"hasn't been SURFACED in N days" can never catch it — it always looks fresh. The honest
signal for "active but not getting worked on" is COMPLETION, not surfacing: a project June
keeps seeing but isn't finishing anything in.

  - ACTIVE cohort (`active_untouched`) — THIS is what "neglect" now means on the plan path:
    active projects whose tasks aren't getting completed. Staleness signal = last completion
    (from completion_log), with a brand-new-project guard (see active_untouched_from).
  - DORMANT cohort (`dormant_neglected`, `query_neglected` kept as an alias) — the ORIGINAL
    Backburner/unset-by-last-surfaced-date behavior, preserved unchanged but UNWIRED from the
    daily plan. It is a separate, later feature: deliberately resurfacing put-away work. Not
    deleted, just not what "neglect" means right now.

STALENESS SOURCE for the dormant cohort (REVISED 2026-07-12 — verified finding). Anytype's
"Last surfaced" field is dead on the live path (written only by an interactive CLI June
doesn't use: 5 of 137 tasks, none newer than 2026-06-18). Trusting it made EVERY item read
back as never-surfaced -> everything looked neglected -> "hidden unless neglected" collapsed
to "nothing is ever hidden" (the gate barely gated). The live source is the append-only
surface log (surface_log.surfaced_dates), written on every real plan generation; the
Anytype field is only a fallback. This is the same resolver the monthly status checker
uses — shared in surface_log so the two never diverge."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import surface_log
import completion_log
import cd_paths


def _cutoff(now, days):
    """The one staleness-window formula both cohorts share. They differ only in WHAT date they
    measure against it — surface recency for the dormant cohort, completion recency (or, absent
    that, earliest-surfaced) for the active cohort."""
    return now - dt.timedelta(days=days)


def find_neglected(items, now, days=16):
    # 16 days — June's calibration 2026-07-12, aligned with the upkeep-strategy threshold;
    # per-priority calibration is the future Strategy-driven version.
    """Pure. items: list of {"last_surfaced": datetime|None, ...}. Returns the neglected ones."""
    cutoff = _cutoff(now, days)
    out = []
    for it in items:
        ls = it.get("last_surfaced")
        if ls is None or ls < cutoff:
            out.append(it)
    return out

# Only these object types are surfaceable work (plan note 1: active Tasks + Projects).
SURFACEABLE_TYPE_KEYS = {"task", "gsdo_project"}

# Status/engagement filter (added 2026-07-12). Without it, finished or deliberately-parked
# work counted as surfaceable and got resurfaced — the opposite of what the state means.
#   Tasks: Done / Parked are never neglect candidates (finished, or deferred-by-design).
#   Projects: Engagement Done is excluded (finished); Open is NOT nagged as neglected
#     (reconciliation Layer 1: Open = available/self-paced, surfaced only by foreground).
#   Backburner + unset projects ARE candidates — that is the whole point of
#     "hidden unless neglected": the ONLY path that ever brings a put-away thread back.
_DEAD_TASK_STATUS = {"Done", "Parked"}
_NON_CANDIDATE_ENGAGEMENT = {"Done", "Open"}

# The ACTIVE cohort's engagement filter — projects June is actually pursuing right now.
# Distinct from _NON_CANDIDATE_ENGAGEMENT above (which is an EXCLUDE list for the dormant
# cohort): this is an INCLUDE list, the opposite kind of filter, for the opposite cohort.
_ACTIVE_ENGAGEMENT = {"Steady", "Sprint", "Hyperfixation"}

def _parse_date(raw):
    """Anytype serializes dates as ISO-8601 with a trailing 'Z' (e.g. '2026-06-15T16:39:41Z')
    — confirmed empirically against the live API. fromisoformat yields a tz-AWARE datetime,
    which cannot be compared against a naive datetime.now(); drop the tz so day-granularity
    neglect compares cleanly (the UTC/local offset is immaterial at a multi-day window)."""
    if not raw:
        return None
    s = raw.replace("Z", "+00:00") if isinstance(raw, str) and raw.endswith("Z") else raw
    d = dt.datetime.fromisoformat(s)
    return d.replace(tzinfo=None) if d.tzinfo is not None else d


def _type_key(o):
    t = o.get("type")
    return t.get("key") if isinstance(t, dict) else t


def _projects_by_id(data):
    """Pure. id -> {"name":, "engagement":, "anytype_ls":} for every gsdo_project object in
    raw Anytype data. Shared by BOTH cohorts (neglect_candidates for the dormant cohort,
    _active_project_task_ids for the active cohort) — they read the same project metadata
    and differ only in which engagement values they keep."""
    proj_by_id = {}
    for o in data:
        if _type_key(o) != "gsdo_project":
            continue
        by_name = {p.get("name"): p for p in o.get("properties", [])}
        eng = (by_name.get("Engagement", {}).get("select") or {})
        eng = eng.get("name") if isinstance(eng, dict) else None
        anytype_ls = _parse_date(by_name.get("Last surfaced", {}).get("date"))
        proj_by_id[o.get("id")] = {"name": o.get("name"), "engagement": eng,
                                   "anytype_ls": anytype_ls}
    return proj_by_id


def _live_task_linked_ids(o):
    """Pure. Given one raw task object, return (task_id, status, is_dead, linked_project_ids).
    `is_dead` mirrors the done/status filter both neglect_candidates and the active cohort's
    task-roster builder need — checkbox-done or status in _DEAD_TASK_STATUS."""
    pv = {p.get("key"): p for p in o.get("properties", [])}
    status = (pv.get("gsdo_task_status", {}).get("select") or {})
    status = status.get("name") if isinstance(status, dict) else status
    is_dead = bool(pv.get("done", {}).get("checkbox")) or status in _DEAD_TASK_STATUS
    linked_raw = pv.get("linked_projects", {}).get("objects") or []
    linked_ids = [x.get("id") if isinstance(x, dict) else x for x in linked_raw]
    return o.get("id"), status, is_dead, linked_ids


def neglect_candidates(data, surface_dates, surfaced_key=None):
    """Pure. Given raw Anytype objects + the surface-log date map, build the surfaceable
    task + project items, applying the status/engagement filter. Each item carries `type`
    ('task'|'project'), `last_surfaced` (effective date — surface log first, Anytype field
    only as fallback; None when never surfaced), and `linked_projects` (task -> its project
    names; project -> its own name) so the daily-plan consumers can tell which project a
    quiet item belongs to.

    A project is never logged under its own id (only its tasks are), so a project's
    effective last-surfaced = the newest surface date across its tasks (the same rollup the
    status checker uses), falling back to the project's own Anytype 'Last surfaced'."""
    proj_by_id = _projects_by_id(data)

    items = []
    proj_task_dates = {}  # project_id -> [surfaced datetimes of its tasks], for the rollup
    for o in data:
        if _type_key(o) != "task":
            continue
        oid, status, is_dead, linked_ids = _live_task_linked_ids(o)
        if is_dead:
            continue
        pv = {p.get("key"): p for p in o.get("properties", [])}
        linked_names = [proj_by_id[i]["name"] for i in linked_ids if i in proj_by_id]
        anytype_ls = _parse_date(pv.get(surfaced_key, {}).get("date")) if surfaced_key else None
        eff, _src = surface_log.effective_last_surfaced([{"id": oid}], surface_dates, anytype_ls)
        items.append({"name": o.get("name"), "id": oid, "type": "task",
                      "last_surfaced": eff, "linked_projects": linked_names,
                      "status": status})
        d = surface_dates.get(oid)
        if d is not None:
            for i in linked_ids:
                proj_task_dates.setdefault(i, []).append(d)

    for pid, meta in proj_by_id.items():
        eng = meta["engagement"] or "unset"
        if eng in _NON_CANDIDATE_ENGAGEMENT:
            continue
        task_hits = proj_task_dates.get(pid, [])
        eff = max(task_hits) if task_hits else meta["anytype_ls"]
        items.append({"name": meta["name"], "id": pid, "type": "project",
                      "last_surfaced": eff, "linked_projects": [meta["name"]],
                      "engagement": eng})
    return items


def dormant_neglected(days=16, now=None):
    # 16 days — June's calibration 2026-07-12, aligned with the upkeep-strategy threshold;
    # per-priority calibration is the future Strategy-driven version.
    """Live wrapper for the DORMANT cohort — the ORIGINAL "neglect" behavior, preserved as-is:
    surfaceable Tasks + Projects from Anytype, flagged by last-SURFACED date. This is the
    future "resurface put-away work" feature (Backburner/unset projects going quiet on
    purpose) — a separate, later design conversation. NOT wired into the daily plan today
    (see daily_plan.load_neglected, which now calls active_untouched instead). Staleness
    comes from the surface log (surface_log.surfaced_dates); the Anytype 'Last surfaced'
    field is a fallback only. NOTE: no pagination yet — fine for the current space size."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    surfaced = g.find_property("Last surfaced")
    surfaced_key = surfaced.get("key") if surfaced else None  # fallback only; absence is fine now
    data = g.fetch_all_objects(sid)
    items = neglect_candidates(data, surface_log.surfaced_dates(), surfaced_key)
    return find_neglected(items, now, days=days)


# Thin alias — kept callable under its original name for any existing caller/import.
query_neglected = dormant_neglected


# ============================================================================
# ACTIVE cohort — active projects whose tasks aren't getting COMPLETED.
# ============================================================================

def _active_project_task_ids(data):
    """Pure. proj_id -> {"name":, "task_ids": set()} for ACTIVE-engagement projects (Steady/
    Sprint/Hyperfixation) — the cohort neglect targets now: work June is actually pursuing.

    Deliberately does NOT drop Done/Parked tasks the way neglect_candidates' candidate list
    does — a project's completion history lives ENTIRELY in its Done tasks, so excluding them
    would erase the very signal this cohort reads. Every task ever linked to the project
    counts toward its task roster, whatever its current status."""
    proj = {pid: {"name": meta["name"], "task_ids": set()}
            for pid, meta in _projects_by_id(data).items()
            if meta["engagement"] in _ACTIVE_ENGAGEMENT}
    for o in data:
        if _type_key(o) != "task":
            continue
        oid, _status, _is_dead, linked_ids = _live_task_linked_ids(o)
        for pid in linked_ids:
            if pid in proj:
                proj[pid]["task_ids"].add(oid)
    return proj


def _last_completion_per_task(events):
    """Pure. task_id -> the most-recent datetime on which it nets to 'done' in the raw
    completion_log events (as returned by completion_log.read_events()). Nets a same-day
    'undone' against an earlier 'done' for that id/date (the last event recorded for a given
    (id, plan_date) pair wins — the log is append-only in chronological order, so this
    mirrors completion_log.completed_ids_on's per-day netting, generalized across every date
    instead of just one). A task absent from this dict has never netted done on any day."""
    last_event_per_day = {}  # (id, plan_date) -> event; last occurrence in the file wins
    for rec in events:
        tid, pd, ev = rec.get("id"), rec.get("plan_date"), rec.get("event")
        if not tid or not pd or not ev:
            continue
        last_event_per_day[(tid, pd)] = ev
    out = {}
    for (tid, pd), ev in last_event_per_day.items():
        if ev != "done":
            continue
        d = dt.datetime.fromisoformat(pd)  # plan_date is a bare YYYY-MM-DD; midnight is fine
        if tid not in out or d > out[tid]:
            out[tid] = d
    return out


def _earliest_surfaced_dates(path=None):
    """item_id -> EARLIEST surfaced datetime, read from the append-only surface log. Mirrors
    surface_log.surfaced_dates() (which keeps the NEWEST — the right thing for dormant
    staleness) but the active cohort's brand-new-project guard needs the OPPOSITE: how long
    ago a task first ever appeared, so a project that is merely a day old isn't mistaken for
    one that has gone quiet since before it ever had a chance to finish anything."""
    p = path or cd_paths.data_file("surface_log.jsonl")
    out = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                tid, ts = rec.get("id"), rec.get("ts")
                if not tid or not ts:
                    continue
                try:
                    when = dt.datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    continue
                if when.tzinfo is not None:
                    when = when.replace(tzinfo=None)
                if tid not in out or when < out[tid]:
                    out[tid] = when
    except FileNotFoundError:
        pass
    return out


def active_untouched_from(data, completion_events, earliest_surfaced, now, days=16):
    """Pure — the piece the tests exercise directly. data: raw Anytype objects.
    completion_events: raw events as from completion_log.read_events(). earliest_surfaced:
    task_id -> earliest-ever-surfaced datetime (from _earliest_surfaced_dates). now/days:
    the shared staleness window (see _cutoff).

    A project (Engagement Steady/Sprint/Hyperfixation) is flagged when:
      - its newest task completion is more than `days` ago; OR
      - it has NO completion at all, AND its earliest-ever-surfaced task is more than `days`
        ago (this second clause is the guard against flagging a brand-new project that
        simply hasn't had time to complete anything yet).

    Returns a list of dicts shaped like neglect_candidates' items — at minimum
    {"name", "type": "project", "id"} — so consumers reading `.get("name")` keep working."""
    cutoff = _cutoff(now, days)
    completion_dates = _last_completion_per_task(completion_events)
    proj = _active_project_task_ids(data)

    out = []
    for pid, meta in proj.items():
        task_ids = meta["task_ids"]
        completions = [completion_dates[t] for t in task_ids if t in completion_dates]
        newest_completion = max(completions) if completions else None
        if newest_completion is not None:
            stale = newest_completion < cutoff
        else:
            surfaces = [earliest_surfaced[t] for t in task_ids if t in earliest_surfaced]
            earliest = min(surfaces) if surfaces else None
            stale = earliest is not None and earliest < cutoff
        if stale:
            out.append({"name": meta["name"], "type": "project", "id": pid,
                        "last_completed": newest_completion})   # None when never completed
    return out


def active_untouched(days=16, now=None):
    # 16 days — same default horizon as the dormant cohort (June's 2026-07-12 calibration);
    # per-priority calibration is the future Strategy-driven version.
    """Live wrapper for the ACTIVE cohort — THIS is what "neglect" means on the daily-plan
    path now (see module docstring). Reads active-engagement projects + the completion log +
    the surface log from Anytype/disk, then delegates the actual selection to
    active_untouched_from (the pure, tested piece)."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    data = g.fetch_all_objects(sid)
    completion_events = completion_log.read_events()
    earliest_surfaced = _earliest_surfaced_dates()
    return active_untouched_from(data, completion_events, earliest_surfaced, now, days=days)
