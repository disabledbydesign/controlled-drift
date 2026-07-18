#!/usr/bin/env python3
"""Verify the full GSDO data model exists and is linked. Prints PASS/FAIL per check."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

EXPECTED = {
    "Goal":      ["Reaching for", "Horizon", "Goal status", "Barriers", "Context"],
    "Project":   ["Goal link", "Description", "Reaching for", "Project status",
                  "Deadline", "Parent project", "Relevant docs",
                  "Affective", "Barriers", "Context", "Depends on", "Arc position rationale",
                  "Access conditions"],   # block-grain access profile (backend spec §4)
    "task":      ["Duration min", "Needs clarifying", "Task status", "Blocked on", "Affective",
                  "Access conditions", "Access notes", "AI autonomous", "Last surfaced", "Scheduled",
                  "Context", "Due date", "Linked Projects"],   # Due date / Linked Projects = built-ins (replace custom Deadline/Project link)
    "Recurring": ["Frequency", "Project link", "Context",
                  "Day of week", "Time of day", "Duration min"],
    "Strategy":  ["Strategy status", "What for", "Learning notes", "Context"],
    # Focus Period is not one of the five GSDO core types, so it was never verified here — which
    # is why `Workday start` (backend spec §17) being absent from the live type was invisible
    # until someone read the builder. Listed now so the check fails loudly while the schema
    # write is still pending June's approval. Built by scripts/build_focus_period.py.
    "Focus Period": ["Period start", "Period end", "Intent",
                     "Availability start", "Availability end", "Availability note",
                     "Days off", "Days on", "Output format",
                     "Workday start", "Workday end",
                     "Foreground projects", "Paused projects"],
}

# Guard-critical formats (guard #3: capacity/affect signals must NEVER be scalars).
# Linkage alone wouldn't catch a property accidentally created with the wrong format.
GUARD_FORMATS = {"Affective": "text"}

# Select/multi-select vocabularies that the planning code and the surface both read BY NAME, so a
# missing or stale option changes behaviour without failing anything loudly. `absent` catches the
# other half of a rename: the new name arriving while the old one is still sitting there, which
# would leave two options meaning the same thing.
EXPECTED_OPTIONS = {
    # backend spec §6 — the six promoted access conditions. Anything unnamed lives in "Access
    # notes" instead; a tag earns its place by being queryable and load-bearing (AI_LAYER_SPEC §2).
    "Access conditions": {
        "present": ["Can-be-done-lying-down", "Involves-leaving-house", "Requires-talking-to-a-person",
                    "Requires-deep-thinking", "Involves-bureaucracy", "Induces-pain"],
        "absent": [],
    },
    # backend spec §12 — "Obligation" was renamed to "Work" on 2026-07-18.
    "Side": {
        "present": ["Work", "Wellbeing", "Fun / hobby", "Daily life"],
        "absent": ["Obligation"],
    },
}

def verify():
    sid = g.get_space_id()
    passed = total = 0
    for type_name, props in EXPECTED.items():
        total += 1
        t = g.find_type(type_name)
        if not t:
            print(f"  [FAIL] type {type_name} missing"); continue
        detail = g.call("GET", f"/spaces/{sid}/types/{t['id']}")[1].get("type", {})
        linked = {p.get("key") for p in detail.get("properties", [])}
        missing = [p for p in props if (g.find_property(p) or {}).get("key") not in linked]
        ok = not missing
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {type_name}: {'all props linked' if ok else f'missing {missing}'}")
    for prop_name, spec in EXPECTED_OPTIONS.items():
        total += 1
        prop = g.find_property(prop_name)
        if not prop:
            print(f"  [FAIL] options {prop_name}: property missing"); continue
        live = {t.get("name") for t in
                g.call("GET", f"/spaces/{sid}/properties/{prop['id']}/tags")[1].get("data", [])}
        missing = [o for o in spec["present"] if o not in live]
        lingering = [o for o in spec["absent"] if o in live]
        ok = not missing and not lingering
        passed += ok
        detail = "all options present" if ok else \
            ", ".join(filter(None, [f"missing {missing}" if missing else "",
                                    f"should be gone {lingering}" if lingering else ""]))
        print(f"  [{'PASS' if ok else 'FAIL'}] options {prop_name}: {detail}")
    for nm, fmt in GUARD_FORMATS.items():
        total += 1
        actual = (g.find_property(nm) or {}).get("format")
        ok = actual == fmt
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] guard-format {nm}: {actual!r} (expect {fmt!r})")
    print(f"\nSUMMARY: {passed}/{total} checks passed")
    return passed == total

if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
