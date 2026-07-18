#!/usr/bin/env python3
"""Ensure the Recurring type exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_recurring():
    p_freq    = g.ensure_property("Frequency", "select", ["Daily", "Weekly", "As-needed"])
    p_project = g.ensure_property("Project link", "objects")  # Recurring's OWN field (read as gsdo_project_link) — NOT Task's built-in linked_projects
    p_context = g.ensure_property("Context", "text")          # reused
    # time-anchor fields (fixed appointments, e.g. weekly therapy):
    p_dow     = g.ensure_property("Day of week", "multi_select",
                                  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    p_dom     = g.ensure_property("Day of month", "number")   # 1-31 anchor for monthly items
    p_tod     = g.ensure_property("Time of day", "text")      # "HH:MM"
    p_dur     = g.ensure_property("Duration min", "number")   # reused from Task
    # interval model: {unit, count} replaces the coarse Frequency select as the canonical
    # representation. unit=day/week/month/as_needed + count=N (e.g. day/3 = every 3 days).
    # The datetime seam uses these; gsdo_frequency is kept for display/legacy but not queried.
    p_iunit   = g.ensure_property("Interval unit", "select", ["day", "week", "month", "as_needed"])
    p_icount  = g.ensure_property("Interval count", "number")
    # Recurring-mirrors-Task: reuse Task's exact keys (shared, NOT duplicated). Match build_task.py
    # VERBATIM (name + type + options) or ensure_property mints a NEW property instead of reusing.
    p_clarify    = g.ensure_property("Needs clarifying", "checkbox")   # build_task.py:16
    p_blocked    = g.ensure_property("Blocked on", "text")             # build_task.py:20
    p_affective  = g.ensure_property("Affective", "text")             # build_task.py:21 — capacity signal, NEVER scalar-flatten (guard #3)
    p_access     = g.ensure_property("Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house",
                                      "Requires-talking-to-a-person"])  # build_task.py:22-24 verbatim
    p_access_nts = g.ensure_property("Access notes", "text")           # build_task.py:25
    p_autonomous = g.ensure_property("AI autonomous", "checkbox")      # build_task.py:26
    p_docs       = g.ensure_property("Relevant docs", "text")          # build_task.py:27
    # as-needed on/off (THIS feature): an active as_needed item surfaces every day until completed.
    p_active     = g.ensure_property("Active", "checkbox")
    key = g.ensure_type("Recurring", "Recurring",
                        [p_freq, p_project, p_context,
                         p_dow, p_dom, p_tod, p_dur, p_iunit, p_icount,
                         p_clarify, p_blocked, p_affective, p_access, p_access_nts,
                         p_autonomous, p_docs, p_active])
    # Retire Has target/Target (Practice-vs-Routine distinction cut; no scheduling consumer reads
    # either). ensure_type/link_properties_to_type only ADD — they never drop a field a prior run
    # linked, so removal needs its own call. Property definitions + any stored values are untouched;
    # this only unlinks them from Recurring's field list. find_property (not ensure_property) — a
    # look-up, not a get-or-create: nothing to unlink on a space where they were never made.
    retired_keys = [p["key"] for p in
                    (g.find_property("Has target"), g.find_property("Target")) if p]
    type_obj = g.find_type("Recurring")
    g.unlink_properties_from_type(type_obj["id"], retired_keys)
    print(f"[ok] Recurring type ready: key={key}")
    return key

if __name__ == "__main__":
    build_recurring()
