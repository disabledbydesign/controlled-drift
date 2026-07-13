"""Within-thread pick signal: the daily plan collapses each thread to ONE item, and picks
that item by an honest signal (nearest deadline, else least-recently-surfaced, else the
current stable order) instead of the old storage-order accident. Pure logic + a mocked
loader — no live Anytype, no LLM. Reconciliation: docs/spec_reconciliation_selection_2026-07-11.md
(Output; "what the code must do" item 4)."""
import sys, os
import datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import daily_plan as dp
import plan_generate as pg


# --- Task 2: the loader reads the built-in Due date -------------------------

def _task_obj(oid, name, due=None, status="Active"):
    props = [{"key": "gsdo_task_status", "select": {"name": status}}]
    if due is not None:
        props.append({"key": "due_date", "date": due})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def test_loader_reads_due_date(monkeypatch):
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _task_obj("t1", "Has a deadline", due="2026-07-20"),
        _task_obj("t2", "No deadline"),
    ])
    _, _, tasks, _, _, _ = dp.load_active_items("sid")
    by_id = {t["id"]: t for t in tasks}
    assert by_id["t1"]["due_date"] == "2026-07-20"
    assert by_id["t2"]["due_date"] is None           # unset -> None, never an error


# --- Task 3: the pure pick helpers ------------------------------------------

def _t(tid, due=None):
    return {"id": tid, "name": tid, "due_date": due, "linked_projects": ["P"]}


def test_parse_date_forms():
    assert pg._parse_date("2026-07-15") == dt.date(2026, 7, 15)
    assert pg._parse_date("2026-07-15T00:00:00Z") == dt.date(2026, 7, 15)
    assert pg._parse_date("2026-07-15T09:30:00+00:00") == dt.date(2026, 7, 15)
    assert pg._parse_date(None) is None
    assert pg._parse_date("") is None
    assert pg._parse_date("not a date") is None


def test_nearest_deadline_wins_over_surface():
    # b has a deadline; a is more stale by surface. Deadline is the stronger signal -> b.
    a, b = _t("a", due=None), _t("b", due="2026-07-20")
    surface = {"a": dt.datetime(2026, 6, 1), "b": dt.datetime(2026, 7, 12)}
    assert pg._pick_within_thread([a, b], None, surface)["id"] == "b"


def test_earlier_deadline_wins():
    a, b = _t("a", due="2026-08-01"), _t("b", due="2026-07-15")
    assert pg._pick_within_thread([a, b], None, {})["id"] == "b"


def test_project_deadline_is_the_floor_when_no_task_due():
    # Neither task has its own due date; the project deadline applies to both equally, so the
    # pick falls through to least-recently-surfaced (a is more stale -> a).
    a, b = _t("a", due=None), _t("b", due=None)
    surface = {"a": dt.datetime(2026, 6, 1), "b": dt.datetime(2026, 7, 10)}
    assert pg._pick_within_thread([a, b], "2026-07-30", surface)["id"] == "a"


def test_own_due_beats_project_floor():
    # b has its own (later) due date; a rides only the project floor. b's explicit due still
    # ranks it as "has a deadline" alongside a, and earlier effective deadline wins:
    # a's effective deadline = project floor 2026-07-16, b's own = 2026-07-25 -> a.
    a, b = _t("a", due=None), _t("b", due="2026-07-25")
    assert pg._pick_within_thread([a, b], "2026-07-16", {})["id"] == "a"


def test_least_recently_surfaced_wins_without_deadlines():
    a, b = _t("a", due=None), _t("b", due=None)
    surface = {"a": dt.datetime(2026, 7, 11), "b": dt.datetime(2026, 6, 18)}
    assert pg._pick_within_thread([a, b], None, surface)["id"] == "b"   # b is quieter


def test_never_surfaced_is_most_stale():
    a, b = _t("a", due=None), _t("b", due=None)
    surface = {"a": dt.datetime(2026, 7, 1)}            # b never surfaced -> maximally stale
    assert pg._pick_within_thread([a, b], None, surface)["id"] == "b"


def test_total_tie_falls_back_to_stable_order():
    a, b = _t("a", due=None), _t("b", due=None)
    # no deadlines, no surface history for either -> stable: first candidate wins.
    assert pg._pick_within_thread([a, b], None, {})["id"] == "a"
    assert pg._pick_within_thread([b, a], None, {})["id"] == "b"


# --- Task 4: the gate uses the pick + records held_back ---------------------

def _proj(name, eng="Steady", deadline=None):
    return {"name": name, "engagement": eng, "deadline": deadline}


def test_gate_picks_the_signal_winner_not_storage_order():
    # Two Steady-thread tasks in storage order [a, b]; b is least-recently-surfaced.
    # Old behavior kept a (first seen); the signal keeps b.
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"], "due_date": None},
             {"id": "b", "name": "b", "linked_projects": ["P"], "due_date": None}]
    projects = [_proj("P")]
    surface = {"a": dt.datetime(2026, 7, 11), "b": dt.datetime(2026, 6, 18)}
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates=surface)
    assert [t["id"] for t in kept] == ["b"]


