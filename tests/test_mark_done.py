"""Tests for the mark-task-done path — id-threading, the close, the cache flip, the route.

Anytype + the LLM are always mocked: tests never call `claude`, never write June's real
space (the conftest sandbox + tripwire guarantee it).
"""
import sys, os, json, threading, urllib.request, urllib.error
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_generate as pg
import plan_store
import task_actions
import gsdo_objects
from http.server import ThreadingHTTPServer
import server


# --- id-threading: the token handshake -------------------------------------

def test_build_task_refs_assigns_tokens_and_table():
    tasks = [{"id": "id-aaa", "name": "Write the grant"},
             {"id": "id-bbb", "name": "Email Donna"}]
    ref_map, table = pg._build_task_refs(tasks)
    assert ref_map == {"T1": "id-aaa", "T2": "id-bbb"}
    assert "T1 — Write the grant" in table
    assert "T2 — Email Donna" in table


def test_resolve_ids_primary_token_path():
    """The model echoed the token -> map it back to the real Anytype id; drop the token."""
    ref_map = {"T1": "id-aaa", "T2": "id-bbb"}
    tasks = [{"id": "id-aaa", "name": "Write the grant"},
             {"id": "id-bbb", "name": "Email Donna"}]
    plan = {"blocks": [{"items": [
        {"task": "Write the grant — needs statement", "ref": "T1"},
    ]}]}
    pg._resolve_ids(plan, ref_map, tasks)
    item = plan["blocks"][0]["items"][0]
    assert item["id"] == "id-aaa"
    assert "ref" not in item          # token consumed; overlay only needs the id


def test_resolve_ids_name_fallback_when_no_token():
    """No/blank token, but the task text matches a real task name exactly -> use that id."""
    ref_map = {"T1": "id-aaa"}
    tasks = [{"id": "id-aaa", "name": "Email Donna"}]
    plan = {"blocks": [{"items": [{"task": "email donna", "ref": None}]}]}  # case-insensitive
    pg._resolve_ids(plan, ref_map, tasks)
    assert plan["blocks"][0]["items"][0]["id"] == "id-aaa"


def test_resolve_ids_no_match_leaves_item_without_id():
    """A non-task item (Lunch) or an unknown token must NOT get an id — better uncompletable
    than wrong. The cardinal sin is marking the wrong task done."""
    ref_map = {"T1": "id-aaa"}
    tasks = [{"id": "id-aaa", "name": "Email Donna"}]
    plan = {"blocks": [{"items": [
        {"task": "Lunch", "ref": None},          # not a task
        {"task": "Mystery", "ref": "T9"},        # unknown token, no name match
    ]}]}
    pg._resolve_ids(plan, ref_map, tasks)
    for item in plan["blocks"][0]["items"]:
        assert "id" not in item


# --- the cache flip ---------------------------------------------------------

def _seed_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    return plan_store.save_plan({
        "woven_frame": "f",
        "blocks": [{"label": "Morning", "items": [
            {"time": "9:00", "task": "Write the grant", "id": "id-aaa"},
            {"time": "10:30", "task": "Email Donna", "id": "id-bbb"},
            {"time": "12:00", "task": "Lunch"},          # no id
        ]}],
        "still_here": [],
    }, source="morning")


def test_mark_item_done_flips_only_the_matching_item(tmp_path, monkeypatch):
    seeded = _seed_plan(tmp_path, monkeypatch)
    before_ts = seeded["generated_at"]
    plan_store.mark_item_done("id-aaa")
    items = plan_store.load_plan()["blocks"][0]["items"]
    assert items[0].get("done") is True       # the matched item
    assert "done" not in items[1]             # untouched
    assert "done" not in items[2]             # the no-id item
    # A checkoff is not a regeneration — generated_at must be preserved.
    assert plan_store.load_plan()["generated_at"] == before_ts


def test_mark_item_done_none_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    assert plan_store.mark_item_done("whatever") is None


# --- complete_task: the Anytype close + read-back ---------------------------

