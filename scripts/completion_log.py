#!/usr/bin/env python3
"""Append-only completion history — the ACTUAL side of planned-vs-actual.

`plan_snapshot_log` records what was PLANNED each day; this records what June actually
finished. Together they answer "what was on the plan and didn't get done" — the record
that rollover, the neglect-repurpose, and completion-based learning all need, and which
did not exist before (Anytype keeps only a task's CURRENT status, not when/whether it was
completed on a given day).

Written at the one completion choke point (`task_actions.complete_task`), and only AFTER
that write is read-back-proved — so a logged completion always reflects a real one.

The path resolves through cd_paths at call time (default scripts/data/completion_log.jsonl),
so the test sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("completion_log.jsonl")


def _append(rec, plan_date, path):
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "plan_date": (plan_date or dt.date.today()).isoformat(), **rec}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_completion(task_id, name, plan_date=None, path=None):
    """Append one completion event (event='done')."""
    _append({"event": "done", "id": task_id, "name": name}, plan_date, path)


def log_uncompletion(task_id, plan_date=None, path=None):
    """Append an undo event (event='undone') — the mis-tap fix. Netted out by completed_ids_on
    within the same plan_date so a done-then-undone reads as not-done."""
    _append({"event": "undone", "id": task_id}, plan_date, path)


def read_events(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def completed_ids_on(date, path=None):
    """The set of task ids June completed on `date`. The last event per id wins, so a done
    then undone on the same day nets to not-done (and undone-then-done back to done)."""
    ds = date.isoformat() if hasattr(date, "isoformat") else str(date)
    last = {}
    for rec in read_events(path):
        if rec.get("plan_date") == ds and rec.get("id"):
            last[rec["id"]] = rec.get("event")
    return {tid for tid, ev in last.items() if ev == "done"}
