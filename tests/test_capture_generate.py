"""Tests for capture_generate — the headless weed/capture engine.

The LLM seam and Anytype are always mocked: tests never call a model or touch the live space.
Paths redirect to tmp_path so session_store + generation_log write only to the sandbox.
"""
import sys, os, json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import capture_generate as cg
import session_store
import generation_log


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
    strategies = []
    monkeypatch.setattr(cg, "_load_weed_context",
                        lambda: ("sid", goals, projects, tasks, recurrings, strategies))
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

    # The model's stated reasoning gets written to Context at creation time — it used to be
    # silently dropped (item.get("context") checked a key the JSON contract never emits; the
    # gate only ever produces "reasoning"), so June never saw why something landed where it did
    # once the session receipt aged out (found 2026-07-02).
    assert by_name["Call surgeon"]["Context"] == "concrete next step"

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


# --- dedup notes captured deterministically into the durable learning log ---

def test_dedup_notes_logged_to_durable_learning_log(tmp_path, monkeypatch):
    # The model's dedup judgments (its OWN uncertainty) must land in the append-only learning
    # log automatically — built in Python every weed, not dependent on the LLM logging it.
    _stub(monkeypatch, tmp_path)   # _CANNED skips "SSRC grant" with a dedup_note
    cg.capture("dump")
    recs = [json.loads(l) for l in
            (tmp_path / "generation_log.jsonl").read_text().strip().splitlines()]
    cap = [r for r in recs if r.get("source") == "capture" and r.get("success")]
    assert cap, "no capture record in the durable learning log"
    structural = cap[-1]["structural"]
    assert structural["n_skipped"] == 1 and structural["n_created"] == 2
    notes = structural["dedup_notes"]
    assert any(n["name"] == "SSRC grant" and n["action"] == "skip" for n in notes)


def test_create_with_overlap_note_is_logged(tmp_path, monkeypatch):
    # A create-with-a-possible-overlap (bias: create, don't drop) still records the doubt.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "email the editor", "link": None, "status": "Ready",
             "action": "create", "dedup_note": "maybe overlaps the Haraway email, but different",
             "reasoning": "different action"},
        ]},
    ]})
    _stub(monkeypatch, tmp_path, canned=canned)
    result = cg.capture("email editor")
    assert result["created"][0]["dedup_note"].startswith("maybe overlaps")   # kept on the record
    recs = [json.loads(l) for l in
            (tmp_path / "generation_log.jsonl").read_text().strip().splitlines()]
    notes = [r for r in recs if r.get("source") == "capture"][-1]["structural"]["dedup_notes"]
    assert any(n["action"] == "create" and "overlap" in n["note"] for n in notes)


def test_check_capture_extracts_only_flagged_notes():
    # Unit check on the deterministic extractor: only items carrying a dedup_note appear.
    parsed = {"capacity_read": {"x": 1}, "groups": [
        {"items": [
            {"name": "A", "action": "create", "dedup_note": "overlap?"},
            {"name": "B", "action": "create"},                      # no note → not logged
            {"name": "C", "action": "skip", "dedup_note": "dup"},
        ]},
    ]}
    s = generation_log.check_capture(parsed, created=[1, 2], skipped=[1], failed=[])
    assert s["n_items"] == 3 and s["n_created"] == 2 and s["n_skipped"] == 1
    assert s["capacity_read_present"] is True
    assert {n["name"] for n in s["dedup_notes"]} == {"A", "C"}


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


# --- Task 2: per-item optional fields parse + default ------------------------

def test_parse_weed_reads_optional_fields():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Task","name":"Call surgeon","link":null,"status":"Ready","action":"create",
       "reasoning":"r","duration_min":15,"affect":"been dreading this call",
       "blocked_on":"the referral","access_conditions":["Involves-leaving-house"]}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["duration_min"] == 15
    assert item["affect"] == "been dreading this call"
    assert item["blocked_on"] == "the referral"
    assert item["access_conditions"] == ["Involves-leaving-house"]


def test_parse_weed_optional_fields_default_safely_when_absent():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Task","name":"X","link":null,"status":"Ready","action":"create","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["duration_min"] is None
    assert item["affect"] == ""
    assert item["blocked_on"] == ""
    assert item["access_conditions"] == []
