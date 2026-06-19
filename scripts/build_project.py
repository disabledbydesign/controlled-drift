#!/usr/bin/env python3
"""Ensure the Project type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_project():
    p_goal_link   = g.ensure_property("Goal link", "objects")
    p_description = g.ensure_property("Description", "text")
    p_reaching    = g.ensure_property("Reaching for", "text")   # reused from Goal
    p_deadline    = g.ensure_property("Deadline", "date")
    p_parent      = g.ensure_property("Parent project", "objects")
    p_excitement  = g.ensure_property("Excitement level", "number")
    p_docs        = g.ensure_property("Relevant docs", "text")
    p_affective   = g.ensure_property("Affective", "text")   # capacity signal, free text (guard #3: never a scalar)
    p_barriers    = g.ensure_property("Barriers", "text")     # queryable struggle-blocks (§10 stuck-support storage)
    p_context     = g.ensure_property("Context", "text")     # reused
    # Engagement: how June is currently engaging with this project.
    # Hyperfixation = current attention capture for the whole space — one project in Hyperfixation
    # explains why other projects are neglected; agents should read it systemically, not project-locally.
    # Replaces the old "Project status" (Active/Parked/Inactive) — that field stays in the space
    # as legacy but is superseded. Learning loop target: system learns what each level means for
    # each project over time from June's corrections. Paired text field = canonical; select = filterable.
    p_engagement  = g.ensure_property("Engagement", "select",
                                      ["Steady", "Sprint", "Hyperfixation",
                                       "Needs Clarifying", "Backburner", "Done"])
    p_eng_notes   = g.ensure_property("Engagement notes", "text")   # open: thresholds, cadence, conditions
    key = g.ensure_type("Project", "Projects",
                        [p_goal_link, p_description, p_reaching, p_deadline,
                         p_parent, p_excitement, p_docs, p_affective, p_barriers,
                         p_context, p_engagement, p_eng_notes])
    print(f"[ok] Project type ready: key={key}")
    return key

if __name__ == "__main__":
    build_project()
