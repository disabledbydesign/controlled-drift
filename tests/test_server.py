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
import daily_plan
import project_summary  # noqa: F401  (ensures the module imports cleanly in the server context)
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
    def fake_generate_plan(source="generate", capacity=None, extra=None):
        calls.append(("generate_plan", source, capacity, extra))
        return plan_store.save_plan({"woven_frame": "fresh", "blocks": [], "still_here": []}, source=source)
    def fake_reorder(message, kind):
        calls.append(("reorder", kind, message))
        return plan_store.save_plan({"woven_frame": "renegotiated", "blocks": [], "still_here": []}, source=kind)
    monkeypatch.setattr(plan_generate, "generate_plan", fake_generate_plan)
    monkeypatch.setattr(plan_generate, "reorder", fake_reorder)

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


def test_get_manifest(live_server):
    base, _ = live_server
    status, body = _get(base, "/manifest.webmanifest")
    assert status == 200
    manifest = json.loads(body)
    assert manifest["display"] == "standalone" and manifest["short_name"] == "Drift"


def test_get_schema_route(live_server, monkeypatch):
    base, _ = live_server
    monkeypatch.setattr(server.api_schema, "build_schema",
                        lambda: {"relations": {"side": {"label": "Side", "options": ["Work"]}},
                                 "controls": {"TASK": []}, "notes": {"TASK": []},
                                 "fields": {"TASK": {}}, "levelTypes": {"TASK": "Task"}})
    status, body = _get(base, "/api/schema")
    assert status == 200
    payload = json.loads(body)
    assert payload["relations"]["side"]["options"] == ["Work"]
    assert set(payload) >= {"relations", "controls", "notes", "fields"}


def test_get_schema_failure_is_a_visible_500_not_a_stub(live_server, monkeypatch):
    base, _ = live_server

    def boom():
        raise RuntimeError("anytype unreachable")
    monkeypatch.setattr(server.api_schema, "build_schema", boom)
    try:
        _get(base, "/api/schema")
        assert False, "expected 500"
    except urllib.error.HTTPError as e:
        assert e.code == 500 and "anytype unreachable" in e.read().decode()


# --- the new surface's bundle at /app/ --------------------------------------

@pytest.fixture
def app_dist(tmp_path, monkeypatch):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<!DOCTYPE html><div id=root></div>")
    (d / "assets" / "index-abc123.js").write_text("console.log('new surface')")
    (d / "assets" / "index-abc123.css").write_text(":root{--x:1}")
    (tmp_path / "secret.txt").write_text("June's health data")
    monkeypatch.setattr(server, "APP_DIST", str(d))
    return d


def test_app_root_serves_index(live_server, app_dist):
    base, _ = live_server
    status, body = _get(base, "/app/")
    assert status == 200 and "id=root" in body


def test_app_serves_hashed_assets_with_correct_mime(live_server, app_dist):
    base, _ = live_server
    with urllib.request.urlopen(base + "/app/assets/index-abc123.js", timeout=5) as r:
        assert r.status == 200
        assert r.headers["Content-Type"] == "text/javascript; charset=utf-8"
        assert "new surface" in r.read().decode()
    with urllib.request.urlopen(base + "/app/assets/index-abc123.css", timeout=5) as r:
        assert r.headers["Content-Type"] == "text/css; charset=utf-8"


def test_app_unknown_path_falls_back_to_index(live_server, app_dist):
    base, _ = live_server
    status, body = _get(base, "/app/review/some-id")
    assert status == 200 and "id=root" in body


def test_app_refuses_path_traversal(live_server, app_dist):
    base, _ = live_server
    # urllib normalizes ".." in the path, so the traversal is sent url-encoded.
    for path in ("/app/%2e%2e/secret.txt", "/app/..%2fsecret.txt", "/app/a/%2e%2e/%2e%2e/secret.txt"):
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                assert False, f"{path} was served ({r.read()[:40]!r}) instead of refused"
        except urllib.error.HTTPError as e:
            assert e.code == 403, f"{path} -> {e.code}, expected 403"


def test_old_overlay_still_served_at_root_alongside_the_app(live_server, app_dist):
    # Load-bearing: June uses the old overlay daily. The new surface comes up beside it.
    base, _ = live_server
    status, body = _get(base, "/")
    assert status == 200 and "<!DOCTYPE html>" in body and "id=root" not in body


