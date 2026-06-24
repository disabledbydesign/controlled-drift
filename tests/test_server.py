"""Integration tests for server.py — every route, with the LLM + Anytype mocked.

Starts the real ThreadingHTTPServer on an ephemeral port and hits it over HTTP, so the
routing, body parsing, and error handling are exercised end-to-end — without calling
`claude` or touching Anytype.
"""
import sys, os, json, threading, urllib.request, urllib.error
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from http.server import ThreadingHTTPServer
import server
import plan_store
import plan_generate
import capture_generate
import task_actions
import session_store
import orient_map


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    # Redirect cache via the deterministic env mechanism; mock the expensive/external bits.
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(orient_map, "render_map", lambda name: "GOAL: test map\n  stream")
    # generation: record calls, return a canned plan
    calls = []
    def fake_generate_plan(source="generate"):
        calls.append(("generate_plan", source))
        return plan_store.save_plan({"woven_frame": "fresh", "blocks": [], "still_here": []}, source=source)
    def fake_negotiate(message, kind):
        calls.append(("negotiate", kind, message))
        return plan_store.save_plan({"woven_frame": "renegotiated", "blocks": [], "still_here": []}, source=kind)
    monkeypatch.setattr(plan_generate, "generate_plan", fake_generate_plan)
    monkeypatch.setattr(plan_generate, "negotiate", fake_negotiate)

    # capture: record the call + write a real session entry (to the sandbox) so the receipt
    # route returns something — mirrors what the real capture() does.
    def fake_capture(text):
        calls.append(("capture", text))
        session_store.append_entry("capture", {
            "intent": "weed", "raw_input": text,
            "created": [{"id": "id-surgeon", "name": "Call surgeon", "type": "Task",
                         "project": "Build Controlled Drift"}],
            "result_summary": "added 1"})
        return {"created": [{"id": "id-surgeon", "name": "Call surgeon"}], "result_summary": "added 1"}
    def fake_archive(object_id):
        calls.append(("archive", object_id))
        return {"id": object_id, "archived": True}
    monkeypatch.setattr(capture_generate, "capture", fake_capture)
    monkeypatch.setattr(task_actions, "archive_object", fake_archive)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}", calls
    srv.shutdown()
    srv.server_close()


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, r.read().decode()


def _post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# --- GET routes -------------------------------------------------------------

def test_get_overlay_html(live_server):
    base, _ = live_server
    status, body = _get(base, "/")
    assert status == 200 and "<!DOCTYPE html>" in body


def test_get_plan_empty_first_run(live_server):
    base, _ = live_server
    status, body = _get(base, "/api/plan")
    assert status == 200 and json.loads(body).get("empty") is True


def test_get_actions(live_server):
    base, _ = live_server
    status, body = _get(base, "/api/actions")
    ids = [p["id"] for p in json.loads(body)["presets"]]
    assert "low-energy" in ids and "stuck" in ids


def test_get_map(live_server):
    base, _ = live_server
    status, body = _get(base, "/api/map")
    assert status == 200 and "test map" in body


def test_unknown_route_404(live_server):
    base, _ = live_server
    try:
        _get(base, "/api/nope")
        assert False, "expected 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404


# --- POST routes ------------------------------------------------------------

def _wait_idle(base, timeout=5.0):
    """Generation is async now — wait for the background thread to finish (status idle)."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, txt = _get(base, "/api/status")
        if json.loads(txt).get("state") == "idle":
            return json.loads(txt)
        time.sleep(0.03)
    raise AssertionError("generation did not reach idle in time")


def test_refresh_generates_and_caches(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/refresh", {})
    assert status == 202 and body["state"] == "running"   # async: returns at once, no blocking
    _wait_idle(base)                                       # background generation completes
    assert ("generate_plan", "refresh") in calls
    _, plan = _get(base, "/api/plan")
    assert json.loads(plan)["woven_frame"] == "fresh"


def test_negotiate_preset_looks_up_payload_and_tags_kind(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate", {"preset_id": "low-energy"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    kind = [c for c in calls if c[0] == "negotiate"][0][1]
    assert kind == "preset:low-energy"
    _, plan = _get(base, "/api/plan")
    assert json.loads(plan)["woven_frame"] == "renegotiated"


def test_negotiate_freetext(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate", {"message": "only 30 minutes today"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    call = [c for c in calls if c[0] == "negotiate"][0]
    assert call[1] == "freetext" and "30 minutes" in call[2]


def test_status_idle_to_landed(live_server):
    base, calls = live_server
    _post(base, "/api/refresh", {})
    st = _wait_idle(base)
    assert st["state"] == "idle" and st["plan_generated_at"]   # a plan timestamp is present


def test_generation_error_surfaces_in_status(live_server, monkeypatch):
    base, calls = live_server
    def boom(source="generate"):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(plan_generate, "generate_plan", boom)   # overrides the fixture's fake
    _post(base, "/api/refresh", {})
    import time
    deadline, st = time.time() + 5, {}
    while time.time() < deadline:
        _, txt = _get(base, "/api/status")
        st = json.loads(txt)
        if st.get("state") == "error":
            break
        time.sleep(0.03)
    assert st.get("state") == "error" and "kaboom" in st.get("error", "")


def test_negotiate_add_preset_does_not_generate(live_server):
    base, calls = live_server
    # "add" has no payload — it's UI-only; the server must not run a generation.
    status, body = _post(base, "/api/negotiate", {"preset_id": "add"})
    assert status == 200
    assert not any(c[0] == "negotiate" for c in calls)


def test_negotiate_unknown_preset_400(live_server):
    base, _ = live_server
    status, body = _post(base, "/api/negotiate", {"preset_id": "made-up"})
    assert status == 400 and "error" in body


def test_negotiate_empty_body_400(live_server):
    base, _ = live_server
    status, body = _post(base, "/api/negotiate", {})
    assert status == 400 and "error" in body


# --- capture / undo / session ----------------------------------------------

def test_capture_async_runs_and_lands_in_session(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/capture", {"text": "call my surgeon"})
    assert status == 202 and body["state"] == "running"   # async, like negotiate
    _wait_idle(base)
    assert ("capture", "call my surgeon") in calls
    # the receipt route shows what landed
    _, txt = _get(base, "/api/session?stream=capture")
    data = json.loads(txt)
    assert data["stream"] == "capture"
    assert data["entries"][-1]["created"][0]["name"] == "Call surgeon"


def test_capture_empty_text_400(live_server):
    base, _ = live_server
    status, body = _post(base, "/api/capture", {"text": "   "})
    assert status == 400 and "error" in body


def test_session_defaults_to_capture_stream(live_server):
    base, _ = live_server
    status, txt = _get(base, "/api/session")
    assert status == 200 and json.loads(txt)["stream"] == "capture"


def test_session_unknown_stream_400(live_server):
    base, _ = live_server
    try:
        _get(base, "/api/session?stream=bogus")
        assert False, "expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_capture_undo_archives_and_logs(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/capture/undo", {"id": "id-surgeon"})
    assert status == 200 and body["undone"]["archived"] is True
    assert ("archive", "id-surgeon") in calls
    # the undo is recorded in the capture stream (next turn's LLM sees it)
    _, txt = _get(base, "/api/session?stream=capture")
    entries = json.loads(txt)["entries"]
    assert any(e.get("intent") == "undo" and e.get("target_id") == "id-surgeon" for e in entries)


def test_capture_undo_empty_id_400(live_server):
    base, _ = live_server
    status, body = _post(base, "/api/capture/undo", {})
    assert status == 400 and "error" in body
