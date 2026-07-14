#!/usr/bin/env python3
"""Ensure the Goal type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_goal():
    p_reaching   = g.ensure_property("Reaching for", "text")
    # Horizon: Chapter (phase ending on a condition), Ongoing (structural, no end),
    # Milestone (discrete, achievable done-state). Replaces vague Long/Medium/Short-term.
    p_horizon    = g.ensure_property("Horizon", "select", ["Chapter", "Ongoing", "Milestone"])
    p_resolution = g.ensure_property("Resolution condition", "text")  # for Chapter goals: what resolved looks like
    p_status     = g.ensure_property("Goal status", "select", ["Active", "Parked", "Achieved"])
    p_barriers   = g.ensure_property("Barriers", "text")
    p_context    = g.ensure_property("Context", "text")
    # Goal-level analog of Project's Engagement: is this whole life-area currently getting
    # focused energy, ongoing baseline attention, or set aside — distinct from any one project
    # under it. No Sprint at this level (June, 2026-07-13: "goals should never be sprints" —
    # a sprint is a Focus Period foreground state on a PROJECT, not a property of a life area).
    p_engagement = g.ensure_property("Goal engagement", "select", ["Steady", "Open", "Backburner"])
    key = g.ensure_type("Goal", "Goals",
                        [p_reaching, p_horizon, p_resolution,
                         p_status, p_barriers, p_context, p_engagement])
    print(f"[ok] Goal type ready: key={key}")
    return key

if __name__ == "__main__":
    build_goal()
