#!/usr/bin/env python3
"""Verify the full GSDO data model exists and is linked. Prints PASS/FAIL per check."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

EXPECTED = {
    "Goal":      ["Reaching for", "Horizon", "Goal status", "Barriers", "Context"],
    "Project":   ["Goal link", "Description", "Reaching for", "Project status",
                  "Deadline", "Parent project", "Excitement level", "Relevant docs",
                  "Affective", "Barriers", "Context", "Depends on", "Arc position rationale"],
    "task":      ["Duration min", "Needs clarifying", "Task status", "Blocked on", "Affective",
                  "Access conditions", "Access notes", "AI autonomous", "Last surfaced", "Scheduled",
                  "Context", "Due date", "Linked Projects"],   # Due date / Linked Projects = built-ins (replace custom Deadline/Project link)
    "Recurring": ["Frequency", "Has target", "Target", "Project link", "Context",
                  "Day of week", "Time of day", "Duration min"],
    "Strategy":  ["Strategy status", "What for", "Learning notes", "Context"],
}

# Guard-critical formats (guard #3: capacity/affect signals must NEVER be scalars).
# Linkage alone wouldn't catch a property accidentally created with the wrong format.
GUARD_FORMATS = {"Affective": "text", "Excitement level": "number"}

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
