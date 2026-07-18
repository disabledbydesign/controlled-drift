#!/usr/bin/env python3
"""Render the Side rename log as a June-READABLE markdown review sheet.

Same reason migration_report.py exists: JSONL is a machine format, and a log a human is expected
to REVIEW is a human-facing artifact. Her words about the last one: "that json is impossible for
me to read given my adhd." That is an access requirement, not a preference — visual grouping, the
important thing first, one item per block, somewhere to write.

Usage: python3 scripts/side_rename_report.py [log.jsonl] [out.md]
"""
import json
import os
import sys

DEFAULT_LOG = "data/side_rename_2026-07-18.jsonl"
DEFAULT_OUT = "../docs/side_rename_2026-07-18_review.md"


def load(path):
    """One record per object. The append-only log accumulates a record per run, so prefer the run
    that actually did the write over a later re-run's `already-renamed` no-op."""
    by_id = {}
    rank = {"renamed": 3, "already-renamed": 2, "untouched": 1}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            prev = by_id.get(r["id"])
            if prev is None or rank.get(r.get("action"), 0) > rank.get(prev.get("action"), 0):
                by_id[r["id"]] = r
    return list(by_id.values())


def block(r, n):
    out = [f"### {n}. {r.get('name') or '(unnamed)'}", "", f"*{r.get('type') or 'object'}*", ""]
    if r.get("action") == "untouched":
        out.append(f"Still **{r.get('after')}** — not affected by the rename.")
    else:
        out.append(f"**{r.get('before')} → {r.get('after')}**")
        out.append("")
        out.append("Re-read from Anytype afterwards and confirmed: "
                   f"{'yes, it says Work' if r.get('read_back_ok') else '⚠️ **NO — CHECK THIS ONE**'}")
    out += ["", "- [ ] I've checked this", "- Notes:", "", "---", ""]
    return out


def render(records):
    renamed = [r for r in records if r.get("action") in ("renamed", "already-renamed")]
    untouched = [r for r in records if r.get("action") == "untouched"]
    bad = [r for r in renamed if not r.get("read_back_ok")]

    by_value = {}
    for r in untouched:
        by_value.setdefault(r.get("after"), []).append(r)

    L = [
        "# Side: \"Obligation\" is now called \"Work\" — 2026-07-18",
        "",
        "You asked to rename this one option. Everything that was marked **Obligation** now reads",
        "**Work**. Nothing else about those projects changed.",
        "",
        "## The short version",
        "",
        f"- **{len(renamed)}** things now say Work instead of Obligation",
        f"- **{len(untouched)}** things kept the label they already had",
        f"- **{len(bad)}** problems found",
        "",
        "## Why nothing could have been lost",
        "",
        "Anytype does not write the word \"Obligation\" onto each project. Each project points at a",
        "single shared label, and the label itself got a new name. So there was one change, not",
        "fifteen — and no project's setting was ever rewritten, cleared, or re-picked.",
        "",
        "Even so, every one of the affected projects was re-read from Anytype afterwards to confirm",
        "it really says Work now. Those confirmations are listed below.",
        "",
        "**The other three labels — Wellbeing, Fun / hobby, Daily life — were not touched at all.**",
        "",
        "---",
        "",
    ]

    if bad:
        L += ["## ⚠️ Check these first", "",
              "These did not read back the way they should have:", ""]
        for i, r in enumerate(bad, 1):
            L += block(r, i)

    L += ["## Now says \"Work\"", "",
          "*These were Obligation before.*", "", ""]
    for i, r in enumerate(sorted(renamed, key=lambda x: (x.get("name") or "").lower()), 1):
        L += block(r, i)

    L += ["## Unchanged", "",
          "*Listed so you can see for yourself that nothing else moved.*", "", ""]
    n = 1
    for value in sorted(by_value):
        L += [f"### Still \"{value}\" — {len(by_value[value])} things", ""]
        for r in sorted(by_value[value], key=lambda x: (x.get("name") or "").lower()):
            L.append(f"- {r.get('name')} *({r.get('type')})*")
            n += 1
        L += ["", "- [ ] I've checked this group", "- Notes:", "", "---", ""]

    L += [
        "## If something here is wrong",
        "",
        "The machine-readable record is `scripts/data/side_rename_2026-07-18.jsonl`. It has the old",
        "and new name for every item, so the rename can be undone by renaming the label back.",
        "",
        "One loose end worth knowing about: Anytype keeps a hidden internal id for each label, and",
        "that id still reads `obligation` underneath. Nothing you see uses it, and nothing in the",
        "system reads it — but if a future export ever shows the word \"obligation\", that is where it",
        "is coming from, and it is not a project that got missed.",
        "",
    ]
    return "\n".join(L) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    log = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, DEFAULT_LOG)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, DEFAULT_OUT)
    if not os.path.exists(log):
        raise SystemExit(f"side_rename_report: log not found: {log}")
    records = load(log)
    if not records:
        raise SystemExit(f"side_rename_report: no records in {log}")
    with open(out, "w") as f:
        f.write(render(records))
    print(f"[ok] {len(records)} items -> {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
