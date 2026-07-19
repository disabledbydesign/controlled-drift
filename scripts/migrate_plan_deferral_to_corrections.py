#!/usr/bin/env python3
"""Move the mis-filed "not today" deferral entries out of signal_log.jsonl.

WHY THIS EXISTS: `signal_log.jsonl` is supposed to hold only June's own typed words (Log Day
entries, check-in replies, focus-period authoring/corrections). `POST /api/task/not-today` used
to log every deferral there too, tagged `source="plan_deferral"` — a machine-written record with
no words of hers in it at all (`raw` was just the deferred task's name, written by the system).
June's correction, 2026-07-18: that does not belong in her own-words log. The write path now
goes to `corrections_log.jsonl` instead (kind `"not_today"`, see `server.py`'s `/api/task/not-today`
handler) — this script moves the entries that already landed in the old place before that fix.

DRY RUN BY DEFAULT. This only reports what it would move until called with `--apply`. Running it
against June's real data is her decision, not this script's — leave it unrun after building it.

The report is plain sentences for June to read, not JSON — a prior migration
(`scripts/migration_report.py`) shipped as JSONL and she could not read it. No metaphors.

IDEMPOTENT: a completed move empties signal_log.jsonl of `plan_deferral` entries, so a re-run
naturally finds nothing left to do. It also survives being interrupted mid-move — each moved
record's ORIGINAL timestamp is preserved in corrections_log.jsonl (`log_correction()` cannot do
this; it always stamps "now", so this script writes the JSONL line directly instead) precisely so
a re-run can recognize "this one's already there" by (object_id, ts) and skip re-appending it,
even if a previous run appended to corrections_log.jsonl but crashed before it could also clear
signal_log.jsonl. Appending to the destination always happens before removing from the source, so
a crash mid-move can at worst leave a record in both places (recoverable by re-running), never in
neither (data loss).

Usage:
    python3 scripts/migrate_plan_deferral_to_corrections.py            # dry run, prints the report
    python3 scripts/migrate_plan_deferral_to_corrections.py --apply    # actually moves the entries
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import signal_log
import corrections_log

# Both modules resolve their real file path through a private `_path()` helper (there is no
# public path-getter — each module only exposes read/append functions bound to its own default
# file). This script needs the raw path itself, to append a hand-built JSONL line with a
# preserved timestamp and to rewrite signal_log.jsonl with entries removed, so it calls the
# private helper directly rather than duplicate cd_paths' resolution logic.

SOURCE_KIND = "plan_deferral"          # the old signal_log source this script clears out
DEST_KIND = "not_today"                # the corrections_log kind the live handler now writes
DEST_SURFACE = "migrated_signal_log"   # marks these records as historical, not app-written


def _migrated_keys(corrections_path=None):
    """(object_id, original ts) pairs already present as migrated records — the idempotency check."""
    keys = set()
    for r in corrections_log.read_records(corrections_path):
        if r.get("kind") == DEST_KIND and r.get("surface") == DEST_SURFACE:
            keys.add((r.get("object_id"), r.get("ts")))
    return keys


def plan(signal_path=None, corrections_path=None):
    """What a migration would do right now. Read-only — makes no changes.

    Returns a dict: `to_move` (every plan_deferral record still in signal_log), `pending` (the
    subset not yet mirrored into corrections_log), `already_migrated` (the subset that IS already
    there — only non-empty after an interrupted prior run), and `kept` (every other signal_log
    record, untouched either way).
    """
    all_signals = signal_log.read_signals(signal_path)
    to_move = [r for r in all_signals if r.get("source") == SOURCE_KIND]
    kept = [r for r in all_signals if r.get("source") != SOURCE_KIND]
    migrated_keys = _migrated_keys(corrections_path)
    pending, already_migrated = [], []
    for r in to_move:
        (already_migrated if (r.get("reference"), r.get("ts")) in migrated_keys else pending).append(r)
    return {"to_move": to_move, "pending": pending, "already_migrated": already_migrated,
            "kept": kept, "total": len(all_signals)}


def _correction_record(signal_rec):
    """The corrections_log-shaped record for one migrated signal_log entry.

    Built directly (not through `corrections_log.log_correction`) because that function always
    stamps the current time and this needs to preserve the ORIGINAL deferral time. `before` holds
    the name the way every live `not_today` record does; `object_type` is left off rather than
    guessed — the old signal_log record never recorded whether the deferred item was a task or a
    project block, and 'unknown' is the honest value here, the same principle `corrections_log`
    already applies to `authored_by`.
    """
    reference = signal_rec.get("reference")
    if not reference:
        raise ValueError(f"plan_deferral record has no reference, cannot migrate: {signal_rec!r}")
    return {
        "ts": signal_rec["ts"],
        "kind": DEST_KIND,
        "before": {"name": signal_rec.get("raw") or ""},
        "after": None,
        "object_id": reference,
        "surface": DEST_SURFACE,
    }


def _append_line(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def _rewrite_signal_log(path, records):
    """Atomic replace so a crash mid-write never leaves a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    os.replace(tmp, path)


