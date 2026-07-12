"""Tests for the monthly status checker — the thing that keeps the work-stream map honest.

Anytype + the LLM are always mocked; git evidence tests build a throwaway real git repo
in tmp_path (stdlib subprocess — the same binary the checker shells out to). The conftest
sandbox + tripwire guarantee no test ever touches June's real space or data files.
"""
import sys, os, json, subprocess, datetime as dt
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import status_check as sc


# --- helpers -----------------------------------------------------------------

def _stream(id="s1", name="Stream one", engagement=None, tasks=(), last_surfaced=None):
    return {"id": id, "name": name, "engagement": engagement, "context": None,
            "last_surfaced": last_surfaced, "tasks": list(tasks)}

def _task(id="t1", name="a step", done=False, status=None):
    return {"id": id, "name": name,
            "status": status or ("Done" if done else "Ready"),
            "done": done, "order": None, "linked_ids": []}

NOW = dt.datetime(2026, 7, 11, 12, 0)


# --- build_findings: the deterministic mismatch detectors ---------------------

def test_done_stream_with_open_tasks_is_flagged():
    s = _stream(engagement="Done", tasks=[_task(done=True), _task(id="t2", done=False)])
    f = sc.build_findings([s], now=NOW)
    assert len(f) == 1
    assert "done_with_open_tasks" in f[0]["kinds"]
    assert f[0]["open_task_count"] == 1

def test_parked_tasks_dont_count_against_done():
    """June's rule (2026-07-12): Parked = deferred-by-design backlog, not unfinished
    work — a Done stream carrying only Parked open tasks is honest, not a mismatch."""
    s = _stream(engagement="Done",
                tasks=[_task(done=True), _task(id="t2", status="Parked")])
    assert sc.build_findings([s], now=NOW) == []

def test_unparked_open_task_still_counts_against_done():
    s = _stream(engagement="Done",
                tasks=[_task(id="t1", status="Parked"), _task(id="t2", status="Ready")])
    f = sc.build_findings([s], now=NOW)
    assert f and "done_with_open_tasks" in f[0]["kinds"]

def test_active_stream_with_all_tasks_done_is_found():
    s = _stream(engagement="Steady", tasks=[_task(done=True), _task(id="t2", done=True)],
                last_surfaced=NOW)  # fresh, so no stale finding muddies the assert
    f = sc.build_findings([s], now=NOW)
    assert f and f[0]["kinds"] == ["active_all_tasks_done"]

def test_active_stream_with_no_tasks_is_found():
    s = _stream(engagement="Sprint", tasks=[], last_surfaced=NOW)
    f = sc.build_findings([s], now=NOW)
    assert f and "no_tasks" in f[0]["kinds"]

def test_stale_active_stream_is_found():
    old = NOW - dt.timedelta(days=sc.STALE_DAYS + 5)
    s = _stream(engagement="Steady", tasks=[_task(done=False)], last_surfaced=old)
    f = sc.build_findings([s], now=NOW)
    assert f and "stale" in f[0]["kinds"]

def test_never_surfaced_is_no_surfacing_history_not_stale():
    """REVISED 2026-07-12: absence of any surfacing data is NOT staleness. A stream whose
    tasks never appeared in a plan (and has no Anytype fallback date) gets the distinct
    'no_surfacing_history' kind — the first-run mass case that the aggregate note absorbs,
    NOT N individual stale flags."""
    s = _stream(engagement="Steady", tasks=[_task(done=False)], last_surfaced=None)
    f = sc.build_findings([s], now=NOW)
    assert f and "no_surfacing_history" in f[0]["kinds"]
    assert "stale" not in f[0]["kinds"]

def test_backburner_is_never_stale_or_no_tasks():
    """Backburner says 'later' honestly — silence there is not a mismatch (and nagging
    a deliberately-parked stream is exactly the scold the design forbids)."""
    s = _stream(engagement="Backburner", tasks=[], last_surfaced=None)
    assert sc.build_findings([s], now=NOW) == []

