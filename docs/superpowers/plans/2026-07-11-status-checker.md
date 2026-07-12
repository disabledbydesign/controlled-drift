# "Keep work-stream statuses current" — Status Checker Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Repo-specific execution note (from auto-memory "SDD subagent-Bash adaptation"):** task subagents WRITE files but cannot run Bash. Every step marked **(main agent, Bash)** — running pytest, git commits, launchctl, live read-backs — is executed by the main agent after the subagent returns. WRITE ALL CODE — no placeholders or TODOs.

**Goal:** A scheduled (~monthly) checker that compares each work-stream's recorded status in Anytype against evidence — staleness, status-vs-open-tasks mismatch, recent commits — auto-fixes ONLY what has concrete positive evidence, flags everything else for June, and logs her responses.

**Architecture:** One new module, `scripts/status_check.py`, layered the way this repo always is: deterministic Python gathers evidence and computes findings (pure, testable); the LLM (via the existing `plan_generate.generate()` seam) reads the evidence dossier and proposes verdicts; **Python — not the prompt — enforces the autonomy asymmetry** (the gate downgrades any auto-fix without verifiable positive evidence to a flag); mutations go through the existing read-back-proven functions (`task_actions.complete_task` + a new sibling `complete_stream`). Flags persist to a store the map (`whats_open.py`) surfaces; June's confirmations are logged via the existing `signal_log` (source `"checkin_reply"` already exists for exactly this). Scheduling = a launchd LaunchAgent, the mechanism this repo already uses (`com.june.controlled-drift.morning.plist` is the template to copy).

**Tech Stack:** Python 3 stdlib only (`subprocess` for git, `json`, `datetime`, `urllib` not needed). Reuses in-repo modules: `orient_map`, `neglect`, `task_actions`, `gsdo_objects`, `plan_generate`, `generation_log`, `signal_log`, `cd_paths`, `gsdt_bind`, `morning_push._notify`. Tests: pytest, isolated by the existing `tests/conftest.py` sandbox (CD_DATA_DIR/CD_CONFIG_DIR redirect + real-data tripwire).

**Build doc (writing-plans step zero):** this project's build discipline already exists — repo `CLAUDE.md` (idempotent writes, raise-don't-assert, read-back verification, tests self-clean and never touch June's real space) + the handoff `docs/handoff_2026-07-11_build-protocol-and-self-describe.md` (the decided design + the integration-or-it-didn't-happen rule). This plan consumes those; no new build doc needed.

---

## THE DECIDED DESIGN (June, 2026-07-11 — honor exactly, do not redesign)

From `docs/handoff_2026-07-11_build-protocol-and-self-describe.md` §"What's OPEN":

