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


# --- Task 7 (plan-input seam): relevance-only gate — no hide, no collapse ----

def _proj(name, eng="Steady", side="Wellbeing"):
    return {"name": name, "engagement": eng, "side": side}


def test_block_project_task_stays_in_selection():
    # Reconciled 2026-07-16: a block-project's REAL tasks stay resolvable/checkoffable in selection
    # (the shipped zero-ghost design) — NOT dropped, NOT replaced by a synthetic unit.
    tasks = [{"id": "a", "name": "Cut", "linked_projects": ["Leatherworking"]}]
    projects = [_proj("Leatherworking")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


def test_task_of_a_dormant_project_is_dropped():
    # A Backburner project was excluded at load (Task 2), so it isn't in `projects`; its task must
    # not leak into the input (the recovery-week off-focus leak the seam fixes).
    tasks = [{"id": "t1", "name": "Dye", "linked_projects": ["Old hobby"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={})   # "Old hobby" not active
    assert kept == []


def test_dormant_project_task_survives_when_rolled_over():
    tasks = [{"id": "t1", "name": "Email editor", "linked_projects": ["Paper"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={}, rollover_ids={"t1"})
    assert [t["id"] for t in kept] == ["t1"]


def test_dormant_project_task_survives_when_named():
    tasks = [{"id": "t1", "name": "Email editor", "linked_projects": ["Paper"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={}, extra="email editor today")
    assert [t["id"] for t in kept] == ["t1"]


def test_no_project_task_always_kept():
    tasks = [{"id": "a", "name": "Call surgeon", "linked_projects": []}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


# --- Rollover-vs-active filter (2026-07-17 fix) ------------------------------
# undone_yesterday() only knows about completions dated exactly yesterday, so a task finished
# THIS morning still reads as "not marked done" and gets offered as a rollover candidate again
# -> the model names it, it can't resolve to an id (already excluded from the active pool), and
# it renders as a same-day ghost row with no checkbox and no way to remove it (live: "Mail
# contestation..." reappeared this way after being checked off). The fix checks against the
# CURRENT active pool instead of trusting the date window.

def test_rollover_drops_task_completed_since_yesterday():
    # "t1" was undone as of yesterday's snapshot but has since been completed (whenever that
    # happened) -> it's no longer in the active pool -> must not be re-offered as a rollover.
    undone_yest = [{"id": "t1", "name": "Mail contestation", "plan_date": "2026-07-16"}]
    tasks = [{"id": "t2", "name": "Something else still active"}]
    assert pg._filter_rollover_to_active(undone_yest, tasks) == []


def test_rollover_keeps_task_still_active():
    undone_yest = [{"id": "t1", "name": "Still undone", "plan_date": "2026-07-16"}]
    tasks = [{"id": "t1", "name": "Still undone"}]
    kept = pg._filter_rollover_to_active(undone_yest, tasks)
    assert [u["id"] for u in kept] == ["t1"]


def test_rollover_filter_is_selective_not_all_or_nothing():
    undone_yest = [
        {"id": "done-since", "name": "Already finished", "plan_date": "2026-07-16"},
        {"id": "still-open", "name": "Genuinely undone", "plan_date": "2026-07-16"},
    ]
    tasks = [{"id": "still-open", "name": "Genuinely undone"}]
    kept = pg._filter_rollover_to_active(undone_yest, tasks)
    assert [u["id"] for u in kept] == ["still-open"]


def test_held_back_is_always_zero_now():
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"]},
             {"id": "b", "name": "b", "linked_projects": ["P"]}]
    projects = [_proj("P")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"a", "b"}          # no collapse — both stay
    assert all(t["held_back"] == 0 for t in kept)


def test_daily_life_task_kept():
    tasks = [{"id": "a", "name": "Dishes", "linked_projects": ["Household"]}]
    projects = [_proj("Household", eng="Steady", side="Daily life")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


def test_multi_linked_task_kept_if_any_project_active():
    # A task linked to BOTH a dormant and an active project stays — `any(pn in active_names)`.
    # Only when EVERY linked project is dormant is it dropped (cross-family review gap-fill).
    tasks = [{"id": "a", "name": "Shared move", "linked_projects": ["Old hobby", "Job search"]}]
    projects = [_proj("Job search")]                     # "Old hobby" absent -> dormant
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


# --- Task 5: the held-back count reaches the LLM context --------------------

def test_task_ref_line_carries_held_back():
    tasks = [{"id": "id-a", "name": "Draft the section", "held_back": 2},
             {"id": "id-b", "name": "Email Donna"}]
    _, table = pg._build_task_refs(tasks)
    assert "T1 — Draft the section" in table
    assert "2 more in this thread" in table            # the honest per-thread count reaches the model
    assert "T2 — Email Donna" in table                 # no annotation when nothing held back


# --- held_back threading onto the plan JSON (renderer still consumes the field) -------------

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


# --- Task 1 (plan-input seam): loader resolves a project's Goal link ---------

def _goal_obj(oid, name):
    return {"id": oid, "type": {"key": "gsdo_goal"}, "name": name, "properties": []}


def _project_obj_with_goal(oid, name, goal_ids=None, engagement=None):
    props = []
    if goal_ids:
        props.append({"key": "gsdo_goal_link", "objects": goal_ids})
    if engagement:
        props.append({"name": "Engagement", "select": {"name": engagement}})
    return {"id": oid, "type": {"key": "gsdo_project"}, "name": name, "properties": props}


def test_loader_resolves_goal_link_to_goal_name(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _goal_obj("g1", "Stay a scholar-builder"),
        _project_obj_with_goal("p1", "Leatherworking", goal_ids=["g1"], engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    proj = next(p for p in projects if p["name"] == "Leatherworking")
    assert proj["goal_id"] == "g1"
    assert proj["goal_name"] == "Stay a scholar-builder"


def test_loader_project_with_no_goal_link_has_none(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Household", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert projects[0]["goal_id"] is None and projects[0]["goal_name"] is None


# --- Task 2 (plan-input seam): active-only at load — Backburner excluded ------

def test_backburner_project_excluded_at_load(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Old hobby", engagement="Backburner"),
        _project_obj_with_goal("p2", "Job search", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Job search"}


def _daily_life_project_obj(oid, name, engagement=None):
    props = [{"name": "Side", "select": {"name": "Daily life"}}]
    if engagement:
        props.append({"name": "Engagement", "select": {"name": engagement}})
    return {"id": oid, "type": {"key": "gsdo_project"}, "name": name, "properties": props}


def test_daily_life_backburner_project_is_also_excluded(monkeypatch):
    # REFINEMENT: engagement is universal — a Backburner Daily-life project is dormant like any
    # other. No Daily-life exemption anymore.
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _daily_life_project_obj("p1", "Old chores", engagement="Backburner"),
        _daily_life_project_obj("p2", "Household", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Household"}


def test_open_and_unset_engagement_projects_stay_active(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Open thread", engagement="Open"),
        _project_obj_with_goal("p2", "Unset thread"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Open thread", "Unset thread"}


# --- Task 3 (plan-input seam): future-Scheduled tasks held off today ---------

def _task_obj_scheduled(oid, name, scheduled=None):
    props = [{"key": "gsdo_task_status", "select": {"name": "Active"}}]
    if scheduled is not None:
        props.append({"key": "scheduled", "date": scheduled})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def test_future_scheduled_task_excluded_at_load(monkeypatch):
    import datetime as dt, daily_plan as dp
    future = (dt.date.today() + dt.timedelta(days=5)).isoformat()
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _task_obj_scheduled("t1", "Future thing", scheduled=future),
        _task_obj_scheduled("t2", "No date thing"),
    ])
    _, _, tasks, _, _, _ = dp.load_active_items("sid")
    assert {t["id"] for t in tasks} == {"t2"}          # the future-dated one is held off today


def test_today_or_earlier_scheduled_task_stays(monkeypatch):
    import datetime as dt, daily_plan as dp
    past = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _task_obj_scheduled("t1", "Overdue-scheduled", scheduled=past),
        _task_obj_scheduled("t2", "Today", scheduled=dt.date.today().isoformat()),
    ])
    _, _, tasks, _, _, _ = dp.load_active_items("sid")
    assert {t["id"] for t in tasks} == {"t1", "t2"}
