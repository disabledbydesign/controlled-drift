#!/usr/bin/env python3
"""Append-only per-entry decision log for the daily memory pass — one line per candidate the
model actually judged, so every decision the pass makes (create / dedup-hit / leave-as-memory /
malformed) is auditable after the fact, not just implied by the state file's end result.

Mirrors generation_log.py's shape (append-only JSONL, path resolved through cd_paths at call
time so tests redirect cleanly) but at finer grain: that module logs one line per LLM call
across the whole batch; this logs one line per ENTRY-level decision within a call.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths

# created              — a new Anytype object was written and read-back proven
# skipped-dedup        — an object with this exact name+type already existed; reused its id
# skipped-not-anytype  — the model judged this entry correctly belongs in memory, left alone
# rejected-malformed   — the candidate's shape was unusable (no source_entry, no match, etc.)
# failed               — a create was attempted and raised (surfaced, not swallowed)
OUTCOMES = ("created", "skipped-dedup", "skipped-not-anytype", "rejected-malformed", "failed")


def log_decision(outcome, entry=None, candidate=None, anytype_id=None, error=None, path=None):
    """Append one decision record. `entry` is the parsed memory-file dict (may be None for a
    malformed candidate with no resolvable source); `candidate` is the model's raw JSON object
    for this entry (may be None for an entry that never reached the model, e.g. a crash)."""
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r} (expected one of {OUTCOMES})")
    path = path or cd_paths.data_file("memory_pass_log.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts": dt.datetime.now().isoformat(),
        "outcome": outcome,
        "source_project": (entry or {}).get("source_project") or (candidate or {}).get("source_project"),
        "source_file": (entry or {}).get("source_file"),
        "name": (entry or {}).get("name") or (candidate or {}).get("source_entry"),
        "content_hash": (entry or {}).get("content_hash"),
        "needs_clarifying": bool((candidate or {}).get("needs_clarifying")) or None,
        "anytype_id": anytype_id,
        "reasoning": (candidate or {}).get("reasoning"),
    }
    if error:
        rec["error"] = error
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
