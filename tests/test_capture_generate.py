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


def test_parse_weed_reads_reactivate_action():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Recurring","name":"Clean the fridge","link":null,"action":"reactivate","reactivate_ref":"R2","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["action"] == "reactivate" and item["reactivate_ref"] == "R2"


def test_parse_weed_defaults_reactivate_ref_to_none():
    parsed = cg.parse_weed('```json\n{"groups":[{"items":[{"name":"x"}]}]}\n```')
    assert parsed["groups"][0]["items"][0]["reactivate_ref"] is None


# --- as-needed reactivation candidates in the weed context (Task 5) --------

def test_as_needed_recurrings_filters_by_interval_unit():
    as_needed = {"id": "r1", "name": "Clean the fridge",
                 "properties": [{"key": "interval_unit", "select": {"name": "as_needed"}}]}
    daily = {"id": "r2", "name": "Take meds",
             "properties": [{"key": "interval_unit", "select": {"name": "day"}}]}
    out = cg._as_needed_recurrings([as_needed, daily])
    assert out == [as_needed]


def test_build_as_needed_ref_table_assigns_r_tokens():
    as_needed = [{"id": "rid-fridge", "name": "Clean the fridge"}]
    ref_map, id2name, table = cg._build_as_needed_ref_table(as_needed)
    assert ref_map == {"R1": "rid-fridge"}
    assert id2name == {"rid-fridge": "Clean the fridge"}
    assert "R1" in table and "Clean the fridge" in table


# --- dedup list enrichment (project + Context signal, June 2026-07-16) ------
# Root case: bare names alone weren't enough for the model to recognize a same-subject item
# worded differently — she forgot she'd already added a related task earlier that day, and a
# near-duplicate got created instead of flagged/skipped. Project + Context give real signal.

def test_dedup_list_includes_linked_project():
    task = {"name": "Pay bills to Sutter and LabQuest",
            "properties": [{"key": "linked_projects", "objects": ["p1"]}]}
    out = cg._format_dedup_list([task], [], id2name={"p1": "Medical bills"})
    assert "Pay bills to Sutter and LabQuest" in out
    assert "under Medical bills" in out


def test_dedup_list_includes_context_snippet():
    task = {"name": "Pay bills to Sutter and LabQuest",
            "properties": [{"key": "gsdo_context", "text": "billing dispute over CPT code 99213"}]}
    out = cg._format_dedup_list([task], [], id2name={})
    assert 'context: "billing dispute over CPT code 99213"' in out


def test_dedup_list_bare_name_when_no_project_or_context():
    # Real bare stub shape — no "properties" key at all — must not crash or invent anything.
    task = {"name": "Water the plants"}
    out = cg._format_dedup_list([task], [], id2name={})
    assert out.strip() == "- Water the plants  (Task)"


def test_dedup_list_truncates_long_context_snippet():
    long_ctx = "x" * 150
    task = {"name": "Follow up", "properties": [{"key": "gsdo_context", "text": long_ctx}]}
    out = cg._format_dedup_list([task], [], id2name={})
    assert ("x" * 97 + "...") in out
    assert long_ctx not in out   # the untruncated 150-char version must not appear


def test_dedup_list_recurring_reads_either_project_link_key():
    # Recurring items were observed live with EITHER key (data-entry drift) — both must resolve.
    rec_a = {"name": "Go on a walk",
             "properties": [{"key": "linked_projects", "objects": ["p1"]}]}
    rec_b = {"name": "Do the dishes",
             "properties": [{"key": "gsdo_project_link", "objects": ["p1"]}]}
    out = cg._format_dedup_list([], [rec_a, rec_b], id2name={"p1": "Household"})
    assert out.count("under Household") == 2


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


