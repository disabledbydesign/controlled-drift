#!/usr/bin/env python3
"""The local surface server — what the overlay talks to.

A tiny stdlib HTTP server (no dependencies) that joins the overlay HTML to the Python
backend. It does two cheap reads instantly (the cached plan, the live map) so the surface
appears the moment June opens it, and two slower writes (refresh, negotiate) that call the
LLM and re-cache — each routed through the learning logs so live negotiation data is kept.

Routes:
  GET  /                serve the overlay (docs/overlay_daily.html)
  GET  /api/plan        the cached daily plan (JSON) — instant, no LLM
  GET  /api/map         orient_map.render_map(...) verbatim (text) — deterministic, no LLM
  GET  /api/actions     the variable button schema (JSON)
  GET  /api/status      generation state {idle|running|error} + plan timestamp (for polling)
  POST /api/refresh     start a fresh generation (async, 202); poll /api/status  [logs surfaced]
  POST /api/negotiate   {preset_id}|{message} -> start a renegotiation (async, 202); poll status
  POST /api/complete    {id} -> mark a task done in Anytype (read-back) + flip the cache
  POST /api/uncomplete  {id} -> undo: status back to Ready (read-back) + un-flip the cache
  GET  /api/session     ?stream=capture|negotiate -> recent session log entries (the receipt)
  POST /api/capture     {text} -> weed input into typed/linked Anytype objects (async, 202)
  POST /api/capture/undo {id}  -> archive a just-captured object + log the undo (sync)

Run:  python3 scripts/server.py   (then open http://localhost:5050)
"""
import sys, os, json, threading
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
import plan_store
import plan_generate
import task_actions
import capture_generate
import session_store
import orient_map

# A generation (the LLM call) takes ~60-110s — far longer than a phone browser will hold a
# connection open, so it must NOT block the HTTP request (that's the "build my plan from bed"
# timeout: the phone gives up, the server finishes into a dead socket). Instead we kick the
# generation off in the background and the overlay polls GET /api/status. One at a time —
# the lock means a second tap while one is running is a no-op, not a double generation.
_gen_lock = threading.Lock()


def _start_generation(fn):
    """Run a generation `fn()` in a background thread, tracking status for the poller.
    Returns True if started, False if one is already in flight (don't stack generations)."""
    if not _gen_lock.acquire(blocking=False):
        return False
    plan_store.set_gen_status("running")

    def worker():
        try:
            fn()
            plan_store.set_gen_status("idle")
        except Exception as e:
            # Surface the failure to the poller honestly — never a silent dead end.
            plan_store.set_gen_status("error", error=str(e))
        finally:
            _gen_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return True

# Bind address. Default is loopback (Mac-only). Set CD_BIND=0.0.0.0 to also accept
# connections from June's phone on the same wifi (so she can use the overlay from bed).
# Security note: 0.0.0.0 exposes the surface to everyone on the local network (no auth) —
# fine on a trusted home network, her call. Loopback stays the safe default.
HOST = os.environ.get("CD_BIND", "127.0.0.1")
PORT = 5050
OVERLAY_HTML = os.path.join(os.path.dirname(__file__), "..", "docs", "overlay_daily.html")
PROJECT_NAME = "Build Controlled Drift"  # the map's root project


