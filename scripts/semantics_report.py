#!/usr/bin/env python3
"""Render the field semantics as a June-READABLE verification sheet.

WHY: June asked to verify the semantic content mapping for the data-structure fields —
"if I can see an overall schema of our data structure and semantics, I can verify it."
`field_semantics.py` is the machine-readable source; this is the human view of the same data.

Grouped by TYPE, because that is how she thinks about her objects, with a per-field block she
can scan and annotate. Anything with no documented meaning is called out rather than hidden,
and anywhere the documented meaning contradicts observed use is flagged — those are the two
places her judgment is actually needed.

Usage: python3 scripts/semantics_report.py [out.md]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import field_semantics as fs  # noqa: E402

DEFAULT_OUT = "../docs/field_semantics_review.md"

# The order she thinks in: the goal tree top-down, then the two non-hierarchical types.
TYPE_ORDER = ["Goal", "Project", "Task", "Recurring", "Strategy", "Focus Period"]


def fields_for(type_name):
    """Fields on this type, as RESOLVED entries.

    Resolved, not the raw FIELDS dict: June's overrides have to win in the sheet she checks, and
    the `does`/`examples` grains are merged in by `resolved()`. Reading FIELDS directly here once
    meant both silently rendered as absent.
    """
    out = []
    for name, e in fs.FIELDS.items():
        if type_name in (e.get("types") or []):
            out.append((name, fs.resolved(name)))
    return sorted(out, key=lambda kv: kv[0])


# Plain words for the three states a field can be in, so the sheet never reads as a defect list.
# A field waiting on design is a normal state for a system still being built.
STATUS_WORDS = {
    "live": "Working now",
    "planned": "Designed, not built yet",
    "undesigned": "Nothing uses it yet, and no design was found",
}


def does_block(d):
    """The 'what it does' section for one field. Empty when nothing was recorded — never guessed."""
    if not d:
        return []
    L = [f"**What it does — {STATUS_WORDS.get(d.get('status'), d.get('status'))}**", ""]
    if d.get("written_by"):
        L.append(f"- *What writes it:* {d['written_by']}")
    if d.get("read_by"):
        L.append(f"- *What reads it, and what changes:* {d['read_by']}")
    L.append("")
    return L


def block(name, e):
    L = [f"### {name}", ""]

    means = e.get("means")
    if means:
        L += [means, ""]

    not_this = e.get("not_this")
    if not_this:
        L += [f"**Not this:** {not_this}", ""]

    instead = e.get("instead") or {}
    if instead:
        L.append("**If it's actually…**")
        L.append("")
        for what, where in instead.items():
            L.append(f"- {what} → `{where}`")
        L.append("")

    L += does_block(e.get("does"))

    ex = e.get("examples") or []
    if ex:
        L.append(f"**Examples — {fs.EXAMPLES_BANNER}**")
        L.append("")
        for x in ex:
            L.append(f"- {x}")
        L.append("")

    usage = e.get("usage") or []
    if usage:
        L.append("**Rules that govern a write:**")
        L.append("")
        for u in usage:
            L.append(f"- {u}")
        L.append("")

    obs = e.get("observed")
    if obs:
        L += [f"⚠️ **Observed use differs:** {obs}", ""]

    src = e.get("source")
    if src:
        L += [f"<sub>from {src}</sub>", ""]

    L += ["- [ ] this is right", "- Change it to:", "", "---", ""]
    return L


def render():
    L = [
        "# What each field means — for checking",
        "",
        "This is what the system now tells an AI about how to fill in your fields. It was pulled",
        "out of your own specs and planning docs, not written fresh — each block says where it came",
        "from, so you can go read the full reasoning if a summary looks wrong.",
        "",
        "**What to do with this:** skim for anything that doesn't match how you actually use the",
        "field. Tick the ones that are right, write a correction under the ones that aren't. Two",
        "sections are worth your attention most — the flagged mismatches, and the fields with no",
        "documented meaning at all.",
        "",
        "There's no validator. Nothing here blocks a write. This is what the AI *reads* before",
        "writing, so getting it right is how the fields stay clean.",
        "",
        "---",
        "",
    ]

    # Lead with the two things that actually need her.
    mismatches = [(n, e) for n, e in sorted(fs.FIELDS.items()) if e.get("observed")]
    if mismatches:
        L += [
            "## ⚠️ Where the written meaning and your real use disagree",
            "",
            "These are the ones to look at first. Nothing was silently reconciled — both readings are",
            "recorded, and which one is right is your call.",
            "",
        ]
        for n, e in mismatches:
            L += [f"**{n}** — {e.get('observed')}", ""]
        L += ["---", ""]

    if getattr(fs, "UNDEFINED", None):
        L += [
            "## Fields with no documented meaning",
            "",
            "Nothing was invented for these. A made-up rationale sitting next to real ones would be",
            "worse than an obvious gap, because it would look just as authoritative.",
            "",
        ]
        und = fs.UNDEFINED
        items = und.items() if hasattr(und, "items") else [(u, "") for u in und]
        for n, why in sorted(items):
            L.append(f"- **{n}** — {why}" if why else f"- **{n}**")
            # No documented meaning and no runtime function are separate gaps. Several of these
            # do something quite specific; saying so is reporting the code, not inventing a reason.
            db = does_block(fs.does(n))
            if db:
                L += [""] + ["  " + x if x else x for x in db]
        L += ["", "---", ""]

    covered = set()
    for t in TYPE_ORDER:
        fl = fields_for(t)
        if not fl:
            L += [f"## {t}", "", "*No fields documented for this type yet.*", "", "---", ""]
            continue
        L += [f"## {t}", ""]
        for name, e in fl:
            covered.add(name)
            L += block(name, e)

    leftover = sorted(set(fs.FIELDS) - covered)
    if leftover:
        L += ["## Fields not attached to any type above", ""]
        for name in leftover:
            L += block(name, fs.resolved(name))

    return "\n".join(L) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, DEFAULT_OUT)
    with open(out, "w") as f:
        f.write(render())
    print(f"[ok] {len(fs.FIELDS)} fields -> {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
