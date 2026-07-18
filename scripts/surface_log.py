#!/usr/bin/env python3
"""Append-only surface history. Mirrors corrections_log pattern.

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


# --- staleness resolution (the LIVE source) ----------------------------------
# THE ONE resolver both the daily-plan neglect query (neglect.py) and the monthly
# status checker (status_check.py) read. Anytype's "Last surfaced" field is written
# only by an interactive CLI path June doesn't use (5 of 137 tasks live, none newer
# than 2026-06-18), so trusting it flags nearly everything as neglected. This
# append-only log is the current truth — every generated plan writes it via
# log_surfaced_batch. Extracted here (surface_log's natural home) so the two callers
# share one implementation instead of three divergent copies.


def surfaced_dates(path=None):
    """item_id -> most-recent surfaced datetime (naive), read from the append-only log.

    Naive datetimes (the log writes local isoformat). A malformed / partial line is
    skipped, never fatal — one unreadable line must not blind the whole staleness read.
    Missing file -> empty dict (first run, before anything has surfaced)."""
    p = path or cd_paths.data_file("surface_log.jsonl")
    out = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                tid, ts = rec.get("id"), rec.get("ts")
                if not tid or not ts:
                    continue
                try:
                    when = dt.datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    continue
                if when.tzinfo is not None:
                    when = when.replace(tzinfo=None)
                if tid not in out or when > out[tid]:
                    out[tid] = when
    except FileNotFoundError:
        pass
    return out


def effective_last_surfaced(items, surface_dates, anytype_ls=None):
    """The effective last-surfaced date + where it came from, for a group of one or more
    items (a single task, or a project's tasks). The surface log WINS; the Anytype field
    is used only when NO item of the group appears in the log. Returns
    (datetime|None, "log"|"anytype"|None). A None source means no surfacing data anywhere
    — that is ABSENCE, not an old date (callers distinguish the two)."""
    log_hits = [surface_dates[it["id"]] for it in items if it.get("id") in surface_dates]
    if log_hits:
        return max(log_hits), "log"
    if anytype_ls is not None:
        return anytype_ls, "anytype"
    return None, None
