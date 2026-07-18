import datetime as dt
import server, plan_store, completion_log

def _stub_plan(monkeypatch, *, recurring=False, as_needed=False):
    monkeypatch.setattr(plan_store, "is_as_needed_item", lambda tid: as_needed)
    monkeypatch.setattr(plan_store, "is_recurring_item", lambda tid: recurring)
    monkeypatch.setattr(plan_store, "is_block_item", lambda tid: False)
    monkeypatch.setattr(plan_store, "mark_item_done", lambda tid: {"items": []})
    monkeypatch.setattr(plan_store, "mark_item_undone", lambda tid: {"items": []})
    monkeypatch.setattr(plan_store, "item_name", lambda tid: "Do the dishes")

def test_recurring_done_lands_in_completion_log(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    _stub_plan(monkeypatch, recurring=True)
    status, body = server.complete_task_row("rec-1")
    assert status == 200 and body["completed"]["recurring"] is True
    assert "rec-1" in completion_log.completed_ids_on(dt.date.today(), path=str(log))

def test_as_needed_done_lands_in_completion_log(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    monkeypatch.setattr(server.recurring_active, "set_recurring_active", lambda rid, active: active)
    _stub_plan(monkeypatch, as_needed=True)
    status, body = server.complete_task_row("an-1")
    assert status == 200 and body["completed"]["as_needed"] is True
    assert "an-1" in completion_log.completed_ids_on(dt.date.today(), path=str(log))

def test_recurring_undo_nets_out(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    _stub_plan(monkeypatch, recurring=True)
    server.complete_task_row("rec-1")
    server.uncomplete_task_row("rec-1")
    assert "rec-1" not in completion_log.completed_ids_on(dt.date.today(), path=str(log))