def test_capture_reactivates_instead_of_creating(tmp_path, monkeypatch):
    # A matched as-needed task activates the EXISTING Recurring — gsdo_objects.create must NOT be
    # called for it, and the receipt shows action:"reactivate" so the surface can render "reopened X".
    recurrings = [{"id": "rid-fridge", "name": "Clean the fridge",
                   "properties": [{"key": "interval_unit", "select": {"name": "as_needed"}},
                                  {"key": "active", "checkbox": False}]}]
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Recurring", "name": "Clean the fridge", "link": None,
             "action": "reactivate", "reactivate_ref": "R1", "reasoning": "asked to pick it back up"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    monkeypatch.setattr(cg, "_load_weed_context",
                        lambda: ("sid", [{"id": "g1", "name": "Material survival"}],
                                 [{"id": "p1", "name": "Build Controlled Drift"}],
                                 [{"id": "t1", "name": "SSRC grant application"}],
                                 recurrings, []))
    activated = {}
    monkeypatch.setattr(cg.recurring_active, "set_recurring_active",
                        lambda rid, active: activated.update({"c": (rid, active)}) or active)
    monkeypatch.setattr(cg, "_get_object", lambda oid: {"name": "Clean the fridge"})

    out = cg.capture("clean the fridge")

    assert activated["c"] == ("rid-fridge", True)
    assert calls == []   # gsdo_objects.create was NOT called — no duplicate
    assert out["failed"] == []
    assert len(out["created"]) == 1
    record = out["created"][0]
    assert record["action"] == "reactivate"
    assert record["id"] == "rid-fridge"
    assert record["name"] == "Clean the fridge"


def test_capture_reactivate_unresolved_ref_fails_without_creating(tmp_path, monkeypatch):
    # A reactivate_ref that doesn't resolve (e.g. the model hallucinated a token) must fail
    # loudly into `failed`, never silently create nor silently drop the item.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Recurring", "name": "Clean the fridge", "link": None,
             "action": "reactivate", "reactivate_ref": "R99", "reasoning": "r"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    activated = {}
    monkeypatch.setattr(cg.recurring_active, "set_recurring_active",
                        lambda rid, active: activated.update({"c": True}))

    out = cg.capture("clean the fridge")

    assert activated == {}                # never called — nothing to activate
    assert calls == []                    # never created either
    assert out["created"] == []
    assert len(out["failed"]) == 1 and out["failed"][0]["name"] == "Clean the fridge"


def test_capture_reactivate_wrong_kind_token_is_dropped_not_applied(tmp_path, monkeypatch):
    # reactivate_ref shares ref_map with the G#/P# link tokens. A wrong-kind token (a hallucinated
    # or copy-pasted G#/P#) must resolve to NOTHING — never silently reactivate a Goal/Project's
    # Active checkbox under a mislabeled "Recurring" receipt. Mirrors
    # test_wrong_kind_link_token_is_dropped_not_applied's guard for `link`.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Recurring", "name": "Clean the fridge", "link": None,
             "action": "reactivate", "reactivate_ref": "G1", "reasoning": "r"},   # G1, not R#
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    activated = {}
    monkeypatch.setattr(cg.recurring_active, "set_recurring_active",
                        lambda rid, active: activated.update({"c": rid}))

    out = cg.capture("clean the fridge")

    assert activated == {}                # G1 (a Goal token) must never reach the primitive
    assert calls == []
    assert out["created"] == []
    assert len(out["failed"]) == 1 and out["failed"][0]["name"] == "Clean the fridge"


def test_capture_writes_estimated_duration_labeled(tmp_path, monkeypatch):
    # June stated no duration; the model estimated one. It lands labeled 'estimated'.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Study Python", "link": "P1", "status": "Ready",
             "duration_min": None, "duration_estimate_min": 90,
             "action": "create", "reasoning": "learning block"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("study python")
    props = {name: p for (_t, name, p) in calls}["Study Python"]
    assert props["Duration min"] == 90
    assert props["Duration source"] == "estimated"


def test_capture_stated_duration_beats_estimate(tmp_path, monkeypatch):
    # June said 20; model also guessed 90. Her number wins and is labeled 'stated'.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Quick email to editor", "link": "P1", "status": "Ready",
             "duration_min": 20, "duration_estimate_min": 90,
             "action": "create", "reasoning": "she said 20"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("quick 20 min email to editor")
    props = {name: p for (_t, name, p) in calls}["Quick email to editor"]
    assert props["Duration min"] == 20
    assert props["Duration source"] == "stated"


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


