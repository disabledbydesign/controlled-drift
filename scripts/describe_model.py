#!/usr/bin/env python3
"""How Controlled Drift's data model works — the LIVE schema, read straight from
Anytype so it never drifts from what's actually there.

Controlled Drift stores everything as objects in one Anytype space. The shape:

  Goal ──< Project ──< Task            (a Goal holds Projects; a Project holds Tasks)
            │
            └─ Parent project ──< Project   (Projects nest: a "work stream" is a
                                             Project under a parent Project)

  Recurring   — repeating items (dishes, meds) resolved per day
  Strategy    — a standing behavioral discipline ("when low energy, do X")

A "work stream" / dev thread is just a Project nested under a parent Project.
`whats_open.py` renders those; this script describes the field shape of each type.

FOR AGENTS working ON Controlled Drift: call this to learn the data structure
before touching it, instead of re-deriving it from source. Field values printed
below are read live. Design depth (why each field exists, the guards): AI_LAYER_SPEC.md §2.

WHAT EACH FIELD MEANS is printed inline below, one line per field, from
`scripts/field_semantics.py` (with June's own revisions applied). Read it before
writing: the free-text fields are easy to mis-route, and a status note written into
`Affective` is wrong data, not a small mistake. Run
`python3 scripts/field_semantics.py` for the full rationale + spec citation per field,
including the fields that have NO documented meaning and so should not be guessed at.

Usage: python3 <REPO>/scripts/describe_model.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import field_semantics

# The five CORE types, by the key/name find_type resolves. Task's type key is "task".
# These are described first and in this order, because they are the model June reasons about.
CORE_TYPES = ["Goal", "Project", "task", "Recurring", "Strategy"]

# ⚠ EVERY OTHER LIVE TYPE IS ALSO DESCRIBED, below the core five.
#
# This file used to show ONLY the five, which made it a filtered view that read like a complete
# one — and that cost three separate errors in a single session (2026-07-18): twice it was used
# as evidence that Focus Period "is not an Anytype type" (it is, with 7 live objects and 12
# fields), and once an agent built a whole field-semantics layer covering 41 fields while never
# seeing Focus Period's, because it worked from this output.
#
# The repo CLAUDE.md tells agents to orient from this command. A tool that silently omits live
# types is worse than one that errors: absence reads as evidence. So types are now DISCOVERED,
# not listed, and anything outside the core five is shown under a heading saying what it is.

# Anytype's built-in/system fields — attached to objects automatically, not part of
# the GSDO model. Hidden as inert so the description shows the actual model, not
# plumbing. NB: `Done`, `Due date`, and `Linked Projects` are ALSO Anytype built-ins
# but ARE wired into the model (done-detection, deadlines, task→project links), so
# they are deliberately NOT in this set — they stay visible.
INERT = {"Backlinks", "Links", "Created by", "Creation date", "Last modified date",
         "Last modified by", "Last opened date", "Added date", "Assignee", "Tag", "Status"}


def _empty_types_note(empty):
    if not empty:
        return []
    return ["", "Also live in this space, with no model fields of their own (Anytype built-ins): "
            + ", ".join(empty) + "."]


def _all_types(sid):
    """Core five first, then every other live type, discovered rather than hardcoded."""
    names = list(CORE_TYPES)
    st, body = g.call("GET", f"/spaces/{sid}/types?limit=200")
    live = [t.get("name") for t in (body or {}).get("data", []) if t.get("name")]
    core_resolved = set()
    for c in CORE_TYPES:
        t = g.find_type(c)
        if t and t.get("name"):
            core_resolved.add(t["name"])
    # Anytype ships built-in types with no model fields (Page, Note, Image…). Listing them
    # verbatim buries the ones that matter, so only types that actually carry fields are
    # described; the rest are named in a single line so they are still ACCOUNTED FOR, never
    # silently dropped — silent omission is the exact failure this discovery replaced.
    extra, empty = [], []
    for n in sorted(x for x in live if x not in core_resolved):
        t = g.find_type(n)
        if not t:
            continue
        d = g.call("GET", f"/spaces/{sid}/types/{t['id']}")[1].get("type", {})
        fields = [p for p in (d.get("properties") or []) if p.get("name") not in INERT]
        (extra if fields else empty).append(n)
    return names + extra, empty


def describe():
    sid = g.get_space_id()
    out = [__doc__.strip(), "", "=" * 60, "LIVE SCHEMA (types and their model fields):", "=" * 60]
    described, empty_types = _all_types(sid)
    for type_name in described:
        t = g.find_type(type_name)
        if not t:
            out.append(f"\n[MISSING] type {type_name!r} not found in the space")
            continue
        detail = g.call("GET", f"/spaces/{sid}/types/{t['id']}")[1].get("type", {})
        # Non-GSDO types (Page, Note, Bookmark…) can return no properties at all.
        props = detail.get("properties") or []
        shown = [p for p in props if p.get("name") not in INERT]
        hidden = sorted(p.get("name", "?") for p in props if p.get("name") in INERT)
        display = detail.get("name", type_name)
        out.append(f"\n{display}  ({len(shown)} model fields)")
        for p in shown:
            nm = p.get("name", "?")
            fmt = p.get("format", "?")
            out.append(f"    · {nm}  [{fmt}]")
            # One short line of meaning, resolved (June's revision wins over the repo default).
            # A field with no documented meaning is marked as such rather than guessed at.
            meaning = field_semantics.one_line(nm, type_name=display)
            if meaning:
                out.append(f"        {meaning}")
                # A second line: what the field DOES — what reads it, and whether that is live,
                # planned but unbuilt, or nothing at all. Knowing a field's MEANING is not enough
                # to write it well; the consequence is what makes a wrong value expensive, and a
                # field waiting on design must not be mistaken for a broken one.
                did = field_semantics.does_line(nm, type_name=display)
                if did:
                    out.append(f"        {did}")
            elif field_semantics.is_undefined(nm) or field_semantics.lookup(nm):
                # Either no documented meaning at all, or documented only for a DIFFERENT type
                # (so this type's use of it is undocumented). Both cases: don't infer one.
                out.append("        (no documented meaning — do not infer one)")
                did = field_semantics.does_line(nm, type_name=display)
                if did:
                    out.append(f"        {did}")
        if hidden:
            out.append(f"    (+{len(hidden)} Anytype system fields hidden: {', '.join(hidden)})")
    out += _empty_types_note(empty_types)
    return "\n".join(out)


if __name__ == "__main__":
    print(describe())
