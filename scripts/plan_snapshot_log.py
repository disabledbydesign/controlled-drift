#!/usr/bin/env python3
"""Durable per-generation plan snapshots — the planned side of planned-vs-actual.

Append-only; the full plan dict is stored verbatim so a future learning loop can diff
what was planned against what June logs she actually did (addendum §Job 2). `surface_log`
already records WHICH items surfaced per day; this adds the full ordered/framed plan.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("plan_snapshots.jsonl")


def log_plan_snapshot(plan, source, path=None):
    """Append {ts, plan_date, source, plan} — the full plan dict stored verbatim."""
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "plan_date": dt.date.today().isoformat(), "source": source, "plan": plan}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_snapshots(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
