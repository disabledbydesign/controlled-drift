import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import backfill_engagement as be


def test_propose_backfill_inactive_to_backburner_else_open():
    projects = [
        {"id": "a", "name": "Old thing", "engagement": None, "side": None, "project_status": "Inactive"},
        {"id": "b", "name": "Job search", "engagement": None, "side": None, "project_status": None},
        {"id": "c", "name": "Already set", "engagement": "Steady", "side": None, "project_status": None},
    ]
    out = {p["name"]: p["proposed"] for p in be.propose_backfill(projects)}
    assert out == {"Old thing": "Backburner", "Job search": "Open"}
    assert "Already set" not in out


def test_propose_backfill_covers_daily_life_projects_by_name_hint():
    projects = [
        {"id": "d", "name": "household", "engagement": None, "side": "Daily life", "project_status": None},
        {"id": "e", "name": "Medical and self-care", "engagement": None, "side": "Daily life", "project_status": None},
        {"id": "f", "name": "Friendships and social", "engagement": None, "side": "Daily life", "project_status": None},
    ]
    out = {p["name"]: p["proposed"] for p in be.propose_backfill(projects)}
    assert out == {"household": "Steady", "Medical and self-care": "Steady",
                   "Friendships and social": "Open"}


def test_propose_backfill_forces_the_networking_end_state():
    projects = [
        {"id": "n", "name": "Networking and relationships", "engagement": "Steady",
         "side": "Wellbeing", "project_status": None},
    ]
    props = [p for p in be.propose_backfill(projects) if p["name"] == "Networking and relationships"]
    assert len(props) == 1
    assert props[0]["proposed"] == "Open" and props[0]["side"] == "Daily life"


def test_apply_backfill_writes_and_reads_back(monkeypatch):
    written = {}
    monkeypatch.setattr(be.gsdo_objects, "update",
                        lambda oid, properties: written.update({oid: properties}))
    calls = {"n": 0}

    def fake_get_project(oid):
        calls["n"] += 1
        val = None if calls["n"] == 1 else "Open"
        props = [{"name": "Engagement", "select": {"name": val}}] if val else []
        return {"id": oid, "properties": props}
    monkeypatch.setattr(be, "_get_project", fake_get_project)

    result = be.apply_backfill([{"id": "a", "name": "Old thing", "proposed": "Open"}])
    assert result == {"updated": 1, "skipped": 0, "failed": []}
    assert written["a"] == {"Engagement": "Open"}


def test_apply_backfill_skips_project_that_gained_engagement_since_proposal(monkeypatch):
    monkeypatch.setattr(be.gsdo_objects, "update", lambda oid, properties: (_ for _ in ()).throw(
        AssertionError("must not write — the project already gained a value")))
    monkeypatch.setattr(be, "_get_project", lambda oid: {
        "id": oid, "properties": [{"name": "Engagement", "select": {"name": "Steady"}}]})
    result = be.apply_backfill([{"id": "a", "name": "Old thing", "proposed": "Open"}])
    assert result == {"updated": 0, "skipped": 1, "failed": []}


def test_apply_backfill_required_end_state_writes_side_and_engagement_despite_current_value(monkeypatch):
    written = {}
    monkeypatch.setattr(be.gsdo_objects, "update",
                        lambda oid, properties: written.update({oid: properties}))
    calls = {"n": 0}

    def fake_get_project(oid):
        calls["n"] += 1
        if calls["n"] == 1:
            props = [{"name": "Engagement", "select": {"name": "Steady"}},
                     {"name": "Side", "select": {"name": "Wellbeing"}}]
        else:
            props = [{"name": "Engagement", "select": {"name": "Open"}},
                     {"name": "Side", "select": {"name": "Daily life"}}]
        return {"id": oid, "properties": props}
    monkeypatch.setattr(be, "_get_project", fake_get_project)

    result = be.apply_backfill([{"id": "n", "name": "Networking and relationships",
                                 "proposed": "Open", "side": "Daily life"}])
    assert result == {"updated": 1, "skipped": 0, "failed": []}
    assert written["n"] == {"Engagement": "Open", "Side": "Daily life"}
