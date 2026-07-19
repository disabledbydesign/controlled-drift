#!/usr/bin/env python3
"""The desktop window — Controlled Drift as a real native app, out of the browser.

A thin pywebview shell around the SAME local server the browser uses. It does three things
and deliberately nothing more:

  1. Ensures the server is up. If nothing answers on :5050 it starts `server.py` DETACHED
     (its own session) so the server's life is not tied to this window. Closing the app never
     stops the server — that is the point: the daily plan keeps regenerating whether the window
     is open or not. (June's stated requirement — server independent of the app.)

  2. Opens ONE native macOS window (real title bar + traffic-lights, draggable, no browser
     chrome) onto http://localhost:5050/?native=1. The `?native=1` is read synchronously by the
     frontend on first paint, so it forces the DESKTOP layout even at the narrow 392px tab width
     — the phone/desktop breakpoint (Surface.tsx, 900px) would otherwise flip a 392px window to
     the phone shell, which is exactly why the mockup's per-tab widths never survived the port.

  3. Exposes `window.pywebview.api.resize(w, h)` so the frontend can drive the window size PER
     TAB, the way v4's `deskApp()` animated its frame div (mockup line 733/776). Python owns only
     the easing: it animates from the current size to the target over ~300ms with a cubic ease,
     so switching tabs glides the whole window instead of snapping.

Run:  .venv-desktop/bin/python scripts/desktop_app.py
      (or double-click "Controlled Drift.command" at the repo root)

Self-test (drives the real window, no clicking needed — proves the animated OS-window resize):
      .venv-desktop/bin/python scripts/desktop_app.py --selftest
"""
import os
import sys
import time
import socket
import threading
import subprocess

import webview

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SERVER = os.path.join(HERE, "server.py")

PORT = int(os.environ.get("CD_PORT", "5050"))
URL = f"http://localhost:{PORT}/?native=1"

# The window opens at the Today tab's width; the frontend re-drives it on every tab change.
# Height is fixed and generous — the mockup fixed its body height too (v4 BODY_H); only width
# is per-tab. The window is resizable, so June can widen it and the per-tab width still applies.
START_W = 392
WIN_H = 860

ANIM_SECONDS = 0.30
ANIM_STEPS = 18


