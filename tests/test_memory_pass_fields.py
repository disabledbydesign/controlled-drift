import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import memory_pass as mp


def test_apply_candidate_writes_optional_fields(monkeypatch):
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-1")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Renew passport"})
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "id": "t"})
    out = mp.apply_candidate({
        "proposed_name": "Renew passport", "proposed_type": "Task", "link_to": None,
        "context_verbatim": "from memory", "duration_min": 40,
        "affect": "been dreading this", "blocked_on": "need the photos",
        "access_conditions": ["Involves-leaving-house"],
    })
    assert out["outcome"] == "created"
    assert seen["Duration min"] == 40
    assert seen["Affective"] == "been dreading this"
    assert seen["Blocked on"] == "need the photos"
    assert seen["Access conditions"] == ["Involves-leaving-house"]


def test_apply_candidate_no_optional_fields_writes_none(monkeypatch):
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-2")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Note a thing"})
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "id": "t"})
    mp.apply_candidate({"proposed_name": "Note a thing", "proposed_type": "Task", "link_to": None})
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in seen
