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
    # Replaces the old "Project status" (Active/Parked/Inactive) — that field stays in the space
    # as legacy but is superseded. Learning loop target: system learns what each level means for
    # each project over time from June's corrections. Paired text field = canonical; select = filterable.
    # Sprint/Hyperfixation RETIRED 2026-07-16 (docs/spec_reconciliation_selection_2026-07-11.md):
    # Sprint routes through a Focus Period foreground action; Hyperfixation routes through the
    # qualitative Engagement notes / Affective free-text. The reconciled set is Steady/Open/
    # Needs Clarifying/Backburner/Done.
    p_engagement  = g.ensure_property("Engagement", "select",
                                      ["Steady", "Open", "Needs Clarifying",
                                       "Backburner", "Done"])
    p_eng_notes   = g.ensure_property("Engagement notes", "text")   # open: thresholds, cadence, conditions
    # Obligation vs wellbeing — set directly on the Project (June thinks of a project
    # AS obligation or hobby; not derived from the goal). The axis is income/survival-
    # relevance: creative work that EARNS (e.g. leather cuffs) is Obligation; creative
    # work that doesn't is Wellbeing. Structurally separates the two sides everywhere they
    # surface: neglect may be offered on the Obligation side; the Wellbeing side is never
    # nagged (only ever surfaced as under-rest/under-play).
    # "Daily life" added 2026-07-14: the always-eligible chore track (medical / household /
    # self-care / social). Present in the live space already; adding it here keeps the model
    # DEFINITION matching reality, so a rebuild can't silently wipe the daily-life track the
    # display-grain design (decision 1) rests on. ensure_select_options is additive/idempotent.
    p_side        = g.ensure_property("Side", "select",
                                      ["Obligation", "Wellbeing", "Fun / hobby", "Daily life"])
    # Block chunk length (minutes) — the per-project duration of a "work on X" block, a durable
    # preference June sets (like Side/Engagement), read back to place the block as a clock-time
    # slot. Anytype auto-generates this field's key, so it is READ BY NAME ("Block chunk min"),
    # not by a gsdo_ key. (display_grain_design.md decision 2.)
    p_block_chunk = g.ensure_property("Block chunk min", "number")
    # Arc ordering — dependency-vs-sequence refinement (guard #6: June needs to understand why).
    # Depends on: hard dependency links (X can't start until Y is done; enforced in orient_map.py).
    # Arc position rationale: full plain-language reasoning for where this stream sits in the arc.
    # Written by the AI when proposing ordering; editable by June; read by render_stream.
    p_depends     = g.ensure_property("Depends on", "objects")
    p_arc_why     = g.ensure_property("Arc position rationale", "text")
    key = g.ensure_type("Project", "Projects",
                        [p_goal_link, p_description, p_reaching, p_deadline,
                         p_parent, p_excitement, p_docs, p_affective, p_barriers,
                         p_context, p_engagement, p_eng_notes, p_side, p_block_chunk,
                         p_depends, p_arc_why])
    print(f"[ok] Project type ready: key={key}")
    return key

if __name__ == "__main__":
    build_project()
