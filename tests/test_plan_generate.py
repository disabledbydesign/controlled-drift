"""Tests for plan_generate — the headless generation engine.

The LLM seam is always mocked: tests never call `claude` (correctness shouldn't depend on
a model, and it shouldn't spend June's subscription). Anytype loading is mocked too.
"""
import sys, os, datetime as dt
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_generate as pg
import plan_store


_CANNED = """Here is your plan in prose.

### Morning (9:00 AM – 12:00 PM)
- 9:00 – 10:30 AM | Build: do the thing

```json
{
  "woven_frame": "a calm frame",
  "blocks": [
    {"label": "Morning", "time": "9:00 AM – 12:00 PM", "framing": "fresh",
     "items": [{"time": "9:00 – 10:30 AM", "project": "Build", "task": "do the thing", "why": "momentum", "ref": "T1"}]}
  ],
  "still_here": [{"label": "Later thread", "note": "held, not dropped"}]
}
```
"""


# --- the pluggable backend seam --------------------------------------------

def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        pg.generate("prompt", backend="bogus")


def test_local_backend_dispatches(monkeypatch):
    # The seam routes "local" to the MLX path (mocked here so no model loads in tests).
    monkeypatch.setattr(pg, "_generate_local", lambda prompt: "LOCAL:" + prompt)
    assert pg.generate("hi", backend="local") == "LOCAL:hi"


# --- parsing the model output ----------------------------------------------

def test_parse_plan_extracts_json_block():
    plan = pg.parse_plan(_CANNED)
    assert plan["woven_frame"] == "a calm frame"
    assert plan["blocks"][0]["items"][0]["task"] == "do the thing"
    assert plan["still_here"][0]["note"] == "held, not dropped"


def test_parse_plan_no_block_raises():
    # A generation that didn't produce the overlay's data is a failure, surfaced — not
    # a silently empty plan.
    with pytest.raises(RuntimeError):
        pg.parse_plan("just prose, no json block at all")


def test_parse_plan_uses_last_block():
    text = '```json\n{"woven_frame": "first"}\n```\nthen\n```json\n{"woven_frame": "second"}\n```'
    assert pg.parse_plan(text)["woven_frame"] == "second"


def test_parse_plan_malformed_json_raises():
    with pytest.raises(RuntimeError):
        pg.parse_plan("```json\n{not: valid}\n```")


def test_parse_plan_fills_missing_keys():
    plan = pg.parse_plan('```json\n{"woven_frame": "x"}\n```')
    assert plan["blocks"] == [] and plan["still_here"] == []


# --- the silent-drop regression (2026-07-02: phone call, dinner, SF drive) --

def test_ensure_all_tasks_accounted_appends_missing_task():
    """REGRESSION: a task the model placed nowhere (not in blocks, not in still_here) used to
    vanish with no trace — the task was untouched in Anytype but June's plan just didn't show
    it, silently. This asserts the deterministic backstop catches it."""
    tasks = [{"id": "t1", "name": "Task One"}, {"id": "t2", "name": "Call the surgeon"}]
    plan = {"blocks": [{"items": [{"id": "t1", "task": "do the thing"}]}],
            "still_here": []}
    pg._ensure_all_tasks_accounted(plan, tasks)
    labels = {sh["label"] for sh in plan["still_here"]}
    assert "Call the surgeon" in labels          # the dropped task got caught
    assert "Task One" not in labels              # the placed task wasn't duplicated


def test_ensure_all_tasks_accounted_skips_task_already_in_still_here():
    """If the model already named the task in still_here (even under its own label), don't
    add a redundant second entry — only truly-uncovered tasks get force-appended."""
    tasks = [{"id": "t1", "name": "Call the surgeon"}]
    plan = {"blocks": [], "still_here": [{"label": "Call the surgeon", "note": "later today"}]}
    pg._ensure_all_tasks_accounted(plan, tasks)
    assert len(plan["still_here"]) == 1


def test_generate_plan_never_drops_a_task_silently(tmp_path, monkeypatch):
    """End-to-end: _CANNED's plan only places/names one of the two stubbed tasks — after
    generate_plan() runs, both must be accounted for somewhere in the saved plan."""
    _stub_pipeline(monkeypatch, tmp_path)
    saved = pg.generate_plan(source="morning")
    scheduled_ids = {item.get("id") for b in saved.get("blocks", []) for item in b.get("items", [])}
    still_here_labels = {sh.get("label") for sh in saved.get("still_here", [])}
    for t in ({"id": "t1", "name": "Task One"}, {"id": "t2", "name": "Task Two"}):
        assert t["id"] in scheduled_ids or t["name"] in still_here_labels


# --- the data-injection regression (tonight's bug) --------------------------