def test_healthy_stream_yields_no_findings():
    s = _stream(engagement="Steady", tasks=[_task(done=False)], last_surfaced=NOW)
    assert sc.build_findings([s], now=NOW) == []

def test_done_stream_with_all_done_tasks_yields_no_findings():
    s = _stream(engagement="Done", tasks=[_task(done=True)])
    assert sc.build_findings([s], now=NOW) == []


# --- the surface-log join: the LIVE staleness source (REVISED 2026-07-12) -------

def test_surface_log_dates_takes_most_recent_per_task(tmp_path):
    """The append-only surface log is the current staleness source (Anytype 'Last surfaced'
    is dead on the live path). One task id, surfaced twice — the map keeps the newer ts."""
    p = tmp_path / "surface_log.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [
        {"ts": "2026-06-01T09:00:00", "id": "tA", "name": "x", "type": "task"},
        {"ts": "2026-07-01T09:00:00", "id": "tA", "name": "x", "type": "task"},
        {"ts": "2026-06-15T09:00:00", "id": "tB", "name": "y", "type": "task"},
        "garbage not json",
    ]) + "\n")
    m = sc._surface_log_dates(path=str(p))
    assert m["tA"] == dt.datetime(2026, 7, 1, 9, 0)
    assert m["tB"] == dt.datetime(2026, 6, 15, 9, 0)

def test_surface_log_dates_missing_file_is_empty(tmp_path):
    assert sc._surface_log_dates(path=str(tmp_path / "nope.jsonl")) == {}

def test_effective_last_surfaced_prefers_log_over_anytype():
    surface = {"t1": dt.datetime(2026, 7, 5, 8, 0)}
    tasks = [_task(id="t1")]
    ls, source = sc._effective_last_surfaced(tasks, surface, anytype_ls=dt.datetime(2026, 6, 1))
    assert ls == dt.datetime(2026, 7, 5, 8, 0) and source == "log"

def test_effective_last_surfaced_falls_back_to_anytype():
    tasks = [_task(id="t1")]
    anytype = dt.datetime(2026, 6, 1)
    ls, source = sc._effective_last_surfaced(tasks, {}, anytype_ls=anytype)
    assert ls == anytype and source == "anytype"

def test_effective_last_surfaced_none_when_no_data():
    ls, source = sc._effective_last_surfaced([_task(id="t1")], {}, anytype_ls=None)
    assert ls is None and source is None


# --- git evidence --------------------------------------------------------------

