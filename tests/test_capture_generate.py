"""Tests for capture_generate — the headless weed/capture engine.

The LLM seam and Anytype are always mocked: tests never call a model or touch the live space.
Paths redirect to tmp_path so session_store + generation_log write only to the sandbox.
"""
import sys, os, json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import capture_generate as cg
import session_store


_CANNED = json.dumps({
    "opening": "one thread: survival logistics",
    "capacity_read": {"text": "a bit stressed", "source": "inferred", "reasoning": "urgency words"},
    "groups": [
        {"label": "Survival", "through_line": "money + health", "items": [
            {"type": "Task", "name": "Call surgeon", "link": "P1", "status": "Ready",
             "action": "create", "reasoning": "concrete next step"},
            {"type": "Task", "name": "SSRC grant", "link": "P1", "status": "Ready",
             "action": "skip", "dedup_note": "already exists", "reasoning": "dupe"},
        ]},
        {"label": "Practice", "through_line": "habit", "items": [
            {"type": "Recurring", "name": "Meditate", "link": "P1", "status": None,
             "action": "create", "reasoning": "routine"},
        ]},
    ],
})


def _stub(monkeypatch, tmp_path, canned=_CANNED, getobj=None):
    """Mock env + Anytype + LLM. Returns the list of (type, name, props) create calls."""
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    goals = [{"id": "g1", "name": "Material survival"}]
    projects = [{"id": "p1", "name": "Build Controlled Drift"}]
    tasks = [{"id": "t1", "name": "SSRC grant application"}]
    recurrings = []
    monkeypatch.setattr(cg, "_load_weed_context",
                        lambda: ("sid", goals, projects, tasks, recurrings))
    # The real LLM emits a fenced ```json block; the mock mirrors that.
    monkeypatch.setattr(cg.plan_generate, "generate",
                        lambda prompt: "```json\n" + canned + "\n```")

    calls = []

    def fake_create(type_name, name, body=None, properties=None):
        calls.append((type_name, name, properties or {}))
        return f"id-{name}"
    monkeypatch.setattr(cg.gsdo_objects, "create", fake_create)

    def default_get(oid):
        return {"name": oid[len("id-"):]}   # name matches what was created
    monkeypatch.setattr(cg, "_get_object", getobj or default_get)
    return calls


# --- parsing ----------------------------------------------------------------

def test_parse_weed_extracts_block():
    parsed = cg.parse_weed("prose\n```json\n" + _CANNED + "\n```\n")
    assert parsed["opening"].startswith("one thread")
    assert len(parsed["groups"]) == 2


def test_parse_weed_no_block_raises():
    with pytest.raises(RuntimeError):
        cg.parse_weed("no json here")


def test_parse_weed_malformed_raises():
    with pytest.raises(RuntimeError):
        cg.parse_weed("```json\n{not valid}\n```")


def test_parse_weed_fills_defaults():
    parsed = cg.parse_weed('```json\n{"opening": "x"}\n```')
    assert parsed["groups"] == [] and parsed["capacity_read"] is None


# --- the happy path ---------------------------------------------------------

def test_capture_creates_links_and_skips(tmp_path, monkeypatch):
    calls = _stub(monkeypatch, tmp_path)
    result = cg.capture("call surgeon, ssrc, meditate daily")

    names = {c["name"] for c in result["created"]}
    assert names == {"Call surgeon", "Meditate"}
    assert [s["name"] for s in result["skipped"]] == ["SSRC grant"]
    assert result["failed"] == []

    # Task linked via Linked Projects, Recurring via Project link — both to p1.
    by_name = {name: props for (_t, name, props) in calls}
    assert by_name["Call surgeon"]["Task status"] == "Ready"
    assert by_name["Call surgeon"]["Linked Projects"] == ["p1"]
    assert by_name["Meditate"]["Project link"] == ["p1"]

    # The created record carries the resolved project NAME + the reasoning (guard #6).
    surgeon = next(c for c in result["created"] if c["name"] == "Call surgeon")
    assert surgeon["project"] == "Build Controlled Drift"
    assert surgeon["alignment_reasoning"] == "concrete next step"


