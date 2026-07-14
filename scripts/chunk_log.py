#!/usr/bin/env python3
"""Append-only DAILY chunk history — "I worked on this project today", not "done".

A block chunk is a fundamentally different meaning from a task's completion. A task's
`done` is complete-forever; a chunk is daily and RESETTING — checking it logs that June
put in time on a project today, and it returns tomorrow untouched. Conflating the two
would silently mark real projects finished, the exact failure the block design guards
against. So this is a clean, daily, resetting, append-only record keyed on `project_id`,
netting the last event per project per day — never a permanent state.

This mirrors `completion_log` exactly, with two differences: it is keyed on `project_id`
(not a task id) and it is DAILY — the per-day net keys on the calendar `date` the chunk
was logged for (today by default), not a plan_date.

The path resolves through cd_paths at call time (default scripts/data/chunk_log.jsonl),
so the test sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("chunk_log.jsonl")


def _normalize_date(date):
    """A calendar date as an ISO string. Accept a date object, an ISO string, or None
    (=today) — mirrors how completion_log normalizes its date argument."""
    if date is None:
        date = dt.date.today()
    return date.isoformat() if hasattr(date, "isoformat") else str(date)


def _append(rec, date, path):
    ds = _normalize_date(date)
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": ds, **rec}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_chunk(project_id, date=None, path=None):
    """Append one chunk event (event='chunked') — June worked on this project today."""
    _append({"event": "chunked", "project_id": project_id}, date, path)


def unlog_chunk(project_id, date=None, path=None):
    """Append an undo event (event='unchunked') — the mis-tap fix. Netted out by
    chunked_today_ids within the same day so a chunked-then-unchunked reads as absent
    (and unchunked-then-chunked back to present)."""
    _append({"event": "unchunked", "project_id": project_id}, date, path)


def read_events(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def chunked_today_ids(date=None, path=None):
    """The set of project_ids June chunked on `date` (default today). The last event per
    project_id on that day wins, so a chunked then unchunked on the same day nets to absent
    (and unchunked-then-chunked back to present)."""
    ds = _normalize_date(date)
    last = {}
    for rec in read_events(path):
        if rec.get("date") == ds and rec.get("project_id"):
            last[rec["project_id"]] = rec.get("event")
    return {pid for pid, ev in last.items() if ev == "chunked"}
