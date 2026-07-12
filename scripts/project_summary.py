#!/usr/bin/env python3
"""Per-project summary ('what it is' / 'next step') for the Today overlay's expandable
work-stream rows.

When June opens a work-stream row, she sees what the project is and its next step FIRST, and
can open it a further step to the individual tasks. The summary is parsed from each project's
plain-language Context (the same gsdo_context lines the map reads), reusing
orient_map._parse_context so there is ONE parser, not two.

NAMING: not called "focus" — that word belongs to the global Focus Period and June flagged the
collision. Internals say `summary`; her screen says "What it is" / "Next step".

HONESTY (divergence ledger H2, docs/divergence_ledger_2026-07-12.md): the Context parse is
fragile string-matching — it only yields anything when the Context is written as
`what it is — …` / `next step — …`, and silently yields nothing otherwise. This module does NOT
invent text to fill the gap. A project whose Context doesn't parse is simply OMITTED from the
map; the overlay then falls back to showing the task list directly. Empty is the honest answer.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import orient_map


def summary_map(projects):
    """projects: the project dicts from daily_plan.load_active_items (each with a 'context' free
    text field). Returns {name: {"what_it_is": str?, "next_step": str?}} including ONLY projects
    whose Context yields at least one of the two lines. A project with neither is left out."""
    out = {}
    for p in projects:
        name = p.get("name")
        if not name:
            continue
        what_it_is, _arc, next_step = orient_map._parse_context(p.get("context") or "")
        entry = {}
        if what_it_is:
            entry["what_it_is"] = what_it_is
        if next_step:
            entry["next_step"] = next_step
        if entry:
            out[name] = entry
    return out