def render_dry_run(p):
    L = ["Not-today deferral cleanup — a dry run, nothing has been changed", ""]
    L += [
        "This checks scripts/data/signal_log.jsonl for deferral entries a machine wrote there when",
        "you tapped \"not today\" on a task. Those entries do not belong in that file — it is",
        "supposed to hold only what you typed yourself. This is a dry run: it only reports what it",
        "would move. Nothing moves until this script is run again with --apply.", "",
    ]
    to_move = p["to_move"]
    if not to_move:
        L.append("Found nothing to move. Every entry in signal_log.jsonl is left exactly as it is.")
        return "\n".join(L) + "\n"
    L.append(f"Found {len(to_move)} entries the system wrote, not you:")
    L.append("")
    for i, r in enumerate(to_move, 1):
        date = (r.get("ts") or "")[:10]
        name = r.get("raw") or "(no name recorded)"
        ref = r.get("reference") or "(no id recorded)"
        state = " — already copied to corrections.jsonl, only needs clearing from signal_log" \
            if r in p["already_migrated"] else ""
        L.append(f"{i}. {name}")
        L.append(f"   Deferred on {date}. Would move to corrections.jsonl, item id {ref}.{state}")
        L.append("")
    L.append(f"The other {len(p['kept'])} entries in signal_log.jsonl are your own words. They would")
    L.append("be left completely alone — this script never edits or removes anything you wrote.")
    L.append("")
    L.append("To actually move the entries above, run this script again with --apply.")
    return "\n".join(L) + "\n"


def render_apply_result(p, moved_count):
    L = ["Not-today deferral cleanup — done", ""]
    if not p["to_move"]:
        L.append("Nothing to move. signal_log.jsonl already had no machine-written deferral entries.")
        return "\n".join(L) + "\n"
    L.append(f"Moved {moved_count} entries from signal_log.jsonl to corrections.jsonl "
              f"({len(p['to_move']) - moved_count} were already there from an earlier run).")
    L.append(f"The other {len(p['kept'])} entries in signal_log.jsonl were left completely alone —")
    L.append("those are your own words and this script never touches them.")
    L.append("")
    L.append("Nothing was deleted outright: every moved entry is now in scripts/data/corrections.jsonl,")
    L.append("kind \"not_today\", with its original date kept.")
    return "\n".join(L) + "\n"


def migrate(dry_run=True, signal_path=None, corrections_path=None):
    """The one entry point. Returns the human-readable report string.

    dry_run=True (the default) makes no changes at all — not to signal_log.jsonl, not to
    corrections.jsonl. Only dry_run=False mutates, and only after computing exactly what needs to
    move (never re-appending an entry `_migrated_keys` already finds in corrections_log)."""
    p = plan(signal_path, corrections_path)
    if dry_run:
        return render_dry_run(p)
    if not p["to_move"]:
        return render_apply_result(p, 0)
    for r in p["pending"]:
        _append_line(corrections_log._path(corrections_path), _correction_record(r))
    if p["to_move"]:
        _rewrite_signal_log(signal_log._path(signal_path), p["kept"])
    return render_apply_result(p, len(p["pending"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Actually move the entries. Without this flag, only reports.")
    args = ap.parse_args()
    print(migrate(dry_run=not args.apply))


if __name__ == "__main__":
    main()