def test_wrong_kind_link_token_is_dropped_not_applied(tmp_path, monkeypatch):
    # A Task whose link points at a GOAL token (G1) must NOT be linked (Tasks link to Projects).
    # Better an unlinked task — honest "might need a project" signal — than a corrupt link.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "HDMI cable", "link": "G1", "status": "Ready",
             "action": "create", "reasoning": "no project fit, reached for a goal"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    result = cg.capture("buy hdmi")
    props = calls[0][2]
    assert "Linked Projects" not in props          # the wrong-kind link was dropped
    assert result["created"][0]["project"] is None  # surfaced honestly as unlinked


def test_capture_writes_session_entry(tmp_path, monkeypatch):
    _stub(monkeypatch, tmp_path)
    cg.capture("a dump")
    recent = session_store.recent_entries("capture")
    assert len(recent) == 1
    entry = recent[0]
    assert entry["raw_input"] == "a dump"
    assert entry["capacity_read"]["source"] == "inferred"
    assert len(entry["created"]) == 2          # what landed is in the log


def test_capture_empty_text_raises(tmp_path, monkeypatch):
    _stub(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        cg.capture("   ")


# --- robustness: one bad item never aborts the batch ------------------------

def test_unknown_type_is_logged_and_skipped_not_fatal(tmp_path, monkeypatch):
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Frobnicate", "name": "weird thing", "action": "create", "reasoning": "?"},
            {"type": "Task", "name": "good task", "link": None, "status": "Ready",
             "action": "create", "reasoning": "ok"},
        ]},
    ]})
    _stub(monkeypatch, tmp_path, canned=canned)
    result = cg.capture("stuff")
    assert [c["name"] for c in result["created"]] == ["good task"]   # the good one still lands
    assert result["failed"][0]["name"] == "weird thing"
    assert any(f["kind"] == "unknown_type" for f in session_store.failures("capture"))


def test_readback_mismatch_fails_item_logs_continues(tmp_path, monkeypatch):
    def bad_get(oid):
        if "Call surgeon" in oid:
            return {"name": "WRONG NAME"}        # didn't persist as expected
        return {"name": oid[len("id-"):]}
    _stub(monkeypatch, tmp_path, getobj=bad_get)
    result = cg.capture("dump")
    assert "Call surgeon" in [f["name"] for f in result["failed"]]
    assert "Meditate" in [c["name"] for c in result["created"]]      # batch continued
    assert any(f["kind"] == "create_failed" for f in session_store.failures("capture"))


# --- never silent: generation + size failures -------------------------------

def test_generation_failure_logs_and_raises(tmp_path, monkeypatch):
    _stub(monkeypatch, tmp_path)
    monkeypatch.setattr(cg.plan_generate, "generate",
                        lambda prompt: (_ for _ in ()).throw(RuntimeError("backend down")))
    with pytest.raises(RuntimeError):
        cg.capture("dump")
    fails = session_store.failures("capture")
    assert any(f["kind"] == "generation_failed" for f in fails)


def test_oversize_prompt_logged_not_silent(tmp_path, monkeypatch):
    _stub(monkeypatch, tmp_path)
    monkeypatch.setattr(cg, "PROMPT_TOKEN_WARN", 0)   # force the size guard to trip
    cg.capture("dump")
    assert any(f["kind"] == "prompt_large" for f in session_store.failures("capture"))


# --- follow-up context: history is assembled into the prompt ----------------

def test_history_feeds_followup_prompt(tmp_path, monkeypatch):
    _stub(monkeypatch, tmp_path)
    cg.capture("first turn: call surgeon")            # lands a capture entry
    captured = {}

    def capturing_generate(prompt):
        captured["prompt"] = prompt
        return "```json\n" + _CANNED + "\n```"
    monkeypatch.setattr(cg.plan_generate, "generate", capturing_generate)
    cg.capture("actually link that to job search")
    # The earlier turn's raw input is in the second prompt, so a follow-up resolves against it.
    assert "first turn: call surgeon" in captured["prompt"]
