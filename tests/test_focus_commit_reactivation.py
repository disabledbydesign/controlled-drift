# tests/test_focus_commit_reactivation.py — /api/focus/commit's reactivate_tasks wiring (Task 6).
# HTTP-level: proves the route actually calls the resolver + primitive, not just that the pure
# functions work in isolation (the repo's build-frame guard — a wiring bug wouldn't show up in
# resolve_reactivate_names/set_recurring_active's own unit tests).
import sys, os, json, threading, urllib.request, urllib.error, datetime as dt
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from http.server import ThreadingHTTPServer
import server


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))

    fake_objects = [
        {"id": "rid-fridge", "name": "Clean the fridge", "type": {"key": "gsdo_recurring"},
         "properties": [{"key": "interval_unit", "select": {"name": "as_needed"}}]},
        # The period as it reads back AFTER a fully-successful write of _BASE_FIELDS. The routes
        # verify every written field on read-back, so a stub with no properties would (correctly)
        # look like a write that silently didn't land.
        {"id": "period-1", "name": "Focus period", "type": {"key": "focus_period"},
         "properties": [{"name": "Period start", "date": "2026-07-20T00:00:00Z"},
                        {"name": "Period end", "date": "2026-07-27T00:00:00Z"},
                        {"name": "Output format", "select": {"name": "Auto"}}]},
    ]
    monkeypatch.setattr(server.g, "fetch_all_objects", lambda sid: fake_objects)
    monkeypatch.setattr(server.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(server.focus_period_author, "author_focus_period",
                        lambda raw_text, name, props, source=None: "period-1")
    monkeypatch.setattr(server.focus_period_author, "update_focus_period",
                        lambda oid, raw_text, name, props, source=None: None)
    monkeypatch.setattr(server.focus_period, "parse_focus_period", lambda obj: {
        "id": "period-1", "start": dt.date(2026, 7, 20), "end": dt.date(2026, 7, 27)})
    monkeypatch.setattr(server.focus_store, "clear", lambda: None)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()
    srv.server_close()


def _post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


_BASE_FIELDS = {"start_date": "2026-07-20", "end_date": "2026-07-27", "foreground_projects": []}


def test_commit_activates_resolved_reactivate_tasks(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.setdefault("activated", []).append((rid, active)) or active)
    fields = dict(_BASE_FIELDS, reactivate_tasks=["Clean the fridge"])
    status, body = _post(live_server, "/api/focus/commit", {"fields": fields, "raw_text": "keep the fridge going"})
    assert status == 200 and body["ok"] is True
    assert calls["activated"] == [("rid-fridge", True)]
    assert "reactivate_unresolved" not in body
    assert "reactivate_failed" not in body


def test_commit_surfaces_unresolved_reactivate_name_without_blocking_the_period(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.setdefault("activated", []).append(rid))
    fields = dict(_BASE_FIELDS, reactivate_tasks=["Nonexistent task"])
    status, body = _post(live_server, "/api/focus/commit", {"fields": fields, "raw_text": "x"})
    assert status == 200 and body["ok"] is True          # the period itself still committed
    assert "activated" not in calls                       # nothing bogus got activated
    assert body["reactivate_unresolved"] == ["Nonexistent task"]


def test_commit_surfaces_activation_failure_without_failing_the_commit(live_server, monkeypatch):
    def boom(rid, active):
        raise RuntimeError("Active read-back mismatch")
    monkeypatch.setattr(server.recurring_active, "set_recurring_active", boom)
    fields = dict(_BASE_FIELDS, reactivate_tasks=["Clean the fridge"])
    status, body = _post(live_server, "/api/focus/commit", {"fields": fields, "raw_text": "x"})
    assert status == 200 and body["ok"] is True
    assert body["reactivate_failed"] == [{"id": "rid-fridge", "error": "Active read-back mismatch"}]


def test_commit_with_no_reactivate_tasks_is_unaffected(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.setdefault("activated", []).append(rid))
    status, body = _post(live_server, "/api/focus/commit", {"fields": _BASE_FIELDS, "raw_text": "x"})
    assert status == 200 and body["ok"] is True
    assert "activated" not in calls
    assert "reactivate_unresolved" not in body and "reactivate_failed" not in body


# --- /api/focus/update (confirm-an-edit) must honor reactivate_tasks too ----------------------
# reflect_back shows the same "Reopening" item on the edit path (it's the same deterministic
# template both routes call) — the route that confirms it must actually do it, not silently drop
# it (review finding: this was the ORIGINAL gap alongside the grounding-context Critical).

def test_update_activates_resolved_reactivate_tasks(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.setdefault("activated", []).append((rid, active)) or active)
    fields = dict(_BASE_FIELDS, reactivate_tasks=["Clean the fridge"])
    status, body = _post(live_server, "/api/focus/update",
                         {"fields": fields, "raw_text": "keep the fridge going", "id": "period-1"})
    assert status == 200 and body["ok"] is True
    assert calls["activated"] == [("rid-fridge", True)]


def test_update_surfaces_unresolved_reactivate_name_without_blocking_the_edit(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.setdefault("activated", []).append(rid))
    fields = dict(_BASE_FIELDS, reactivate_tasks=["Nonexistent task"])
    status, body = _post(live_server, "/api/focus/update",
                         {"fields": fields, "raw_text": "x", "id": "period-1"})
    assert status == 200 and body["ok"] is True
    assert "activated" not in calls
    assert body["reactivate_unresolved"] == ["Nonexistent task"]


# --- read-back must cover EVERY written field, not just start/end ---------------------------

def test_commit_rejects_a_partial_persist(live_server, monkeypatch):
    """Start and end landed, the intent did not. This used to return {"ok": true} — the route
    re-fetched and then only checked start/end, so every other field she authored was unverified.
    A write we cannot prove must never present as saved."""
    fields = dict(_BASE_FIELDS, intent="jobs first, everything else waits")
    status, body = _post(live_server, "/api/focus/commit",
                         {"fields": fields, "raw_text": "jobs first"})
    assert status == 500
    assert "did not persist" in body["error"] and "Intent" in body["error"]


def test_update_rejects_a_partial_persist(live_server, monkeypatch):
    """Same guard on the edit-confirm path."""
    fields = dict(_BASE_FIELDS, intent="jobs first, everything else waits")
    status, body = _post(live_server, "/api/focus/update",
                         {"fields": fields, "raw_text": "jobs first", "id": "period-1"})
    assert status == 500
    assert "did not persist" in body["error"] and "Intent" in body["error"]


def test_commit_accepts_a_fully_verified_write(live_server, monkeypatch):
    """The positive counterpart: when the intent DOES read back, the commit succeeds — the guard
    proves persistence, it doesn't just reject everything."""
    intent = "jobs first, everything else waits"
    obj = next(o for o in server.g.fetch_all_objects("sid") if o["id"] == "period-1")
    obj["properties"].append({"name": "Intent", "text": intent})
    try:
        status, body = _post(live_server, "/api/focus/commit",
                             {"fields": dict(_BASE_FIELDS, intent=intent), "raw_text": "x"})
        assert status == 200 and body["ok"] is True
    finally:
        obj["properties"] = [p for p in obj["properties"] if p.get("name") != "Intent"]
