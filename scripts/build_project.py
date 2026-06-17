#!/usr/bin/env python3
"""Ensure the GSDO Project type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_project():
    p_goal_link   = g.ensure_property("GSDO Goal link", "objects")
    p_description = g.ensure_property("GSDO Description", "text")
    p_reaching    = g.ensure_property("GSDO Reaching for (text)", "text")   # reused from Goal
    p_status      = g.ensure_property("GSDO Project status", "select", ["Active", "Parked", "Inactive"])
    p_deadline    = g.ensure_property("GSDO Deadline", "date")
    p_parent      = g.ensure_property("GSDO Parent project", "objects")
    p_excitement  = g.ensure_property("GSDO Excitement level", "number")
    p_docs        = g.ensure_property("GSDO Relevant docs", "text")
    p_affective   = g.ensure_property("GSDO Affective", "text")   # capacity signal, free text
    p_barriers    = g.ensure_property("GSDO Barriers", "text")     # reused from Goal; queryable struggle-blocks
    p_context     = g.ensure_property("GSDO Context", "text")     # reused
    key = g.ensure_type("GSDO Project", "GSDO Projects",
                        [p_goal_link, p_description, p_reaching, p_status, p_deadline,
                         p_parent, p_excitement, p_docs, p_affective, p_barriers, p_context])
    print(f"[ok] Project type ready: key={key}")
    return key

if __name__ == "__main__":
    build_project()