def test_assemble_prompt_includes_the_real_data():
    """REGRESSION: the bug that made a headless run report 'task data didn't load'.

    Placeholder-replacement silently no-op'd, dropping the context from the prompt.
    This asserts the real data is always present in the assembled prompt.
    """
    sentinel = "SENTINEL_TASK_a1b2c3 — email Donna Haraway"
    start = dt.datetime(2026, 6, 23, 9, 0)
    prompt = pg._assemble_prompt(full_context=sentinel, start_time=start, capacity="okay")
    assert sentinel in prompt          # the data made it in
    assert "okay" in prompt            # capacity made it in
    assert "9:00 AM" in prompt or "09:00" in prompt  # the time made it in


def test_assemble_prompt_includes_negotiation_message():
    prompt = pg._assemble_prompt("ctx", dt.datetime(2026, 6, 23, 9, 0),
                                 extra="please do quick wins first")
    assert "quick wins first" in prompt


# --- generate_plan / negotiate wire the learning logs -----------------------

def _stub_pipeline(monkeypatch, tmp_path):
    """Mock the LLM + Anytype + cache so we can assert the logging wiring."""
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    fake_tasks = [{"id": "t1", "name": "Task One"}, {"id": "t2", "name": "Task Two"}]
    monkeypatch.setattr(pg, "build_context",
                        lambda capacity=None, start_time=None, end_time=None, extra=None, **kw:
                        ("ctx", fake_tasks, dt.datetime(2026, 6, 23, 9, 0), "clock",
                         [], dt.datetime(2026, 6, 23, 18, 0)))
    monkeypatch.setattr(pg, "generate", lambda prompt: _CANNED)
    surfaced, corrections = [], []
    monkeypatch.setattr(pg, "log_surfaced_batch", lambda items, **k: surfaced.append(items))
    monkeypatch.setattr(pg, "log_correction", lambda kind, before, after, **k: corrections.append((kind, before, after)))
    return surfaced, corrections


def test_generate_plan_caches_and_logs_surfaced(tmp_path, monkeypatch):
    surfaced, corrections = _stub_pipeline(monkeypatch, tmp_path)
    saved = pg.generate_plan(source="morning")
    assert saved["source"] == "morning"
    assert plan_store.load_plan()["woven_frame"] == "a calm frame"   # cached
    assert surfaced and len(surfaced[0]) == 2                        # both tasks logged
    assert not corrections                                          # fresh gen ≠ a correction


def test_reorder_logs_correction_with_kind_and_before_after(tmp_path, monkeypatch):
    surfaced, corrections = _stub_pipeline(monkeypatch, tmp_path)
    plan_store.save_plan({"woven_frame": "old"}, source="morning")  # a "before" exists
    pg.reorder("go gentle", kind="preset:quick-wins")
    assert len(corrections) == 1
    kind, before, after = corrections[0]
    assert kind == "preset:quick-wins"
    assert before["woven_frame"] == "old"          # before captured
    assert after["woven_frame"] == "a calm frame"  # after captured
    assert surfaced                                # renegotiated plan also re-surfaces


# --- the zero-ref validity guard (measured live 2026-07-11) -----------------

# A plan whose one item resolves to NO id: unknown ref token + a task name that matches none
# of the stubbed tasks. Structurally broken — every row unactionable.
_CANNED_ZERO_REF = """```json
{
  "woven_frame": "a frame",
  "blocks": [
    {"label": "Morning", "time": "9:00 AM – 12:00 PM", "framing": "x",
     "items": [{"time": "9:00 – 10:30 AM", "project": "Ghost", "task": "an unlisted thing", "why": "?", "ref": "T99"}]}
  ],
  "still_here": []
}
```"""


def _read_gen_log(tmp_path):
    import json
    p = tmp_path / "generation_log.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def test_generate_plan_valid_plan_passes_and_does_not_retry(tmp_path, monkeypatch):
    """A healthy plan (at least one ref resolves) is cached on the first attempt — no retry,
    one success log, no zero_ref_plan event."""
    _stub_pipeline(monkeypatch, tmp_path)
    calls = {"n": 0}
    real_generate = _CANNED
    def once(prompt):
        calls["n"] += 1
        return real_generate
    monkeypatch.setattr(pg, "generate", once)
    saved = pg.generate_plan(source="morning")
    assert saved["woven_frame"] == "a calm frame"
    assert calls["n"] == 1                                   # no retry on a valid plan
    log = _read_gen_log(tmp_path)
    assert any(r["success"] for r in log)
    assert not any(r.get("error_type") == "zero_ref_plan" for r in log)


def test_generate_plan_retries_once_on_zero_ref_then_succeeds(tmp_path, monkeypatch):
    """The intermittent fault: first generation is zero-ref, the retry resolves fine. June still
    gets a real, cached plan; the fragility is logged as one zero_ref_plan event."""
    _stub_pipeline(monkeypatch, tmp_path)
    seq = iter([_CANNED_ZERO_REF, _CANNED])
    monkeypatch.setattr(pg, "generate", lambda prompt: next(seq))
    saved = pg.generate_plan(source="morning")
    assert saved["woven_frame"] == "a calm frame"           # the retry's good plan was cached
    log = _read_gen_log(tmp_path)
    zero = [r for r in log if r.get("error_type") == "zero_ref_plan"]
    assert len(zero) == 1                                    # the first (bad) attempt was logged
    assert any(r["success"] for r in log)                   # the retry succeeded


