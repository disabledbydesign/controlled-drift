#!/usr/bin/env python3
"""Monthly status checker — keeps the work-stream map honest.

The map (whats_open.py) SHOWS each stream's status; nothing kept it TRUE. Statuses
drift until the map lies and June stops trusting the one surface built so she doesn't
have to hold state in her head. This checker compares each work-stream's recorded
status against evidence: staleness (the surface log), status-vs-open-tasks mismatch,
and the repo's recent commits.

THE SAFETY LINE (decided by June, 2026-07-11 — do not weaken):
  AUTO-FIX only with concrete POSITIVE evidence of the true state — i.e. marking
  demonstrably-finished work as Done, with commit citations Python itself verifies.
  Everything resting on absence-of-evidence or judgment (stale, can't-confirm,
  done-but-tasks-open) is FLAGGED for June and never changed. Auto-marking from
  absence would let a wrong guess silently become the record — the map lying a new
  way. The asymmetry lives in gate_verdicts(), in code, not just in the prompt.

STALENESS SOURCE (REVISED 2026-07-12 — verified finding):
  Anytype's "Last surfaced" field is dead on the live path (written only by a CLI
  flow June doesn't use: 5 of 137 tasks, none newer than 2026-06-18). Trusting it
  would flag nearly every stream on the first run. The live source is the append-only
  surface log (scripts/data/surface_log.jsonl) — every generated plan writes it. A
  stream's effective last-surfaced = the newest surface-log timestamp across its own
  tasks; the Anytype field is only a fallback when the log has nothing. A stream with
  NO surfacing data anywhere is not "stale" (that's absence, not an old date) — it gets
  the no_surfacing_history kind, and on the first run those collapse into ONE aggregate
  note for June instead of a flood of individual flags.

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

FINDING_KINDS = ("done_with_open_tasks", "active_all_tasks_done", "no_tasks", "stale",
                 "no_surfacing_history")

# Engagement values that mean "deliberately parked" — silence there is honest, not drift.
_PARKED = ("Backburner",)


# --- layer 1: evidence ---------------------------------------------------------

def _surface_log_dates(path=None):
    """task_id -> most-recent surfaced datetime, from the append-only surface log.

    REVISED 2026-07-12: this is the LIVE staleness source. Anytype's 'Last surfaced'
    field is written only by an interactive CLI path June doesn't use (5 of 137 tasks,
    none newer than 2026-06-18), so trusting it would flag nearly every stream. The
    surface log is append-only and current — every generated plan writes it via
    surface_log.log_surfaced_batch. Naive datetimes (the log writes local isoformat);
    a malformed line is skipped, never fatal (an unreadable line must not blind the
    whole staleness read)."""
    p = path or cd_paths.data_file("surface_log.jsonl")
    out = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                tid, ts = rec.get("id"), rec.get("ts")
                if not tid or not ts:
                    continue
                try:
                    when = dt.datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    continue
                if when.tzinfo is not None:
                    when = when.replace(tzinfo=None)
                if tid not in out or when > out[tid]:
                    out[tid] = when
    except FileNotFoundError:
        pass
    return out


def _effective_last_surfaced(tasks, surface_dates, anytype_ls):
    """The stream's last-surfaced date + where it came from. The surface log wins; the
    Anytype field is used only when NO task of this stream appears in the log. Returns
    (datetime|None, "log"|"anytype"|None). None source == no surfacing data anywhere —
    that is absence, not staleness (see build_findings)."""
    log_hits = [surface_dates[t["id"]] for t in tasks if t.get("id") in surface_dates]
    if log_hits:
        return max(log_hits), "log"
    if anytype_ls is not None:
        return anytype_ls, "anytype"
    return None, None


def load_streams(project_name):
    """All work-streams (nested Projects) under `project_name`, with status + tasks +
    effective last-surfaced date — everything the findings + the dossier need. One
    Anytype read; the surface log is read once and joined per stream."""
    goals, projects, tasks = orient_map._load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        raise RuntimeError(f"status_check: no project named {project_name!r} in the space")
    surface_dates = _surface_log_dates()
    streams = []
    for s in orient_map._all_sub_projects(proj["id"], projects):
        props = orient_map._props(s)
        by_name = {p.get("name"): p for p in s.get("properties", [])}
        raw_ls = (by_name.get("Last surfaced") or {}).get("date")
        anytype_ls = neglect._parse_date(raw_ls)
        steps = orient_map._steps_for(s["id"], tasks)
        eff_ls, ls_source = _effective_last_surfaced(steps, surface_dates, anytype_ls)
        streams.append({
            "id": s["id"],
            "name": s.get("name", ""),
            "engagement": orient_map._sel(props, "engagement"),
            "context": orient_map._txt(props, "gsdo_context"),
            "last_surfaced": eff_ls,
            "last_surfaced_source": ls_source,
            "anytype_last_surfaced": anytype_ls,
            "tasks": steps,
        })
    return streams


def build_findings(streams, now=None):
    """Pure. The deterministic mismatch detectors — facts only, no judgment.

    Kinds:
      done_with_open_tasks  - engagement says Done but open tasks remain (map may lie "done")
      active_all_tasks_done - active, has tasks, every one Done (map may lie "in progress")
      no_tasks              - active but no steps recorded (nothing to check it against)
      stale                 - active, KNOWN last-surfaced date older than STALE_DAYS
                              (absence-of-evidence: can ONLY ever feed a flag, never
                              an auto-fix)
      no_surfacing_history  - active, has tasks, but NO surfacing data in either source
                              (REVISED 2026-07-12): distinct from stale — it is absence,
                              not an old date. First-run mass case; the aggregate note
                              absorbs these instead of one flag per stream.
    Done and Backburner streams are exempt from the absence-based kinds — a finished or
    deliberately-parked stream being quiet is honest, and nagging it is the scold the
    check-in design forbids. `last_surfaced` is already the EFFECTIVE date (resolved in
    load_streams: surface log first, Anytype field only as fallback).
    """
    now = now or dt.datetime.now()
    cutoff = now - dt.timedelta(days=STALE_DAYS)
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
            else:
                ls = s.get("last_surfaced")
                if ls is None:
                    kinds.append("no_surfacing_history")
                elif ls < cutoff:
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
    "no_surfacing_history":
        "“{name}” has never come up in a plan yet. Still current, or should it move "
        "to later?",
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


# The aggregate first-run note (REVISED 2026-07-12). A stable synthetic stream_id so the
# no-repeat-nagging dedup treats the aggregate like any other pending flag: surfaced once,
# never re-nagged while it stays open.
_NO_SURFACING_ID = "__no_surfacing_history__"


def record_no_surfacing_flag(count, names, path=None):
    """ONE aggregate question for the streams that have never come up in a plan, instead
    of one flag per stream (which on a first run would flood June — exactly the noise the
    revised staleness source exists to prevent). No-op when count is 0 or an aggregate is
    already pending. Returns the new flag or None."""
    if count <= 0:
        return None
    data = load_flags(path)
    if any(f["stream_id"] == _NO_SURFACING_ID and f.get("status") == "pending"
           for f in data["flags"]):
        return None
    word = "work stream has" if count == 1 else "work streams have"
    flag = {
        "id": f"{dt.date.today().isoformat()}-nosurface",
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "stream_id": _NO_SURFACING_ID,
        "stream_name": "(never surfaced)",
        "kinds": ["no_surfacing_history"],
        "june_line": (f"{count} {word} never come up in a plan yet. "
                      "Want to look at them together sometime?"),
        "agent_detail": {"count": count, "stream_names": list(names)},
        "status": "pending",
        "resolution": None,
    }
    data["flags"].append(flag)
    save_flags(data, path)
    return flag


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
    log_run({"event": "flag_resolved", "flag_id": flag_id, "action": action})
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


def _split_no_surfacing(findings):
    """Partition findings for the first-run grace (REVISED 2026-07-12). A stream whose
    ONLY finding is 'no_surfacing_history' has never come up in a plan — there is no
    evidence for the LLM to weigh (git can't show work on a never-surfaced stream), so
    it stays out of the dossier and joins the ONE aggregate note. Streams that ALSO have
    a real mismatch keep going through the normal path."""
    no_surf, actionable = [], []
    for f in findings:
        if f["kinds"] == ["no_surfacing_history"]:
            no_surf.append(f)
        else:
            actionable.append(f)
    return actionable, no_surf


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
             "flagged": 0, "downgraded": 0, "failed": 0, "malformed": 0,
             "no_surfacing": 0}
    results = []
    no_surfacing_names = []
    for pname in project_names:
        streams = load_streams(pname)
        findings = build_findings(streams, now=_now_for_findings())
        actionable, no_surf = _split_no_surfacing(findings)
        tally["streams"] += len(streams)
        tally["findings"] += len(findings)
        tally["no_surfacing"] += len(no_surf)
        no_surfacing_names += [f["stream_name"] for f in no_surf]
        result = {"project": pname, "findings": findings,
                  "no_surfacing": [f["stream_name"] for f in no_surf]}

        if mode != "dry-run" and actionable:
            git_log = gather_git_evidence(repo_dir)
            map_text = orient_map.render_map(pname)
            prompt = _assemble_prompt(pname, streams, actionable, git_log, map_text)
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
        agg_flag = record_no_surfacing_flag(tally["no_surfacing"], no_surfacing_names)
        n_agg = 1 if agg_flag else 0
        log_run({"event": "run", **tally,
                 "applied": [r for res in results for r in res.get("applied", [])],
                 "downgraded": [{"stream_id": v["stream_id"],
                                 "reason": v["downgrade_reason"]}
                                for res in results
                                for v in res.get("gated", {}).get("downgraded", [])]})
        total_new = sum(len(res.get("new_flags", [])) for res in results) + n_agg
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
                 f"malformed {t['malformed']} · never-surfaced {t['no_surfacing']}")
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
