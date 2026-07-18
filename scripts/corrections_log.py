#!/usr/bin/env python3
"""Append-only log of June's CORRECTIONS — anything she changed that the system had proposed.

RENAMED 2026-07-18 (was `plan_corrections_log` / `plan_corrections.jsonl`). It began as a
plan-only log (§9 item 7) but `kind` always distinguished record types, and it now also carries
field-semantics revisions. The old name understated its scope, and the repo rule is to route new
signals through an EXISTING log rather than add a thirteenth — so the name widened instead.
Existing records were migrated; `kind` values are unchanged.

v1 logs only; the learning loop reads it but does not yet act on it.

The path resolves through cd_paths at call time (default scripts/data/corrections.jsonl), so the
test suite's sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def log_correction(kind, before, after, path=None):
    """kind: e.g. 'move_time' | 'reject' | 'reorder' | 'field_semantics'. before/after: JSON-serializable or None."""
    path = path or cd_paths.data_file("corrections.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {"ts": dt.datetime.now().isoformat(), "kind": kind, "before": before, "after": after}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
