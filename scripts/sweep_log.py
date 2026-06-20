#!/usr/bin/env python3
"""Sweep feedback log (.gsdot-log.md) — read/write helpers.

IMPORTANT: write_log_entry() is for genuine signal only — something that would
help a future instance run sweeps better. Do NOT call it as a required step or
on a routine sweep with no surprises. Noise in this log makes it useless.
"""
import os, datetime
import sys; sys.path.insert(0, os.path.dirname(__file__))
from gsdt_bind import find_marker

LOG_FILENAME = ".gsdot-log.md"


def write_log_entry(folder, entry_text):
    """Append a dated entry to .gsdot-log.md.
    Call ONLY when there's genuine signal about what worked or went wrong.
    """
    marker_path = find_marker(folder)
    if not marker_path:
        raise FileNotFoundError(f"No .gsdot found from {os.path.abspath(folder)}")
    log_path = os.path.join(os.path.dirname(marker_path), LOG_FILENAME)
    today = datetime.date.today().isoformat()
    entry = f"\n---\n## {today}\n\n{entry_text.strip()}\n"
    with open(log_path, "a") as f:
        f.write(entry)


def read_log(folder):
    """Return full .gsdot-log.md text, or '' if absent or unbound."""
    marker_path = find_marker(folder)
    if not marker_path:
        return ""
    log_path = os.path.join(os.path.dirname(marker_path), LOG_FILENAME)
    try:
        with open(log_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""