- Delivery is a **scheduled checker (~monthly)** comparing each work-stream's recorded status against evidence: staleness (`neglect.py`), status-vs-tasks mismatch, and reading code/commits to investigate.
- **Autonomy asymmetry is the safety line.** The checker may **auto-fix only cases with concrete positive evidence of the true state** (e.g. work demonstrably complete in code but not marked done — "the code is right there"). Anything resting on **absence of evidence or judgment** (looks stale; marked done but the capability can't be found) it **flags for June and does not change** — auto-marking from absence would let a wrong guess silently become the record.
- **June's confirmations/responses get logged** (learning-loop material; `signal_log` source `"checkin_reply"`).
- **Assemble the two existing pieces**, don't invent parallel mechanisms: (1) agents closing their own tasks via `task_actions.complete_task` — already built, nothing to add; the checker only catches what falls through; (2) the "system notices, you confirm" check-in design (`docs/focus_configuration_addendum.md`): surface gently, once, permission-granting register, never scold, never repeat-nag; every reply stored as learning signal.

Design consequence made explicit in this plan: **staleness is absence-of-evidence by definition**, so staleness can only ever produce a flag, never an auto-fix. The ONLY auto-fixable direction is *marking demonstrably-finished work as Done* — never reopening, never demoting, never marking stale.

---

## OPEN QUESTIONS — decided design is underspecified here (June to confirm; v1 defaults marked, chosen to be the least-assuming option, NOT resolutions)

1. **Where do flags reach June?** The check-in design says "system notices, you confirm" but names no surface for a *monthly* check (the addendum's sketch was for daily check-ins). v1 default: a macOS notification when new flags land + a standing notice line on the map (`whats_open.py`) + June resolves them in conversation (drift skill reads `--flags`, walks her through, records replies). ntfy phone push / overlay tab are alternatives June may prefer.
2. **Scope beyond repo-bound projects.** Commit evidence only exists for streams whose project is bound to a code repo (here: "Build Controlled Drift"). For non-code projects there is no "the code is right there" evidence class, so nothing could ever qualify for auto-fix — is the checker meant to run over those at all in v1, flags-only? v1 default: the checker runs per-repo over the bound project(s), exactly like `whats_open.py` — i.e. this repo's plist checks "Build Controlled Drift" only.
3. **Exact cadence.** "~monthly" — v1 default: 1st of each month, 10:00 AM (after the 9 AM morning push; laptop likely awake). launchd runs a missed slot on next wake, but a powered-off machine skips the month — the map notice (Task 7) surfaces a checker that hasn't run in >45 days, so a silent skip can't go unnoticed.
4. **May the checker auto-close individual tasks, or only streams?** The handoff's example is stream-level. v1 builds both behind the same gate (task-close reuses `complete_task`, which exists precisely so agents close finished work), but if June wants stream-only, Task 4 has a one-line constant to shrink (`AUTO_FIX_KINDS`).
5. **Which LLM backend reads the dossier?** The dossier contains stream names, task names, and commit messages. v1 default: the `CD_BACKEND` default (mistral — the decided production default, EU/no-train). Confirm June is comfortable with commit messages going to the same tier as plan data.
6. **Flag lifetime.** v1: a stream with a pending unresolved flag is never re-flagged (no repeated nagging, per the check-in constraints). But should an unresolved flag ever expire or escalate? Not designed anywhere — v1 leaves flags pending until resolved.

---

## Global Constraints

- **Python 3 stdlib only** — no new dependencies.
- **Autonomy asymmetry enforced in code, not prompt** (defense in depth: the prompt states the rules too, but the Python gate is authoritative). Auto-fix = mark-Done only, and only with commit evidence that Python itself verifies against the repo (`git cat-file -e`).
- **Idempotent writes; run-twice-safe.** A second `--run` immediately after the first must produce zero new mutations (already-Done targets are no-ops; pending flags are not re-created).
- **No silent failures — raise, don't `assert`** (outside tests). Per-stream failures are caught, logged, and never abort the rest of the run.
- **Read-back verification** on every Anytype mutation (the existing `task_actions` discipline — a good answer is not a saved object).
- **Tests self-clean, never touch June's real space** — all Anytype and LLM calls mocked; file I/O rides the conftest sandbox (`cd_paths` env redirect + tripwire). No test creates real Anytype objects.
- **June-facing language: plain words, no metaphors** (auto-memory hard access guard). Flag lines shown to June come from deterministic templates (Task 5), never raw LLM prose; LLM reasoning is stored agent-side only (store-vs-surface).
- **Register: permission-granting, never scolding** — "Is it actually finished?", never "you're behind".
- All new persistent paths resolve through `cd_paths` at call time (so the test sandbox catches everything): flags + last-run stamp in the config dir; the append-only run log in the data dir.

## File Structure

- **Create** `scripts/status_check.py` — the whole checker: evidence, findings, dossier, gate, apply, flags, log, CLI. Built up across Tasks 1, 3, 4, 5, 6 (each appends complete sections; one file because the pieces share the module's constants and are one responsibility: "keep the map honest").
- **Create** `prompts/status_check.md` — the checker's operating prompt (Task 3).
- **Modify** `scripts/task_actions.py` — add `complete_stream()` beside `complete_task()` (Task 2).
- **Modify** `scripts/whats_open.py` — append the status notice to the map (Task 7).
- **Create** `tests/test_status_check.py` — all checker tests.
- **Modify** `tests/test_mark_done.py` — `complete_stream` tests live with the other mutation tests.
- **Create** `~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist` — the monthly trigger (Task 8, main agent).

---

### Task 1: Evidence layer — load streams, compute findings, gather git evidence

> **REVISED 2026-07-12 — staleness source + first-run grace (verified finding, `docs/orchestrator_flags_2026-07-11.md` "status-checker" + "selection" §1).**
> The plan as written derived staleness from Anytype's `Last surfaced` field via `neglect.find_neglected`. That field is **dead on the live path** — written only by an interactive CLI flow June doesn't use (live: 5 of 137 tasks carry it, none newer than 2026-06-18). Built as-is, the very first run would mark nearly every stream `stale`: flag-noise that defeats the tool.
> **What changed:**
> 1. **Live staleness source = `scripts/data/surface_log.jsonl`** (append-only, every generated plan writes it; ~1,656 records current through today). New helper `_surface_log_dates()` returns `{task_id: most-recent-surfaced-datetime}`. `load_streams` computes each stream's **effective** last-surfaced = `max(ts)` over the stream's own task ids in that map, **falling back to the Anytype `Last surfaced` field only when the log has nothing** for any of the stream's tasks. `build_findings` still reads `s["last_surfaced"]`, so it stays pure/testable — the resolution happens upstream in `load_streams`.
> 2. **`stale` now means "known last-surfaced date older than `STALE_DAYS`"** — a *positive* old date, never absence. A stream with **no surfacing data in either source** is no longer `stale`; it gets a new finding kind **`no_surfacing_history`** (added to `FINDING_KINDS`).
> 3. **First-run grace:** `no_surfacing_history`-only streams do **not** each become a June flag. `run_check` counts them (`tally["no_surfacing"]`) and, on `--run`, records **ONE aggregate flag** ("N work streams have never come up in a plan…") via `record_no_surfacing_flag()` — surfaced once on the map, no re-nag. They are excluded from the LLM dossier (nothing to judge — no git evidence can ever exist for a never-surfaced stream).
> Consequence unchanged: staleness is still absence-shaped and can only ever feed a flag, never an auto-fix. The one test that asserted "never-surfaced → stale" is updated to "never-surfaced → `no_surfacing_history`, not stale".

**Files:**
- Create: `scripts/status_check.py`
- Test: `tests/test_status_check.py`

**Interfaces:**
- Produces: `load_streams(project_name) -> list[dict]` (live; each dict: `{"id": str, "name": str, "engagement": str|None, "context": str|None, "last_surfaced": datetime|None, "tasks": [{"id","name","status","done","order",...}]}` — tasks are `orient_map._steps_for` dicts).
- Produces: `build_findings(streams, now=None) -> list[dict]` (pure; each: `{"stream_id","stream_name","engagement","kinds": [str], "open_task_count": int, "done_task_count": int}`; kinds ⊆ `FINDING_KINDS`).
- Produces: `gather_git_evidence(repo_dir, days=45) -> str`, `commit_exists(repo_dir, ref) -> bool`.
- Consumes: `orient_map._load`, `orient_map._all_sub_projects`, `orient_map._props`, `orient_map._sel`, `orient_map._txt`, `orient_map._steps_for`, `neglect.find_neglected`, `neglect._parse_date`. (Same-repo private-helper imports are the established convention here — `whats_open.py` and `memory_pass.py` do the same; comment the deliberate coupling.)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_status_check.py`:

```python
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

def _task(id="t1", name="a step", done=False):
    return {"id": id, "name": name, "status": "Done" if done else "Ready",
            "done": done, "order": None, "linked_ids": []}

NOW = dt.datetime(2026, 7, 11, 12, 0)


# --- build_findings: the deterministic mismatch detectors ---------------------

def test_done_stream_with_open_tasks_is_flagged():
    s = _stream(engagement="Done", tasks=[_task(done=True), _task(id="t2", done=False)])
    f = sc.build_findings([s], now=NOW)
    assert len(f) == 1
    assert "done_with_open_tasks" in f[0]["kinds"]
    assert f[0]["open_task_count"] == 1

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

def test_never_surfaced_counts_as_stale():
    s = _stream(engagement="Steady", tasks=[_task(done=False)], last_surfaced=None)
    f = sc.build_findings([s], now=NOW)
    assert f and "stale" in f[0]["kinds"]

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
```

- [ ] **Step 2: Run the tests to verify they fail** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v`
Expected: FAIL / collection error — `ModuleNotFoundError: No module named 'status_check'`

- [ ] **Step 3: Write the implementation**

Create `scripts/status_check.py`:

```python
#!/usr/bin/env python3
"""Monthly status checker — keeps the work-stream map honest.

The map (whats_open.py) SHOWS each stream's status; nothing kept it TRUE. Statuses
drift until the map lies and June stops trusting the one surface built so she doesn't
have to hold state in her head. This checker compares each work-stream's recorded
status against evidence: staleness (neglect.py), status-vs-open-tasks mismatch, and
the repo's recent commits.

THE SAFETY LINE (decided by June, 2026-07-11 — do not weaken):
  AUTO-FIX only with concrete POSITIVE evidence of the true state — i.e. marking
  demonstrably-finished work as Done, with commit citations Python itself verifies.
  Everything resting on absence-of-evidence or judgment (stale, can't-confirm,
  done-but-tasks-open) is FLAGGED for June and never changed. Auto-marking from
  absence would let a wrong guess silently become the record — the map lying a new
  way. The asymmetry lives in gate_verdicts(), in code, not just in the prompt.

Layers (the repo's standing shape — deterministic facts, LLM judgment, gated writes):
  1. Evidence (Python, pure-testable): load_streams / build_findings / gather_git_evidence
  2. Investigation (LLM via plan_generate seam): the dossier prompt -> per-stream verdicts
  3. The gate (Python): gate_verdicts enforces the asymmetry; citations verified via git
  4. Apply (existing read-back-proven mutations): task_actions.complete_stream / complete_task
  5. Flags + June's replies: status_flags.json + signal_log(source="checkin_reply")

Run manually:   python3 scripts/status_check.py            (dry-run: findings only, no LLM)
                python3 scripts/status_check.py --preview  (LLM verdicts, writes NOTHING)
                python3 scripts/status_check.py --run      (the real monthly pass)
                python3 scripts/status_check.py --flags    (what's waiting for June)
Scheduled by:   ~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist
"""
import sys, os, re, json, subprocess, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths
import neglect
# Same-repo private-helper reuse is the established convention here (whats_open.py,
# memory_pass.py do the same) — deliberate coupling, one source of truth for parsing.
import orient_map

STALE_DAYS = 30      # ~monthly cadence: untouched for a month = worth a gentle question
GIT_LOG_DAYS = 45    # evidence window: a little wider than the run cadence, so a run
                     # delayed by a sleeping laptop still sees the whole month

FINDING_KINDS = ("done_with_open_tasks", "active_all_tasks_done", "no_tasks", "stale")

# Engagement values that mean "deliberately parked" — silence there is honest, not drift.
_PARKED = ("Backburner",)


# --- layer 1: evidence ---------------------------------------------------------

def load_streams(project_name):
    """All work-streams (nested Projects) under `project_name`, with status + tasks +
    last-surfaced date — everything the findings + the dossier need, one Anytype read."""
    goals, projects, tasks = orient_map._load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        raise RuntimeError(f"status_check: no project named {project_name!r} in the space")
    streams = []
    for s in orient_map._all_sub_projects(proj["id"], projects):
        props = orient_map._props(s)
        by_name = {p.get("name"): p for p in s.get("properties", [])}
        raw_ls = (by_name.get("Last surfaced") or {}).get("date")
        streams.append({
            "id": s["id"],
            "name": s.get("name", ""),
            "engagement": orient_map._sel(props, "engagement"),
            "context": orient_map._txt(props, "gsdo_context"),
            "last_surfaced": neglect._parse_date(raw_ls),
            "tasks": orient_map._steps_for(s["id"], tasks),
        })
    return streams


def build_findings(streams, now=None):
    """Pure. The deterministic mismatch detectors — facts only, no judgment.

    Kinds:
      done_with_open_tasks  - engagement says Done but open tasks remain (map may lie "done")
      active_all_tasks_done - active, has tasks, every one Done (map may lie "in progress")
      no_tasks              - active but no steps recorded (nothing to check it against)
      stale                 - active, not surfaced in STALE_DAYS (absence-of-evidence:
                              can ONLY ever feed a flag, never an auto-fix)
    Done and Backburner streams are exempt from no_tasks/stale — a finished or
    deliberately-parked stream being quiet is honest, and nagging it is the scold
    the check-in design forbids.
    """
    now = now or dt.datetime.now()
    findings = []
    for s in streams:
        open_tasks = [t for t in s["tasks"] if not t["done"]]
        done_tasks = [t for t in s["tasks"] if t["done"]]
        eng = s["engagement"]
        kinds = []
        if eng == "Done" and open_tasks:
            kinds.append("done_with_open_tasks")
        if eng != "Done" and s["tasks"] and not open_tasks:
            kinds.append("active_all_tasks_done")
        if eng != "Done" and eng not in _PARKED:
            if not s["tasks"]:
                kinds.append("no_tasks")
            if neglect.find_neglected([{"last_surfaced": s.get("last_surfaced")}],
                                      now, days=STALE_DAYS):
                kinds.append("stale")
        if kinds:
            findings.append({"stream_id": s["id"], "stream_name": s["name"],
                             "engagement": eng, "kinds": kinds,
                             "open_task_count": len(open_tasks),
                             "done_task_count": len(done_tasks)})
    return findings


def gather_git_evidence(repo_dir, days=GIT_LOG_DAYS):
    """Recent commit log for the bound repo — the raw material for 'the code is right
    there'. Raises on any git failure (no silent empty evidence: an empty dossier
    would quietly make every auto-fix impossible and every verdict a flag)."""
    try:
        p = subprocess.run(
            ["git", "-C", repo_dir, "log", f"--since={days} days ago", "--no-merges",
             "--pretty=format:%h %ad %s", "--date=short"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"status_check: git log failed in {repo_dir!r}: {e}")
    if p.returncode != 0:
        raise RuntimeError(f"status_check: git log failed in {repo_dir!r}: {p.stderr.strip()}")
    return p.stdout.strip()


_HASH_RE = re.compile(r"[0-9a-f]{7,40}")

def commit_exists(repo_dir, ref):
    """True iff `ref` is a hex hash that resolves to a commit in repo_dir. Only hashes
    count — 'HEAD'/'main'/prose are not verifiable citations, and nothing un-hash-like
    ever reaches the subprocess."""
    ref = (ref or "").strip().lower() if isinstance(ref, str) else ""
    if not _HASH_RE.fullmatch(ref):
        return False
    try:
        p = subprocess.run(["git", "-C", repo_dir, "cat-file", "-e", ref + "^{commit}"],
                           capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0
```

- [ ] **Step 4: Run the tests to verify they pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v`
Expected: all Task-1 tests PASS. Then the whole suite: `python3 -m pytest tests/ -q` — no regressions.

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/status_check.py tests/test_status_check.py
git commit -m "feat(status): evidence layer — findings + git evidence for the monthly checker"
```

---

### Task 2: `complete_stream` — the read-back-proven stream mutation

**Files:**
- Modify: `scripts/task_actions.py` (append after `uncomplete_task`, before `archive_object`)
- Test: `tests/test_mark_done.py` (append a section)

**Interfaces:**
- Produces: `task_actions.complete_stream(stream_id) -> {"id","name","engagement":"Done","done":True}` — raises `RuntimeError` if the write doesn't persist.
- Consumes: `gsdo_objects.update` (resolves `"Engagement": "Done"` select-name → tag id — its own docstring shows exactly this call), `task_actions._get_object` (exists).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mark_done.py`:

```python
# --- complete_stream: the checker's stream close + read-back ------------------

def test_complete_stream_writes_done_engagement_and_confirms(monkeypatch):
    updates = []
    monkeypatch.setattr(task_actions.gsdo_objects, "update",
                        lambda oid, properties=None: updates.append((oid, properties)))
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "Finish the daily-plan pipeline",
        "properties": [{"key": "engagement", "select": {"name": "Done"}}],
    })
    result = task_actions.complete_stream("id-stream")
    assert updates == [("id-stream", {"Engagement": "Done"})]
    assert result == {"id": "id-stream", "name": "Finish the daily-plan pipeline",
                      "engagement": "Done", "done": True}


def test_complete_stream_raises_if_engagement_did_not_persist(monkeypatch):
    monkeypatch.setattr(task_actions.gsdo_objects, "update", lambda oid, properties=None: None)
    monkeypatch.setattr(task_actions, "_get_object", lambda oid: {
        "name": "x", "properties": [{"key": "engagement", "select": {"name": "Steady"}}],
    })
    with pytest.raises(RuntimeError):
        task_actions.complete_stream("id-stream")
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_mark_done.py -v -k complete_stream`
Expected: FAIL — `AttributeError: module 'task_actions' has no attribute 'complete_stream'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/task_actions.py` (after `uncomplete_task`):

```python
def complete_stream(stream_id):
    """Mark a work-stream (Project) Done in Anytype and confirm it persisted. Returns:
        {"id", "name", "engagement": "Done", "done": True}

    Completion for a STREAM = the Engagement select -> 'Done' — the property the whole
    map already reads (orient_map routes engagement == 'Done' to the Finished section).
    One property, the one everything else reads: same principle as complete_task.

    Used by the monthly status checker (status_check.py) for its ONE allowed autonomous
    change: marking demonstrably-finished work as Done. The checker's gate — not this
    function — decides WHETHER; this function only makes the write honest (read-back).
    """
    gsdo_objects.update(stream_id, properties={"Engagement": "Done"})

    obj = _get_object(stream_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    eng = (pv.get("engagement", {}).get("select") or {}).get("name")
    if eng != "Done":
        raise RuntimeError(
            f"complete_stream({stream_id!r}): Engagement did not persist (read-back={eng!r})")
    return {"id": stream_id, "name": obj.get("name"), "engagement": "Done", "done": True}
```

- [ ] **Step 4: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_mark_done.py -v`
Expected: PASS (new tests + all existing mutation tests untouched).

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/task_actions.py tests/test_mark_done.py
git commit -m "feat(status): complete_stream — read-back-proven Engagement->Done for the checker"
```

---

### Task 3: The dossier — prompt file, prompt assembly, verdict parsing, LLM call

**Files:**
- Create: `prompts/status_check.md`
- Modify: `scripts/status_check.py` (append a "layer 2" section)
- Test: `tests/test_status_check.py` (append)

**Interfaces:**
- Produces: `_assemble_prompt(project_name, streams, findings, git_log, map_text) -> str`
- Produces: `_parse_verdicts(model_text) -> (verdicts, malformed)` — verdict dict: `{"stream_id": str, "stream_name": str, "verdict": "confirmed"|"auto_fix"|"flag", "proposed_change": {"kind": str, "target_id": str}|None, "evidence": [{"kind": str, "ref": str, "note": str}], "reasoning": str}`
- Produces: `_generate_verdicts(prompt, backend=None) -> (verdicts, malformed)` — retries once (`GEN_ATTEMPTS = 2`), logs every attempt via `generation_log.log_generation(source="status_check")`, raises only if all attempts fail. Mirrors `memory_pass.generate_candidates` exactly.
- Consumes: `plan_generate.generate(prompt, backend=)`, `plan_generate._active_model`, `generation_log.log_generation`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_status_check.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v -k "verdict or assemble"`
Expected: FAIL — `AttributeError: ... no attribute '_parse_verdicts'`

- [ ] **Step 3: Create the prompt file**

Create `prompts/status_check.md`:

```markdown
# Monthly status check — checker operating prompt

You are the status checker for Controlled Drift, June's task system. Below you get:
the project map as June sees it, every work-stream with its recorded status and its
tasks, the deterministic findings Python already computed, and the repo's recent git
log. Your job: for EACH stream that has findings (and only those), judge whether its
recorded status matches reality, and say what should happen.

## The autonomy rules (decided by June — also enforced in code; a verdict that breaks
## them is downgraded to a flag, so breaking them only wastes the verdict)

- `"auto_fix"` — ONLY when there is concrete POSITIVE evidence of the true state:
  work demonstrably complete in the git log ("the code is right there") AND every
  recorded step of the stream already Done. The only allowed changes are
  `mark_stream_done` and `mark_task_done`. You MUST cite at least one commit hash
  copied exactly from the git log below as evidence — it will be verified against
  the repo. Never cite a hash that is not in the log.
- `"flag"` — anything resting on absence of evidence or judgment: the stream looks
  stale; it is marked Done but you cannot find the capability; it has open tasks;
  you are inferring rather than seeing. Flagging is the right call whenever unsure —
  a wrong auto-fix silently corrupts the record June trusts.
- `"confirmed"` — the recorded status matches the evidence; nothing to do.

Never propose reopening, demoting, or marking anything stale as a change — those are
June's calls; use `"flag"` and explain in `reasoning`.

## Output

Reply with ONE fenced ```json block: an array with one object per stream-with-findings.

```json
[
  {
    "stream_id": "<id copied exactly from the input>",
    "stream_name": "<name>",
    "verdict": "confirmed" | "auto_fix" | "flag",
    "proposed_change": {"kind": "mark_stream_done" | "mark_task_done",
                        "target_id": "<stream or task id>"}   // null unless auto_fix
    ,
    "evidence": [{"kind": "commit" | "task" | "map", "ref": "<hash or id>",
                  "note": "<what this shows, one line>"}],
    "reasoning": "<one or two plain sentences — stored for the record, June may read it>"
  }
]
```

`reasoning` register: plain, factual, never scolding. The input sections follow.
```

- [ ] **Step 4: Write the implementation**

Append to `scripts/status_check.py`:

```python
# --- layer 2: investigation (LLM via the existing seam) --------------------------

import plan_generate
import generation_log

PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts",
                           "status_check.md")

GEN_ATTEMPTS = 2  # 1 retry — same evidence-based tuning as memory_pass (transient API
                  # stalls happen; one retry absorbs them without masking a bad prompt)

VERDICT_VALUES = ("confirmed", "auto_fix", "flag")


def _assemble_prompt(project_name, streams, findings, git_log, map_text):
    """The dossier: prompt template + the map + streams/findings JSON + the git log.
    Facts travel WITH their meaning (context text rides along) — the standing principle."""
    with open(PROMPT_PATH, encoding="utf-8") as f:
        template = f.read()
    payload = {
        "project": project_name,
        "streams": [{"stream_id": s["id"], "name": s["name"],
                     "engagement": s["engagement"], "context": s["context"],
                     "last_surfaced": s["last_surfaced"].isoformat() if s.get("last_surfaced") else None,
                     "tasks": [{"id": t["id"], "name": t["name"],
                                "status": t["status"], "done": t["done"]}
                               for t in s["tasks"]]} for s in streams],
        "deterministic_findings": findings,
    }
    return "\n".join([
        template, "",
        "### THE PROJECT MAP AS JUNE SEES IT", "", map_text, "",
        "### STREAMS + DETERMINISTIC FINDINGS (JSON)", "",
        json.dumps(payload, indent=2), "",
        f"### GIT LOG (last {GIT_LOG_DAYS} days of this repo)", "",
        git_log or "(no commits in the window)",
    ])


def _parse_verdicts(model_text):
    """Extract the verdict array from the model's fenced ```json block. A malformed
    ELEMENT is isolated, never fatal to the batch (memory_pass discipline)."""
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot read verdicts")
    try:
        parsed = json.loads(blocks[-1].strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    if not isinstance(parsed, list):
        raise RuntimeError(f"model's JSON block was not a list (got {type(parsed).__name__})")
    verdicts, malformed = [], []
    for v in parsed:
        if isinstance(v, dict) and v.get("stream_id") and v.get("verdict") in VERDICT_VALUES:
            verdicts.append(v)
        else:
            malformed.append(v if isinstance(v, dict) else {"_raw": v})
    return verdicts, malformed


def _generate_verdicts(prompt, backend=None):
    """One LLM call for the whole dossier, retried once; every attempt logged. Raises
    only if every attempt fails (an honest loud failure, never a silent empty run)."""
    backend_name = backend or os.environ.get("CD_BACKEND", "mistral")
    model = plan_generate._active_model(backend_name)
    backend_label = f"{backend_name}/{model}" if model else backend_name
    last_err = None
    for attempt in range(1, GEN_ATTEMPTS + 1):
        t0 = time.monotonic()
        try:
            text = plan_generate.generate(prompt, backend=backend)
            verdicts, malformed = _parse_verdicts(text)
        except Exception as e:
            generation_log.log_generation(
                backend=backend_label, duration_s=time.monotonic() - t0,
                success=False, source="status_check",
                error_type=type(e).__name__, error_msg=str(e),
                structural={"attempt": attempt})
            last_err = e
            continue
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=True, source="status_check",
            structural={"attempt": attempt, "n_verdicts": len(verdicts),
                        "n_malformed": len(malformed)})
        return verdicts, malformed
    raise last_err
```

- [ ] **Step 5: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v`
Expected: PASS.

- [ ] **Step 6: Commit** (main agent, Bash)

```bash
git add prompts/status_check.md scripts/status_check.py tests/test_status_check.py
git commit -m "feat(status): dossier prompt + verdict parsing through the plan_generate seam"
```

---

### Task 4: The gate + apply — the autonomy asymmetry, enforced in code

**Files:**
- Modify: `scripts/status_check.py` (append a "layer 3+4" section)
- Test: `tests/test_status_check.py` (append)

**Interfaces:**
- Produces: `AUTO_FIX_KINDS = ("mark_stream_done", "mark_task_done")` — shrink to `("mark_stream_done",)` if June answers open question 4 with stream-only.
- Produces: `gate_verdicts(verdicts, streams_by_id, repo_dir) -> {"auto_fix": [...], "flag": [...], "confirmed": [...], "downgraded": [...]}` (pure except `commit_exists` subprocess; every downgraded verdict also appears in `"flag"`, carrying `downgrade_reason`).
- Produces: `apply_auto_fixes(auto_fixes, streams_by_id) -> [result]` — result: `{"stream_id","stream_name","kind","target_id","outcome": "applied"|"noop-already-done"|"failed", "read_back": dict|None, "error": str|None}`.
- Consumes: `commit_exists` (Task 1), `task_actions.complete_stream` (Task 2), `task_actions.complete_task` (exists).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_status_check.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v -k "gate or apply"`
Expected: FAIL — `AttributeError: ... no attribute 'gate_verdicts'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/status_check.py`:

```python
# --- layers 3+4: the gate (THE SAFETY LINE) + gated apply -------------------------

import task_actions

# The ONLY changes the checker may make on its own: marking demonstrably-finished work
# Done. Never reopen, never demote, never mark stale. If June decides (open question 4)
# the checker should close streams only, shrink this to ("mark_stream_done",).
AUTO_FIX_KINDS = ("mark_stream_done", "mark_task_done")


def _autofix_block_reason(v, streams_by_id, repo_dir):
    """Why this auto_fix verdict may NOT be applied autonomously — or None if it may.
    Every condition is a positive-evidence requirement; failing any one means the
    verdict rests on judgment or absence, which is June's territory."""
    change = v.get("proposed_change") or {}
    kind = change.get("kind")
    if kind not in AUTO_FIX_KINDS:
        return f"proposed change {kind!r} is not an allowed autonomous fix"
    stream = streams_by_id.get(v.get("stream_id"))
    if stream is None:
        return f"verdict references stream {v.get('stream_id')!r} not in this run"
    commits = [e for e in (v.get("evidence") or [])
               if isinstance(e, dict) and e.get("kind") == "commit"]
    if not commits:
        return "no commit evidence cited — concrete positive evidence is required"
    bad = [e.get("ref") for e in commits if not commit_exists(repo_dir, e.get("ref"))]
    if bad:
        return f"cited commit(s) do not exist in the repo: {bad}"
    if kind == "mark_stream_done":
        if change.get("target_id") != stream["id"]:
            return "target_id does not match the stream"
        open_tasks = [t for t in stream["tasks"] if not t["done"]]
        if open_tasks:
            return (f"stream still has {len(open_tasks)} open task(s) — "
                    "not demonstrably complete")
    if kind == "mark_task_done":
        if not any(t["id"] == change.get("target_id") for t in stream["tasks"]):
            return f"target task {change.get('target_id')!r} not found in this stream"
    return None


def gate_verdicts(verdicts, streams_by_id, repo_dir):
    """Enforce the autonomy asymmetry IN CODE. auto_fix verdicts that fail any
    positive-evidence check are downgraded to flags (recorded with the reason —
    a downgrade is itself signal about the model's judgment). flag/confirmed pass
    through untouched: the checker never escalates a flag into a write."""
    out = {"auto_fix": [], "flag": [], "confirmed": [], "downgraded": []}
    for v in verdicts:
        if v["verdict"] == "confirmed":
            out["confirmed"].append(v)
        elif v["verdict"] == "flag":
            out["flag"].append(v)
        else:  # auto_fix candidate
            reason = _autofix_block_reason(v, streams_by_id, repo_dir)
            if reason is None:
                out["auto_fix"].append(v)
            else:
                d = dict(v, downgrade_reason=reason)
                out["downgraded"].append(d)
                out["flag"].append(d)
    return out


def apply_auto_fixes(auto_fixes, streams_by_id):
    """Apply gate-approved fixes through the read-back-proven mutations. Idempotent:
    an already-Done target is a no-op (run-twice-safe). One failure never aborts the
    rest; every outcome is returned for the run log."""
    results = []
    for v in auto_fixes:
        change = v["proposed_change"]
        stream = streams_by_id[v["stream_id"]]
        base = {"stream_id": v["stream_id"], "stream_name": v.get("stream_name"),
                "kind": change["kind"], "target_id": change["target_id"],
                "read_back": None, "error": None}
        try:
            if change["kind"] == "mark_stream_done":
                if stream["engagement"] == "Done":
                    results.append({**base, "outcome": "noop-already-done"})
                    continue
                rb = task_actions.complete_stream(change["target_id"])
            else:  # mark_task_done (gate guarantees the task exists in this stream)
                task = next(t for t in stream["tasks"] if t["id"] == change["target_id"])
                if task["done"]:
                    results.append({**base, "outcome": "noop-already-done"})
                    continue
                rb = task_actions.complete_task(change["target_id"])
            results.append({**base, "outcome": "applied", "read_back": rb})
        except Exception as e:
            results.append({**base, "outcome": "failed",
                            "error": f"{type(e).__name__}: {e}"})
    return results
```

- [ ] **Step 4: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/status_check.py tests/test_status_check.py
git commit -m "feat(status): the gate — autonomy asymmetry enforced in code, gated apply"
```

---

### Task 5: Flags for June + her logged responses + the run log

**Files:**
- Modify: `scripts/status_check.py` (append a "layer 5" section)
- Test: `tests/test_status_check.py` (append)

**Interfaces:**
- Produces: `record_flags(flag_verdicts, findings, path=None) -> [new_flag]` — flag dict: `{"id": str, "created": iso, "stream_id","stream_name","kinds": [str], "june_line": str, "agent_detail": verdict, "status": "pending", "resolution": None}`. Skips streams that already have a pending flag (no repeated nagging).
- Produces: `pending_flags(path=None) -> [flag]`, `load_flags(path=None) -> {"flags": [...]}`, `save_flags(data, path=None)`.
- Produces: `resolve_flag(flag_id, response_text, action="leave", target_id=None, path=None) -> flag` — logs June's words via `signal_log.log_signal(source="checkin_reply")`, optionally applies a confirmed fix (`mark_stream_done` / `mark_task_done`) through `task_actions`, marks the flag resolved. Raises on unknown/already-resolved flag or unknown action.
- Produces: `log_run(record, path=None)` — append-only jsonl (`status_check_log.jsonl`, data dir), `read_run_log(path=None)`.
- Produces: `JUNE_LINES` — deterministic plain-language templates (June-facing; the LLM's prose never reaches her directly).
- Consumes: `signal_log.log_signal` (SOURCES already contains `"checkin_reply"`), `cd_paths.config_file` / `cd_paths.data_file`, `task_actions`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_status_check.py`:

```python
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


# --- the run log --------------------------------------------------------------------

def test_log_run_appends_and_reads_back(tmp_path):
    p = str(tmp_path / "runlog.jsonl")
    sc.log_run({"event": "run", "auto_fixed": 1}, path=p)
    sc.log_run({"event": "run", "auto_fixed": 0}, path=p)
    recs = sc.read_run_log(path=p)
    assert len(recs) == 2 and recs[0]["auto_fixed"] == 1 and all("ts" in r for r in recs)
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v -k "flag or log_run or june_line"`
Expected: FAIL — `AttributeError: ... no attribute 'record_flags'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/status_check.py`:

```python
# --- layer 5: flags for June + her logged replies + the run log --------------------

import signal_log

# June-facing lines: deterministic templates, plain words, permission-granting, a
# question not a verdict. The LLM's reasoning stays agent-side in agent_detail
# (store-vs-surface). HARD access guard: no metaphors, no jargon, no coded status words.
JUNE_LINES = {
    "done_with_open_tasks":
        "The map shows “{name}” as finished, but {open} of its steps are still open. "
        "Is it actually finished?",
    "active_all_tasks_done":
        "Every recorded step of “{name}” is finished, but the map still shows it as "
        "in progress. Is it done, or is there more to add?",
    "stale":
        "“{name}” hasn't come up in over a month. Still current, or should it move "
        "to later?",
    "no_tasks":
        "“{name}” shows as in progress but has no steps recorded, so the check "
        "can't tell where it stands. Want to add its steps, or set it aside?",
    "default":
        "The check couldn't confirm that “{name}” matches what's actually built. "
        "Worth a look together?",
}


def _june_line(kinds, name, open_count=0):
    for k in kinds:
        if k in JUNE_LINES:
            return JUNE_LINES[k].format(name=name, open=open_count)
    return JUNE_LINES["default"].format(name=name, open=open_count)


def _flags_path(path=None):
    return path or cd_paths.config_file("status_flags.json")


def load_flags(path=None):
    try:
        with open(_flags_path(path), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"flags": []}


def save_flags(data, path=None):
    p = _flags_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def pending_flags(path=None):
    return [f for f in load_flags(path)["flags"] if f.get("status") == "pending"]


def record_flags(flag_verdicts, findings, path=None):
    """Persist flag verdicts as pending questions for June. Surface once, then defer:
    a stream with an existing PENDING flag is never re-flagged (the check-in design's
    no-repeat-nagging constraint). Returns only the newly created flags."""
    data = load_flags(path)
    already_pending = {f["stream_id"] for f in data["flags"] if f.get("status") == "pending"}
    findings_by_id = {f["stream_id"]: f for f in findings}
    new = []
    for v in flag_verdicts:
        sid = v["stream_id"]
        if sid in already_pending:
            continue
        finding = findings_by_id.get(sid, {})
        kinds = finding.get("kinds", [])
        flag = {
            "id": f"{dt.date.today().isoformat()}-{sid[-8:]}",
            "created": dt.datetime.now().isoformat(timespec="seconds"),
            "stream_id": sid,
            "stream_name": v.get("stream_name", ""),
            "kinds": kinds,
            "june_line": _june_line(kinds, v.get("stream_name", "this stream"),
                                    open_count=finding.get("open_task_count", 0)),
            "agent_detail": v,          # reasoning/evidence/downgrade_reason: agent-side
            "status": "pending",
            "resolution": None,
        }
        data["flags"].append(flag)
        already_pending.add(sid)
        new.append(flag)
    if new:
        save_flags(data, path)
    return new


RESOLVE_ACTIONS = ("leave", "mark_stream_done", "mark_task_done")


def resolve_flag(flag_id, response_text, action="leave", target_id=None,
                 path=None, signal_path=None):
    """June answered a flag. Log her words verbatim (signal_log source 'checkin_reply' —
    the learning-loop material the design asks for), apply the confirmed fix if she said
    so, mark the flag resolved. Raises on unknown flag / action — never a silent no-op."""
    if action not in RESOLVE_ACTIONS:
        raise ValueError(f"resolve_flag: unknown action {action!r} (expected {RESOLVE_ACTIONS})")
    data = load_flags(path)
    flag = next((f for f in data["flags"]
                 if f["id"] == flag_id and f.get("status") == "pending"), None)
    if flag is None:
        raise RuntimeError(f"resolve_flag: no pending flag with id {flag_id!r}")

    signal_log.log_signal(response_text, source="checkin_reply",
                          reference={"flag_id": flag_id, "stream_id": flag["stream_id"],
                                     "stream_name": flag["stream_name"]},
                          path=signal_path)
    read_back = None
    if action == "mark_stream_done":
        read_back = task_actions.complete_stream(target_id or flag["stream_id"])
    elif action == "mark_task_done":
        if not target_id:
            raise ValueError("resolve_flag: mark_task_done needs target_id")
        read_back = task_actions.complete_task(target_id)

    flag["status"] = "resolved"
    flag["resolution"] = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
                          "action": action, "target_id": target_id,
                          "read_back": read_back}
    save_flags(data, path)
    log_run({"event": "flag_resolved", "flag_id": flag_id, "action": action}, )
    return flag


def log_run(record, path=None):
    """Append-only jsonl of everything the checker did — every verdict tally, every
    applied fix with its read-back, every downgrade with its reason, every resolution.
    The durable record that makes the checker itself auditable."""
    p = path or cd_paths.data_file("status_check_log.jsonl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"), **record}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def read_run_log(path=None):
    p = path or cd_paths.data_file("status_check_log.jsonl")
    try:
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
```

(Note the trailing `, )` in `log_run({...}, )` inside `resolve_flag` is just a default-path call — write it as `log_run({"event": "flag_resolved", "flag_id": flag_id, "action": action})`.)

- [ ] **Step 4: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v`
Expected: PASS. Also confirm `signal_log.log_signal` accepts the `reference` dict (it does — `reference=None` param, stored verbatim).

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/status_check.py tests/test_status_check.py
git commit -m "feat(status): flags June confirms + checkin_reply signal logging + run log"
```

---

### Task 6: Orchestration + CLI — dry-run / preview / run, resolve, flags

**Files:**
- Modify: `scripts/status_check.py` (append the final section)
- Test: `tests/test_status_check.py` (append)

**Interfaces:**
- Produces: `run_check(repo_dir=".", project=None, backend=None, mode="dry-run") -> report` — report: `{"mode", "projects": [name], "results": [per-project dict], "tally": {"streams","findings","confirmed","auto_fixed","noop","flagged","downgraded","failed","malformed"}}`. Modes exactly mirror `memory_pass.py`: `dry-run` = no LLM, no writes (findings only); `preview` = LLM + gate, **zero writes** (no flags recorded, no stamp, no log); `run` = the real pass.
- Produces: `_write_last_run()`, `read_last_run() -> datetime|None` (config file `status_check_last_run`).
- Produces: CLI (`--dir`, `--project`, `--dry-run`/`--preview`/`--run`, `--backend`, `--flags`, `--resolve FLAG_ID --response TEXT [--action A] [--target ID]`).
- Consumes: everything above + `gsdt_bind.load_context`, `orient_map.render_map`, `morning_push._notify` (the existing gentle macOS notification — reused, not reinvented).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_status_check.py`:

