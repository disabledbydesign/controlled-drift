#!/usr/bin/env python3
"""Verify the full GSDO data model exists and is linked. Prints PASS/FAIL per check."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

EXPECTED = {
    "GSDO Goal":     ["GSDO Reaching for (text)", "GSDO Horizon", "GSDO Goal status", "GSDO Barriers", "GSDO Context"],
    "GSDO Project":  ["GSDO Goal link", "GSDO Description", "GSDO Reaching for (text)", "GSDO Project status",
                      "GSDO Deadline", "GSDO Parent project", "GSDO Excitement level", "GSDO Relevant docs",
                      "GSDO Affective", "GSDO Barriers", "GSDO Context"],
    "task":          ["GSDO Duration min", "GSDO Needs clarifying", "GSDO Task status",
                      "GSDO Project link", "GSDO Blocked on", "GSDO Deadline", "GSDO Affective",
                      "GSDO Access conditions", "GSDO Access notes",
                      "GSDO AI autonomous", "GSDO Last surfaced", "GSDO Context"],
    "GSDO Recurring":["GSDO Frequency", "GSDO Has target", "GSDO Target", "GSDO Context",
                      "GSDO Day of week", "GSDO Time of day", "GSDO Duration min"],
    "GSDO Strategy": ["GSDO Strategy status", "GSDO What for", "GSDO Learning notes", "GSDO Context"],
}

# Guard-critical formats (guard #3: capacity/affect signals must NEVER be scalars).
# Linkage alone wouldn't catch a property accidentally created with the wrong format.
GUARD_FORMATS = {"GSDO Affective": "text", "GSDO Excitement level": "number"}

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