@pytest.fixture
def tiny_repo(tmp_path):
    """A real one-commit git repo, so commit_exists checks the same thing the checker will."""
    d = tmp_path / "repo"
    d.mkdir()
    def git(*args):
        subprocess.run(["git", "-C", str(d)] + list(args), check=True,
                       capture_output=True, text=True,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    git("init")
    (d / "f.txt").write_text("x")
    git("add", "f.txt")
    git("commit", "-m", "feat: the demonstrable work")
    sha = subprocess.run(["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return str(d), sha

def test_gather_git_evidence_includes_recent_commit(tiny_repo):
    d, sha = tiny_repo
    log = sc.gather_git_evidence(d)
    assert sha in log and "the demonstrable work" in log

def test_commit_exists_true_for_real_and_false_for_fake(tiny_repo):
    d, sha = tiny_repo
    assert sc.commit_exists(d, sha) is True
    assert sc.commit_exists(d, "deadbeef") is False

def test_commit_exists_rejects_non_hash_refs(tiny_repo):
    """Only hex hashes are verifiable citations — 'HEAD', 'main', or shell junk are not
    evidence and must never reach the git subprocess."""
    d, _ = tiny_repo
    assert sc.commit_exists(d, "HEAD") is False
    assert sc.commit_exists(d, "main; rm -rf /") is False
    assert sc.commit_exists(d, None) is False

def test_gather_git_evidence_raises_on_non_repo(tmp_path):
    with pytest.raises(RuntimeError):
        sc.gather_git_evidence(str(tmp_path / "nope"))


# --- the dossier + verdict parsing ---------------------------------------------

GOOD_VERDICT = {
    "stream_id": "s1", "stream_name": "Stream one", "verdict": "auto_fix",
    "proposed_change": {"kind": "mark_stream_done", "target_id": "s1"},
    "evidence": [{"kind": "commit", "ref": "abc1234", "note": "the feature, wired in"}],
    "reasoning": "code merged and tests green; all recorded steps Done",
}

def test_parse_verdicts_reads_fenced_json():
    text = "thinking...\n```json\n" + json.dumps([GOOD_VERDICT]) + "\n```\n"
    verdicts, malformed = sc._parse_verdicts(text)
    assert verdicts == [GOOD_VERDICT] and malformed == []

def test_parse_verdicts_isolates_malformed_elements():
    bad = {"verdict": "auto_fix"}  # no stream_id
    text = "```json\n" + json.dumps([GOOD_VERDICT, bad, "junk"]) + "\n```"
    verdicts, malformed = sc._parse_verdicts(text)
    assert verdicts == [GOOD_VERDICT]
    assert len(malformed) == 2

def test_parse_verdicts_rejects_unknown_verdict_values():
    v = dict(GOOD_VERDICT, verdict="obliterate")
    text = "```json\n" + json.dumps([v]) + "\n```"
    verdicts, malformed = sc._parse_verdicts(text)
    assert verdicts == [] and len(malformed) == 1

def test_parse_verdicts_raises_without_json_block():
    with pytest.raises(RuntimeError):
        sc._parse_verdicts("no fence here")

def test_assemble_prompt_carries_streams_findings_git_and_rules():
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    f = sc.build_findings([s], now=NOW)
    prompt = sc._assemble_prompt("Build Controlled Drift", [s], f,
                                 "abc1234 2026-07-01 feat: x", "MAP TEXT")
    assert "abc1234" in prompt and "MAP TEXT" in prompt
    assert "Stream one" in prompt and "active_all_tasks_done" in prompt
    # the safety line travels in the prompt too (defense in depth; code gate is authoritative)
    assert "positive evidence" in prompt

def test_generate_verdicts_retries_once_then_succeeds(monkeypatch):
    calls = []
    def fake_generate(prompt, backend=None):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient")
        return "```json\n" + json.dumps([GOOD_VERDICT]) + "\n```"
    monkeypatch.setattr(sc.plan_generate, "generate", fake_generate)
    verdicts, malformed = sc._generate_verdicts("p")
    assert len(calls) == 2 and verdicts == [GOOD_VERDICT]

def test_generate_verdicts_raises_after_all_attempts(monkeypatch):
    def always_fail(prompt, backend=None):
        raise RuntimeError("down")
    monkeypatch.setattr(sc.plan_generate, "generate", always_fail)
    with pytest.raises(RuntimeError):
        sc._generate_verdicts("p")


# --- the gate: the safety line, in code ------------------------------------------

def _streams_by_id(*streams):
    return {s["id"]: s for s in streams}

def _autofix(stream_id="s1", kind="mark_stream_done", target="s1", evid=None):
    return {"stream_id": stream_id, "stream_name": "Stream one", "verdict": "auto_fix",
            "proposed_change": {"kind": kind, "target_id": target},
            "evidence": evid if evid is not None else
                        [{"kind": "commit", "ref": "REALSHA", "note": "done in code"}],
            "reasoning": "r"}

@pytest.fixture
def gated_repo(tiny_repo):
    """tiny_repo + a helper that swaps the placeholder REALSHA for the repo's real hash."""
    d, sha = tiny_repo
    def fix(v):
        for e in v.get("evidence", []):
            if e.get("ref") == "REALSHA":
                e["ref"] = sha
        return v
    return d, sha, fix

def test_gate_passes_verified_stream_close(gated_repo):
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    out = sc.gate_verdicts([fix(_autofix())], _streams_by_id(s), d)
    assert len(out["auto_fix"]) == 1 and out["downgraded"] == []

def test_gate_downgrades_autofix_without_commit_evidence(gated_repo):
    d, _, _ = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    v = _autofix(evid=[{"kind": "map", "ref": "s1", "note": "looks done"}])
    out = sc.gate_verdicts([v], _streams_by_id(s), d)
    assert out["auto_fix"] == []
    assert len(out["downgraded"]) == 1
    assert "positive evidence" in out["downgraded"][0]["downgrade_reason"]
    assert out["downgraded"][0] in out["flag"]   # a downgrade becomes a June flag

def test_gate_downgrades_unverifiable_commit_citation(gated_repo):
    d, _, _ = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    v = _autofix(evid=[{"kind": "commit", "ref": "deadbeef", "note": "invented"}])
    out = sc.gate_verdicts([v], _streams_by_id(s), d)
    assert out["auto_fix"] == [] and len(out["downgraded"]) == 1

def test_gate_downgrades_stream_close_with_open_tasks(gated_repo):
    """Open tasks = the work is NOT demonstrably complete, whatever the model says."""
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True), _task(id="t2", done=False)])
    out = sc.gate_verdicts([fix(_autofix())], _streams_by_id(s), d)
    assert out["auto_fix"] == [] and "open task" in out["downgraded"][0]["downgrade_reason"]

