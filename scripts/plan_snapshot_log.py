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


# --- planned-vs-actual join (the foundation rollover / neglect / learning read) ---------

def _date_str(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def _plan_task_items(plan):
    """Real task rows (those carrying an Anytype id) across BOTH plan shapes — a clock day's
    blocks[] and a fragmented day's flat items[]. Id-less rows (meal/break/appointment
    anchors) are not tasks and are skipped."""
    rows = []
    for b in plan.get("blocks", []):
        rows.extend(b.get("items", []))
    rows.extend(plan.get("items", []))
    return [it for it in rows if it.get("id")]


def undone_on(date, path=None):
    """Tasks that were on `date`'s plan and did NOT get completed that day — the join of the
    planned side (this log) and the actual side (completion_log). Uses the LATEST snapshot for
    the day (a renegotiation replaces the morning plan). Returns [{id, name, plan_date}]."""
    import completion_log
    ds = _date_str(date)
    snaps = [s for s in read_snapshots(path) if s.get("plan_date") == ds]
    if not snaps:
        return []
    done = completion_log.completed_ids_on(date)
    seen, undone = set(), []
    for it in _plan_task_items(snaps[-1].get("plan", {})):
        tid = it["id"]
        if tid in done or tid in seen:
            continue
        seen.add(tid)
        undone.append({"id": tid, "name": it.get("task") or it.get("name"), "plan_date": ds})
    return undone


def undone_yesterday(today=None, path=None):
    """Convenience: undone_on(yesterday). `today` is overridable for tests."""
    today = today or dt.date.today()
    return undone_on(today - dt.timedelta(days=1), path=path)
