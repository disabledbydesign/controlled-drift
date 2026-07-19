#!/usr/bin/env python3
"""Extend the built-in Task type with GSDO properties. Idempotent. Reuses existing standalone props.

Uses the built-in 'due_date' (Due date) and 'linked_projects' (Linked Projects) instead of
custom Deadline / Project-link fields — they're semantically identical and avoid double fields
in Anytype's native Tasks tab. Keeps a distinct 'Task status' (Ready/In Design/Needs Clarifying/Blocked/Done)
because the built-in Status (To Do/In Progress/Done) lacks the load-bearing 'Needs Clarifying'
weeding state. Ready = well-specified, executable. In Design = real work, needs design-first."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import intentionally_none as inone

def build_task():
    # reuse the two standalone properties already in the space (do NOT recreate):
    p_duration = g.ensure_property("Duration min", "number")        # existing
    p_clarify  = g.ensure_property("Needs clarifying", "checkbox")  # existing
    # new task properties:
    p_status     = g.ensure_property("Task status", "select",
                                     ["Ready", "In Design", "Parked", "Needs Clarifying", "Blocked", "Done"])
    p_blocked    = g.ensure_property("Blocked on", "text")
    p_affective  = g.ensure_property("Affective", "text")           # reused; capacity signal, never a scalar
    # Access conditions — the queryable access/capacity tags. A condition earns a TAG only when it
    # is both queryable and load-bearing for planning (AI_LAYER_SPEC §2); everything else stays in
    # the free-text "Access notes" and feeds the promotion loop. The three added 2026-07-18 were
    # promoted deliberately (backend spec §6) — do not add more without that same judgement.
    # ⚠ Induces-pain is the physical-pain cost of doing the task: a capacity signal, and a TAG,
    # never a 1-5 scalar (guard #3).
    p_access     = g.ensure_property("Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house",
                                      "Requires-talking-to-a-person",
                                      "Requires-deep-thinking", "Involves-bureaucracy",
                                      "Induces-pain"])
    p_access_nts = g.ensure_property("Access notes", "text")  # open annotations → §6 promotion loop
    p_autonomous = g.ensure_property("AI autonomous", "checkbox")
    p_docs       = g.ensure_property("Relevant docs", "text")       # reused
    p_context    = g.ensure_property("Context", "text")             # reused
    p_surfaced   = g.ensure_property("Last surfaced", "date")       # plan note 1
    # When June wants a task worked (anchored to a real ISO date at capture time by
    # when_resolve — never a weekday word). Distinct from the built-in Due date (a deadline):
    # Scheduled is "start considering it on/after this day", Due date is "it's late after this
    # day". The selection thread reads this to hold future-dated tasks off today's plan.
    p_scheduled  = g.ensure_property("Scheduled", "date")
    # Provenance for Duration min: did June state this duration ("stated") or did the model
    # estimate it to fill a silence ("estimated")? The scheduler ignores this field — it only
    # reads Duration min — but the duration-bias learning loop reads it to know which durations
    # it may correct (estimated) vs. must never touch (stated). A select, not a checkbox, so it
    # reads plainly in June's UI and leaves room for a future "corrected" value.
    p_dur_source = g.ensure_property("Duration source", "select", ["stated", "estimated"])
    # Which inheritable fields this object sets to "none" ON PURPOSE (spec §4's third state).
    # A separate property, not a tag inside the field itself, because the daily plan reads and
    # PRINTS access tags — a marker in that list would surface as a fake access condition and
    # reach plan_generate's tag filtering as a phantom constraint. See `intentionally_none`.
    p_inone      = g.ensure_property(inone.PROPERTY, "multi_select", inone.OPTIONS)

    task_type = g.find_type("task")
    if not task_type:
        raise RuntimeError("built-in 'task' type not found")
    # built-in keys used in place of custom Deadline / Project-link:
    g.link_properties_to_type(task_type["id"],
        [p_duration, p_dur_source, p_clarify, p_status, p_blocked, p_affective, p_access, p_access_nts,
         p_autonomous, p_docs, p_context, p_surfaced, p_scheduled, p_inone, "due_date", "linked_projects"])
    print(f"[ok] Task type extended: id={task_type['id']}")

if __name__ == "__main__":
    build_task()