def test_gate_allows_stream_close_when_only_parked_remain(gated_repo):
    """Parked backlog doesn't block a demonstrably-complete close (June's 2026-07-12 rule)."""
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady",
                tasks=[_task(done=True), _task(id="t2", status="Parked")])
    out = sc.gate_verdicts([fix(_autofix())], _streams_by_id(s), d)
    assert len(out["auto_fix"]) == 1 and out["downgraded"] == []

def test_gate_downgrades_disallowed_change_kinds(gated_repo):
    """Reopening / demoting are never autonomous — even a 'positive-evidence' reopen
    is judgment about what June wants, not fact."""
    d, sha, fix = gated_repo
    s = _stream(engagement="Done", tasks=[_task(done=False)])
    v = fix(_autofix(kind="reopen_stream"))
    out = sc.gate_verdicts([v], _streams_by_id(s), d)
    assert out["auto_fix"] == [] and len(out["downgraded"]) == 1

def test_gate_downgrades_unknown_stream_and_mismatched_target(gated_repo):
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    ghost = fix(_autofix(stream_id="nope"))
    wrong_target = fix(_autofix(target="other-id"))
    out = sc.gate_verdicts([ghost, wrong_target], _streams_by_id(s), d)
    assert out["auto_fix"] == [] and len(out["downgraded"]) == 2

def test_gate_passes_flags_and_confirmed_through(gated_repo):
    d, _, _ = gated_repo
    s = _stream()
    flag = {"stream_id": "s1", "stream_name": "Stream one", "verdict": "flag",
            "proposed_change": None, "evidence": [], "reasoning": "stale, can't confirm"}
    ok = {"stream_id": "s1", "stream_name": "Stream one", "verdict": "confirmed",
          "proposed_change": None, "evidence": [], "reasoning": "matches"}
    out = sc.gate_verdicts([flag, ok], _streams_by_id(s), d)
    assert len(out["flag"]) == 1 and len(out["confirmed"]) == 1 and out["auto_fix"] == []


# --- apply: gated writes through the read-back-proven mutations -------------------

def test_apply_marks_stream_done_via_task_actions(monkeypatch, gated_repo):
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady", tasks=[_task(done=True)])
    closed = []
    monkeypatch.setattr(sc.task_actions, "complete_stream",
                        lambda sid: closed.append(sid) or
                        {"id": sid, "name": "Stream one", "engagement": "Done", "done": True})
    results = sc.apply_auto_fixes([fix(_autofix())], _streams_by_id(s))
    assert closed == ["s1"]
    assert results[0]["outcome"] == "applied" and results[0]["read_back"]["done"] is True

