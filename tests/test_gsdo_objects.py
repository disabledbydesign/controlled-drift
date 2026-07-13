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

def test_guard_keeps_right_kind_link(monkeypatch):
    # A Task linked to a real Project is untouched — the guard only refuses wrong kinds.
    monkeypatch.setattr(o, "_object_type_key", lambda sid, oid: "gsdo_project")
    props = o.guard_link_kinds("sid", "task", {"Linked Projects": ["proj-1"], "Task status": "Ready"})
    assert props == {"Linked Projects": ["proj-1"], "Task status": "Ready"}

def test_guard_drops_wrong_kind_link(monkeypatch):
    # A Task linked to a GOAL (wrong kind) — the link is dropped, the object still gets created,
    # and no bad link is written. Non-link properties are left alone.
    monkeypatch.setattr(o, "_object_type_key", lambda sid, oid: "gsdo_goal")
    props = o.guard_link_kinds("sid", "task", {"Linked Projects": ["goal-1"], "Task status": "Ready"})
    assert "Linked Projects" not in props        # every id wrong-kind -> no link at all
    assert props == {"Task status": "Ready"}

def test_guard_keeps_right_drops_wrong_in_mixed_list(monkeypatch):
    kinds = {"proj-1": "gsdo_project", "goal-9": "gsdo_goal"}
    monkeypatch.setattr(o, "_object_type_key", lambda sid, oid: kinds[oid])
    props = o.guard_link_kinds("sid", "task", {"Linked Projects": ["proj-1", "goal-9"]})
    assert props["Linked Projects"] == ["proj-1"]  # the wrong-kind one is dropped, right kept

def test_guard_keeps_unverifiable_link(monkeypatch):
    # A link whose target can't be read is KEPT — we only drop what we can prove is wrong-kind.
    monkeypatch.setattr(o, "_object_type_key", lambda sid, oid: None)
    props = o.guard_link_kinds("sid", "task", {"Linked Projects": ["mystery"]})
    assert props == {"Linked Projects": ["mystery"]}

def test_guard_enforces_project_and_recurring_rules(monkeypatch):
    # Project -> Goal is the rule; a Project linked to another Project is refused. And a Recurring
    # links to a Project. Each type's own link property + expected kind.
    monkeypatch.setattr(o, "_object_type_key", lambda sid, oid: "gsdo_project")
    proj = o.guard_link_kinds("sid", "gsdo_project", {"Goal link": ["proj-x"]})
    assert "Goal link" not in proj                 # a Project is not a Goal -> dropped
    rec = o.guard_link_kinds("sid", "gsdo_recurring", {"Project link": ["proj-x"]})
    assert rec == {"Project link": ["proj-x"]}     # Recurring -> Project is right-kind

def test_guard_untouched_for_unlinked_and_nonlink_creates(monkeypatch):
    # No link property present, and a type with no link rule (Goal): guard never fetches, never
    # changes anything — legitimate unlinked creates are not broken.
    called = {"n": 0}
    def _boom(sid, oid): called["n"] += 1; return "gsdo_project"
    monkeypatch.setattr(o, "_object_type_key", _boom)
    assert o.guard_link_kinds("sid", "task", {"Task status": "Ready"}) == {"Task status": "Ready"}
    assert o.guard_link_kinds("sid", "gsdo_goal", {"Goal status": "Active"}) == {"Goal status": "Active"}
    assert called["n"] == 0                          # nothing to verify -> no network reads

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
