#!/usr/bin/env python3
"""Append-only store for qualitative learning signal. CAPTURE ONLY — no interpretation.

Stores June's own words about how a day went / what didn't fit / why she diverged,
tagged with a structural source + reference + timestamp. The meaning is deliberately
NOT classified here: a future learning loop reads this accumulated raw material and lets
categories emerge from it (addendum §"persisting signals for a learning loop"). Forcing
categories now is the premature-operationalizing the whole system resists.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

# Structural sources — cheap and worth recording, but they do NOT encode meaning
# (a Log Day entry is not the same as "the plan was wrong"). The why stays in the raw text.
SOURCES = ("log_day", "checkin_reply", "config_authoring", "config_correction", "plan_renegotiation")
# "plan_deferral" ("not today") used to live here but was a machine-recorded event, not June's own
# words, so it was moved to corrections_log (kind "not_today") — June's correction, 2026-07-18.
# scripts/migrate_plan_deferral_to_corrections.py moves the entries that already landed here.


def _path(path=None):
    return path or cd_paths.data_file("signal_log.jsonl")


def log_signal(raw_text, source, reference=None, path=None):
    """Append one signal record {ts, source, reference, raw}. raw_text is stored verbatim."""
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "source": source, "reference": reference, "raw": raw_text}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_signals(path=None):
    """All records (for tests + the future loop). Empty list if the store doesn't exist yet."""
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
