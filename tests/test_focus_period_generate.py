"""focus_period_generate — the LLM-authoring backend. The LLM call itself isn't unit-tested
(non-deterministic); the pure parse + prompt-anchor are."""
import datetime as dt
import focus_period_generate as fpg
import daily_plan as dp


def test_parse_fields_from_fenced_json():
    text = 'Here you go:\n```json\n{"name": "Week of Jun 30", "output_format": "Auto"}\n```\nend'
    out = fpg.parse_fields(text)
    assert out["name"] == "Week of Jun 30"
    assert out["output_format"] == "Auto"


def test_parse_fields_from_bare_json():
    out = fpg.parse_fields('{"foreground_projects": ["Job Search"], "paused_projects": []}')
    assert out["foreground_projects"] == ["Job Search"]
    assert out["paused_projects"] == []


def test_prompt_carries_the_deterministic_date_anchor():
    # Python supplies today; the LLM must never guess the current date.
    prompt = fpg.build_authoring_prompt("jobs this week", dt.date(2026, 7, 2), ["Job Search"])
    assert "Thursday" in prompt and "2026-07-02" in prompt   # weekday + ISO anchor present
    assert "Job Search" in prompt                             # her real project names offered


def test_prompt_carries_goals_and_tasks_as_grounding_context():
    # Goals/Tasks are grounding only (not a field the model fills) — but must be visible so the
    # model can recognize a real name ("Material survival") instead of inventing generic framing.
    prompt = fpg.build_authoring_prompt(
        "focusing on survival stuff", dt.date(2026, 7, 2), ["Job Search"],
        goals=["Material survival"], tasks=["Packing"])
    assert "Material survival" in prompt
    assert "Packing" in prompt


def test_prompt_handles_no_goals_or_tasks():
    # Grounding lists can be empty (new space, or nothing fetched) — must not crash or render "None".
    prompt = fpg.build_authoring_prompt("jobs this week", dt.date(2026, 7, 2), ["Job Search"])
    assert "None" not in prompt


def test_prompt_lists_reactivate_tasks_output_key():
    # The authoring prompt must ask the model for reactivate_tasks — Task 6's "just say it" entry
    # point for as-needed reactivation via Focus Period.
    prompt = fpg.build_authoring_prompt(
        "keep the dishes going", dt.date(2026, 7, 2), ["Job Search"], tasks=["Clean the fridge"])
    assert "reactivate_tasks" in prompt
    assert "Clean the fridge" in prompt   # her existing tasks are visible for the model to match


# --- _load_authoring_context: the filtering logic itself, mocked loader ------
# Same fixture convention as test_within_thread_pick.py (mock dp.g, call the real loader) —
# proves the workstream/hobby/discrete-task filtering against realistic raw Anytype shapes,
# not just that the prompt renders whatever list it's handed.

def _goal_obj(oid, name):
    return {"id": oid, "type": {"key": "gsdo_goal"}, "name": name, "properties": []}


def _project_obj(oid, name, side=None, is_workstream=False):
    props = [{"name": "Engagement", "select": {"name": "Steady"}}]
    if side is not None:
        props.append({"name": "Side", "select": {"name": side}})
    if is_workstream:
        props.append({"key": "is_workstream", "checkbox": True})
    return {"id": oid, "type": {"key": "gsdo_project"}, "name": name, "properties": props}


def _task_obj(oid, name, linked_project_ids=None):
    props = [{"key": "gsdo_task_status", "select": {"name": "Ready"}}]
    if linked_project_ids:
        props.append({"key": "linked_projects", "objects": linked_project_ids})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def _recurring_obj(oid, name, interval_unit="as_needed", active=False):
    return {"id": oid, "type": {"key": "gsdo_recurring"}, "name": name,
            "properties": [{"key": "interval_unit", "select": {"name": interval_unit}},
                           {"key": "active", "checkbox": active}]}


def test_load_authoring_context_filters_workstreams_hobby_and_block_tasks(monkeypatch):
    monkeypatch.setattr(fpg.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _goal_obj("g1", "Stay a scholar-builder"),
        _project_obj("p1", "Daily Chore Project", side="Daily life"),
        _project_obj("p2", "Big Work Project"),                          # no Side -> block grain
        _project_obj("p3", "Hobby Project", side="Fun / hobby"),
        _project_obj("p4", "A Workstream", is_workstream=True),
        _task_obj("t1", "Water the plants", linked_project_ids=["p1"]),  # discrete (Daily life)
        _task_obj("t2", "Draft the intro", linked_project_ids=["p2"]),   # block-project -> excluded
        _task_obj("t3", "Leatherworking step", linked_project_ids=["p3"]),  # hobby -> excluded
        _task_obj("t4", "Dev backlog item", linked_project_ids=["p4"]),  # workstream -> excluded
        _task_obj("t5", "Orphan errand"),                                # no project -> discrete
    ])
    projects, goals, tasks = fpg._load_authoring_context()
    assert projects == ["Daily Chore Project", "Big Work Project", "Hobby Project"]  # workstream out
    assert goals == ["Stay a scholar-builder"]
    assert tasks == ["Water the plants", "Orphan errand"]


def test_load_authoring_context_includes_off_as_needed_recurring(monkeypatch):
    # THE fix (Task 6 review, 2026-07-17): daily_plan.load_active_items only folds an as_needed
    # Recurring into `tasks` when it's "due today" — which for as_needed IS its Active state — so
    # an OFF task (the one June needs to NAME to reactivate) was structurally invisible to the
    # authoring prompt's grounding list. It must now be merged in regardless of Active state.
    monkeypatch.setattr(fpg.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _recurring_obj("r1", "Clean the fridge", interval_unit="as_needed", active=False),  # OFF
        _recurring_obj("r2", "Water the garden", interval_unit="as_needed", active=True),   # ON
    ])
    _projects, _goals, tasks = fpg._load_authoring_context()
    assert "Clean the fridge" in tasks    # the fix: an OFF as-needed task is now visible
    assert "Water the garden" in tasks    # an already-active one still visible (was already fine)