class Handler(BaseHTTPRequestHandler):
    # --- small response helpers ---------------------------------------------

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # --- GET ----------------------------------------------------------------

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            try:
                with open(OVERLAY_HTML, "rb") as f:
                    self._send(200, f.read(), ctype="text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, {"error": "overlay HTML not found"})
            return

        if self.path == "/api/plan":
            plan = plan_store.load_plan()
            # None is honest — first run / failed generation. The overlay shows an empty
            # state, never a fabricated plan.
            self._send(200, plan if plan is not None else {"empty": True})
            return

        if self.path == "/api/map":
            try:
                text = orient_map.render_map(PROJECT_NAME)
            except Exception as e:
                self._send(500, f"(map render failed: {e})", ctype="text/plain; charset=utf-8")
                return
            self._send(200, text, ctype="text/plain; charset=utf-8")
            return

        if self.path == "/api/actions":
            self._send(200, plan_store.load_actions())
            return

        if self.path == "/api/status":
            # The overlay polls this after kicking off a generation: are we still running,
            # did it land (idle + a newer plan timestamp), or did it fail?
            st = plan_store.get_gen_status()
            plan = plan_store.load_plan()
            st["plan_generated_at"] = plan.get("generated_at") if plan else None
            self._send(200, st)
            return

        if urlparse(self.path).path == "/api/session":
            # The Add tab's receipt: recent capture (or negotiate) turns, so June can SEE what
            # she's done this session without holding it — and undo from there.
            stream = (parse_qs(urlparse(self.path).query).get("stream", ["capture"])[0])
            if stream not in session_store.STREAMS:
                self._send(400, {"error": f"unknown stream {stream!r}"})
                return
            self._send(200, {"stream": stream, "entries": session_store.recent_entries(stream)})
            return

        self._send(404, {"error": f"no route {self.path}"})

    # --- POST ---------------------------------------------------------------

    def do_POST(self):
        if self.path == "/api/refresh":
            # Async: kick off the generation, return immediately; the overlay polls /api/status.
            started = _start_generation(lambda: plan_generate.generate_plan(source="refresh"))
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/negotiate":
            body = self._read_json_body()
            preset_id = body.get("preset_id")
            if preset_id:
                preset = plan_store.find_preset(preset_id)
                if not preset:
                    self._send(400, {"error": f"unknown preset {preset_id!r}"})
                    return
                payload = preset.get("payload")
                if not payload:
                    # e.g. "add" — a UI-only action; nothing to generate (synchronous).
                    self._send(200, plan_store.load_plan() or {"empty": True})
                    return
                started = _start_generation(
                    lambda: plan_generate.negotiate(payload, kind=f"preset:{preset_id}"))
                self._send(202, {"state": "running", "started": started})
                return
            message = (body.get("message") or "").strip()
            if message:
                started = _start_generation(
                    lambda: plan_generate.negotiate(message, kind="freetext"))
                self._send(202, {"state": "running", "started": started})
                return
            self._send(400, {"error": "negotiate needs preset_id or message"})
            return

        if self.path == "/api/complete":
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            if not task_id:
                self._send(400, {"error": "complete needs a task id"})
                return
            # Mark done in Anytype (with read-back), then flip the cache so the surface
            # shows it checked without a regeneration. A failed close surfaces honestly.
            try:
                confirmed = task_actions.complete_task(task_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            plan = plan_store.mark_item_done(task_id)
            self._send(200, {"completed": confirmed, "plan": plan or {"empty": True}})
            return

        if self.path == "/api/uncomplete":
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            if not task_id:
                self._send(400, {"error": "uncomplete needs a task id"})
                return
            # Undo a completion (mis-tap fix): status back to Ready in Anytype (read-back),
            # then un-check the cache. A failed undo surfaces honestly.
            try:
                confirmed = task_actions.uncomplete_task(task_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            plan = plan_store.mark_item_undone(task_id)
            self._send(200, {"uncompleted": confirmed, "plan": plan or {"empty": True}})
            return

        if self.path == "/api/capture":
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "capture needs text"})
                return
            # Async like /api/negotiate: a weed is an LLM call (~30s), too long to hold the
            # phone's connection. Kick it off; the Add tab polls /api/status, then reads
            # /api/session for the result. One generation at a time (the shared lock).
            started = _start_generation(lambda: capture_generate.capture(text))
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/capture/undo":
            body = self._read_json_body()
            object_id = (body.get("id") or "").strip()
            if not object_id:
                self._send(400, {"error": "undo needs an object id"})
                return
            # Sync — undo is cheap (no LLM): archive the just-captured object, log the undo so
            # the next turn's LLM sees it. A failed undo surfaces honestly.
            try:
                archived = task_actions.archive_object(object_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            session_store.mark_undo("capture", object_id, detail=f"removed {object_id}")
            self._send(200, {"undone": archived})
            return

        self._send(404, {"error": f"no route {self.path}"})

    # quieter logging — one line per request, no client noise
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[cd-server] {self.address_string()} {fmt % args}\n")


def main():
    plan_store.load_actions()  # seed the button schema on first run
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Controlled Drift overlay → http://{HOST}:{PORT}")
    print("  GET /api/plan · /api/map · /api/actions · /api/status · /api/session")
    print("  POST /api/refresh · /api/negotiate · /api/capture (async)")
    print("  POST /api/complete · /api/uncomplete · /api/capture/undo")
    print("  Ctrl-C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        srv.server_close()


if __name__ == "__main__":
    main()