```python
# --- orchestration ------------------------------------------------------------------

@pytest.fixture
def wired(monkeypatch, tiny_repo):
    """run_check with every live seam mocked: streams from a fixture, LLM canned,
    mutations recorded, notifications suppressed. File I/O rides the conftest sandbox."""
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

def test_last_run_stamp_roundtrip():
    sc._write_last_run()
    ts = sc.read_last_run()
    assert ts is not None and (dt.datetime.now() - ts).total_seconds() < 60
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v -k "run or preview or stamp"`
Expected: FAIL — `AttributeError: ... no attribute 'run_check'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/status_check.py`:

```python
# --- orchestration + CLI ------------------------------------------------------------

from gsdt_bind import load_context

MODES = ("dry-run", "preview", "run")
LAST_RUN_FILE = "status_check_last_run"


def _now_for_findings():
    """Seam so tests pin 'now' without reaching into build_findings call sites."""
    return dt.datetime.now()


def _write_last_run():
    p = cd_paths.config_file(LAST_RUN_FILE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(dt.datetime.now().isoformat(timespec="seconds"))


def read_last_run():
    try:
        with open(cd_paths.config_file(LAST_RUN_FILE), encoding="utf-8") as f:
            return dt.datetime.fromisoformat(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _notify_new_flags(n):
    """Gentle macOS notification when the monthly check has questions. Best-effort —
    reuses the morning push's notifier; a notification failure never loses the flags
    (they're already saved, and the map notice will still show them)."""
    import morning_push
    word = "question" if n == 1 else "questions"
    morning_push._notify(
        "Controlled Drift",
        f"The monthly status check has {n} {word} about the map, whenever you're ready.")


def run_check(repo_dir=".", project=None, backend=None, mode="dry-run"):
    """The whole pass. dry-run: findings only (no LLM, no writes). preview: LLM + gate,
    writes NOTHING (for June-reviewed first runs — the memory-pass precedent). run: the
    real monthly pass — apply gated fixes, record flags, stamp, log."""
    if mode not in MODES:
        raise ValueError(f"run_check: unknown mode {mode!r} (expected {MODES})")
    if project:
        project_names = [project]
    else:
        ctx = load_context(repo_dir)
        project_names = [p.get("name") for p in (ctx or {}).get("projects", [])
                         if p.get("name")]
    if not project_names:
        raise RuntimeError("status_check: no project — pass --project or run from a "
                           "repo bound to Controlled Drift")

    tally = {"streams": 0, "findings": 0, "confirmed": 0, "auto_fixed": 0, "noop": 0,
             "flagged": 0, "downgraded": 0, "failed": 0, "malformed": 0}
    results = []
    for pname in project_names:
        streams = load_streams(pname)
        findings = build_findings(streams, now=_now_for_findings())
        tally["streams"] += len(streams)
        tally["findings"] += len(findings)
        result = {"project": pname, "findings": findings}

        if mode != "dry-run" and findings:
            git_log = gather_git_evidence(repo_dir)
            map_text = orient_map.render_map(pname)
            prompt = _assemble_prompt(pname, streams, findings, git_log, map_text)
            verdicts, malformed = _generate_verdicts(prompt, backend=backend)
            streams_by_id = {s["id"]: s for s in streams}
            gated = gate_verdicts(verdicts, streams_by_id, repo_dir)
            tally["malformed"] += len(malformed)
            tally["confirmed"] += len(gated["confirmed"])
            tally["downgraded"] += len(gated["downgraded"])
            result.update({"verdicts": verdicts, "malformed": malformed, "gated": gated})

            if mode == "run":
                applied = apply_auto_fixes(gated["auto_fix"], streams_by_id)
                new_flags = record_flags(gated["flag"], findings)
                for r in applied:
                    tally["auto_fixed" if r["outcome"] == "applied" else
                          "noop" if r["outcome"] == "noop-already-done" else
                          "failed"] += 1
                tally["flagged"] += len(new_flags)
                result.update({"applied": applied, "new_flags": new_flags})
        results.append(result)

    report = {"mode": mode, "projects": project_names, "results": results, "tally": tally}
    if mode == "run":
        _write_last_run()
        log_run({"event": "run", **tally,
                 "applied": [r for res in results for r in res.get("applied", [])],
                 "downgraded": [{"stream_id": v["stream_id"],
                                 "reason": v["downgrade_reason"]}
                                for res in results
                                for v in res.get("gated", {}).get("downgraded", [])]})
        total_new = sum(len(res.get("new_flags", [])) for res in results)
        if total_new:
            _notify_new_flags(total_new)
    return report


def status_notice(now=None):
    """One or two plain lines for the map (whats_open.py): pending questions, and a
    checker that hasn't run in too long. Empty string when there's nothing to say —
    the map must not grow a permanent nag fixture."""
    now = now or dt.datetime.now()
    lines = []
    n = len(pending_flags())
    if n:
        word = "question" if n == 1 else "questions"
        lines.append(f"  ⚠ the monthly status check has {n} {word} waiting — "
                     f"python3 scripts/status_check.py --flags")
    last = read_last_run()
    if last is not None and (now - last).days > 45:
        lines.append("  ⚠ the status check hasn't run in over 45 days — "
                     "statuses may have drifted")
    return "\n".join(lines)


def _format_report(report):
    lines = [f"status check ({report['mode']}) — projects: {', '.join(report['projects'])}"]
    t = report["tally"]
    lines.append(f"  streams {t['streams']} · findings {t['findings']} · "
                 f"confirmed {t['confirmed']} · auto-fixed {t['auto_fixed']} · "
                 f"noop {t['noop']} · flagged {t['flagged']} · "
                 f"downgraded {t['downgraded']} · failed {t['failed']} · "
                 f"malformed {t['malformed']}")
    for res in report["results"]:
        for f in res["findings"]:
            lines.append(f"  [{','.join(f['kinds'])}] {f['stream_name']} "
                         f"(engagement={f['engagement']}, open={f['open_task_count']})")
        for v in res.get("gated", {}).get("downgraded", []):
            lines.append(f"  downgraded->flag: {v['stream_name']}: {v['downgrade_reason']}")
        for r in res.get("applied", []):
            lines.append(f"  {r['outcome']}: {r['stream_name']} ({r['kind']})")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Monthly status checker — keeps the map honest")
    ap.add_argument("--dir", default=".", help="repo dir for binding + git evidence")
    ap.add_argument("--project", default=None, help="check this project instead of the bound one")
    ap.add_argument("--backend", default=None, help="override CD_BACKEND for this run")
    ap.add_argument("--dry-run", action="store_true",
                    help="findings only — no LLM, no writes (default action)")
    ap.add_argument("--preview", action="store_true",
                    help="LLM verdicts + gate, but write NOTHING — for reviewed first runs")
    ap.add_argument("--run", action="store_true", help="the real pass: apply + flag + log")
    ap.add_argument("--flags", action="store_true", help="list what's waiting for June")
    ap.add_argument("--resolve", default=None, metavar="FLAG_ID",
                    help="record June's answer to a flag (with --response, --action)")
    ap.add_argument("--response", default=None, help="June's words, verbatim")
    ap.add_argument("--action", default="leave",
                    help="leave | mark_stream_done | mark_task_done")
    ap.add_argument("--target", default=None, help="target id for mark_task_done")
    args = ap.parse_args()

    if sum([args.run, args.preview, args.dry_run]) > 1:
        print("--dry-run / --preview / --run are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if args.flags:
        flags = pending_flags()
        if not flags:
            print("Nothing waiting — the map and the check agree.")
        for f in flags:
            print(f"[{f['id']}] {f['june_line']}")
        sys.exit(0)

    if args.resolve:
        if not args.response:
            print("--resolve needs --response (June's words, verbatim)", file=sys.stderr)
            sys.exit(1)
        flag = resolve_flag(args.resolve, args.response, action=args.action,
                            target_id=args.target)
        print(json.dumps({"resolved": flag["id"], "action": args.action,
                          "read_back": flag["resolution"]["read_back"]}, indent=2))
        sys.exit(0)

    mode = "run" if args.run else "preview" if args.preview else "dry-run"
    report = run_check(repo_dir=args.dir, project=args.project,
                       backend=args.backend, mode=mode)
    print(_format_report(report))
```

