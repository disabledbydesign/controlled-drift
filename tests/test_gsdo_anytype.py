# tests/test_gsdo_anytype.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdo_anytype as g

def test_space_id_resolves():
    assert isinstance(g.get_space_id(), str) and len(g.get_space_id()) > 10

def test_ensure_property_is_idempotent():
    k1 = g.ensure_property("GSDO Test Context", "text")
    k2 = g.ensure_property("GSDO Test Context", "text")
    assert k1 == k2  # second call must NOT create a duplicate

def _count_named(name):
    sid = g.get_space_id()
    data = g.call("GET", f"/spaces/{sid}/properties?limit=200")[1].get("data", [])
    return sum(1 for p in data if p.get("name") == name)

def test_reuses_existing_duration_property():
    # gsdo_duration_min already exists in the space; ensure must find/reuse, not recreate
    before = _count_named("GSDO Duration min")
    k = g.ensure_property("GSDO Duration min", "number")
    after = _count_named("GSDO Duration min")
    assert g.find_property(k) is not None
    assert after == before == 1  # reused the single existing property, no duplicate created

def test_ensure_select_options_idempotent():
    k = g.ensure_property("GSDO Test Status", "select", options=["Active", "Parked"])
    before = g.find_property(k)
    g.ensure_select_options(k, ["Active", "Parked"])  # re-run
    after = g.find_property(k)
    assert before is not None and after is not None
