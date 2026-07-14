"""Tests for block chunk length — durable Anytype preference + local event log.

The Anytype write is mocked (never hit the real space in a test); the local log uses an
explicit tmp path. Mirrors how test_plan_mirror.py mocks the write layer.
"""
import block_duration


def test_get_chunk_min_returns_field_value_when_set():
    assert block_duration.get_chunk_min({"chunk_min": 240}) == 240


def test_get_chunk_min_normalizes_float_to_int():
    assert block_duration.get_chunk_min({"chunk_min": 120.0}) == 120


def test_get_chunk_min_falls_back_to_default_when_unset():
    assert block_duration.get_chunk_min({"chunk_min": None}) == block_duration.BLOCK_DEFAULT_MIN
    assert block_duration.get_chunk_min({}) == block_duration.BLOCK_DEFAULT_MIN
    assert block_duration.get_chunk_min({}, default=45) == 45


def test_set_chunk_min_writes_anytype_and_logs_event(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(block_duration.gsdo_objects, "update",
                        lambda oid, properties=None, **kw: calls.append((oid, properties)))
    p = tmp_path / "block_duration_log.jsonl"
    block_duration.set_chunk_min("proj-1", 180, path=str(p))

    # Anytype write: by display name, correct value.
    assert calls == [("proj-1", {"Block chunk min": 180})]
    # Local event appended: full ts, event 'set', minutes.
    events = block_duration.read_events(path=str(p))
    assert len(events) == 1
    assert events[0]["event"] == "set"
    assert events[0]["project_id"] == "proj-1"
    assert events[0]["minutes"] == 180
    assert "T" in events[0]["ts"]  # full timestamp kept for later pattern-mining


def test_log_scheduled_appends_without_anytype_write(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(block_duration.gsdo_objects, "update",
                        lambda *a, **k: called.append(True))
    p = tmp_path / "block_duration_log.jsonl"
    block_duration.log_scheduled("proj-2", 90, path=str(p))
    block_duration.log_scheduled("proj-2", 120, path=str(p))

    assert called == []  # scheduling logs only, never writes Anytype
    events = block_duration.read_events(path=str(p))
    assert [e["event"] for e in events] == ["scheduled", "scheduled"]
    assert [e["minutes"] for e in events] == [90, 120]


def test_read_events_empty_when_no_file(tmp_path):
    assert block_duration.read_events(path=str(tmp_path / "nope.jsonl")) == []
