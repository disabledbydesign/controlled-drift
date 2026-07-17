#!/usr/bin/env python3
"""Engagement-change log — the learning SIGNAL for the tap-to-change engagement chip.

When June changes an AI-proposed engagement (the chip on the capture receipt), the old->new
change is appended here. This is the COLLECT half: no reader consumes it yet — the mining loop
is the deferred learning-loops subsystem (docs/superpowers/plans/2026-07-02-learning-loops-v1.md,
its engagement_watch was never built). Log rich now, mine later (June, 2026-07-16). Record shape
{ts, date, project_id, name, old, new} matches that spec so a future loop finds what it expected.
Do NOT treat this as a live feedback loop.

Path resolves through cd_paths at call time (default scripts/data/engagement_corrections_log.jsonl),
so the test sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("engagement_corrections_log.jsonl")


def log_change(project_id, name, old, new, path=None):
    """Append an old->new engagement change. No-op when old == new (a re-tap that lands on the
    same value is not a correction — nothing to learn from it)."""
    if old == new:
        return
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "project_id": project_id, "name": name, "old": old, "new": new}
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