def test_app_reports_a_missing_build_rather_than_a_route_miss(live_server, tmp_path, monkeypatch):
    base, _ = live_server
    monkeypatch.setattr(server, "APP_DIST", str(tmp_path / "nope"))
    try:
        _get(base, "/app/")
        assert False, "expected 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404 and "not built" in e.read().decode()


def test_get_settings_reports_backend_and_resolved_options(live_server):
    base, _ = live_server
    status, body = _get(base, "/api/settings")
    data = json.loads(body)
    assert status == 200
    ids = [o["id"] for o in data["options"]]
    assert data["backend"] in ids
    assert "mistral" in ids and "claude" in ids
    # each option reports the real mechanism + concrete model (not marketing copy)
    mistral = next(o for o in data["options"] if o["id"] == "mistral")
    assert mistral["model"] == "mistral-large-latest" and "Mistral API" in mistral["mechanism"]
    openrouter = next(o for o in data["options"] if o["id"] == "openrouter")
    assert openrouter["model"] == "anthropic/claude-sonnet-4"   # pinned, NOT "many models"


def test_post_settings_switches_backend_and_persists(live_server, monkeypatch, tmp_path):
    # monkeypatch records CD_BACKEND's pre-test value and restores it on teardown, even though
    # the handler mutates os.environ directly — so this test can't leak the backend choice.
    monkeypatch.setenv("CD_BACKEND", "mistral")
    base, _ = live_server
    status, data = _post(base, "/api/settings", {"backend": "claude"})
    assert status == 200 and data["backend"] == "claude"
    # the next GET reflects it (live, no restart)
    _, body = _get(base, "/api/settings")
    assert json.loads(body)["backend"] == "claude"
    # and it persisted to the sandboxed settings.json (atomic write target)
    saved = json.loads((tmp_path / "settings.json").read_text())
    assert saved["backend"] == "claude"


def test_post_settings_rejects_unknown_backend(live_server, monkeypatch):
    monkeypatch.setenv("CD_BACKEND", "mistral")
    base, _ = live_server
    status, data = _post(base, "/api/settings", {"backend": "gpt4"})
    assert status == 400 and "unknown backend" in data["error"]
    # a rejected switch must NOT change the live backend
    _, body = _get(base, "/api/settings")
    assert json.loads(body)["backend"] == "mistral"


def test_settings_health_absent_when_no_failures(live_server):
    # A clean week says nothing — the health section must not become a standing nag fixture.
    base, _ = live_server
    _, body = _get(base, "/api/settings")
    assert json.loads(body)["health"] == {}


def test_settings_health_surfaces_recent_capture_failures(live_server):
    # A logged capture failure (generation_failed) must reach June via /api/settings — giving
    # session_store.failures() the reader it never had. The 'prompt_large' size warning is a
    # capacity signal, not a failed action, so it must NOT inflate the count into a scare.
    base, _ = live_server
    session_store.log_failure("capture", "generation_failed", {"error": "connection reset"})
    session_store.log_failure("capture", "prompt_large", {"approx_tokens": 30000})
    _, body = _get(base, "/api/settings")
    health = json.loads(body)["health"]
    assert health["count"] == 1                      # prompt_large excluded
    assert "hit an error" in health["line"]
    assert "nothing you did" in health["line"]       # names that the trouble wasn't hers


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
    assert any(c[:2] == ("generate_plan", "refresh") for c in calls)
    _, plan = _get(base, "/api/plan")
    assert json.loads(plan)["woven_frame"] == "fresh"


