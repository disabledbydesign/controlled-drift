#!/usr/bin/env python3
"""Ensure the GSDO Strategy type (strategies/disciplines/mindsets) exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_strategy():
    p_status   = g.ensure_property("GSDO Strategy status", "select", ["Active", "Retired"])
    p_what_for = g.ensure_property("GSDO What for", "text")
    p_learning = g.ensure_property("GSDO Learning notes", "text")
    p_context  = g.ensure_property("GSDO Context", "text")  # reused
    key = g.ensure_type("GSDO Strategy", "GSDO Strategies",
                        [p_status, p_what_for, p_learning, p_context])
    print(f"[ok] Strategy type ready: key={key}")
    return key

if __name__ == "__main__":
    build_strategy()
