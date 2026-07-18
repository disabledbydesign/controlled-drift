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


def test_resolve_ids_flags_a_recurring_task_so_completion_stays_cache_only():
    """A due-but-timeless Recurring chore folded into `tasks` (daily_plan.load_active_items,
    2026-07-17) carries is_recurring=True. Once resolved, the plan row must carry
    recurring=True too — plan_store.is_recurring_item reads that flag to route completion to
    the cache-only 'done for today' flip instead of a real Anytype Task-status write (Recurring
    objects have no Task status). A regular task must NOT get this flag."""
    ref_map = {"T1": "id-dishes", "T2": "id-aaa"}
    tasks = [{"id": "id-dishes", "name": "Do the dishes", "is_recurring": True},
             {"id": "id-aaa", "name": "Write the grant"}]
    plan = {"blocks": [{"items": [
        {"task": "Do the dishes", "ref": "T1"},
        {"task": "Write the grant", "ref": "T2"},
    ]}]}
    pg._resolve_ids(plan, ref_map, tasks)
    dishes, grant = plan["blocks"][0]["items"]
    assert dishes["id"] == "id-dishes" and dishes["recurring"] is True
    assert grant["id"] == "id-aaa" and "recurring" not in grant


# --- same task named twice -> one row, not two ------------------------------

def test_dedup_resolved_items_drops_second_occurrence_across_blocks():
    """Live 2026-07-15: 'Calling the insurance...' appeared twice in one plan — the model named
    the same real task in two different blocks. _resolve_ids has no cross-item check (each item
    resolves independently), so dedup must run as its own pass and keep only the first row."""
    ref_map = {"T1": "id-ins"}
    tasks = [{"id": "id-ins", "name": "Call insurance to check about outpatient maximum"}]
    plan = {"blocks": [
        {"items": [{"task": "Call insurance to check about outpatient maximum", "ref": "T1"}]},
        {"items": [{"task": "Call insurance to check about outpatient maximum", "ref": "T1"}]},
    ]}
    pg._resolve_ids(plan, ref_map, tasks)
    pg._dedup_resolved_items(plan)
    all_items = [it for b in plan["blocks"] for it in b["items"]]
    assert len(all_items) == 1
    assert all_items[0]["id"] == "id-ins"


def test_dedup_resolved_items_priority_shape():
    ref_map = {"T1": "id-a"}
    tasks = [{"id": "id-a", "name": "Draft the intro"}]
    plan = {"items": [
        {"task": "Draft the intro", "ref": "T1"},
        {"task": "Draft the intro", "ref": "T1"},
    ]}
    pg._resolve_ids(plan, ref_map, tasks)
    pg._dedup_resolved_items(plan)
    assert len(plan["items"]) == 1


def test_dedup_resolved_items_leaves_unresolved_items_alone():
    """Two items with no id (e.g. two separate 'Lunch' breaks) are NOT duplicates of each
    other — nothing to dedup against, both must survive."""
    plan = {"items": [{"task": "Lunch"}, {"task": "Lunch"}]}
    pg._dedup_resolved_items(plan)
    assert len(plan["items"]) == 2


# --- identity-field overwrite: the label must match the id it acts on -------

def test_resolve_ids_overwrites_mislabeled_task_from_id():
    """The live 2026-07-11 trust bug: the model wrote one task's words on a row whose ref
    resolves to a DIFFERENT task. June taps 'done' on the words she reads → the id completes
    a task she never saw. Once the id resolves, the displayed label MUST become the resolved
    task's real name, and the drift must be counted."""
    ref_map = {"T1": "id-real"}
    tasks = [{"id": "id-real",
              "name": "Open decision: aim to finish a manuscript",
              "linked_projects": ["Anthropic Fellows coding prep"]}]
    plan = {"blocks": [{"items": [
        {"task": "Check rivets / Leatherworking", "project": "Leatherworking", "ref": "T1"},
    ]}]}
    mislabels, resolved = pg._resolve_ids(plan, ref_map, tasks)
    item = plan["blocks"][0]["items"][0]
    assert resolved == 1
    assert item["id"] == "id-real"
    assert item["task"] == "Open decision: aim to finish a manuscript"   # id wins over free text
    assert item["project"] == "Anthropic Fellows coding prep"           # project stamped from id
    assert mislabels == 1                                                # the drift is measured


def test_resolve_ids_stamps_project_from_resolved_task():
    """When the resolved task carries a project, the item's project is overwritten to it —
    even if the model left project null or wrong."""
    ref_map = {"T1": "id-a"}
    tasks = [{"id": "id-a", "name": "Draft the intro", "linked_projects": ["The Book"]}]
    plan = {"items": [{"task": "Draft the intro", "project": None, "ref": "T1"}]}   # priority shape
    pg._resolve_ids(plan, ref_map, tasks)
    assert plan["items"][0]["project"] == "The Book"


def test_resolve_ids_leaves_null_ref_item_untouched():
    """A non-task item (Lunch — ref null, no name match) keeps its model text and gets no id;
    a legitimate label with no drift is not counted as a mislabel."""
    ref_map = {"T1": "id-a"}
    tasks = [{"id": "id-a", "name": "Email Donna"}]
    plan = {"blocks": [{"items": [
        {"task": "Lunch", "project": None, "ref": None},
        {"task": "email donna", "ref": None},        # exact (normalized) name match — not a mislabel
    ]}]}
    mislabels, resolved = pg._resolve_ids(plan, ref_map, tasks)
    lunch, donna = plan["blocks"][0]["items"]
    assert lunch["task"] == "Lunch" and "id" not in lunch          # untouched, uncompletable
    assert donna["id"] == "id-a" and donna["task"] == "Email Donna"  # canonicalized, no drift
    assert mislabels == 0


