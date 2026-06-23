#!/usr/bin/env python3
"""Append-only log of June's plan corrections (§9 item 7). v1 logs only; no learning loop yet.

The path resolves through cd_paths at call time (default scripts/data/plan_corrections.jsonl),
so the test suite's sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def log_correction(kind, before, after, path=None):
    """kind: e.g. 'move_time' | 'reject' | 'reorder'. before/after: JSON-serializable or None."""
    path = path or cd_paths.data_file("plan_corrections.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {"ts": dt.datetime.now().isoformat(), "kind": kind, "before": before, "after": after}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
