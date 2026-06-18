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