def _server_up() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def ensure_server() -> None:
    """Make sure something answers on :PORT. Never our job to STOP it — it outlives this window.

    Two launch contexts, because the repo sits under the privacy-protected ~/Documents:
      · From the repo / Terminal, `server.py` is readable next to us → start it detached.
      · From the .app bundle, ~/Documents is off-limits (TCC), so we cannot read server.py.
        There the server is expected to be up already via its launchd job; if it is not, we
        kick that job rather than reach into Documents, then fall back to just opening the window.
    """
    if _server_up():
        print(f"[desktop] server already up on :{PORT} — leaving it be")
        return
    if os.path.exists(SERVER):
        print(f"[desktop] no server on :{PORT} — starting one (detached, survives this window)")
        # start_new_session=True → own process group, so quitting the app never signals it.
        subprocess.Popen(
            [sys.executable, SERVER],
            cwd=REPO,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        # Bundle context: can't touch Documents. Ask launchd to (re)start the managed server.
        print(f"[desktop] no server on :{PORT} — asking launchd to start it")
        try:
            uid = os.getuid()
            subprocess.run(
                ["launchctl", "kickstart", f"gui/{uid}/com.june.controlled-drift.server"],
                check=False,
            )
        except Exception as exc:
            sys.stderr.write(f"[desktop] launchctl kickstart failed: {exc}\n")
    for _ in range(40):  # up to ~10s
        if _server_up():
            print("[desktop] server is up")
            return
        time.sleep(0.25)
    print("[desktop] WARNING: server did not come up in time — the window may show an error")


def _ease_in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


class Api:
    """The JS bridge. `window.pywebview.api.resize(w, h)` animates the native window."""

    def __init__(self) -> None:
        self.window = None
        self._cur = [START_W, WIN_H]
        self._gen = 0
        self._lock = threading.Lock()

    def resize(self, w, h):
        """Animate from the current size to (w, h). Rapid calls cancel the one in flight."""
        target = [int(w), int(h)]
        with self._lock:
            self._gen += 1
            gen = self._gen
            start = list(self._cur)
        if start == target:
            return True
        threading.Thread(
            target=self._animate, args=(start, target, gen), daemon=True
        ).start()
        return True

    def _animate(self, start, target, gen):
        for i in range(1, ANIM_STEPS + 1):
            with self._lock:
                if gen != self._gen:  # a newer resize superseded this one
                    return
            e = _ease_in_out_cubic(i / ANIM_STEPS)
            cw = round(start[0] + (target[0] - start[0]) * e)
            ch = round(start[1] + (target[1] - start[1]) * e)
            self._apply(cw, ch, gen)
            time.sleep(ANIM_SECONDS / ANIM_STEPS)
        self._apply(target[0], target[1], gen)

    def _apply(self, w, h, gen):
        try:
            if self.window is not None:
                self.window.resize(w, h)
        except Exception as exc:  # never let a resize hiccup kill the animation thread
            sys.stderr.write(f"[desktop] resize({w},{h}) failed: {exc}\n")
            return
        with self._lock:
            if gen == self._gen:
                self._cur = [w, h]


def _selftest(api: Api):
    """Drive the REAL feature end-to-end via the live DOM: confirm the app rendered the desktop
    shell, then CLICK each tab and read `window.innerWidth` back — proving tab-switch → resize.
    DOM introspection, not screenshots: `screencapture` returns black without Screen-Recording
    permission, so the window's own reported width is the honest signal.
    """
    w = api.window
    time.sleep(2.5)  # let the bundle load + mount

    def js(code):
        try:
            return w.evaluate_js(code)
        except Exception as exc:
            return f"ERR:{exc}"

    find_click = (
        "(function(t){var b=[].slice.call(document.querySelectorAll('button'))"
        ".find(function(x){return x.textContent.trim()===t;});if(b)b.click();return !!b;})"
    )
    print("[verify] search       :", js("location.search"))
    print("[verify] title        :", js("document.title"))
    print("[verify] #buttons      :", js("document.querySelectorAll('button').length"))
    print("[verify] body text len :", js("document.body.innerText.length"))
    print("[verify] innerW @load  :", js("window.innerWidth"))
    print("[verify] desktop tabs  :", js(
        "JSON.stringify([].slice.call(document.querySelectorAll('button'))"
        ".map(function(b){return b.textContent.trim();})"
        ".filter(function(t){return ['Today','Add/Log','Map','Routines','Strategies'].indexOf(t)>=0;}))"
    ))
    for tab in ("Map", "Routines", "Today"):
        clicked = js(f"({find_click})('{tab}')")
        time.sleep(1.1)  # animation (0.3s) + settle
        print(f"[verify] click {tab:<9}: found={clicked}  innerW now {js('window.innerWidth')}  (api {api._cur})")
    if w is not None:
        w.destroy()


# Found next to this file when bundled into the .app (Resources/appicon.icns), or under
# desktop/ when running from the repo. First existing wins.
ICNS = next(
    (p for p in (os.path.join(HERE, "appicon.icns"),
                 os.path.join(HERE, "desktop", "appicon.icns")) if os.path.exists(p)),
    os.path.join(HERE, "appicon.icns"),
)


def _set_dock_icon():
    """Point the RUNNING process's dock icon at our icns. Required because the bundle execs an
    external python, so the live process registers as `org.python.python` — without this the Dock
    would show the python rocket, not our icon.

    ⚠️ Load the icns EAGERLY. `initWithContentsOfFile_` reads every representation up front;
    `initByReferencingFile_` is LAZY and can leave the Dock holding a single low-res rep, so the
    icon's edge visibly softens when the launch bounce re-renders it (the 'edge drops on the first
    hop' bug). We also stamp the logical size to 1024 so the Dock scales from the sharpest rep.
    Best-effort — never block launch on it."""
    try:
        from AppKit import NSApplication, NSImage  # pyobjc, a pywebview dependency
        from Foundation import NSMakeSize

        if os.path.exists(ICNS):
            img = NSImage.alloc().initWithContentsOfFile_(ICNS)
            if img is not None:
                img.setSize_(NSMakeSize(1024, 1024))
                NSApplication.sharedApplication().setApplicationIconImage_(img)
    except Exception as exc:
        sys.stderr.write(f"[desktop] could not set dock icon: {exc}\n")


def main():
    selftest = "--selftest" in sys.argv
    ensure_server()
    api = Api()
    window = webview.create_window(
        "Controlled Drift",
        URL,
        js_api=api,
        width=START_W,
        height=WIN_H,
        min_size=(360, 480),
        resizable=True,
        frameless=False,  # real native title bar — draggable, has the close button
    )
    api.window = window
    # The process runs as org.python.python, so set our icon once the window (and NSApplication)
    # exists — else the Dock shows the python rocket. Loaded eagerly to keep the edge crisp.
    window.events.shown += _set_dock_icon
    if selftest:
        threading.Thread(target=_selftest, args=(api,), daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
