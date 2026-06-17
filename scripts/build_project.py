#!/usr/bin/env python3
"""Ensure the Project type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_project():
    p_goal_link   = g.ensure_property("Goal link", "objects")
    p_description = g.ensure_property("Description", "text")
    p_reaching    = g.ensure_property("Reaching for", "text")   # reused from Goal
    p_status      = g.ensure_property("Project status", "select", ["Active", "Parked", "Inactive"])
    p_deadline    = g.ensure_property("Deadline", "date")
    p_parent      = g.ensure_property("Parent project", "objects")
    p_excitement  = g.ensure_property("Excitement level", "number")
    p_docs        = g.ensure_property("Relevant docs", "text")
    p_affective   = g.ensure_property("Affective", "text")   # capacity signal, free text (guard #3: never a scalar)
    p_barriers    = g.ensure_property("Barriers", "text")     # reused from Goal; queryable struggle-blocks
    p_context     = g.ensure_property("Context", "text")     # reused
    key = g.ensure_type("Project", "Projects",
                        [p_goal_link, p_description, p_reaching, p_status, p_deadline,
                         p_parent, p_excitement, p_docs, p_affective, p_barriers, p_context])
    print(f"[ok] Project type ready: key={key}")
    return key

if __name__ == "__main__":
    build_project()
