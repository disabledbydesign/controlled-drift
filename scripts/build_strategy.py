#!/usr/bin/env python3
"""Ensure the Strategy type (strategies/disciplines/mindsets) exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_strategy():
    p_status   = g.ensure_property("Strategy status", "select", ["Active", "Retired"])
    p_what_for = g.ensure_property("What for", "text")
    p_learning = g.ensure_property("Learning notes", "text")
    p_context  = g.ensure_property("Context", "text")  # reused
    # When a strategy applies. "Always" = read into every daily plan (the general strategies).
    # A state value ("Low energy", …) = a TRIGGERED strategy, pulled in only when that state is
    # active (e.g. the Low-energy button) — so state-specific rules don't colour every plan.
    p_applies  = g.ensure_property("Applies when", "select", ["Always", "Low energy"])
    key = g.ensure_type("Strategy", "Strategies",
                        [p_status, p_what_for, p_learning, p_context, p_applies])
    print(f"[ok] Strategy type ready: key={key}")
    return key

if __name__ == "__main__":
    build_strategy()
