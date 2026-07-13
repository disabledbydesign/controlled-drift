# tests/test_neglect.py
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from neglect import find_neglected, neglect_candidates
import surface_log


def test_never_surfaced_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": None}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]

def test_recently_surfaced_is_not_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 16, 9, 0)}]
    assert find_neglected(items, now, days=3) == []

def test_stale_beyond_window_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 10, 9, 0)}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]


# --- the shared staleness resolver (surface_log — the LIVE source) --------------

def test_surfaced_dates_keeps_newest_and_skips_garbage(tmp_path):
    p = tmp_path / "surface_log.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [
        {"ts": "2026-06-01T09:00:00", "id": "tA", "name": "x", "type": "task"},
        {"ts": "2026-07-01T09:00:00", "id": "tA", "name": "x", "type": "task"},
        {"ts": "2026-06-15T09:00:00", "id": "tB", "name": "y", "type": "task"},
        "not json at all",
    ]) + "\n")
    m = surface_log.surfaced_dates(path=str(p))
    assert m == {"tA": dt.datetime(2026, 7, 1, 9, 0), "tB": dt.datetime(2026, 6, 15, 9, 0)}

def test_surfaced_dates_missing_file_is_empty(tmp_path):
    assert surface_log.surfaced_dates(path=str(tmp_path / "nope.jsonl")) == {}

def test_effective_last_surfaced_prefers_log_over_anytype():
    ls, src = surface_log.effective_last_surfaced(
        [{"id": "t1"}], {"t1": dt.datetime(2026, 7, 5)}, anytype_ls=dt.datetime(2026, 6, 1))
    assert ls == dt.datetime(2026, 7, 5) and src == "log"

def test_effective_last_surfaced_falls_back_to_anytype_then_none():
    ls, src = surface_log.effective_last_surfaced([{"id": "t1"}], {}, anytype_ls=dt.datetime(2026, 6, 1))
    assert ls == dt.datetime(2026, 6, 1) and src == "anytype"
    ls, src = surface_log.effective_last_surfaced([{"id": "t1"}], {}, anytype_ls=None)
    assert ls is None and src is None


# --- the status/engagement candidate filter + the project rollup ----------------

def _task(oid, name, status="Active", done=False, linked=(), last_surfaced_iso=None):
    props = [{"key": "gsdo_task_status", "select": {"name": status}},
             {"key": "done", "checkbox": done},
             {"key": "linked_projects", "objects": list(linked)}]
    if last_surfaced_iso:
        props.append({"key": "gsdo_last_surfaced", "date": last_surfaced_iso})
    return {"id": oid, "name": name, "type": {"key": "task"}, "properties": props}

def _project(oid, name, engagement=None, last_surfaced_iso=None):
    props = [{"name": "Engagement", "select": ({"name": engagement} if engagement else None)}]
    if last_surfaced_iso:
        props.append({"name": "Last surfaced", "date": last_surfaced_iso})
    return {"id": oid, "name": name, "type": {"key": "gsdo_project"}, "properties": props}

def _by_name(items):
    return {i["name"]: i for i in items}


def test_done_and_parked_tasks_are_not_candidates():
    data = [_task("t1", "Active one"),
            _task("t2", "Done one", status="Done"),
            _task("t3", "Parked one", status="Parked"),
            _task("t4", "Checkbox done", done=True)]
    names = {i["name"] for i in neglect_candidates(data, {})}
    assert names == {"Active one"}

def test_done_and_open_projects_are_not_candidates_but_backburner_and_unset_are():
    data = [_project("p1", "Steady proj", "Steady"),
            _project("p2", "Backburner proj", "Backburner"),
            _project("p3", "Unset proj", None),
            _project("p4", "Open proj", "Open"),
            _project("p5", "Done proj", "Done")]
    got = _by_name(neglect_candidates(data, {}))
    assert set(got) == {"Steady proj", "Backburner proj", "Unset proj"}
    assert all(got[n]["type"] == "project" for n in got)

def test_task_carries_type_and_linked_project_names():
    data = [_project("p1", "Bar", "Steady"),
            _task("t1", "Foo", linked=[{"id": "p1"}])]
    task = _by_name(neglect_candidates(data, {}))["Foo"]
    assert task["type"] == "task"
    assert task["linked_projects"] == ["Bar"]

def test_surface_log_beats_anytype_for_a_task():
    data = [_task("t1", "Foo", last_surfaced_iso="2026-06-01T00:00:00Z")]
    got = _by_name(neglect_candidates(data, {"t1": dt.datetime(2026, 7, 5)}, surfaced_key="gsdo_last_surfaced"))
    assert got["Foo"]["last_surfaced"] == dt.datetime(2026, 7, 5)   # log wins

def test_project_last_surfaced_rolls_up_from_its_tasks():
    """A project is never logged under its own id — its effective last-surfaced is the newest
    surface date across its tasks (so a Backburner project whose tasks are all quiet reads as
    neglected, and one whose tasks surfaced yesterday does not)."""
    data = [_project("p1", "Bar", "Backburner"),
            _task("t1", "Foo", linked=[{"id": "p1"}]),
            _task("t2", "Baz", linked=[{"id": "p1"}])]
    surface = {"t1": dt.datetime(2026, 6, 1), "t2": dt.datetime(2026, 7, 10)}
    proj = _by_name(neglect_candidates(data, surface))["Bar"]
    assert proj["last_surfaced"] == dt.datetime(2026, 7, 10)   # newest of its tasks

def test_project_with_no_surfaced_tasks_falls_back_then_none():
    data = [_project("p1", "Bar", "Backburner", last_surfaced_iso="2026-05-01T00:00:00Z"),
            _project("p2", "Quiet", "Backburner")]
    got = _by_name(neglect_candidates(data, {}))
    assert got["Bar"]["last_surfaced"] == dt.datetime(2026, 5, 1)   # own Anytype fallback
    assert got["Quiet"]["last_surfaced"] is None                    # nothing anywhere
