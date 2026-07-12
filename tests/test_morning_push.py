"""Tests for morning_push — the keystone scheduled job.

The notification (osascript) and the generator are mocked: tests assert the logic and the
permission-granting register without firing real notifications or calling the LLM.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import morning_push as mp
import plan_generate
import plan_store


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


def _no_sleep(monkeypatch):
    """Zero the retry delay so failure-path tests don't actually wait."""
    monkeypatch.setattr(mp, "RETRY_DELAY_S", 0)


def test_run_failure_with_no_cache_notifies_phone_and_returns_1(monkeypatch):
    # Generation fails every attempt AND there's no cached plan (sandbox is empty) → honest
    # failure notice, and crucially it must reach the PHONE, not just the Mac.
    _no_sleep(monkeypatch)
    def boom(source="morning"):
        raise RuntimeError("backend down")
    monkeypatch.setattr(plan_generate, "generate_plan", boom)
    monkeypatch.setattr(mp, "_notify", lambda title, msg: None)
    phone = []
    monkeypatch.setattr(mp, "_push_failure_to_phone", lambda: phone.append("failure") or True)
    rc = mp.run()
    assert rc == 1
    assert phone == ["failure"]   # the failure reached the phone, not silence


def test_run_retries_then_succeeds(monkeypatch):
    # First two attempts fail, third succeeds — June still gets her real plan.
    _no_sleep(monkeypatch)
    calls = {"n": 0}
    def flaky(source="morning"):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("[Errno 54] Connection reset by peer")
        return {"woven_frame": "f", "blocks": [{"items": [{"task": "the real thing"}]}]}
    monkeypatch.setattr(plan_generate, "generate_plan", flaky)
    monkeypatch.setattr(mp, "_notify", lambda title, msg: None)
    monkeypatch.setattr(mp, "notify", None)
    pushed = []
    monkeypatch.setattr(mp, "_push_to_phone", lambda plan, stale=False: pushed.append(stale) or True)
    rc = mp.run()
    assert rc == 0 and calls["n"] == 3
    assert pushed == [False]   # a FRESH plan (not stale)


def test_run_uses_fallback_backend_when_primary_fails(monkeypatch):
    # Primary (Mistral) fails every retry; the fallback backend (claude -p) then succeeds → June
    # still gets a FRESH plan, not a stale one. generate_plan is called with CD_BACKEND switched.
    _no_sleep(monkeypatch)
    seen_backends = []
    def gen(source="morning"):
        b = os.environ.get("CD_BACKEND", "mistral")
        seen_backends.append(b)
        if b == mp.FALLBACK_BACKEND:           # the fallback attempt succeeds
            return {"woven_frame": "fresh-from-fallback", "blocks": [{"items": [{"task": "go"}]}]}
        raise OSError("[Errno 54] Connection reset by peer")   # primary keeps failing
    monkeypatch.setattr(plan_generate, "generate_plan", gen)
    monkeypatch.setattr(mp, "_notify", lambda title, msg: None)
    monkeypatch.setattr(mp, "notify", None)
    pushed = []
    monkeypatch.setattr(mp, "_push_to_phone", lambda plan, stale=False: pushed.append(stale) or True)
    rc = mp.run()
    assert rc == 0
    assert mp.FALLBACK_BACKEND in seen_backends   # the fallback backend was actually tried
    assert pushed == [False]                      # fresh plan (not stale)
    assert os.environ.get("CD_BACKEND") != mp.FALLBACK_BACKEND or "CD_BACKEND" not in os.environ  # restored


def test_run_falls_back_to_cached_plan_when_generation_fails(monkeypatch):
    # All retries fail but a cached plan exists → push it, clearly marked stale, rather than nothing.
    _no_sleep(monkeypatch)
    monkeypatch.setattr(plan_generate, "generate_plan",
                        lambda source="morning": (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(plan_store, "load_plan",
                        lambda: {"woven_frame": "yesterday", "blocks": [], "still_here": []})
    notes = []
    monkeypatch.setattr(mp, "_notify", lambda title, msg: notes.append((title, msg)))
    monkeypatch.setattr(mp, "notify", None)
    pushed = []
    monkeypatch.setattr(mp, "_push_to_phone", lambda plan, stale=False: pushed.append(stale) or True)
    rc = mp.run()
    assert rc == 0
    assert pushed == [True]   # pushed, flagged STALE
    assert "yesterday" in notes[0][0].lower()   # Mac title signals it's the prior plan


# --- the phone push is content-free (June's privacy decision, 2026-07-12) -----
# ntfy.sh is a public relay: the body must NEVER carry plan content (woven frame,
# task names) — only "a plan is ready" + the tap-to-open link. A regression here
# silently leaks June's plan text off-device with nothing else to catch it.

def _capture_push(monkeypatch):
    sent = []
    import urllib.request
    def fake_urlopen(req, timeout=None):
        sent.append({"body": req.data.decode("utf-8"),
                     "title": req.get_header("Title"),
                     "click": req.get_header("Click")})
        class R:  # minimal response object
            pass
        return R()
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mp, "_ntfy_topic", lambda: "test-topic")
    monkeypatch.setattr(mp, "_overlay_url", lambda: "http://example.local:5050")
    return sent

_SENSITIVE_PLAN = {
    "woven_frame": "SECRET-FRAME pay the medical bill before the deadline",
    "blocks": [{"label": "Morning", "time": "9:00",
                "items": [{"time": "9:00", "task": "SECRET-TASK call the lawyer"}]}],
}

def test_push_body_is_content_free(monkeypatch):
    sent = _capture_push(monkeypatch)
    assert mp._push_to_phone(_SENSITIVE_PLAN, stale=False) is True
    body = sent[0]["body"]
    assert "SECRET-FRAME" not in body and "SECRET-TASK" not in body
    assert "pay the medical bill" not in body and "call the lawyer" not in body
    assert sent[0]["click"]  # the tap-to-open link survives

def test_stale_push_body_is_content_free_and_says_stale(monkeypatch):
    sent = _capture_push(monkeypatch)
    assert mp._push_to_phone(_SENSITIVE_PLAN, stale=True) is True
    body = sent[0]["body"]
    assert "SECRET-FRAME" not in body and "SECRET-TASK" not in body
    assert "refresh" in body.lower()  # still honestly labelled as not-fresh
    assert sent[0]["title"] == "Yesterday's plan"