def test_apply_is_idempotent_on_already_done_stream(monkeypatch, gated_repo):
    d, sha, fix = gated_repo
    s = _stream(engagement="Done", tasks=[_task(done=True)])
    monkeypatch.setattr(sc.task_actions, "complete_stream",
                        lambda sid: pytest.fail("must not write an already-Done stream"))
    results = sc.apply_auto_fixes([fix(_autofix())], _streams_by_id(s))
    assert results[0]["outcome"] == "noop-already-done"

def test_apply_task_close_and_idempotency(monkeypatch, gated_repo):
    d, sha, fix = gated_repo
    s = _stream(engagement="Steady",
                tasks=[_task(id="t1", done=False), _task(id="t2", done=True)])
    closed = []
    monkeypatch.setattr(sc.task_actions, "complete_task",
                        lambda tid: closed.append(tid) or
                        {"id": tid, "name": "a step", "status": "Done", "done": True})
    v1 = fix(_autofix(kind="mark_task_done", target="t1"))
    v2 = fix(_autofix(kind="mark_task_done", target="t2"))   # already done -> noop
    results = sc.apply_auto_fixes([v1, v2], _streams_by_id(s))
    assert closed == ["t1"]
    assert [r["outcome"] for r in results] == ["applied", "noop-already-done"]

def test_apply_records_failure_and_continues(monkeypatch, gated_repo):
    """One failed write never aborts the rest — logged, surfaced, moved past."""
    d, sha, fix = gated_repo
    s1 = _stream(id="s1", engagement="Steady", tasks=[_task(done=True)])
    s2 = _stream(id="s2", name="Stream two", engagement="Steady", tasks=[_task(id="t9", done=True)])
    def boom_then_ok(sid):
        if sid == "s1":
            raise RuntimeError("anytype hiccup")
        return {"id": sid, "name": "Stream two", "engagement": "Done", "done": True}
    monkeypatch.setattr(sc.task_actions, "complete_stream", boom_then_ok)
    results = sc.apply_auto_fixes(
        [fix(_autofix()), fix(_autofix(stream_id="s2", target="s2"))],
        _streams_by_id(s1, s2))
    assert results[0]["outcome"] == "failed" and "anytype hiccup" in results[0]["error"]
    assert results[1]["outcome"] == "applied"


# --- flags: the "system notices, you confirm" half ---------------------------------

import signal_log

def _flag_verdict(stream_id="s1", name="Stream one", reason="stale, can't confirm"):
    return {"stream_id": stream_id, "stream_name": name, "verdict": "flag",
            "proposed_change": None, "evidence": [], "reasoning": reason}

def _findings_for(stream_id="s1", kinds=("stale",)):
    return [{"stream_id": stream_id, "stream_name": "Stream one", "engagement": "Steady",
             "kinds": list(kinds), "open_task_count": 1, "done_task_count": 0}]

def test_record_flags_creates_pending_flag_with_plain_june_line(tmp_path):
    p = str(tmp_path / "flags.json")
    new = sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    assert len(new) == 1
    flag = sc.pending_flags(path=p)[0]
    assert flag["status"] == "pending" and flag["stream_id"] == "s1"
    assert "Stream one" in flag["june_line"]
    # June-facing register: plain words, a question, no scold, no jargon
    assert "?" in flag["june_line"]
    for banned in ("stale", "verdict", "auto", "evidence"):
        assert banned not in flag["june_line"].lower()
    # agent detail is stored, not surfaced
    assert flag["agent_detail"]["reasoning"] == "stale, can't confirm"

