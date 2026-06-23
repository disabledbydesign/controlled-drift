#!/usr/bin/env python3
"""Append-only surface history. Mirrors plan_corrections_log pattern.

When the daily plan surfaces an item (updates last_surfaced in Anytype), it also
appends here — because last_surfaced is a single overwriting field. Without this log,
surfacing history is gone the moment the next plan runs. The rhythm/neglect learning
loops (post-v1) need this history from day one to have anything to train on.

The path resolves through cd_paths at call time (default scripts/data/surface_log.jsonl),
so the test suite's sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def log_surfaced(item_id, item_name, item_type, plan_date=None, path=None):
    """Append one surfacing event. item_type: 'task' | 'project' | 'recurring' | etc."""
    path = path or cd_paths.data_file("surface_log.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts":        dt.datetime.now().isoformat(),
        "plan_date": (plan_date or dt.date.today()).isoformat(),
        "id":        item_id,
        "name":      item_name,
        "type":      item_type,
    }
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_surfaced_batch(items, plan_date=None, path=None):
    """items: list of {"id", "name", "type"}."""
    for it in items:
        log_surfaced(it["id"], it["name"], it.get("type", "unknown"),
                     plan_date=plan_date, path=path)
