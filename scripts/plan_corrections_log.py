#!/usr/bin/env python3
"""Append-only log of June's plan corrections (§9 item 7). v1 logs only; no learning loop yet."""
import os, json, datetime as dt

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "plan_corrections.jsonl")

def log_correction(kind, before, after, path=DEFAULT_PATH):
    """kind: e.g. 'move_time' | 'reject' | 'reorder'. before/after: JSON-serializable or None."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {"ts": dt.datetime.now().isoformat(), "kind": kind, "before": before, "after": after}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