def test_record_flags_never_renag_a_pending_stream(tmp_path):
    p = str(tmp_path / "flags.json")
    sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    again = sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    assert again == []                       # surface once, then defer — never re-nag
    assert len(sc.pending_flags(path=p)) == 1

def test_june_line_templates_cover_every_finding_kind_plus_default():
    for kind in sc.FINDING_KINDS:
        line = sc._june_line([kind], "Stream one", open_count=2)
        assert "Stream one" in line and "{" not in line
    assert "Stream one" in sc._june_line(["something_new"], "Stream one", open_count=0)

def test_resolve_flag_logs_junes_words_and_applies_confirmed_close(tmp_path, monkeypatch):
    p = str(tmp_path / "flags.json")
    sig = str(tmp_path / "signals.jsonl")
    closed = []
    monkeypatch.setattr(sc.task_actions, "complete_stream",
                        lambda sid: closed.append(sid) or
                        {"id": sid, "name": "Stream one", "engagement": "Done", "done": True})
    sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    fid = sc.pending_flags(path=p)[0]["id"]
    flag = sc.resolve_flag(fid, "yes that one is finished, close it",
                           action="mark_stream_done", path=p, signal_path=sig)
    assert closed == ["s1"] and flag["status"] == "resolved"
    assert sc.pending_flags(path=p) == []
    recs = signal_log.read_signals(path=sig)
    assert recs and recs[0]["source"] == "checkin_reply"
    assert recs[0]["raw"] == "yes that one is finished, close it"
    assert recs[0]["reference"]["stream_id"] == "s1"

def test_resolve_flag_leave_records_reply_and_changes_nothing(tmp_path, monkeypatch):
    p = str(tmp_path / "flags.json")
    sig = str(tmp_path / "signals.jsonl")
    monkeypatch.setattr(sc.task_actions, "complete_stream",
                        lambda sid: pytest.fail("'leave' must never write"))
    sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    fid = sc.pending_flags(path=p)[0]["id"]
    flag = sc.resolve_flag(fid, "no — still working on it", action="leave",
                           path=p, signal_path=sig)
    assert flag["status"] == "resolved" and flag["resolution"]["action"] == "leave"
    assert signal_log.read_signals(path=sig)[0]["raw"] == "no — still working on it"

def test_resolve_flag_raises_on_unknown_id_or_action(tmp_path):
    p = str(tmp_path / "flags.json")
    sc.record_flags([_flag_verdict()], _findings_for(), path=p)
    fid = sc.pending_flags(path=p)[0]["id"]
    with pytest.raises(RuntimeError):
        sc.resolve_flag("no-such-flag", "x", path=p)
    with pytest.raises(ValueError):
        sc.resolve_flag(fid, "x", action="obliterate", path=p)


# --- the aggregate 'no surfacing history' note (REVISED 2026-07-12) -----------------

def test_record_no_surfacing_flag_makes_one_aggregate_flag(tmp_path):
    p = str(tmp_path / "flags.json")
    flag = sc.record_no_surfacing_flag(7, ["A", "B", "C"], path=p)
    assert flag is not None
    pend = sc.pending_flags(path=p)
    assert len(pend) == 1                     # ONE note, not seven
    assert "7" in pend[0]["june_line"] and "?" in pend[0]["june_line"]
    for banned in ("stale", "verdict", "auto"):
        assert banned not in pend[0]["june_line"].lower()

def test_record_no_surfacing_flag_never_renags(tmp_path):
    p = str(tmp_path / "flags.json")
    sc.record_no_surfacing_flag(7, ["A"], path=p)
    again = sc.record_no_surfacing_flag(9, ["A", "B"], path=p)
    assert again is None                      # already pending -> surface once
    assert len(sc.pending_flags(path=p)) == 1

def test_record_no_surfacing_flag_noop_on_zero(tmp_path):
    p = str(tmp_path / "flags.json")
    assert sc.record_no_surfacing_flag(0, [], path=p) is None
    assert sc.pending_flags(path=p) == []


