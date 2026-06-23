"""Tests for morning_push — the keystone scheduled job.

The notification (osascript) and the generator are mocked: tests assert the logic and the
permission-granting register without firing real notifications or calling the LLM.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import morning_push as mp
import plan_generate


# --- the notification summary ----------------------------------------------

def test_summary_prefers_first_task():
    plan = {"woven_frame": "frame", "blocks": [
        {"items": [{"task": "Email the surgeon"}, {"task": "second"}]}]}
    assert mp._first_line_summary(plan) == "Email the surgeon"


def test_summary_strips_leading_parenthetical():
    # A task like "(Optional, only if mid-thought) Case note: …" should not lead the
    # notification with the aside — strip it to the real content.
    plan = {"blocks": [{"items": [{"task": "(Optional, only if mid-thought) Case note: dump it"}]}]}
    assert mp._first_line_summary(plan) == "Case note: dump it"


def test_summary_falls_back_to_woven_frame():
    plan = {"woven_frame": "Tonight is for stopping cleanly.", "blocks": []}
    assert mp._first_line_summary(plan) == "Tonight is for stopping cleanly."


def test_summary_default_when_empty():
    assert mp._first_line_summary({"blocks": [], "woven_frame": ""}) == "A shape for today is ready."


def test_summary_trims_long_task():
    long_task = "x" * 200
    out = mp._first_line_summary({"blocks": [{"items": [{"task": long_task}]}]})
    assert len(out) <= 91 and out.endswith("…")


# --- run(): success + failure paths ----------------------------------------

def test_run_success_notifies_and_returns_0(monkeypatch):
    monkeypatch.setattr(plan_generate, "generate_plan",
                        lambda source="morning": {"woven_frame": "f", "blocks": [
                            {"items": [{"task": "do the first thing"}]}]})
    notes = []
    monkeypatch.setattr(mp, "_notify", lambda title, msg: notes.append((title, msg)))
    monkeypatch.setattr(mp, "notify", None)  # skip the ding
    rc = mp.run()
    assert rc == 0
    title, msg = notes[0]
    # Permission-granting register — offers, never commands.
    assert "today" in title.lower()
    assert msg == "do the first thing"


def test_run_failure_notifies_honestly_and_returns_1(monkeypatch):
    def boom(source="morning"):
        raise RuntimeError("backend down")
    monkeypatch.setattr(plan_generate, "generate_plan", boom)
    notes = []
    monkeypatch.setattr(mp, "_notify", lambda title, msg: notes.append((title, msg)))
    rc = mp.run()
    assert rc == 1
    # On failure: an honest "couldn't build it" note, not a cheerful fake plan.
    assert notes and "couldn't" in notes[0][1].lower()
