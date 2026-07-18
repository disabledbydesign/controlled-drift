"""The write routes over real HTTP — the REAL ThreadingHTTPServer on an ephemeral port, with
Anytype replaced at the transport seam by `tests/fake_space.py`.

These are the routing/status-code half; `tests/test_api_write.py` covers the write semantics. The
point of testing them separately is that `server.py` is the layer contract §4 says currently
discards read-backs the helpers performed — so what the HTTP boundary actually returns is its own
claim, not something the helper tests establish.
"""
import sys, os, json, threading, urllib.request, urllib.error
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from http.server import ThreadingHTTPServer
import fake_space
import server
from test_api_write import _seed


@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    space = fake_space.install(fake_space.FakeSpace(_seed()), monkeypatch.setattr)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", space
    srv.shutdown()
    srv.server_close()


def _req(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# --- the five actions, over HTTP -------------------------------------------

def test_patch_renames_and_returns_the_refetched_object(live):
    base, _ = live
    st, b = _req(base, "PATCH", "/api/object/task-1", {"title": "Call the surgeon's office"})
    assert st == 200 and b["ok"] is True
    assert b["object"]["title"] == "Call the surgeon's office"


def test_patch_sets_a_field(live):
    base, _ = live
    st, b = _req(base, "PATCH", "/api/object/task-1", {"vals": {"status": "Done"}})
    assert st == 200 and b["object"]["vals"]["status"] == "Done"


def test_post_move_reparents(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object/task-1/move", {"parent_id": "proj-2"})
    assert st == 200 and b["ok"] is True and b["object"]["id"] == "task-1"


def test_post_creates(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object",
                 {"level": "TASK", "title": "Book the movers", "parent_id": "proj-1"})
    assert st == 200 and b["object"]["title"] == "Book the movers"
    assert b["object"]["id"].startswith("new-"), "the real id must come back to replace the temp id"


def test_delete_archives(live):
    base, _ = live
    st, b = _req(base, "DELETE", "/api/object/task-2")
    assert st == 200 and b == {"ok": True, "id": "task-2", "archived": True}


def test_recurring_active_route_now_also_returns_the_object(live):
    """Converged onto contract §4 by ADDING `object`; `active` stays for the old overlay."""
    base, _ = live
    st, b = _req(base, "POST", "/api/recurring/active", {"id": "rec-1", "active": False})
    assert st == 200 and b["active"] is False
    assert b["object"]["vals"]["paused"] is True


# --- status codes carry meaning --------------------------------------------

def test_duplicate_name_is_409_with_the_existing_id(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object", {"level": "TASK", "title": "Call the surgeon"})
    assert st == 409 and b["ok"] is False and b["existing_id"] == "task-1"


def test_a_guard_refusal_is_400(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object/task-1/move", {"parent_id": "goal-1"})
    assert st == 400 and b["ok"] is False and "cannot sit under" in b["error"]


def test_a_missing_object_is_404(live):
    base, _ = live
    st, b = _req(base, "PATCH", "/api/object/nope-1", {"title": "X"})
    assert st == 404 and b["ok"] is False


def test_a_write_that_does_not_persist_is_a_500_never_a_silent_ok(live):
    """Anytype answers 200 and stores nothing. The route must NOT report success."""
    base, space = live
    space.swallow_writes = True
    st, b = _req(base, "PATCH", "/api/object/task-1", {"vals": {"status": "Done"}})
    assert st == 500 and b["ok"] is False and "did not persist" in b["error"]


def test_patch_needs_a_title_or_vals(live):
    base, _ = live
    st, b = _req(base, "PATCH", "/api/object/task-1", {})
    assert st == 400


def test_patch_refuses_title_and_vals_together(live):
    base, _ = live
    st, b = _req(base, "PATCH", "/api/object/task-1", {"title": "X", "vals": {"status": "Done"}})
    assert st == 400


def test_unknown_object_suffix_is_404(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object/task-1/frobnicate", {})
    assert st == 404


# --- type conversion over HTTP (spec §5) ------------------------------------

def test_post_type_converts_a_task_to_a_recurring(live):
    """Was asserted as 404 while §5 was unbuilt, so the endpoint could not half-exist. It exists
    now: the response carries the RE-FETCHED object at its new level, with the same id."""
    base, _ = live
    st, b = _req(base, "POST", "/api/object/task-1/type", {"target": "Recurring"})
    assert st == 200 and b["ok"] is True
    assert b["object"]["id"] == "task-1", "the id must survive — every reference depends on it"
    assert b["object"]["type"] == "Recurring"
    assert b["object"]["level"] == "RECURRING"


def test_post_type_leaf_guard_is_400_and_names_the_children(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object/proj-1/type", {"target": "Task"})
    assert st == 400 and b["ok"] is False
    assert "Call the surgeon" in b["error"]


def test_post_type_rejects_an_unknown_target(live):
    base, _ = live
    st, b = _req(base, "POST", "/api/object/task-1/type", {"target": "Sandwich"})
    assert st == 400 and b["ok"] is False


def test_post_type_that_does_not_persist_is_a_500_never_a_silent_ok(live):
    base, space = live
    space.swallow_writes = True
    st, b = _req(base, "POST", "/api/object/task-1/type", {"target": "Recurring"})
    assert st == 500 and b["ok"] is False and "did not persist" in b["error"]
