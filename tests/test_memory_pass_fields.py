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


def test_apply_candidate_forwards_estimated_duration(monkeypatch):
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-1")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Draft the SSRC narrative"})
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "id": "t"})
    mp.apply_candidate({
        "proposed_name": "Draft the SSRC narrative", "proposed_type": "Task", "link_to": None,
        "duration_estimate_min": 120,
    })
    assert seen["Duration min"] == 120
    assert seen["Duration source"] == "estimated"


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


# --- Task A3: memory-pass Projects write the proposed engagement, not hardcoded Steady ----

def _apply_candidate_props(monkeypatch, candidate):
    """Stub the network + read-back the same way the duration/affect tests above do, run
    apply_candidate on `candidate`, and return the props dict passed to gsdo_objects.create —
    the shared capture point every A3 memory-pass test needs (mirrors the duration/affect stubs;
    added here since no prior task introduced this helper)."""
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-x")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": candidate["proposed_name"]})
    type_key = (candidate.get("proposed_type") or "task").strip().lower()
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": type_key, "id": "t"})
    candidate.setdefault("link_to", None)
    mp.apply_candidate(candidate)
    return seen


def test_memory_pass_project_writes_engagement(monkeypatch):
    # a Project candidate with an explicit Backburner signal + notes
    props = _apply_candidate_props(monkeypatch, {
        "proposed_type": "Project", "proposed_name": "Old side thing",
        "engagement": "Backburner", "engagement_notes": "revisit after the move",
    })
    assert props["Engagement"] == "Backburner"
    assert props["Engagement notes"] == "revisit after the move"


def test_memory_pass_project_defaults_open(monkeypatch):
    props = _apply_candidate_props(monkeypatch, {
        "proposed_type": "Project", "proposed_name": "Named but unsignalled",
    })
    assert props["Engagement"] == "Open"   # NOT hardcoded Steady, NOT blank
