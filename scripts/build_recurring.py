#!/usr/bin/env python3
"""Ensure the Recurring type (Practices + Routines) exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_recurring():
    p_freq    = g.ensure_property("Frequency", "select", ["Daily", "Weekly", "As-needed"])
    p_target  = g.ensure_property("Has target", "checkbox")
    p_tgt_txt = g.ensure_property("Target", "text")
    p_project = g.ensure_property("Project link", "objects")  # reused from Task
    p_context = g.ensure_property("Context", "text")          # reused
    # time-anchor fields (fixed appointments, e.g. weekly therapy):
    p_dow     = g.ensure_property("Day of week", "multi_select",
                                  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    p_tod     = g.ensure_property("Time of day", "text")      # "HH:MM"
    p_dur     = g.ensure_property("Duration min", "number")   # reused from Task
    key = g.ensure_type("Recurring", "Recurring",
                        [p_freq, p_target, p_tgt_txt, p_project, p_context, p_dow, p_tod, p_dur])
    print(f"[ok] Recurring type ready: key={key}")
    return key

if __name__ == "__main__":
    build_recurring()
