# tests/test_neglect_active.py
"""The ACTIVE neglect cohort (June ratified 2026-07-13): active projects (Steady/Sprint/
Hyperfixation) whose tasks aren't getting COMPLETED — as opposed to the dormant cohort's
original "not surfaced in N days" (which an active project can never trip, since it
resurfaces every day via one-move-per-thread selection). See scripts/neglect.py's module
docstring for the full split.

Pure tests only: raw Anytype-shaped objects + injected completion/surface data, mirroring
tests/test_neglect.py's fixture style (_task/_project helpers) and never touching Anytype
or the live log files.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import neglect
from neglect import active_untouched_from, _last_completion_per_task


def _task(oid, name, status="Active", done=False, linked=()):
    return {"id": oid, "name": name, "type": {"key": "task"},
            "properties": [{"key": "gsdo_task_status", "select": {"name": status}},
                            {"key": "done", "checkbox": done},
                            {"key": "linked_projects", "objects": list(linked)}]}


def _project(oid, name, engagement=None):
    return {"id": oid, "name": name, "type": {"key": "gsdo_project"},
            "properties": [{"name": "Engagement",
                             "select": ({"name": engagement} if engagement else None)}]}


NOW = dt.datetime(2026, 7, 13, 9, 0)


def _by_name(items):
    return {i["name"]: i for i in items}


# --- (a) active project, newest completion > 16 days ago -> flagged -------------

def test_active_project_stale_completion_is_flagged():
    data = [_project("p1", "Steady proj", "Steady"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    completions = [{"id": "t1", "plan_date": "2026-06-01", "event": "done"}]  # 42 days ago
    got = _by_name(active_untouched_from(data, completions, {}, NOW, days=16))
    assert "Steady proj" in got
    assert got["Steady proj"]["type"] == "project"
    assert got["Steady proj"]["id"] == "p1"


# --- (b) active project, completion within 16 days -> NOT flagged ---------------

def test_active_project_recent_completion_is_not_flagged():
    data = [_project("p1", "Steady proj", "Steady"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    completions = [{"id": "t1", "plan_date": "2026-07-05", "event": "done"}]  # 8 days ago
    got = _by_name(active_untouched_from(data, completions, {}, NOW, days=16))
    assert "Steady proj" not in got


# --- (c) brand-new active project: no completions, earliest surface recent -----

def test_brand_new_active_project_is_not_flagged():
    data = [_project("p1", "New proj", "Sprint"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    earliest = {"t1": dt.datetime(2026, 7, 10, 9, 0)}  # 3 days ago
    got = _by_name(active_untouched_from(data, [], earliest, NOW, days=16))
    assert "New proj" not in got


# --- (d) never-completed active project, earliest surface > 16 days -> flagged -

def test_never_completed_project_with_old_earliest_surface_is_flagged():
    data = [_project("p1", "Stale proj", "Hyperfixation"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    earliest = {"t1": dt.datetime(2026, 5, 1, 9, 0)}  # 73 days ago
    got = _by_name(active_untouched_from(data, [], earliest, NOW, days=16))
    assert "Stale proj" in got


# --- (e) Backburner project is never in the active cohort -----------------------

def test_backburner_project_is_never_in_active_cohort():
    data = [_project("p1", "Backburner proj", "Backburner"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    # Even with data that WOULD flag an active project (no completion, ancient earliest
    # surface), a Backburner project must not appear at all — it's the other cohort's job.
    earliest = {"t1": dt.datetime(2026, 1, 1, 9, 0)}
    got = active_untouched_from(data, [], earliest, NOW, days=16)
    assert got == []


def test_unset_engagement_project_is_also_not_in_active_cohort():
    data = [_project("p1", "Unset proj", None),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    got = active_untouched_from(data, [], {"t1": dt.datetime(2026, 1, 1)}, NOW, days=16)
    assert got == []


# --- dead-status tasks still count toward the roster (completion lives in Done tasks) --

def test_done_status_task_still_counts_toward_completion_signal():
    """A task that is CURRENTLY status=Done (or checkbox done=True) must still contribute
    its completion date — that's the whole point (a project's completion history lives
    entirely in its Done tasks). If the active-cohort roster builder dropped dead tasks the
    way neglect_candidates does, this project would look never-completed and misfire."""
    data = [_project("p1", "Steady proj", "Steady"),
            _task("t1", "Finished task", status="Done", done=True, linked=[{"id": "p1"}])]
    completions = [{"id": "t1", "plan_date": "2026-07-05", "event": "done"}]  # 8 days ago
    got = _by_name(active_untouched_from(data, completions, {}, NOW, days=16))
    assert "Steady proj" not in got   # recent completion -> not stale


# --- same-day done/undone netting (mirrors completion_log.completed_ids_on) -----

def test_last_completion_per_task_nets_out_same_day_undone():
    events = [
        {"id": "t1", "plan_date": "2026-07-01", "event": "done"},
        {"id": "t1", "plan_date": "2026-07-01", "event": "undone"},  # mis-tap fix, nets to not-done
        {"id": "t1", "plan_date": "2026-06-01", "event": "done"},    # earlier real completion stands
    ]
    out = _last_completion_per_task(events)
    assert out["t1"] == dt.datetime(2026, 6, 1)


def test_last_completion_per_task_takes_newest_across_multiple_done_dates():
    events = [
        {"id": "t1", "plan_date": "2026-06-01", "event": "done"},
        {"id": "t1", "plan_date": "2026-07-01", "event": "done"},
    ]
    out = _last_completion_per_task(events)
    assert out["t1"] == dt.datetime(2026, 7, 1)


def test_task_never_completed_is_absent_from_completion_dates():
    assert _last_completion_per_task([]) == {}
    assert "t1" not in _last_completion_per_task(
        [{"id": "t1", "plan_date": "2026-07-01", "event": "undone"}])


# --- multi-task project: newest completion across ALL its tasks wins -----------

def test_project_completion_signal_is_newest_across_its_tasks():
    data = [_project("p1", "Steady proj", "Steady"),
            _task("t1", "Foo", linked=[{"id": "p1"}]),
            _task("t2", "Bar", linked=[{"id": "p1"}])]
    completions = [{"id": "t1", "plan_date": "2026-06-01", "event": "done"},   # 42 days ago
                   {"id": "t2", "plan_date": "2026-07-05", "event": "done"}]  # 8 days ago
    got = _by_name(active_untouched_from(data, completions, {}, NOW, days=16))
    assert "Steady proj" not in got   # newest (t2) wins, well within window


# --- dormant cohort is untouched: still callable, alias intact -----------------

def test_dormant_neglected_alias_is_still_the_same_callable():
    assert neglect.query_neglected is neglect.dormant_neglected
