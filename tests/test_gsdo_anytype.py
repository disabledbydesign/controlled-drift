# tests/test_gsdo_anytype.py
# Integration tests against the live Anytype API (the repo's established pattern).
# Tests that CREATE properties clean up after themselves so they don't pollute the real space.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdo_anytype as g
from anytype_test import call

def _delete_prop_by_name(name):
    """Remove every property with this display name (test teardown)."""
    sid = g.get_space_id()
    for p in call("GET", f"/spaces/{sid}/properties?limit=200")[1].get("data", []):
        if p.get("name") == name:
            call("DELETE", f"/spaces/{sid}/properties/{p['id']}")

def _count_named(name):
    sid = g.get_space_id()
    data = call("GET", f"/spaces/{sid}/properties?limit=200")[1].get("data", [])
    return sum(1 for p in data if p.get("name") == name)

def test_space_id_resolves():
    assert isinstance(g.get_space_id(), str) and len(g.get_space_id()) > 10

def test_ensure_property_is_idempotent():
    name = "Test Context (gsdo-test)"
    try:
        k1 = g.ensure_property(name, "text")
        k2 = g.ensure_property(name, "text")
        assert k1 == k2          # second call must NOT create a duplicate
        assert _count_named(name) == 1
    finally:
        _delete_prop_by_name(name)

def test_reuses_existing_duration_property():
    # 'Duration min' already exists in the space; ensure must find/reuse, not recreate
    before = _count_named("Duration min")
    k = g.ensure_property("Duration min", "number")
    after = _count_named("Duration min")
    assert g.find_property(k) is not None
    assert after == before == 1  # reused the single existing property, no duplicate created

def test_ensure_select_options_idempotent():
    name = "Test Status (gsdo-test)"
    try:
        k = g.ensure_property(name, "select", options=["Active", "Parked"])
        g.ensure_select_options(k, ["Active", "Parked"])  # re-run must not duplicate tags
        assert g.find_property(k) is not None
        assert _count_named(name) == 1
    finally:
        _delete_prop_by_name(name)

def _type_property_keys(type_id):
    sid = g.get_space_id()
    t = call("GET", f"/spaces/{sid}/types/{type_id}")[1].get("type", {})
    return {p.get("key") for p in t.get("properties", [])}

def test_unlink_properties_from_type_removes_a_linked_property():
    # Uses the real Recurring type (unlink_properties_from_type's actual production target) but
    # only touches a throwaway scratch property, cleaned up in the finally block.
    name = "Test Unlink (gsdo-test)"
    recurring = g.find_type("Recurring")
    try:
        k = g.ensure_property(name, "text")
        g.link_properties_to_type(recurring["id"], [k])
        assert k in _type_property_keys(recurring["id"])

        g.unlink_properties_from_type(recurring["id"], [k])
        assert k not in _type_property_keys(recurring["id"])
    finally:
        _delete_prop_by_name(name)

def test_unlink_properties_from_type_noop_when_not_linked():
    # Unlinking a key that was never linked (or already removed) must not error or perturb
    # the type's other properties — the removal is skip-if-absent, not assert-present.
    recurring = g.find_type("Recurring")
    before = _type_property_keys(recurring["id"])
    g.unlink_properties_from_type(recurring["id"], ["gsdo_definitely_not_linked_key"])
    assert _type_property_keys(recurring["id"]) == before

def test_recurring_mirrors_task_situated_fields_by_identical_key():
    # Cross-family review (2026-07-17): build_recurring.py reuses Task's exact property keys for
    # its 7 mirrored situated fields (build_task.py:16-27) — a name/type/option mismatch between
    # the two build_*.py calls would silently MINT A DUPLICATE property instead of reusing Task's
    # (ensure_property finds-by-name; a near-miss name creates new). This is a permanent live
    # regression guard, not just a one-time build_model.py verification.
    task = g.find_type("task")
    recurring = g.find_type("Recurring")
    task_by_name = {p.get("name"): p.get("key") for p in task.get("properties", [])}
    recurring_by_name = {p.get("name"): p.get("key") for p in recurring.get("properties", [])}
    mirrored = ["Needs clarifying", "Blocked on", "Affective", "Access conditions",
                "Access notes", "AI autonomous", "Relevant docs"]
    for name in mirrored:
        assert name in task_by_name, f"{name!r} missing from Task — can't verify the mirror"
        assert name in recurring_by_name, f"{name!r} missing from Recurring"
        assert recurring_by_name[name] == task_by_name[name], (
            f"{name!r} has DIFFERENT keys on Task ({task_by_name[name]!r}) vs Recurring "
            f"({recurring_by_name[name]!r}) — a duplicate property was minted, not reused")