Adjust `build_findings` call inside `run_check` — it already takes `now=_now_for_findings()` as written above; no other change to earlier sections.

- [ ] **Step 4: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v` then `python3 -m pytest tests/ -q`
Expected: all PASS, no regressions, conftest tripwire silent (no real-data writes).

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/status_check.py tests/test_status_check.py
git commit -m "feat(status): orchestration + CLI — dry-run/preview/run, resolve, flags"
```

---

### Task 7: The map surfaces the checker — notice line in `whats_open.py`

The map is where June (and agents) already look; a flag store nobody surfaces is a built-but-dead piece. This is the in-repo call site that makes pending flags visible without any new surface.

**Files:**
- Modify: `scripts/whats_open.py` (function `whats_open`, lines 24–37)
- Test: `tests/test_status_check.py` (append)

**Interfaces:**
- Consumes: `status_check.status_notice()` (Task 6).
- Produces: `whats_open.whats_open(...)` output gains a trailing notice block when (and only when) there is something to say.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_status_check.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py -v -k "whats_open or notice"`
Expected: the two `whats_open` tests FAIL (no notice appended); notice tests PASS already (Task 6) — that's fine, keep them here as the surface's contract.

- [ ] **Step 3: Write the implementation**

In `scripts/whats_open.py`, replace the `whats_open` function body's return path:

```python
def whats_open(start_dir=".", project=None):
    if project:
        return _with_notice(render_map(project))
    ctx = load_context(start_dir)
    if not ctx or not ctx.get("projects"):
        return ("No Controlled Drift binding found for this directory.\n"
                "  - pass --project \"Project Name\" to render a specific project, or\n"
                "  - bind this repo first (invoke the drift skill and say \"bind this folder\").")
    blocks = []
    for p in ctx["projects"]:
        name = p.get("name")
        if name:
            blocks.append(render_map(name))
    out = "\n\n".join(blocks) if blocks else "(binding found, but no named project to render)"
    return _with_notice(out)