# --- Task 3: capture writes per-item optional fields ------------------------

def test_capture_affect_scope_single_item(monkeypatch, tmp_path):
    # FIDELITY case (a): June attached the feeling to ONE item — only that item carries it.
    canned = json.dumps({
        "opening": "o",
        "capacity_read": {"text": "generally frazzled", "source": "inferred", "reasoning": "x"},
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Book dentist", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "duration_min": 10,
             "affect": "dreading the call", "blocked_on": "the insurance card",
             "access_conditions": ["Requires-talking-to-a-person"]},
            {"type": "Task", "name": "Sketch the zine cover", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("book the dentist (~10 min, dreading it, need the insurance card first); sketch the zine cover")
    props = {name: p for (typ, name, p) in calls}
    dentist = props["Book dentist"]
    assert dentist["Duration min"] == 10
    assert dentist["Affective"] == "dreading the call"        # the ITEM's affect, verbatim
    assert dentist["Blocked on"] == "the insurance card"
    assert dentist["Access conditions"] == ["Requires-talking-to-a-person"]
    zine = props["Sketch the zine cover"]
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in zine    # she gave this item no signal → nothing written
    # capacity_read is never auto-copied onto objects (objects get affect only via `affect`):
    assert dentist.get("Affective") != "generally frazzled"


def test_capture_affect_scope_whole_dump(monkeypatch, tmp_path):
    # FIDELITY case (b): June stated one feeling about EVERYTHING — the contract has the LLM put
    # it on every item, and every object carries it. Her information, faithfully captured.
    canned = json.dumps({
        "opening": "o",
        "capacity_read": {"text": "dreading all of this", "source": "stated", "reasoning": "x"},
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "File the extension", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "affect": "dreading all of this"},
            {"type": "Task", "name": "Call the landlord", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "affect": "dreading all of this"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("I'm dreading all of this: file the extension, call the landlord")
    props = {name: p for (typ, name, p) in calls}
    assert props["File the extension"]["Affective"] == "dreading all of this"
    assert props["Call the landlord"]["Affective"] == "dreading all of this"


def test_capture_no_signals_writes_no_optional_props(monkeypatch, tmp_path):
    canned = json.dumps({
        "opening": "o", "capacity_read": None,
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Email editor", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("email the editor")
    props = {name: p for (typ, name, p) in calls}["Email editor"]
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in props   # absent stays absent — flat-default behavior preserved


def test_parse_weed_reads_project_engagement_and_notes():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"Leatherworking","link":null,"status":null,"action":"create",
       "reasoning":"r","engagement":"Steady","engagement_notes":"~30 min daily"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Steady" and item["engagement_notes"] == "~30 min daily"


def test_parse_weed_engagement_defaults_open_notes_blank():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"X","link":null,"status":null,"action":"create","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Open" and item["engagement_notes"] == ""


# --- Task A3: capture writes the proposed engagement, retiring hardcoded Steady ----

def test_capture_project_writes_proposed_engagement(monkeypatch, tmp_path):
    canned = json.dumps({"opening":"o","capacity_read":None,"groups":[{"label":"g","through_line":"t","items":[
        {"type":"Project","name":"Leatherworking","link":None,"status":None,"action":"create",
         "reasoning":"r","engagement":"Steady","engagement_notes":"~30 min daily"},
        {"type":"Project","name":"Maybe-someday garden","link":None,"status":None,"action":"create",
         "reasoning":"r"},   # no signal -> parse_weed defaulted engagement to "Open"
    ]}]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("start leatherworking, ~30 min a day; maybe a garden someday")
    props = {name: p for (typ, name, p) in calls}
    assert props["Leatherworking"]["Engagement"] == "Steady"
    assert props["Leatherworking"]["Engagement notes"] == "~30 min daily"
    assert props["Maybe-someday garden"]["Engagement"] == "Open"   # NOT the old hardcoded Steady
    assert "Engagement notes" not in props["Maybe-someday garden"]
