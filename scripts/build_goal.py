#!/usr/bin/env python3
"""Ensure the GSDO Goal type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_goal():
    p_reaching = g.ensure_property("GSDO Reaching for (text)", "text")
    p_horizon  = g.ensure_property("GSDO Horizon", "select", ["Long-term", "Medium-term", "Short-term"])
    p_status   = g.ensure_property("GSDO Goal status", "select", ["Active", "Parked", "Achieved"])
    p_barriers = g.ensure_property("GSDO Barriers", "text")   # queryable struggle-blocks (§10 stuck-support storage)
    p_context  = g.ensure_property("GSDO Context", "text")
    key = g.ensure_type("GSDO Goal", "GSDO Goals", [p_reaching, p_horizon, p_status, p_barriers, p_context])
    print(f"[ok] Goal type ready: key={key}")
    return key

if __name__ == "__main__":
    build_goal()
