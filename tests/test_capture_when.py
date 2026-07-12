# tests/test_capture_when.py — capture anchors the when + exposes today on the session entry.
# Mocks the LLM, the network (create/read-back), AND the loggers, so nothing touches June's
# real Anytype space, session log, or generation log.
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def test_capture_writes_scheduled_and_marks_today(monkeypatch):
    from importlib import import_module
    cg = import_module("capture_generate")
    weed = '''```json
{"capacity_read":"","groups":[{"items":[
  {"type":"Task","name":"Email registrar","link":"","status":"Ready","action":"create","dedup_note":"","reasoning":"r","when":"today"},
  {"type":"Task","name":"Clean zotero","link":"","status":"Ready","action":"create","dedup_note":"","reasoning":"r","when":"someday"}]}]}
```'''
    monkeypatch.setattr(cg.plan_generate, "generate", lambda prompt: weed)
    monkeypatch.setattr(cg, "_load_weed_context", lambda: ("sid", [], [], [], [], []))  # real shape: 6-tuple
    created = {}
    monkeypatch.setattr(cg.gsdo_objects, "create",
                        lambda type_name, name, properties=None: created.__setitem__(name, properties) or "id-" + name)
    monkeypatch.setattr(cg, "_get_object", lambda oid: {"id": oid, "name": oid.replace("id-", ""), "properties": []})
    entries = []
    monkeypatch.setattr(cg.session_store, "append_entry", lambda kind, payload: entries.append(payload))
    monkeypatch.setattr(cg.generation_log, "log_generation", lambda *a, **k: None)
    result = cg.capture("email registrar today, someday clean zotero", today=dt.date(2026, 7, 13))
    assert created["Email registrar"]["Scheduled"] == "2026-07-13"
    assert created["Clean zotero"].get("Task status") == "Parked"
    assert result["has_today"] is True
    today_items = [c for e in entries for c in e.get("created", []) if c.get("is_today")]
    assert any(c.get("when_label") == "Today" for c in today_items)
