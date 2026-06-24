#!/usr/bin/env python3
"""Append-only log of every generation attempt — success or failure.

The raw material for future learning loops: which backends fail, on what inputs,
how long they take, and basic structural signals when they succeed. v1 logs only;
a future design session builds the loop that reads patterns from this.

Path resolves through cd_paths at call time (default scripts/data/generation_log.jsonl),
so the test suite's sandbox redirect keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def log_generation(backend, duration_s, success, source=None,
                   error_type=None, error_msg=None, structural=None, path=None):
    """Append one generation event.

    backend:    e.g. "openrouter/anthropic/claude-sonnet-4" or "claude"
    structural: dict of basic quality signals on success, from check_plan()
    """
    path = path or cd_paths.data_file("generation_log.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts":         dt.datetime.now().isoformat(),
        "backend":    backend,
        "source":     source,
        "duration_s": round(duration_s, 1),
        "success":    success,
    }
    if error_type:
        rec["error_type"] = error_type
    if error_msg:
        rec["error_msg"] = error_msg[:500]
    if structural:
        rec["structural"] = structural
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def check_plan(plan, n_input_tasks=None):
    """Basic structural facts about a parsed plan. Not a score — just what's there.

    n_input_tasks: how many tasks were in the input context.
    """
    woven_frame = (plan.get("woven_frame") or "").strip()
    blocks = plan.get("blocks", [])
    items = [item for b in blocks for item in b.get("items", [])]
    still_here = plan.get("still_here", [])
    refs_resolved = sum(1 for item in items if item.get("id"))

    result = {
        "woven_frame_len":    len(woven_frame),
        "block_count":        len(blocks),
        "item_count":         len(items),
        "still_here_count":   len(still_here),
        "task_refs_resolved": refs_resolved,
    }
    if n_input_tasks is not None:
        result["input_task_count"] = n_input_tasks
    return result


def check_capture(parsed, created, skipped, failed):
    """Deterministic structural facts about a weed turn — built in Python from the model's
    output every time, so the learning signal is captured automatically, never dependent on the
    LLM (or an instance) remembering to record it.

    The load-bearing field is `dedup_notes`: every place the model flagged a possible duplicate —
    on a skip OR a create-with-overlap. That's the model surfacing its OWN uncertainty, which is
    exactly where the dedup learning loop should look. This log is durable (append-only); the
    session log that also holds these notes is ephemeral (windowed), so the durable copy lives
    here on purpose.
    """
    groups = parsed.get("groups", []) if isinstance(parsed, dict) else []
    items = [it for g in groups for it in (g.get("items", []) or [])]
    dedup_notes = [
        {"name": it.get("name"), "action": it.get("action", "create"), "note": it.get("dedup_note")}
        for it in items if it.get("dedup_note")
    ]
    return {
        "n_groups":              len(groups),
        "n_items":               len(items),
        "n_created":             len(created),
        "n_skipped":             len(skipped),
        "n_failed":              len(failed),
        "capacity_read_present": bool(parsed.get("capacity_read")) if isinstance(parsed, dict) else False,
        "dedup_notes":           dedup_notes,
    }
