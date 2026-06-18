# tests/test_gsdo_objects.py
# Integration test against the live Anytype API. Creates objects then deletes them (self-cleaning).
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdo_objects as o
import gsdo_anytype as g
from anytype_test import call

def _delete(oid):
    call("DELETE", f"/spaces/{g.get_space_id()}/objects/{oid}")

def test_create_task_with_mixed_value_types():
    """Exercises select, multi_select, checkbox, text value-formatting + name resolution."""
    oid = None
    try:
        oid = o.create("Task", "__test task (gsdo-test)__",
                       body="probe body",
                       properties={
                           "Task status": "Active",                       # select by option name
                           "Access conditions": ["Can-be-done-lying-down"], # multi_select by names
                           "AI autonomous": True,                          # checkbox
                           "Blocked on": "nothing",                        # text
                       })
        assert oid
        sid = g.get_space_id()
        rb = call("GET", f"/spaces/{sid}/objects/{oid}")[1].get("object", {})
        pv = {p.get("key"): p for p in rb.get("properties", [])}
        assert pv["gsdo_task_status"]["select"]["name"] == "Active"
        assert pv["gsdo_access_conditions"]["multi_select"][0]["name"] == "Can-be-done-lying-down"
        assert pv["gsdo_ai_autonomous"]["checkbox"] is True
    finally:
        if oid:
            _delete(oid)

def test_unknown_select_option_raises():
    import pytest
    with pytest.raises(ValueError):
        # 'Nonsense' is not a Task status option -> must raise, not silently miswrite
        oid = o.create("Task", "__should not persist__",
                       properties={"Task status": "Nonsense"})
        _delete(oid)  # safety if it wrongly succeeded