def test_gate_records_held_back_count():
    # b is least-recently-surfaced -> it's the shown move; a and c are the 2 held back.
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"], "due_date": None},
             {"id": "b", "name": "b", "linked_projects": ["P"], "due_date": None},
             {"id": "c", "name": "c", "linked_projects": ["P"], "due_date": None}]
    projects = [_proj("P")]
    surface = {"a": dt.datetime(2026, 7, 11), "b": dt.datetime(2026, 6, 18),
               "c": dt.datetime(2026, 7, 10)}
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates=surface)
    assert len(kept) == 1
    assert kept[0]["id"] == "b"                         # the signal pick is the one shown
    assert kept[0]["held_back"] == 2                    # 3 in thread, 1 shown -> 2 held


def test_gate_no_project_tasks_never_collapsed():
    # No-project tasks are discrete errands. The hide gate treats an empty project as unset
    # (hidden-unless-neglected) — unchanged, pre-existing behavior — so make them visible via
    # neglect, then assert the COLLAPSE pass never merges them: both survive, held_back 0.
    tasks = [{"id": "a", "name": "a", "linked_projects": [], "due_date": None},
             {"id": "b", "name": "b", "linked_projects": [], "due_date": None}]
    neglected = [{"name": ""}]                          # "" project counts as neglected -> visible
    kept = pg._gate_and_collapse(tasks, [], neglected, None, surface_dates={})
    assert {t["id"] for t in kept} == {"a", "b"}        # discrete actions, both kept, not collapsed
    assert all(t.get("held_back", 0) == 0 for t in kept)


def test_gate_forced_task_still_passes_through():
    tasks = [{"id": "a", "name": "alpha move", "linked_projects": ["P"], "due_date": None},
             {"id": "b", "name": "beta move", "linked_projects": ["P"], "due_date": None}]
    projects = [_proj("P")]
    # June explicitly names task b -> it must surface even if the signal would pick a.
    surface = {"b": dt.datetime(2026, 7, 11)}           # b is the freshest -> not the signal pick
    kept = pg._gate_and_collapse(tasks, projects, [], None, extra="put beta move in today",
                                 surface_dates=surface)
    assert "b" in {t["id"] for t in kept}              # forced through the collapse


# --- Task 5: the held-back count reaches the LLM context --------------------

def test_task_ref_line_carries_held_back():
    tasks = [{"id": "id-a", "name": "Draft the section", "held_back": 2},
             {"id": "id-b", "name": "Email Donna"}]
    _, table = pg._build_task_refs(tasks)
    assert "T1 — Draft the section" in table
    assert "2 more in this thread" in table            # the honest per-thread count reaches the model
    assert "T2 — Email Donna" in table                 # no annotation when nothing held back


# --- per-thread rendering (Task 5): held_back NAMES + threading onto the plan JSON ----------

def test_gate_records_held_back_names():
    # b is shown; a and c are held. The names of the held items travel with the shown one so the
    # renderer can reveal them on expand — held, not dropped.
    tasks = [{"id": "a", "name": "task a", "linked_projects": ["P"], "due_date": None},
             {"id": "b", "name": "task b", "linked_projects": ["P"], "due_date": None},
             {"id": "c", "name": "task c", "linked_projects": ["P"], "due_date": None}]
    projects = [_proj("P")]
    surface = {"a": dt.datetime(2026, 7, 11), "b": dt.datetime(2026, 6, 18),
               "c": dt.datetime(2026, 7, 10)}
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates=surface)
    assert kept[0]["id"] == "b"
    assert kept[0]["held_back"] == 2
    assert set(kept[0]["held_back_names"]) == {"task a", "task c"}   # the shown item is not among them


def test_gate_no_held_names_when_thread_is_alone():
    tasks = [{"id": "a", "name": "only move", "linked_projects": ["P"], "due_date": None}]
    kept = pg._gate_and_collapse(tasks, [_proj("P")], [], None, surface_dates={})
    assert kept[0]["held_back"] == 0
    assert kept[0]["held_back_names"] == []


def test_resolve_ids_threads_held_back_onto_plan_item():
    # Python owns the id->held-back map; the model only echoes the ref token. The count + names
    # must land on the plan item (via the id) so the overlay renders '· N more' + the drill-down.
    tasks = [{"id": "id-b", "name": "task b", "held_back": 2, "held_back_names": ["task a", "task c"]}]
    ref_map = {"T1": "id-b"}
    plan = {"blocks": [{"items": [{"task": "Do task b", "ref": "T1"}]}]}
    pg._resolve_ids(plan, ref_map, tasks)
    item = plan["blocks"][0]["items"][0]
    assert item["id"] == "id-b"
    assert item["held_back"] == 2
    assert item["held_back_names"] == ["task a", "task c"]


def test_resolve_ids_omits_held_back_when_zero():
    # A thread with nothing held stays clean — no held_back keys on the item at all.
    tasks = [{"id": "id-x", "name": "solo", "held_back": 0, "held_back_names": []}]
    ref_map = {"T1": "id-x"}
    plan = {"items": [{"task": "Solo move", "ref": "T1"}]}     # priority (flat) shape
    pg._resolve_ids(plan, ref_map, tasks)
    item = plan["items"][0]
    assert item["id"] == "id-x"
    assert "held_back" not in item
    assert "held_back_names" not in item
