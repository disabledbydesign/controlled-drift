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
    p_engagement = g.ensure_property("Goal engagement", "select", ["Steady", "Sprint", "Backburner"])
    p_status     = g.ensure_property("Goal status", "select", ["Active", "Parked", "Achieved"])
    p_barriers   = g.ensure_property("Barriers", "text")
    p_context    = g.ensure_property("Context", "text")
    key = g.ensure_type("Goal", "Goals",
                        [p_reaching, p_horizon, p_resolution, p_engagement,
                         p_status, p_barriers, p_context])
    print(f"[ok] Goal type ready: key={key}")
    return key

if __name__ == "__main__":
    build_goal()
