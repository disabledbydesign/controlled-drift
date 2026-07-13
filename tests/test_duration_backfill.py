"""Tests for duration_backfill — estimate + label durations onto existing duration-less tasks.
The LLM seam and Anytype are always mocked; nothing here calls a model or touches the live space."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import duration_backfill as db


def _task(oid, name, dur=None, status="Ready"):
    props = [{"key": "gsdo_task_status", "select": {"name": status}}]
    if dur is not None:
        props.append({"key": "gsdo_duration_min", "number": dur})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def test_load_sizeless_tasks_excludes_tasks_with_a_duration(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(db.g, "fetch_all_objects", lambda sid: [
        _task("t1", "Study Python"),                 # no duration -> included
        _task("t2", "Call pharmacy", dur=15),        # already sized -> excluded
        {"id": "g1", "type": {"key": "gsdo_goal"}, "name": "A goal", "properties": []},
    ])
    tasks = db.load_sizeless_tasks(sid="sid")
    assert [t["id"] for t in tasks] == ["t1"]


def test_parse_estimates_reads_json_array():
    text = "```json\n" + json.dumps([{"id": "t1", "estimated_min": 90, "reasoning": "study block"}]) + "\n```"
    ests = db.parse_estimates(text)
    assert ests[0]["id"] == "t1" and ests[0]["estimated_min"] == 90


def test_parse_estimates_raises_without_block():
    import pytest
    with pytest.raises(RuntimeError):
        db.parse_estimates("no json here")


def test_apply_writes_labeled_estimate_and_reads_back(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    # Pre-resolve the source key so apply() never reaches out to the live space to find it
    # (keeps this test hermetic — nothing here touches Anytype or a model).
    monkeypatch.setattr(db, "_DURATION_SOURCE_KEY", "duration_source")
    updated = {}

    def fake_update(oid, name=None, properties=None):
        updated[oid] = properties or {}
        return oid
    monkeypatch.setattr(db.gsdo_objects, "update", fake_update)
    # Model the real sequence: the pre-write fetch shows the task still has no duration (so apply
    # proceeds); the post-write read-back shows the value we just wrote, labeled estimated.
    fetches = {"n": 0}

    def stateful_get(oid):
        fetches["n"] += 1
        if fetches["n"] == 1:
            return {"id": oid, "properties": []}   # pre-check: still sizeless -> proceed
        return {"id": oid, "properties": [          # read-back: the written, labeled value
            {"key": "gsdo_duration_min", "number": 90},
            {"key": db._DURATION_SOURCE_KEY, "select": {"name": "estimated"}}]}
    monkeypatch.setattr(db, "_get_task", stateful_get)

    preview = {"tasks": [_task("t1", "Study Python")],
               "estimates": [{"id": "t1", "estimated_min": 90, "reasoning": "x"}],
               "by_id": {"t1": _task("t1", "Study Python")}}
    result = db.apply(preview)
    assert result["updated"] == 1
    assert updated["t1"]["Duration min"] == 90
    assert updated["t1"]["Duration source"] == "estimated"


def test_apply_skips_task_that_gained_a_duration_since_preview(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(db, "_DURATION_SOURCE_KEY", "duration_source")
    monkeypatch.setattr(db.gsdo_objects, "update",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")))
    # by the time apply runs, t1 already has a stated duration -> never overwrite
    monkeypatch.setattr(db, "_get_task", lambda oid: _task("t1", "Study Python", dur=20))
    preview = {"tasks": [_task("t1", "Study Python")],
               "estimates": [{"id": "t1", "estimated_min": 90, "reasoning": "x"}],
               "by_id": {"t1": _task("t1", "Study Python")}}
    result = db.apply(preview)
    assert result["updated"] == 0 and result["skipped_no_estimate"] >= 0
