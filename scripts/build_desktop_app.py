#!/usr/bin/env python3
"""Assemble `Controlled Drift.app` — a real macOS bundle, so double-clicking launches the app
with NO Terminal window and its own icon (a `.command` is a shell script and always opens
Terminal; a `.app` runs headless).

⚠️ Why the bundle is SELF-CONTAINED (launcher + icon copied inside it) and points at a venv in
~/Library, NOT at the repo: the repo lives under ~/Documents, which macOS privacy-protects
(TCC). A double-clicked .app has no access there, so it cannot read a venv or script inside
~/Documents — Python would crash at startup before the window appears. Everything the app
touches on launch therefore lives OUTSIDE ~/Documents: the venv in ~/Library/Application
Support, and the launcher + icon copied into the bundle. The window itself only talks to the
server over the network (localhost), so it never needs Documents at all.

It is a build artifact (gitignored) — re-run this after changing `desktop_app.py` or the icon.

Run:  "$HOME/Library/Application Support/Controlled Drift/venv/bin/python" scripts/build_desktop_app.py
"""
import os
import stat
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
APP = os.path.join(REPO, "Controlled Drift.app")
# The runtime venv lives OUTSIDE ~/Documents (see the module docstring for why).
APP_SUPPORT = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Controlled Drift")
VENV_PY = os.path.join(APP_SUPPORT, "venv", "bin", "python")
ENTRY = os.path.join(HERE, "desktop_app.py")
ICNS = os.path.join(HERE, "desktop", "appicon.icns")

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Controlled Drift</string>
  <key>CFBundleDisplayName</key><string>Controlled Drift</string>
  <key>CFBundleIdentifier</key><string>com.junebloch.controlleddrift</string>
  <key>CFBundleExecutable</key><string>controlled-drift</string>
  <key>CFBundleIconFile</key><string>appicon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
"""


def _launcher() -> str:
    # execs the ~/Library venv python on the launcher COPIED INSIDE the bundle — neither path is
    # under ~/Documents, so LaunchServices can read both. `$(dirname "$0")` is Contents/MacOS.
    return '''#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "%s" "$DIR/../Resources/desktop_app.py"
''' % VENV_PY


def main():
    if not os.path.exists(VENV_PY):
        raise SystemExit(
            f"venv python missing: {VENV_PY}\n"
            f"create it (outside ~/Documents — see the module docstring):\n"
            f'  /opt/homebrew/bin/python3 -m venv "{os.path.join(APP_SUPPORT, "venv")}"\n'
            f'  "{VENV_PY}" -m pip install pywebview pillow'
        )
    if not os.path.exists(ICNS):
        raise SystemExit(
            f"icon missing: {ICNS} — run scripts/desktop/make_icon.py first"
        )

    # rebuild clean so a rename/icon change never leaves stale files behind
    if os.path.exists(APP):
        shutil.rmtree(APP)
    macos = os.path.join(APP, "Contents", "MacOS")
    resources = os.path.join(APP, "Contents", "Resources")
    os.makedirs(macos)
    os.makedirs(resources)

    with open(os.path.join(APP, "Contents", "Info.plist"), "w") as f:
        f.write(INFO_PLIST)
    exe = os.path.join(macos, "controlled-drift")
    with open(exe, "w") as f:
        f.write(_launcher())
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    # Copy BOTH the launcher and the icon into the bundle — nothing the app reads at startup may
    # live under ~/Documents (TCC). `desktop_app.py` finds its icns next to itself (ICNS resolver).
    shutil.copyfile(ICNS, os.path.join(resources, "appicon.icns"))
    shutil.copyfile(ENTRY, os.path.join(resources, "desktop_app.py"))

    # nudge Finder/LaunchServices to pick up the new bundle + icon immediately
    subprocess.run(["touch", APP], check=False)
    print(f"[build] assembled {APP}")
    print("[build] double-click it (no Terminal), or drag it to the Dock / Applications.")


if __name__ == "__main__":
    main()
