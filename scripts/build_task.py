#!/usr/bin/env python3
"""Extend the built-in Task type with GSDO properties. Idempotent. Reuses existing standalone props."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_task():
    # reuse the two standalone properties already in the space (do NOT recreate):
    p_duration = g.ensure_property("GSDO Duration min", "number")        # existing
    p_clarify  = g.ensure_property("GSDO Needs clarifying", "checkbox")  # existing
    # new task properties:
    p_status     = g.ensure_property("GSDO Task status", "select",
                                     ["Active", "Needs Clarifying", "Blocked", "Done"])
    p_project    = g.ensure_property("GSDO Project link", "objects")
    p_blocked    = g.ensure_property("GSDO Blocked on", "text")
    p_deadline   = g.ensure_property("GSDO Deadline", "date")            # reused from Project
    p_affective  = g.ensure_property("GSDO Affective", "text")           # reused
    p_access     = g.ensure_property("GSDO Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house"])
    p_access_nts = g.ensure_property("GSDO Access notes", "text")  # open annotations → §6 promotion loop
    p_autonomous = g.ensure_property("GSDO AI autonomous", "checkbox")
    p_docs       = g.ensure_property("GSDO Relevant docs", "text")       # reused
    p_context    = g.ensure_property("GSDO Context", "text")             # reused
    p_surfaced   = g.ensure_property("GSDO Last surfaced", "date")       # plan note 1

    task_type = g.find_type("task")
    assert task_type, "built-in 'task' type not found"
    g.link_properties_to_type(task_type["id"],
        [p_duration, p_clarify, p_status, p_project, p_blocked, p_deadline,
         p_affective, p_access, p_access_nts, p_autonomous, p_docs, p_context, p_surfaced])
    print(f"[ok] Task type extended: id={task_type['id']}")

if __name__ == "__main__":
    build_task()
