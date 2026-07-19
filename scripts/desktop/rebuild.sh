#!/bin/bash
# Rebuild the desktop app + icon after you drop your own art at scripts/desktop/icon_source.png
# (a 1024×1024 PNG). Regenerates the icon, then reassembles "Controlled Drift.app".
#   bash scripts/desktop/rebuild.sh
set -e
VENV="$HOME/Library/Application Support/Controlled Drift/venv/bin/python"
cd "$(cd "$(dirname "$0")/../.." && pwd)"
"$VENV" scripts/desktop/make_icon.py
"$VENV" scripts/build_desktop_app.py
echo "→ Double-click 'Controlled Drift.app' (or its Dock icon) to see the new icon."
