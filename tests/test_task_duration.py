"""General duration edit: task_actions.set_task_duration writes 'Duration min' + reads back.

The Anytype write + read-back are mocked (never hit the real space). The route dispatch
(block vs real-object) is proven live in the integration verify.
"""
import pytest
import task_actions


def test_set_task_duration_writes_by_name_and_reads_back(monkeypatch):
    calls = []
    monkeypatch.setattr(task_actions.gsdo_objects, "update",
                        lambda oid, properties=None, **k: calls.append((oid, properties)))
    monkeypatch.setattr(task_actions, "_get_object",
                        lambda tid: {"name": "Go on a walk",
                                     "properties": [{"key": "gsdo_duration_min", "number": 60}]})
    out = task_actions.set_task_duration("t1", 60)
    assert calls == [("t1", {"Duration min": 60})]
    assert out == {"id": "t1", "name": "Go on a walk", "duration_min": 60}


def test_set_task_duration_raises_on_readback_mismatch(monkeypatch):
    monkeypatch.setattr(task_actions.gsdo_objects, "update", lambda *a, **k: None)
    monkeypatch.setattr(task_actions, "_get_object",
                        lambda tid: {"properties": [{"key": "gsdo_duration_min", "number": 30}]})
    with pytest.raises(RuntimeError):
        task_actions.set_task_duration("t1", 60)   # wrote 60, read back 30 → no silent write
