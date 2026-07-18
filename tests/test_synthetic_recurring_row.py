import daily_plan

def test_synthetic_recurring_row_shape():
    obj = {"id": "rec-1", "name": "Water plants",
           "properties": [
               {"key": "gsdo_project_link", "objects": [{"id": "p1"}]},
               {"key": "gsdo_context", "text": "kitchen"}]}
    row = daily_plan.synthetic_recurring_row(obj, {"p1": "Household"},
                                             duration_min=15, as_needed=False)
    assert row["id"] == "rec-1"
    assert row["name"] == "Water plants"
    assert row["is_recurring"] is True
    assert row["as_needed"] is False
    assert row["duration_min"] == 15
    assert row["context"] == "kitchen"
    assert row["linked_projects"] == ["Household"]
    assert row["status"] == "Ready" and row["due_date"] is None
