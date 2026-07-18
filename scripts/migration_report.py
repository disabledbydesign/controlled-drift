#!/usr/bin/env python3
"""Render a migration log as a June-READABLE markdown review sheet.

WHY THIS EXISTS: the affective migration wrote its log as JSONL, and June could not read it.
Her words: "that json is impossible for me to read given my adhd. Can we convert it to an
organized md file or something else where i view it with a visual organization and can make
my notes?"

That is an access requirement, not a preference. JSONL is a machine format; a log she is
expected to REVIEW is a June-facing artifact and must be written for her.

The general rule, worth applying beyond this script: **if a human is the audience of an
artifact, it is written in a human format.** A reviewable record needs visual grouping, the
important thing first, one item per visual block, and somewhere to write.

Usage: python3 scripts/migration_report.py [log.jsonl] [out.md]
Defaults to the affective migration log, writing alongside it.
"""
import json
import os
import sys

DEFAULT_LOG = "data/affective_migration_2026-07-18.jsonl"
DEFAULT_OUT = "../docs/affective_migration_2026-07-18_review.md"


def load(path):
    """One record per object. Later records win, so a re-run's no-op does not mask the real move."""
    by_id = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            key = (r.get("id"), r.get("name"))
            # Keep the record that actually did something; a later "skipped" is just the
            # idempotency check re-running, not a correction.
            if key in by_id and by_id[key].get("action") == "moved":
                continue
            by_id[key] = r
    return list(by_id.values())


def block(r, n):
    """One reviewable item. Name first — that is what she scans by."""
    out = [f"### {n}. {r.get('name', '(unnamed)')}", ""]
    orig = (r.get("original_affective") or "").strip()
    if orig:
        out += ["> " + orig, ""]
    dest = r.get("destination")
    if r.get("action") == "moved":
        out.append(f"**Moved to `{dest}`** — {r.get('reason', '')}")
        if r.get("appended_to_existing"):
            out.append("")
            out.append("⚠️ The destination already had text, so this was **added to it**, not replacing it.")
    else:
        out.append(f"**Left alone** — {r.get('reason', '')}")
    out += ["", "- [ ] I've checked this", "- Notes:", "", "---", ""]
    return out


def render(records):
    moved_blocked = [r for r in records if r.get("action") == "moved" and r.get("destination") == "Blocked on"]
    moved_ctx = [r for r in records if r.get("action") == "moved" and r.get("destination") == "Context"]
    left = [r for r in records if r.get("action") != "moved"]

    L = [
        "# Affective field cleanup — 2026-07-18",
        "",
        "Agents had been writing status notes and findings into **Affective**, which is meant to hold",
        "only how you feel about a thing. This moved the misplaced text to where it belongs.",
        "",
        "**Nothing was deleted.** Every move was confirmed by re-reading the object before the original",
        "was cleared. If any of this is wrong, the original text is right here to put back.",
        "",
        "## What happened",
        "",
        f"- **{len(moved_blocked)}** moved to `Blocked on`",
        f"- **{len(moved_ctx)}** moved to `Context`",
        f"- **{len(left)}** left exactly as they were — these are real feelings, correctly filed",
        "",
        "## Check these first",
        "",
        "Three of the moves to `Context` are the debatable ones. They're about **not knowing** rather",
        "than about **feeling** — \"isn't sure what else exists\", \"doesn't have a clean home\". None of",
        "them used feeling-words, so they were treated as notes rather than affect. If you'd rather",
        "\"I'm not sure\" counted as a feeling, those are the ones to pull back.",
        "",
        "They're marked 🔸 below.",
        "",
        "---",
        "",
    ]

    if moved_blocked:
        L += ["## Moved to `Blocked on`", "", "*Something is actually waiting on someone else.*", "", ""]
        for i, r in enumerate(moved_blocked, 1):
            L += block(r, i)

    if moved_ctx:
        L += ["## Moved to `Context`", "", "*Findings, confirmations, notes — true things about the task, not feelings.*", "", ""]
        for i, r in enumerate(moved_ctx, 1):
            reason = (r.get("reason") or "").lower()
            mark = "🔸 " if ("sure" in reason or "home" in reason or "epistemic" in reason) else ""
            r = dict(r, name=mark + (r.get("name") or ""))
            L += block(r, i)

    if left:
        L += [
            "## Left alone — these were right",
            "",
            "*Real affect, correctly filed. Listed so you can see nothing was touched.*",
            "",
            "",
        ]
        for i, r in enumerate(left, 1):
            L += block(r, i)

    L += [
        "## If something here is wrong",
        "",
        "The machine-readable record is `scripts/data/affective_migration_2026-07-18.jsonl` — every",
        "entry has the original text verbatim, so anything can be put back exactly as it was.",
        "",
    ]
    return "\n".join(L) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    log = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, DEFAULT_LOG)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, DEFAULT_OUT)
    if not os.path.exists(log):
        raise SystemExit(f"migration_report: log not found: {log}")
    records = load(log)
    if not records:
        raise SystemExit(f"migration_report: no records in {log}")
    with open(out, "w") as f:
        f.write(render(records))
    print(f"[ok] {len(records)} items -> {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