def test_complete_task_writes_done_and_confirms(monkeypatch):
    updates = []
    monkeypatch.setattr(task_actions.gsdo_objects, "update",
                        lambda oid, properties=None: updates.append((oid, properties)))
    # Read-back returns the persisted Done status.
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "Write the grant",
        "properties": [{"key": "gsdo_task_status", "select": {"name": "Done"}}],
    })
    result = task_actions.complete_task("id-aaa")
    assert updates == [("id-aaa", {"Task status": "Done"})]   # canonical property, not built-in
    assert result == {"id": "id-aaa", "name": "Write the grant", "status": "Done", "done": True}


def test_complete_task_raises_if_status_did_not_persist(monkeypatch):
    """Read-back is the proof. If Anytype didn't actually take the write, fail loudly —
    never report a close that didn't happen."""
    monkeypatch.setattr(task_actions.gsdo_objects, "update", lambda oid, properties=None: None)
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "x", "properties": [{"key": "gsdo_task_status", "select": {"name": "Ready"}}],
    })
    with pytest.raises(RuntimeError):
        task_actions.complete_task("id-aaa")


# --- uncomplete_task: the mis-tap fix ---------------------------------------

def test_uncomplete_task_reverts_to_ready_and_confirms(monkeypatch):
    updates = []
    monkeypatch.setattr(task_actions.gsdo_objects, "update",
                        lambda oid, properties=None: updates.append((oid, properties)))
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "Write the grant",
        "properties": [{"key": "gsdo_task_status", "select": {"name": "Ready"}}],
    })
    result = task_actions.uncomplete_task("id-aaa")
    assert updates == [("id-aaa", {"Task status": "Ready"})]   # reverts to the active status
    assert result == {"id": "id-aaa", "name": "Write the grant", "status": "Ready", "done": False}


def test_uncomplete_task_raises_if_not_reverted(monkeypatch):
    monkeypatch.setattr(task_actions.gsdo_objects, "update", lambda oid, properties=None: None)
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "x", "properties": [{"key": "gsdo_task_status", "select": {"name": "Done"}}],
    })
    with pytest.raises(RuntimeError):
        task_actions.uncomplete_task("id-aaa")


def test_mark_item_undone_flips_back(tmp_path, monkeypatch):
    _seed_plan(tmp_path, monkeypatch)
    plan_store.mark_item_done("id-aaa")
    assert plan_store.load_plan()["blocks"][0]["items"][0]["done"] is True
    plan_store.mark_item_undone("id-aaa")
    assert plan_store.load_plan()["blocks"][0]["items"][0]["done"] is False   # un-checked


# --- the /api/complete route (end-to-end over HTTP) -------------------------

@pytest.fixture
def live_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    _seed_plan(tmp_path, monkeypatch)
    # Mock the Anytype close so the route test never touches the real space.
    monkeypatch.setattr(server.task_actions, "complete_task",
                        lambda task_id: {"id": task_id, "name": "Write the grant",
                                         "status": "Done", "done": True})
    monkeypatch.setattr(server.task_actions, "uncomplete_task",
                        lambda task_id: {"id": task_id, "name": "Write the grant",
                                         "status": "Ready", "done": False})
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


def test_complete_route_closes_task_and_flips_cache(live_server):
    status, body = _post(live_server, "/api/complete", {"id": "id-aaa"})
    assert status == 200
    assert body["completed"]["status"] == "Done"
    # the returned plan shows the item checked
    items = body["plan"]["blocks"][0]["items"]
    assert items[0]["done"] is True and "done" not in items[1]


def test_complete_route_needs_an_id(live_server):
    status, body = _post(live_server, "/api/complete", {})
    assert status == 400 and "id" in body["error"]


def test_uncomplete_route_reverts_and_unflips_cache(live_server):
    _post(live_server, "/api/complete", {"id": "id-aaa"})        # check it first
    status, body = _post(live_server, "/api/uncomplete", {"id": "id-aaa"})
    assert status == 200
    assert body["uncompleted"]["status"] == "Ready"
    items = body["plan"]["blocks"][0]["items"]
    assert not items[0].get("done")                              # un-checked again


def test_uncomplete_route_needs_an_id(live_server):
    status, body = _post(live_server, "/api/uncomplete", {})
    assert status == 400 and "id" in body["error"]
