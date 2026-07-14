import daily_plan


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
