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
  POST /api/refresh     regenerate a fresh plan, re-cache  [logs surfaced]
  POST /api/negotiate   {preset_id} or {message} -> renegotiate  [logs correction + surfaced]

Run:  python3 scripts/server.py   (then open http://localhost:5050)
"""
import sys, os, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
import plan_store
import plan_generate
import orient_map

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

        self._send(404, {"error": f"no route {self.path}"})

    # --- POST ---------------------------------------------------------------

    def do_POST(self):
        if self.path == "/api/refresh":
            self._generate(lambda: plan_generate.generate_plan(source="refresh"))
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
                    # e.g. "add" — a UI-only action; nothing to generate.
                    self._send(200, plan_store.load_plan() or {"empty": True})
                    return
                self._generate(lambda: plan_generate.negotiate(payload, kind=f"preset:{preset_id}"))
                return
            message = (body.get("message") or "").strip()
            if message:
                self._generate(lambda: plan_generate.negotiate(message, kind="freetext"))
                return
            self._send(400, {"error": "negotiate needs preset_id or message"})
            return

        self._send(404, {"error": f"no route {self.path}"})

    def _generate(self, fn):
        """Run a generation; surface failures honestly instead of a fake/empty plan."""
        try:
            plan = fn()
        except Exception as e:
            self._send(500, {"error": str(e)})
            return
        self._send(200, plan)

    # quieter logging — one line per request, no client noise
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[cd-server] {self.address_string()} {fmt % args}\n")


def main():
    plan_store.load_actions()  # seed the button schema on first run
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Controlled Drift overlay → http://{HOST}:{PORT}")
    print("  GET /api/plan · /api/map · /api/actions   POST /api/refresh · /api/negotiate")
    print("  Ctrl-C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        srv.server_close()


if __name__ == "__main__":
    main()
