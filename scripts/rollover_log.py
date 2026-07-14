#!/usr/bin/env python3
"""Rollover observability — its OWN tag, per June's ask ("track it as its own category so if
something's going wrong we have data on HOW").

Rollover feeds the composer yesterday's uncompleted items and lets the MODEL decide which carry
into today. This records that decision on every generation: which carried (a task row for it is
in today's plan) vs which the model let go. Read this to judge how well the LLM handles carry-over
BEFORE adding manual always-roll / never-roll controls — the marks come once there's data to
justify them, not before.

Path resolves through cd_paths at call time so the test sandbox stays isolated.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths
import plan_snapshot_log


def _path(path=None):
    return path or cd_paths.data_file("rollover_log.jsonl")


def log_rollover(plan, path=None):
    """Classify yesterday's undone items into carried vs dropped against today's saved `plan`,
    and append one record. No-op (writes nothing) when there was nothing to carry."""
    undone = plan_snapshot_log.undone_yesterday()
    if not undone:
        return
    plan_ids = {it.get("id") for it in plan_snapshot_log._plan_task_items(plan)}
    carried = [{"id": u["id"], "name": u["name"]} for u in undone if u["id"] in plan_ids]
    dropped = [{"id": u["id"], "name": u["name"]} for u in undone if u["id"] not in plan_ids]
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "considered": len(undone), "carried": carried, "dropped": dropped}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_rollovers(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
