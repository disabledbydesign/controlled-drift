#!/usr/bin/env python3
"""Neglect-resurfacing: active items not surfaced in N days. Makes the daily plan's
'still here, not today' reassurance HONEST (§9 item 6) — re-surfacing must be real.

STALENESS SOURCE (REVISED 2026-07-12 — verified finding). Anytype's "Last surfaced"
field is dead on the live path (written only by an interactive CLI June doesn't use:
5 of 137 tasks, none newer than 2026-06-18). Trusting it made EVERY item read back as
never-surfaced -> everything looked neglected -> "hidden unless neglected" collapsed to
"nothing is ever hidden" (the gate barely gated). The live source is the append-only
surface log (surface_log.surfaced_dates), written on every real plan generation; the
Anytype field is only a fallback. This is the same resolver the monthly status checker
uses — shared in surface_log so the two never diverge."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import surface_log

def find_neglected(items, now, days=16):
    # 16 days — June's calibration 2026-07-12, aligned with the upkeep-strategy threshold;
    # per-priority calibration is the future Strategy-driven version.
    """Pure. items: list of {"last_surfaced": datetime|None, ...}. Returns the neglected ones."""
    cutoff = now - dt.timedelta(days=days)
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
    # Project metadata, keyed by id: name, engagement, own Anytype fallback date.
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

    items = []
    proj_task_dates = {}  # project_id -> [surfaced datetimes of its tasks], for the rollup
    for o in data:
        if _type_key(o) != "task":
            continue
        pv = {p.get("key"): p for p in o.get("properties", [])}
        status = (pv.get("gsdo_task_status", {}).get("select") or {})
        status = status.get("name") if isinstance(status, dict) else status
        if pv.get("done", {}).get("checkbox") or status in _DEAD_TASK_STATUS:
            continue
        oid = o.get("id")
        linked_raw = pv.get("linked_projects", {}).get("objects") or []
        linked_ids = [x.get("id") if isinstance(x, dict) else x for x in linked_raw]
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


def query_neglected(days=16, now=None):
    # 16 days — June's calibration 2026-07-12, aligned with the upkeep-strategy threshold;
    # per-priority calibration is the future Strategy-driven version.
    """Live wrapper: read surfaceable Tasks + Projects from Anytype, return the neglected
    ones. Staleness comes from the surface log (surface_log.surfaced_dates); the Anytype
    'Last surfaced' field is a fallback only. NOTE: no pagination yet — fine for the
    current space size."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    surfaced = g.find_property("Last surfaced")
    surfaced_key = surfaced.get("key") if surfaced else None  # fallback only; absence is fine now
    data = g.fetch_all_objects(sid)
    items = neglect_candidates(data, surface_log.surfaced_dates(), surfaced_key)
    return find_neglected(items, now, days=days)