# --- the run log --------------------------------------------------------------------

def test_log_run_appends_and_reads_back(tmp_path):
    p = str(tmp_path / "runlog.jsonl")
    sc.log_run({"event": "run", "auto_fixed": 1}, path=p)
    sc.log_run({"event": "run", "auto_fixed": 0}, path=p)
    recs = sc.read_run_log(path=p)
    assert len(recs) == 2 and recs[0]["auto_fixed"] == 1 and all("ts" in r for r in recs)


# --- orchestration ------------------------------------------------------------------

@pytest.fixture
def wired(monkeypatch, tiny_repo, cd_sandbox):
    """run_check with every live seam mocked: streams from a fixture, LLM canned,
    mutations recorded, notifications suppressed. cd_sandbox gives each run test a
    pristine flag/stamp store (the checker writes to the default paths, so without
    per-test isolation the run tests would leak flags into each other)."""
    d, sha = tiny_repo
    streams = [
        _stream(id="s1", name="Finished in code", engagement="Steady",
                tasks=[_task(id="t1", done=True)], last_surfaced=NOW),
        _stream(id="s2", name="Gone quiet", engagement="Steady",
                tasks=[_task(id="t2", done=False)],
                last_surfaced=NOW - dt.timedelta(days=99)),
    ]
    verdicts = [
        {"stream_id": "s1", "stream_name": "Finished in code", "verdict": "auto_fix",
         "proposed_change": {"kind": "mark_stream_done", "target_id": "s1"},
         "evidence": [{"kind": "commit", "ref": sha, "note": "shipped"}], "reasoning": "r"},
        {"stream_id": "s2", "stream_name": "Gone quiet", "verdict": "flag",
         "proposed_change": None, "evidence": [], "reasoning": "no activity found"},
    ]
    closed = []
    monkeypatch.setattr(sc, "load_streams", lambda name: streams)
    monkeypatch.setattr(sc, "_now_for_findings", lambda: NOW)
    monkeypatch.setattr(sc.orient_map, "render_map", lambda name: "MAP")
    monkeypatch.setattr(sc.plan_generate, "generate",
                        lambda p, backend=None: "```json\n" + json.dumps(verdicts) + "\n```")
    monkeypatch.setattr(sc.task_actions, "complete_stream",
                        lambda sid: closed.append(sid) or
                        {"id": sid, "name": "Finished in code", "engagement": "Done",
                         "done": True})
    monkeypatch.setattr(sc, "_notify_new_flags", lambda n: None)
    return d, closed, streams

def test_dry_run_computes_findings_no_llm_no_writes(wired, monkeypatch):
    d, closed, _ = wired
    monkeypatch.setattr(sc.plan_generate, "generate",
                        lambda *a, **k: pytest.fail("dry-run must not call the LLM"))
    report = sc.run_check(repo_dir=d, project="P", mode="dry-run")
    assert report["tally"]["findings"] == 2 and closed == []
    assert sc.pending_flags() == [] and sc.read_last_run() is None

def test_preview_calls_llm_but_writes_nothing(wired):
    d, closed, _ = wired
    report = sc.run_check(repo_dir=d, project="P", mode="preview")
    assert report["tally"]["auto_fixed"] == 0        # counted as would-fix, not applied
    assert report["results"][0]["gated"]["auto_fix"] # the verdict IS visible for review
    assert closed == [] and sc.pending_flags() == [] and sc.read_last_run() is None

def test_run_applies_gated_fix_flags_the_rest_and_stamps(wired):
    d, closed, _ = wired
    report = sc.run_check(repo_dir=d, project="P", mode="run")
    assert closed == ["s1"]                               # the positive-evidence close
    assert report["tally"]["auto_fixed"] == 1
    flags = sc.pending_flags()
    assert len(flags) == 1 and flags[0]["stream_id"] == "s2"   # absence -> June, not a write
    assert sc.read_last_run() is not None
    assert any(r.get("event") == "run" for r in sc.read_run_log())

