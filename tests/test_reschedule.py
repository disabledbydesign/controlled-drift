# tests/test_reschedule.py — tap-a-chip-to-fix reschedule. Mocks update + read-back; no network.
# The update mock mirrors the REAL gsdo_objects.update(object_id, name=None, properties=None),
# which task_actions calls with properties= (keyword), exactly like complete_task.
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def test_reschedule_sets_scheduled(monkeypatch):
    from importlib import import_module
    ta = import_module("task_actions")
    seen = {}
    monkeypatch.setattr(ta.gsdo_objects, "update",
                        lambda oid, name=None, properties=None: seen.update({"id": oid, **(properties or {})}) or {"id": oid})
    monkeypatch.setattr(ta, "_get_object",
                        lambda oid: {"id": oid, "properties": [{"key": ta.SCHEDULED_KEY, "date": "2026-07-16T00:00:00Z"}]})
    out = ta.reschedule_task("abc", "thursday", today=dt.date(2026, 7, 13))
    assert seen["Scheduled"] == "2026-07-16"
    assert out["when_label"] == "Thu Jul 16"


def test_reschedule_raises_when_scheduled_absent_on_readback(monkeypatch):
    """The write silently didn't land: the read-back carries NO Scheduled date at all. That used
    to pass the guard (`persisted is not None and ...`) and report success — a saved-looking
    nothing, exactly what read-back exists to prevent."""
    import pytest
    from importlib import import_module
    ta = import_module("task_actions")
    monkeypatch.setattr(ta.gsdo_objects, "update",
                        lambda oid, name=None, properties=None: {"id": oid})
    monkeypatch.setattr(ta, "_get_object", lambda oid: {"id": oid, "properties": []})
    with pytest.raises(RuntimeError) as e:
        ta.reschedule_task("abc", "thursday", today=dt.date(2026, 7, 13))
    assert "Scheduled did not persist" in str(e.value)


def test_reschedule_someday_parks(monkeypatch):
    from importlib import import_module
    ta = import_module("task_actions")
    seen = {}
    monkeypatch.setattr(ta.gsdo_objects, "update",
                        lambda oid, name=None, properties=None: seen.update(properties or {}) or {"id": oid})
    # honest read-back needs the persisted status to confirm the park — the stub provides it.
    monkeypatch.setattr(ta, "_get_object",
                        lambda oid: {"id": oid, "properties": [{"key": ta.TASK_STATUS_KEY, "select": {"name": "Parked"}}]})
    out = ta.reschedule_task("abc", "someday", today=dt.date(2026, 7, 13))
    assert seen.get("Task status") == "Parked"
    assert out["when_label"] == "Parked"