def _with_notice(map_text):
    """Append the status checker's notice (pending questions / overdue check) so the
    map itself says when its own statuses are in doubt. Nothing pending -> unchanged."""
    import status_check
    notice = status_check.status_notice()
    return f"{map_text}\n\n{notice}" if notice else map_text
```

(Import inside the function keeps `whats_open`'s module import light for the common path and avoids a cycle if `status_check` ever imports map helpers directly.)

- [ ] **Step 4: Run to verify pass** (main agent, Bash)

Run: `python3 -m pytest tests/test_status_check.py tests/ -q`
Expected: all PASS.

- [ ] **Step 5: Commit** (main agent, Bash)

```bash
git add scripts/whats_open.py tests/test_status_check.py
git commit -m "feat(status): the map surfaces pending status questions + an overdue checker"
```

---

### Task 8: Integration & end-to-end verification — the required final task (main agent, Bash, June in the loop)

**The real call sites this feature wires into** (naming them explicitly, per the build rule this repo just adopted):
1. **Scheduled entry point:** `~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist` → runs `python3 scripts/status_check.py --run --dir <repo>` monthly. launchd LaunchAgents are the scheduling mechanism this repo already uses (`com.june.controlled-drift.morning.plist` runs `morning_push.py` daily; `com.june.controlled-drift.server.plist` keeps the overlay server up) — copy the morning plist's structure, including its PATH fix. No cron is in use (the only crontab entry is a disabled Canvas job).
2. **Reading surface:** `scripts/whats_open.py` (wired in Task 7) — the map every agent and June already read now shows pending status questions.
3. **June's reply path:** `status_check.py --resolve` / `resolve_flag()`, invoked from a drift-skill conversation → `signal_log` (`checkin_reply`) + read-back-proven fixes.

**Files:**
- Create: `~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist`

- [ ] **Step 1: Live dry-run against the real system** (main agent, Bash — read-only)

```bash
python3 scripts/status_check.py --dry-run --dir /Users/june/Documents/GitHub/cyborg-memory/controlled-drift
```
Expected: real streams under "Build Controlled Drift" listed with real findings (e.g. "Keep work-stream statuses current" itself shows `● active`); zero writes (confirm `~/.controlled-drift/status_flags.json` and `status_check_last_run` do not exist yet).

- [ ] **Step 2: Live preview — LLM verdicts, zero writes** (main agent, Bash)

```bash
python3 scripts/status_check.py --preview --dir /Users/june/Documents/GitHub/cyborg-memory/controlled-drift
```
Expected: verdicts + gate decisions printed; any auto_fix visible for review; still no files written, no Anytype changes (re-run `python3 scripts/whats_open.py` — map unchanged).

- [ ] **Step 3: June reviews the preview — HUMAN GATE.** Show her the would-fix and would-flag lists in plain language. This is the memory-pass precedent (reviewed first run before the scheduled steady state) and the "June approves before it touches her space" discipline. Do not proceed without her go.

- [ ] **Step 4: Supervised first `--run`** (main agent, Bash)

```bash
python3 scripts/status_check.py --run --dir /Users/june/Documents/GitHub/cyborg-memory/controlled-drift
```
Verify, live:
- any applied fix: re-fetch the stream in Anytype (`python3 -c "import sys; sys.path.insert(0,'scripts'); import task_actions; print(task_actions._get_object('<id>'))"`) — Engagement really reads Done;
- flags landed: `python3 scripts/status_check.py --flags` prints plain-language questions;
- the map shows the notice: `python3 scripts/whats_open.py` ends with the "questions waiting" line;
- run log has the record: `tail -1 scripts/data/status_check_log.jsonl`;
- **idempotency:** run `--run` again immediately — expected: `auto_fixed 0`, no duplicate flags, no new mutations.

- [ ] **Step 5: Exercise the reply path once, for real** (with June) — she answers one flag in her own words:

```bash
python3 scripts/status_check.py --resolve <flag-id> --response "<her words verbatim>" --action leave
```
Verify: flag resolved (`--flags` no longer lists it), her words in `scripts/data/signal_log.jsonl` with `"source": "checkin_reply"`, map notice count drops.

- [ ] **Step 6: Create the scheduled entry point** — write `~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.june.controlled-drift.status-check</string>

  <!-- The monthly status check: keeps the work-stream map honest. Auto-fixes only
       positive-evidence cases; everything else becomes a question for June. -->
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/python3</string>
    <string>/Users/june/Documents/GitHub/cyborg-memory/controlled-drift/scripts/status_check.py</string>
    <string>--run</string>
    <string>--dir</string>
    <string>/Users/june/Documents/GitHub/cyborg-memory/controlled-drift</string>
  </array>

  <!-- CRITICAL (copied from the morning plist): launchd starts with a bare PATH. -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/june/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <!-- 1st of each month, 10:00 AM (after the 9 AM morning push). If the laptop is
       asleep, macOS runs it on next wake; if powered off, the month is skipped —
       the map's ">45 days" notice (whats_open.py) surfaces that, so a silent skip
       can't go unnoticed. Day/time = open question 3; move by editing + reloading. -->
  <key>StartCalendarInterval</key>
  <dict>
    <key>Day</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>10</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>/Users/june/.controlled-drift/status_check.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/june/.controlled-drift/status_check.err.log</string>
