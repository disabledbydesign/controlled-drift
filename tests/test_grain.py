import daily_plan
import grain


def test_is_workstream_inherits_from_ancestor():
    parent = {"id": "p", "name": "GRA", "is_workstream": True, "parent_project_id": None}
    child = {"id": "c", "name": "Metabolize", "is_workstream": False, "parent_project_id": "p"}
    daily_plan._inherit_is_workstream([parent, child])
    assert child["is_workstream"] is True


def test_is_workstream_own_true_is_kept():
    p = {"id": "p", "name": "WS", "is_workstream": True, "parent_project_id": None}
    daily_plan._inherit_is_workstream([p])
    assert p["is_workstream"] is True


def test_is_workstream_stays_false_with_no_ws_ancestor():
    parent = {"id": "p", "name": "Real project", "is_workstream": False, "parent_project_id": None}
    child = {"id": "c", "name": "Sub", "is_workstream": False, "parent_project_id": "p"}
    daily_plan._inherit_is_workstream([parent, child])
    assert child["is_workstream"] is False


# ---------------------------------------------------------------------------
# grain.classify — which unit a project shows as in the daily plan
# ---------------------------------------------------------------------------

def test_classify_fun_hobby_is_excluded():
    assert grain.classify({"name": "Guitar", "side": "Fun / hobby"}) == "excluded"


def test_classify_workstream_is_excluded():
    assert grain.classify({"name": "GRA", "side": "Wellbeing", "is_workstream": True}) == "excluded"


def test_classify_daily_life_is_task():
    assert grain.classify({"name": "Dishes", "side": "Daily life"}) == "task"


def test_classify_wellbeing_is_block():
    assert grain.classify({"name": "Write paper", "side": "Wellbeing"}) == "block"


# ---------------------------------------------------------------------------
# grain.project_arc — the ordered step arc under a block
# ---------------------------------------------------------------------------

def _task_obj(name, project_id, order, done):
    """Build a raw-Anytype-shaped task object, mirroring the property shapes in
    orient_map._load (linked_projects "objects", "Step order" number, "Task
    status" select, built-in done checkbox)."""
    return {
        "id": "task-" + name,
        "name": name,
        "type": {"key": "task"},
        "properties": [
            {"key": "linked_projects", "name": "Linked projects",
             "objects": [project_id]},
            {"key": "step_order_key", "name": "Step order", "number": order},
            {"key": "gsdo_task_status", "name": "Task status",
             "select": {"name": "Done"} if done else {"name": "To do"}},
            {"key": "done", "name": "Done", "checkbox": done},
        ],
    }


def test_project_arc_states_in_order():
    proj_id = "proj-1"
    proj_id_to_name = {proj_id: "Write paper"}
    all_objects = [
        _task_obj("Outline", proj_id, 1, done=True),
        _task_obj("Draft", proj_id, 2, done=False),
        _task_obj("Revise", proj_id, 3, done=False),
    ]
    arc = grain.project_arc("Write paper", all_objects, proj_id_to_name)
    assert [s["state"] for s in arc] == ["done", "here", "ahead"]
    assert [s["text"] for s in arc] == ["Outline", "Draft", "Revise"]


def test_project_arc_none_when_no_linked_tasks():
    proj_id_to_name = {"proj-1": "Write paper", "proj-2": "Other"}
    all_objects = [
        _task_obj("Some step", "proj-2", 1, done=False),
    ]
    assert grain.project_arc("Write paper", all_objects, proj_id_to_name) is None
