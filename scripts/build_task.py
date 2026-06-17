#!/usr/bin/env python3
"""Extend the built-in Task type with GSDO properties. Idempotent. Reuses existing standalone props.

Uses the built-in 'due_date' (Due date) and 'linked_projects' (Linked Projects) instead of
custom Deadline / Project-link fields — they're semantically identical and avoid double fields
in Anytype's native Tasks tab. Keeps a distinct 'Task status' (Active/Needs Clarifying/Blocked/Done)
because the built-in Status (To Do/In Progress/Done) lacks the load-bearing 'Needs Clarifying'
weeding state."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_task():
    # reuse the two standalone properties already in the space (do NOT recreate):
    p_duration = g.ensure_property("Duration min", "number")        # existing
    p_clarify  = g.ensure_property("Needs clarifying", "checkbox")  # existing
    # new task properties:
    p_status     = g.ensure_property("Task status", "select",
                                     ["Active", "Needs Clarifying", "Blocked", "Done"])
    p_blocked    = g.ensure_property("Blocked on", "text")
    p_affective  = g.ensure_property("Affective", "text")           # reused; capacity signal, never a scalar
    p_access     = g.ensure_property("Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house"])
    p_access_nts = g.ensure_property("Access notes", "text")  # open annotations → §6 promotion loop
    p_autonomous = g.ensure_property("AI autonomous", "checkbox")
    p_docs       = g.ensure_property("Relevant docs", "text")       # reused
    p_context    = g.ensure_property("Context", "text")             # reused
    p_surfaced   = g.ensure_property("Last surfaced", "date")       # plan note 1

    task_type = g.find_type("task")
    if not task_type:
        raise RuntimeError("built-in 'task' type not found")
    # built-in keys used in place of custom Deadline / Project-link:
    g.link_properties_to_type(task_type["id"],
        [p_duration, p_clarify, p_status, p_blocked, p_affective, p_access, p_access_nts,
         p_autonomous, p_docs, p_context, p_surfaced, "due_date", "linked_projects"])
    print(f"[ok] Task type extended: id={task_type['id']}")

if __name__ == "__main__":
    build_task()