def test_generate_plan_zero_ref_twice_raises_and_logs(tmp_path, monkeypatch):
    """Both attempts zero-ref → a real failure, raised so the caller's fallback fires (morning
    push serves the stale cache). Two distinct zero_ref_plan events, no success, nothing cached."""
    _stub_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(pg, "generate", lambda prompt: _CANNED_ZERO_REF)
    with pytest.raises(pg.ZeroRefPlanError):
        pg.generate_plan(source="morning")
    log = _read_gen_log(tmp_path)
    assert len([r for r in log if r.get("error_type") == "zero_ref_plan"]) == 2
    assert not any(r["success"] for r in log)               # a dead plan was never logged as success
    assert plan_store.load_plan() is None                    # nothing dead was cached


_CANNED_LIGHT_DAY = """```json
{
  "woven_frame": "a gentle evening",
  "blocks": [
    {"label": "Evening", "time": "8:00 – 9:00 PM", "framing": "wind down",
     "items": [{"time": "8:00 – 8:15 PM", "project": null, "task": "Make tea", "why": null, "ref": null, "interstitial": true}]}
  ],
  "still_here": [{"project": "Job search", "task": "the held thread", "note": "back tomorrow"}]
}
```"""


def test_generate_plan_light_day_all_in_still_here_is_valid(tmp_path, monkeypatch):
    """A plan that schedules NO focused work — blocks hold only interstitials, every gated task
    honestly in still_here — is a legitimate light-day shape (late evening; a gentle low-spoon
    day), NOT a zero-ref failure. Observed live 2026-07-12: the first guard version failed 5/5
    evening regenerations this way; on June's first low-spoon morning it would have spuriously
    served the stale fallback."""
    _stub_pipeline(monkeypatch, tmp_path)
    calls = {"n": 0}
    def once(prompt):
        calls["n"] += 1
        return _CANNED_LIGHT_DAY
    monkeypatch.setattr(pg, "generate", once)
    saved = pg.generate_plan(source="morning")
    assert saved["woven_frame"] == "a gentle evening"        # cached, not failed
    assert calls["n"] == 1                                   # no retry
    log = _read_gen_log(tmp_path)
    assert not any(r.get("error_type") == "zero_ref_plan" for r in log)
    assert any(r["success"] for r in log)


def test_generate_plan_no_gated_tasks_is_valid(tmp_path, monkeypatch):
    """A rest/wind-down plan with an empty gated task set is legitimately zero-ref — the guard
    only fires when there WERE tasks to resolve. Such a plan passes through, no retry."""
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pg, "build_context",
                        lambda capacity=None, start_time=None, end_time=None, extra=None, **kw:
                        ("ctx", [], dt.datetime(2026, 6, 23, 20, 0), "clock",
                         [], dt.datetime(2026, 6, 23, 23, 0)))
    monkeypatch.setattr(pg, "log_surfaced_batch", lambda items, **k: None)
    calls = {"n": 0}
    def once(prompt):
        calls["n"] += 1
        return _CANNED_ZERO_REF
    monkeypatch.setattr(pg, "generate", once)
    saved = pg.generate_plan(source="morning")
    assert calls["n"] == 1                                   # no retry: no tasks means not broken
    assert saved["woven_frame"] == "a frame"


# --- single-source auth: the durable-token wiring --------------------------

def test_claude_env_prefers_existing_env_token(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "from-env")
    (tmp_path / "claude_token").write_text("from-file")
    # An interactive shell already holding the token wins over the file.
    assert pg._claude_env()["CLAUDE_CODE_OAUTH_TOKEN"] == "from-env"


def test_claude_env_reads_token_file_when_env_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    (tmp_path / "claude_token").write_text("  from-file\n")  # whitespace trimmed
    # This is the launchd path: no interactive login, so read the durable token file.
    assert pg._claude_env()["CLAUDE_CODE_OAUTH_TOKEN"] == "from-file"


def test_claude_env_no_token_when_neither(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    # Don't invent a token — let `claude` fall back to its own login.
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in pg._claude_env()


# --- meal-time parsing helper ----------------------------------------------

def test_parse_first_time_basic():
    assert pg._parse_first_time("9:00 – 10:30 AM") == dt.time(9, 0)
    assert pg._parse_first_time("12:30 PM") == dt.time(12, 30)
    assert pg._parse_first_time("12:00 AM") == dt.time(0, 0)
    assert pg._parse_first_time("no time here") is None