def test_resolve_ids_keeps_model_project_when_resolved_task_has_none():
    """If the resolved task carries no project, the model's project text is left alone (only a
    real project name overwrites)."""
    ref_map = {"T1": "id-a"}
    tasks = [{"id": "id-a", "name": "Call the plumber"}]           # no linked_projects
    plan = {"items": [{"task": "Call plumber", "project": "Household", "ref": "T1"}]}
    pg._resolve_ids(plan, ref_map, tasks)
    assert plan["items"][0]["task"] == "Call the plumber"
    assert plan["items"][0]["project"] == "Household"             # kept — nothing real to overwrite


def test_check_plan_logs_mislabel_count():
    """The mislabel count reaches the generation log's structural payload (only when provided)."""
    import generation_log
    plan = {"woven_frame": "f", "blocks": [{"items": [{"task": "x", "id": "i"}]}], "still_here": []}
    assert generation_log.check_plan(plan, n_input_tasks=1, mislabel_count=2)["mislabel_count"] == 2
    assert "mislabel_count" not in generation_log.check_plan(plan, n_input_tasks=1)


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


# --- appointments[] rides the same completion route as blocks/items (2026-07-17) ------
# daily_plan.format_appointments gives a real timed anchor its own top-level plan field so it
# survives regardless of shape. _iter_items must walk it too, or a checkoff would look like it
# worked (is_recurring_item finds the real id) but the cache flip in mark_item_done would never
# find the row — the item would un-check itself the instant the overlay re-rendered.

def _seed_plan_with_appointment(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    return plan_store.save_plan({
        "woven_frame": "f",
        "items": [{"project": "Build", "task": "do the thing", "id": "id-task"}],
        "appointments": [{"id": "id-therapy", "task": "Therapy", "time": "11:00",
                          "duration_min": 60, "recurring": True}],
        "still_here": [],
    }, source="morning")


def test_is_recurring_item_true_for_an_appointment(tmp_path, monkeypatch):
    _seed_plan_with_appointment(tmp_path, monkeypatch)
    assert plan_store.is_recurring_item("id-therapy") is True


def test_mark_item_done_flips_an_appointment(tmp_path, monkeypatch):
    _seed_plan_with_appointment(tmp_path, monkeypatch)
    plan_store.mark_item_done("id-therapy")
    appts = plan_store.load_plan()["appointments"]
    assert appts[0]["done"] is True
    # the flat items[] list is untouched
    assert "done" not in plan_store.load_plan()["items"][0]


def test_mark_item_undone_flips_an_appointment_back(tmp_path, monkeypatch):
    _seed_plan_with_appointment(tmp_path, monkeypatch)
    plan_store.mark_item_done("id-therapy")
    plan_store.mark_item_undone("id-therapy")
    assert plan_store.load_plan()["appointments"][0]["done"] is False


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


# --- the /api/recurring/active route (undo-a-reactivation + June's tick-list) ----

def test_recurring_active_route_calls_the_primitive(live_server, monkeypatch):
    calls = {}
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.update({"c": (rid, active)}) or active)
    status, body = _post(live_server, "/api/recurring/active", {"id": "rid-fridge", "active": False})
    assert status == 200
    assert body == {"ok": True, "active": False}
    assert calls["c"] == ("rid-fridge", False)


def test_recurring_active_route_needs_id_and_bool_active(live_server):
    status, body = _post(live_server, "/api/recurring/active", {"active": False})
    assert status == 400 and "id" in body["error"]
    status2, body2 = _post(live_server, "/api/recurring/active", {"id": "rid-fridge"})
    assert status2 == 400 and "active" in body2["error"]
    status3, body3 = _post(live_server, "/api/recurring/active", {"id": "rid-fridge", "active": "yes"})
    assert status3 == 400   # a string, not a real bool — JSON true/false only


def test_recurring_active_route_surfaces_primitive_failure(live_server, monkeypatch):
    def boom(rid, active):
        raise RuntimeError("Active read-back mismatch")
    monkeypatch.setattr(server.recurring_active, "set_recurring_active", boom)
    status, body = _post(live_server, "/api/recurring/active", {"id": "rid-fridge", "active": True})
    assert status == 500 and "mismatch" in body["error"]


# --- complete_stream: the checker's stream close + read-back ------------------

def test_complete_stream_writes_done_engagement_and_confirms(monkeypatch):
    updates = []
    monkeypatch.setattr(task_actions.gsdo_objects, "update",
                        lambda oid, properties=None: updates.append((oid, properties)))
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "Finish the daily-plan pipeline",
        "properties": [{"key": "engagement", "select": {"name": "Done"}}],
    })
    result = task_actions.complete_stream("id-stream")
    assert updates == [("id-stream", {"Engagement": "Done"})]
    assert result == {"id": "id-stream", "name": "Finish the daily-plan pipeline",
                      "engagement": "Done", "done": True}


def test_complete_stream_raises_if_engagement_did_not_persist(monkeypatch):
    monkeypatch.setattr(task_actions.gsdo_objects, "update", lambda oid, properties=None: None)
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "x", "properties": [{"key": "engagement", "select": {"name": "Steady"}}],
    })
    with pytest.raises(RuntimeError):
        task_actions.complete_stream("id-stream")