</dict>
</plist>
```

(The Mistral key resolves headless — `plan_generate._load_key` falls back to `~/Documents/.env`, same as the working morning push; no extra env vars needed.)

- [ ] **Step 7: Load + fire the scheduled job once, watched** (main agent, Bash)

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.june.controlled-drift.status-check.plist
launchctl kickstart gui/$(id -u)/com.june.controlled-drift.status-check
sleep 90
cat ~/.controlled-drift/status_check.log
cat ~/.controlled-drift/status_check.err.log
```
Expected: the log shows a completed run report under launchd's environment (PATH + key resolution proven, not assumed). Because Step 4 just ran, this fire should report `auto_fixed 0` and create no duplicate flags — the scheduled run re-proving idempotency IS the end-to-end verification that the wire-in works.

- [ ] **Step 8: Full suite + whole-branch review** (main agent, Bash)

```bash
python3 -m pytest tests/ -q
```
Expected: green, tripwire silent. Then the build-loop's final review: cross-family review of the branch (per repo convention, `~/.claude/skills/requesting-code-review/github_models_review.py`) — this code was Claude-generated.

- [ ] **Step 9: Close the loop in the system itself.** In a drift-skill session (not this plan's job to script): mark the "Keep work-stream statuses current" work-stream's steps done as they complete — the checker's own stream must not be the next thing the checker catches lying. Commit:

```bash
git add -A
git commit -m "feat(status): wire the monthly status check into launchd — end-to-end verified"
```

---

## Self-review notes (run after drafting — kept for the executor)

- Spec coverage: staleness (`neglect.find_neglected`, Task 1) ✓; status-vs-tasks mismatch (Task 1) ✓; reading commits (Tasks 1+3; depth of "investigation" flagged as open question 2's cousin — v1 is Python-gathered git log in the dossier, not a tool-wielding agent, which matches the repo's headless-LLM pattern and every scheduling precedent here) ✓; auto-fix-on-positive-evidence-only (Task 4, in code) ✓; flags-not-changes for absence/judgment (Tasks 4+5) ✓; June's responses logged (Task 5, `checkin_reply`) ✓; assembles `complete_task` + check-in design rather than inventing parallel mechanisms (Tasks 2/5 reuse; nothing new does what an existing piece does) ✓; scheduled ~monthly via the mechanism the repo already uses (Task 8) ✓; final integration-and-verify task with named call sites ✓.
- Type consistency: verdict/finding/flag dict shapes are defined once (Tasks 1, 3, 5 Interfaces) and used identically in Tasks 4, 6, 7 tests.
- The one intentional deviation from bite-size: Tasks build one module cumulatively; each task's code block is complete and self-contained for its section, so out-of-order reading still works.