def test_negotiate_preset_reorder_tags_kind(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate", {"preset_id": "quick-wins"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    reorder_calls = [c for c in calls if c[0] == "reorder"]
    assert reorder_calls and reorder_calls[0][1] == "preset:quick-wins"
    _, plan = _get(base, "/api/plan")
    assert json.loads(plan)["woven_frame"] == "renegotiated"


def test_negotiate_preset_generate_dispatches_to_generate_plan(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate", {"preset_id": "low-energy"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    # low-energy has operation=generate: must call generate_plan, NOT reorder
    gen_calls = [c for c in calls if c[0] == "generate_plan"]
    assert gen_calls, "expected generate_plan to be called for low-energy preset"
    assert gen_calls[0][2] == "low-energy"           # capacity_flag passed through
    # the preset's instructional payload text must reach the model too (bug fixed 2026-07-02:
    # only capacity_flag used to arrive, the richer payload text was silently dropped)
    assert "shorter sessions" in gen_calls[0][3]
    assert not any(c[0] == "reorder" for c in calls)
    # session log has request_type=generate
    _, txt = _get(base, "/api/session?stream=negotiate")
    entries = json.loads(txt)["entries"]
    assert any(e.get("request_type") == "generate" for e in entries)


def test_negotiate_freetext_reorder(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate", {"message": "only 30 minutes today"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    call = [c for c in calls if c[0] == "reorder"][0]
    assert call[1] == "freetext" and "30 minutes" in call[2]


def test_negotiate_freetext_generate_dispatches_to_generate_plan(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/negotiate",
                         {"message": "fresh start please", "operation": "generate"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    gen_calls = [c for c in calls if c[0] == "generate_plan"]
    assert gen_calls, "expected generate_plan for freetext operation=generate"
    # THE core bug (2026-07-02): June's freetext message used to never reach generate_plan at
    # all for the "generate" operation — it was logged to session history but the model building
    # the plan never saw it, so naming a task explicitly had zero effect on the output.
    assert gen_calls[0][3] == "fresh start please"
    assert not any(c[0] == "reorder" for c in calls)


def test_refresh_with_capacity_passes_through(live_server):
    base, calls = live_server
    status, body = _post(base, "/api/refresh", {"capacity": "low-energy"})
    assert status == 202 and body["state"] == "running"
    _wait_idle(base)
    gen_calls = [c for c in calls if c[0] == "generate_plan"]
    assert gen_calls and gen_calls[0][2] == "low-energy"


def test_status_idle_to_landed(live_server):
    base, calls = live_server
    _post(base, "/api/refresh", {})
    st = _wait_idle(base)
    assert st["state"] == "idle" and st["plan_generated_at"]   # a plan timestamp is present


def test_generation_error_surfaces_in_status(live_server, monkeypatch):
    base, calls = live_server
    def boom(source="generate", capacity=None):
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
    assert not any(c[0] in ("reorder", "generate_plan") for c in calls)


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


# --- /api/task/move + /api/project-summaries --------------------------------
# NOTE: _post returns (status, parsed_dict) — not a raw string — so these read the dict
# directly (matching the existing negotiate tests). _get returns a raw string body.

def _seed_clock_plan():
    plan_store.save_plan({
        "woven_frame": "wf",
        "blocks": [
            {"label": "Morning", "time": "09:00 – 12:00",
             "items": [{"time": "09:00 – 10:30", "project": "Alpha", "task": "draft", "id": "T1"}]},
            {"label": "Afternoon", "time": "13:00 – 17:00",
             "items": [{"time": "13:00 – 14:00", "project": "Gamma", "task": "call", "id": "T4"}]},
        ],
        "still_here": [],
    }, source="generate")


def test_move_relocates_and_reflows_in_cache(live_server):
    base, _calls = live_server
    _seed_clock_plan()
    status, data = _post(base, "/api/task/move", {"id": "T1", "target_block": 1, "position": 1})
    assert status == 200 and data["ok"] is True
    moved = next(i for i in data["plan"]["blocks"][1]["items"] if i.get("id") == "T1")
    assert moved["time"] == "14:00 – 15:30"   # re-flowed, never blanked
    # And it actually persisted to the cache (not just echoed).
    assert "T1" in [i.get("id") for i in plan_store.load_plan()["blocks"][1]["items"]]


def test_move_priority_shape_reorders(live_server):
    base, _ = live_server
    plan_store.save_plan({"shape": "priority",
                          "items": [{"task": "a", "id": "P1"}, {"task": "b", "id": "P2"}],
                          "still_here": []}, source="generate")
    status, data = _post(base, "/api/task/move", {"id": "P1", "position": 1})
    assert status == 200
    assert [i["id"] for i in data["plan"]["items"]] == ["P2", "P1"]


def test_move_bad_body_is_400(live_server):
    base, _ = live_server
    status, _b = _post(base, "/api/task/move", {"id": "", "target_block": 1})
    assert status == 400
    status2, _b2 = _post(base, "/api/task/move", {"id": "T1"})           # no destination at all
    assert status2 == 400
    status3, _b3 = _post(base, "/api/task/move", {"id": "T1", "target_block": "later"})
    assert status3 == 400
    # A JSON boolean must not sneak through as an int (bool is an int subclass in Python).
    status4, _b4 = _post(base, "/api/task/move", {"id": "T1", "target_block": True})
    assert status4 == 400
    status5, _b5 = _post(base, "/api/task/move", {"id": "T1", "position": True})
    assert status5 == 400


def test_move_unknown_id_is_404_and_not_later_is_400(live_server):
    base, _ = live_server
    _seed_clock_plan()
    status, _b = _post(base, "/api/task/move", {"id": "NOPE", "target_block": 1})
    assert status == 404
    status2, _b2 = _post(base, "/api/task/move", {"id": "T4", "target_block": 0})
    assert status2 == 400


def test_project_summaries_route(live_server, monkeypatch):
    base, _ = live_server
    # load_active_items returns (goals, projects, tasks, ...) — mock to a 3-tuple; the route
    # only reads element [1] (projects).
    monkeypatch.setattr(daily_plan, "load_active_items", lambda sid: (
        [],
        [{"name": "Alpha", "context": "what it is — the build\nnext step — ship it"},
         {"name": "Beta", "context": "no structured lines here"}],
        [],
    ))
    status, body = _get(base, "/api/project-summaries")
    data = json.loads(body)
    assert status == 200
    assert data["summaries"]["Alpha"] == {"what_it_is": "the build", "next_step": "ship it"}
    assert "Beta" not in data["summaries"]   # unparseable → omitted, never fabricated


# --- /api/task/not-today ("not today" deferral) -----------------------------

def _seed_task_and_block_plan():
    plan_store.save_plan({
        "woven_frame": "wf",
        "blocks": [{"label": "Afternoon", "time": "13:00 – 17:00", "items": [
            {"time": "13:00 – 13:30", "task": "a flat task", "id": "T1", "project": "Alpha"},
            {"time": "13:30 – 14:00", "task": "block step", "id": "B1",
             "project": "IOP", "project_id": "PROJ", "block_project": True},
        ]}],
        "still_here": [],
    }, source="generate")


def test_not_today_task_removes_row_and_logs(live_server):
    base, _ = live_server
    _seed_task_and_block_plan()
    import signal_log
    status, data = _post(base, "/api/task/not-today", {"id": "T1", "kind": "task"})
    assert status == 200 and data["ok"] is True
    ids = [i.get("id") for i in data["plan"]["blocks"][0]["items"]]
    assert "T1" not in ids and "B1" in ids                 # only the task row goes
    assert "T1" not in [i.get("id") for i in plan_store.load_plan()["blocks"][0]["items"]]
    # logged to BOTH the 8h window and the permanent learning store
    defs = session_store.recent_entries("deferral", hours=8, token_budget=10 ** 7)
    assert [(e["kind"], e["id"]) for e in defs] == [("task", "T1")]
    assert [(s["source"], s["reference"]) for s in signal_log.read_signals()] == [("plan_deferral", "T1")]


def test_not_today_block_removes_every_project_row(live_server):
    base, _ = live_server
    _seed_task_and_block_plan()
    status, data = _post(base, "/api/task/not-today", {"id": "PROJ", "kind": "block"})
    assert status == 200 and data["ok"] is True
    ids = [i.get("id") for i in data["plan"]["blocks"][0]["items"]]
    assert ids == ["T1"]                                    # the whole block (B1) dropped
    defs = session_store.recent_entries("deferral", hours=8, token_budget=10 ** 7)
    assert [(e["kind"], e["id"]) for e in defs] == [("block", "PROJ")]


def test_not_today_missing_id_is_400(live_server):
    base, _ = live_server
    _seed_task_and_block_plan()
    status, data = _post(base, "/api/task/not-today", {"kind": "task"})
    assert status == 400 and "error" in data


def test_not_today_unknown_id_is_404(live_server):
    base, _ = live_server
    _seed_task_and_block_plan()
    status, data = _post(base, "/api/task/not-today", {"id": "NOPE", "kind": "task"})
    assert status == 404 and "error" in data
