# tests/test_engagement_chip.py — tap-to-change engagement chip backend (server.set_project_engagement).
# Mocks gsdo_objects.update, capture_generate._get_object (read-back), and engagement_log.log_change;
# no network, no real Anytype. Mirrors the reschedule test's monkeypatch style (test_reschedule.py):
# the update mock takes (object_id, name=None, properties=None) exactly like the real gsdo_objects.update.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def test_set_project_engagement_writes_reads_back_and_logs(monkeypatch):
    from importlib import import_module
    srv = import_module("server")

    update_calls = []
    monkeypatch.setattr(srv.gsdo_objects, "update",
                        lambda oid, name=None, properties=None: update_calls.append(
                            {"id": oid, "properties": properties}) or {"id": oid})

    def fake_get_object(oid):
        return {"id": oid, "name": "Redesign the kitchen",
                "properties": [{"name": "Engagement", "select": {"name": "Steady"}}]}
    monkeypatch.setattr(srv.capture_generate, "_get_object", fake_get_object)

    log_calls = []
    monkeypatch.setattr(srv.engagement_log, "log_change",
                        lambda pid, name, old, new: log_calls.append((pid, name, old, new)))

    out = srv.set_project_engagement("proj123", "Open", "Steady")

    assert out == "Steady"
    assert len(update_calls) == 1
    assert update_calls[0]["id"] == "proj123"
    assert update_calls[0]["properties"] == {"Engagement": "Steady"}
    assert log_calls == [("proj123", "Redesign the kitchen", "Open", "Steady")]


def test_set_project_engagement_raises_on_readback_mismatch(monkeypatch):
    from importlib import import_module
    srv = import_module("server")

    monkeypatch.setattr(srv.gsdo_objects, "update",
                        lambda oid, name=None, properties=None: {"id": oid})

    def fake_get_object(oid):
        # The write didn't actually persist to "Steady" — read-back still shows the old value.
        return {"id": oid, "name": "Redesign the kitchen",
                "properties": [{"name": "Engagement", "select": {"name": "Open"}}]}
    monkeypatch.setattr(srv.capture_generate, "_get_object", fake_get_object)

    log_calls = []
    monkeypatch.setattr(srv.engagement_log, "log_change",
                        lambda pid, name, old, new: log_calls.append((pid, name, old, new)))

    try:
        srv.set_project_engagement("proj123", "Open", "Steady")
        assert False, "expected RuntimeError on read-back mismatch"
    except RuntimeError:
        pass

    # A failed read-back must never reach the log — nothing to learn from an unpersisted change.
    assert log_calls == []
