#!/usr/bin/env python3
"""Ensure the Focus Period type exists. Idempotent.

A Focus Period is the short-term configuration June authors: what this stretch of
time is about (intent), the availability shape (a window + its situated meaning),
day-off overrides, and plan-behavior overrides (output shape, workday end,
foreground/paused projects). The enduring baseline lives on each Project; the
period OVERRIDES it while active. See docs/focus_configuration_addendum.md.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_focus_period():
    p_start     = g.ensure_property("Period start", "date")
    p_end       = g.ensure_property("Period end", "date")
    p_intent    = g.ensure_property("Intent", "text")
    p_av_start  = g.ensure_property("Availability start", "date")
    p_av_end    = g.ensure_property("Availability end", "date")
    p_av_note   = g.ensure_property("Availability note", "text")
    # Day-off overrides: small structured lists of ISO dates (comma-separated or a tiny
    # JSON array). Structured (not NL) so Python parses deterministically. Weekly default
    # lives in settings.json; these override it per-day, both ways.
    p_days_off  = g.ensure_property("Days off", "text")
    p_days_on   = g.ensure_property("Days on", "text")
    # Plan-behavior overrides — each structured + Python-readable:
    p_out_fmt   = g.ensure_property("Output format", "select",
                                    ["Auto", "Clock schedule", "Priority list"])
    # Workday bounds, both "HH:MM". End widens the day for a sprint or narrows it for a gentle
    # week. Start is the companion added for backend spec §17 — the object had only an end, so
    # the scheduler's day-bounds logic was end-only and a period could not say "not before 11"
    # on a slow-morning stretch. Either empty = the system default (10:00 / 18:00).
    p_wk_start  = g.ensure_property("Workday start", "text")
    p_wk_end    = g.ensure_property("Workday end", "text")
    p_fg        = g.ensure_property("Foreground projects", "objects")
    p_paused    = g.ensure_property("Paused projects", "objects")
    key = g.ensure_type("Focus Period", "Focus Periods",
                        [p_start, p_end, p_intent, p_av_start, p_av_end, p_av_note,
                         p_days_off, p_days_on, p_out_fmt, p_wk_start, p_wk_end,
                         p_fg, p_paused])
    print(f"[ok] Focus Period type ready: key={key}")
    return key

if __name__ == "__main__":
    build_focus_period()
