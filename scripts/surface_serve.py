#!/usr/bin/env python3
"""Serve June's review-and-reorganize surface locally, so the in-page
"↻ Rebuild from Anytype" button works.

A plain file:// page is sandboxed — it can't run a script or reach Anytype — so the
Rebuild button needs a same-origin endpoint. This tiny stdlib server provides one:
  GET  /            -> serves docs/controlled_drift_tree.html (read fresh each time)
  POST /rebuild     -> regenerates that file from live Anytype (review_surface.build), then
                       the page reloads and shows current data.

Local only: binds to 127.0.0.1. No dependencies beyond the standard library.

Usage:  python3 scripts/surface_serve.py [PORT]     (default 8765)
        opens http://127.0.0.1:8765/ in your browser.
"""
import sys, os, webbrowser, threading, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review_surface

PAGE = review_surface.DEFAULT_OUT
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if not os.path.exists(PAGE):
                review_surface.build(PAGE)
            with open(PAGE, "rb") as f:
                self._send(200, f.read())
        elif self.path == "/favicon.ico":
            self._send(204, b"")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path == "/rebuild":
            try:
                review_surface.build(PAGE)
                self._send(200, json.dumps({"ok": True}), "application/json")
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "error": str(e)}), "application/json")
        else:
            self._send(404, "not found")

    def log_message(self, fmt, *args):
        # quieter: only log rebuilds
        if "POST" in (args[0] if args else ""):
            sys.stderr.write("[surface] %s\n" % (fmt % args))


def main():
    # ensure a page exists before first load
    if not os.path.exists(PAGE):
        print("Building initial surface…")
        review_surface.build(PAGE)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://127.0.0.1:%d/" % PORT
    print("Serving the review surface at %s" % url)
    print("  • the '↻ Rebuild from Anytype' button now works (pulls fresh live data)")
    print("  • Ctrl-C to stop")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
