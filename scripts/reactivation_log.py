#!/usr/bin/env python3
"""Reactivation log — the learning SIGNAL for as-needed on/off changes.

When an as-needed task is turned on (asked for in Add/Focus, or June's tick-list) or off (completed),
the old->new toggle is appended here. COLLECT half only: no reader consumes it yet (mirrors
engagement_log — mine later per the deferred learning-loops subsystem). Record shape
{ts, date, recurring_id, name, old, new} with boolean old/new. Do NOT treat as a live feedback loop.

Path resolves through cd_paths at call time (default scripts/data/reactivation_log.jsonl), so the
test sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("reactivation_log.jsonl")


def log_change(recurring_id, name, old, new, path=None):
    """Append an old->new Active toggle. No-op when old == new (a re-tap landing on the same
    state is not a change — nothing to learn)."""
    if old == new:
        return
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "recurring_id": recurring_id, "name": name, "old": old, "new": new}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_changes(path=None):
    """Tolerant reader — a missing file is an empty history, not an error."""
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
