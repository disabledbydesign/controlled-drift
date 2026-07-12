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

Usage: python3 <REPO>/scripts/describe_model.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

# The five types, by the key/name find_type resolves. Task's type key is "task".
TYPES = ["Goal", "Project", "task", "Recurring", "Strategy"]

# Anytype's built-in/system fields — attached to objects automatically, not part of
# the GSDO model. Hidden as inert so the description shows the actual model, not
# plumbing. NB: `Done`, `Due date`, and `Linked Projects` are ALSO Anytype built-ins
# but ARE wired into the model (done-detection, deadlines, task→project links), so
# they are deliberately NOT in this set — they stay visible.
INERT = {"Backlinks", "Links", "Created by", "Creation date", "Last modified date",
         "Last modified by", "Last opened date", "Added date", "Assignee", "Tag", "Status"}


def describe():
    sid = g.get_space_id()
    out = [__doc__.strip(), "", "=" * 60, "LIVE SCHEMA (types and their model fields):", "=" * 60]
    for type_name in TYPES:
        t = g.find_type(type_name)
        if not t:
            out.append(f"\n[MISSING] type {type_name!r} not found in the space")
            continue
        detail = g.call("GET", f"/spaces/{sid}/types/{t['id']}")[1].get("type", {})
        props = detail.get("properties", [])
        shown = [p for p in props if p.get("name") not in INERT]
        hidden = sorted(p.get("name", "?") for p in props if p.get("name") in INERT)
        display = detail.get("name", type_name)
        out.append(f"\n{display}  ({len(shown)} model fields)")
        for p in shown:
            nm = p.get("name", "?")
            fmt = p.get("format", "?")
            out.append(f"    · {nm}  [{fmt}]")
        if hidden:
            out.append(f"    (+{len(hidden)} Anytype system fields hidden: {', '.join(hidden)})")
    return "\n".join(out)


if __name__ == "__main__":
    print(describe())
