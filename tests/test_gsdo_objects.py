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

def test_update_name_and_text_property():
    """update() changes an existing object's name + a text property, resolving shapes."""
    oid = None
    try:
        oid = o.create("Project", "__test stream (gsdo-test)__",
                       properties={"gsdo_context": "what it is — original\nnext step — original"})
        assert oid
        o.update(oid, name="__renamed stream (gsdo-test)__",
                 properties={"gsdo_context": "what it is — updated\nnext step — updated"})
        sid = g.get_space_id()
        rb = call("GET", f"/spaces/{sid}/objects/{oid}")[1].get("object", {})
        assert rb.get("name") == "__renamed stream (gsdo-test)__"
        pv = {p.get("key"): p for p in rb.get("properties", [])}
        assert "updated" in pv["gsdo_context"]["text"]
    finally:
        if oid:
            _delete(oid)

def test_update_nothing_raises():
    import pytest
    with pytest.raises(ValueError):
        o.update("whatever", )  # no name, no properties

def test_unknown_select_option_raises():
    import pytest
    with pytest.raises(ValueError):
        # 'Nonsense' is not a Task status option -> must raise, not silently miswrite
        oid = o.create("Task", "__should not persist__",
                       properties={"Task status": "Nonsense"})
        _delete(oid)  # safety if it wrongly succeeded

def test_create_dedups_on_exact_name_same_type():
    """Two create() calls with the identical name + type return the SAME id, not two objects.

    Guards against the 3x-duplicate failure (a real prior incident: a Strategy got created 3x
    because nothing in the write layer caught a repeat name). Confirmed empirically 2026-07-02
    that neither this function nor the live Anytype API deduped by name before this guard.
    """
    oid1 = oid2 = oid3 = None
    try:
        name = "__test dedup task (gsdo-test)__"
        oid1 = o.create("Task", name, properties={"Task status": "Ready"})
        oid2 = o.create("Task", name, properties={"Task status": "Ready"})
        assert oid1 == oid2

        # A different name must NOT be caught by the guard (no false dedup).
        oid3 = o.create("Task", "__test dedup task different (gsdo-test)__",
                        properties={"Task status": "Ready"})
        assert oid3 != oid1
    finally:
        for oid in {oid1, oid2, oid3} - {None}:
            _delete(oid)