def test_run_twice_is_idempotent(wired, monkeypatch):
    d, closed, streams = wired
    sc.run_check(repo_dir=d, project="P", mode="run")
    streams[0]["engagement"] = "Done"    # what the first run's write did in Anytype
    report2 = sc.run_check(repo_dir=d, project="P", mode="run")
    assert closed == ["s1"]                          # no second write
    assert len(sc.pending_flags()) == 1              # no duplicate flag
    assert report2["tally"]["auto_fixed"] == 0

def test_run_check_rejects_unknown_mode(wired):
    d, _, _ = wired
    with pytest.raises(ValueError):
        sc.run_check(repo_dir=d, project="P", mode="yolo")

def test_run_check_requires_a_project_or_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "load_context", lambda d: None)
    with pytest.raises(RuntimeError):
        sc.run_check(repo_dir=str(tmp_path), project=None, mode="dry-run")

def test_run_aggregates_no_surfacing_streams_into_one_flag(monkeypatch, tiny_repo, cd_sandbox):
    """REVISED 2026-07-12: many never-surfaced streams on a first run become ONE aggregate
    note, not N flags — and they never reach the LLM (no evidence can exist for them)."""
    d, sha = tiny_repo
    streams = [_stream(id=f"n{i}", name=f"Never seen {i}", engagement="Steady",
                       tasks=[_task(id=f"tn{i}", done=False)], last_surfaced=None)
               for i in range(5)]
    monkeypatch.setattr(sc, "load_streams", lambda name: streams)
    monkeypatch.setattr(sc, "_now_for_findings", lambda: NOW)
    monkeypatch.setattr(sc.orient_map, "render_map", lambda name: "MAP")
    monkeypatch.setattr(sc.plan_generate, "generate",
                        lambda p, backend=None: pytest.fail("no_surfacing streams must not reach the LLM"))
    monkeypatch.setattr(sc, "_notify_new_flags", lambda n: None)
    report = sc.run_check(repo_dir=d, project="P", mode="run")
    assert report["tally"]["no_surfacing"] == 5
    pend = sc.pending_flags()
    assert len(pend) == 1 and "5" in pend[0]["june_line"]

def test_last_run_stamp_roundtrip(cd_sandbox):
    sc._write_last_run()
    ts = sc.read_last_run()
    assert ts is not None and (dt.datetime.now() - ts).total_seconds() < 60


# --- the map surfaces the checker ---------------------------------------------------

import whats_open as wo

def test_whats_open_appends_notice_when_flags_pending(monkeypatch):
    monkeypatch.setattr(wo, "load_context",
                        lambda d: {"projects": [{"name": "P"}]})
    monkeypatch.setattr(wo, "render_map", lambda name: "THE MAP")
    sc.record_flags([_flag_verdict()], _findings_for())
    out = wo.whats_open(".")
    assert "THE MAP" in out and "status check" in out and "--flags" in out

def test_whats_open_clean_when_nothing_pending(monkeypatch, cd_sandbox):
    monkeypatch.setattr(wo, "load_context",
                        lambda d: {"projects": [{"name": "P"}]})
    monkeypatch.setattr(wo, "render_map", lambda name: "THE MAP")
    out = wo.whats_open(".")
    assert out == "THE MAP"        # no permanent nag fixture on the map

def test_status_notice_warns_when_checker_overdue(cd_sandbox, monkeypatch):
    sc._write_last_run()
    late = dt.datetime.now() + dt.timedelta(days=50)
    assert "hasn't run" in sc.status_notice(now=late)
    assert sc.status_notice(now=dt.datetime.now()) == ""   # fresh stamp: silent

def test_status_notice_silent_before_first_ever_run(cd_sandbox):
    """No stamp yet = the checker hasn't been wired long enough to judge — don't nag
    about a job that never existed."""
    assert sc.status_notice() == ""
