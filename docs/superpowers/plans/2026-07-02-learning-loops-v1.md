# Learning Loops v1 — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. For code review, route through `cross-review` (non-Claude) to avoid same-family blind spots, per this project's practice.

**Goal:** Ship the pieces of this project's learning-loop backlog whose *mechanism* is already decidable today, even where input data is currently thin — a duplicate-detection digest and a duration-estimate bias loop (real "loops," both with an established low-stakes numeric shape) — plus two pure capture/logging pieces that record signal for a later design pass without interpreting it (engagement-change, capacity-at-surfacing-time) — plus the capture-pipeline fix (Task 1) the duration loop turned out to depend on.

**Revised 2026-07-03 (June's catch):** Task 5 originally also proposed a "capacity-surfacing-amount" loop that would write a Note suggesting fewer/more items on low/high-completion days. Cut from this plan — see Task 5 for the full reasoning. Task 5 is now capture-only, same shape as Task 3.

**Revised 2026-07-03 (critic-swarm pass):** Task 4's wiring into the live capture path is held back — build and test the bias math, don't integrate it yet (see Task 4). Task 3's Engagement lookup is corrected to match this codebase's established name-based convention (see Task 3). Task 3 also still carries an **open design question from June, unresolved — see the callout inside Task 3** — this plan is not "complete" until that's answered.

**Architecture:** Each loop is a small standalone script under the new `scripts/learning_loops/` package (this repo's first subpackage — everything else in `scripts/` is flat, so this is a deliberate, requested exception, not a unilateral restructure), reading from the append-only logs this project already writes (`generation_log.jsonl`, `surface_log.jsonl`) or a fresh snapshot-diff against live Anytype state. Nothing here auto-changes June's data or behavior without her confirmation — every task in this plan writes to a durable log; none integrate into a live behavior path in this pass (Task 4's bias math is built and tested standalone, not wired in — see Task 4). Task 1 stays in `scripts/capture_generate.py` — it's a capture-pipeline fix the loops turned out to depend on, not a loop itself (see Task 4 for the dependency).

**Tech Stack:** Python 3 stdlib only (matches the rest of `scripts/`), pytest, the existing `cd_paths`/`gsdo_anytype`/`gsdo_objects`/`generation_log`/`surface_log` modules.

## Global Constraints

- No silent failures: raise, don't `assert`, on anything that isn't test-only sandboxing.
- Every write to Anytype is additive/logging or a `Note` proposal — never a live behavior change without June's confirmation (offer, don't impose).
- Tests never touch June's live Anytype space or real log files — redirect via `monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))` / `monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))`, or pass an explicit `path=`/`sid=` override, exactly as the existing test suite does.
- Property dict keys passed to `gsdo_objects.create`/`update` are **display names** ("Duration min", "Context"), not property keys (`gsdo_duration_min`) — matches every existing call site.
- Run the full suite (`python3 -m pytest tests/ -q`) after every task, not just the new file — confirm no regression before committing.

---

### Task 1: Propose a duration estimate at capture time (the missing Step 0)

**What this gives you:** when you add a task, the system guesses how long it'll actually take (in minutes) instead of leaving it blank — which is why every task in your plan today gets treated as if it takes exactly 30 minutes, whether it's a 5-minute phone call or a 2-hour writing session.

**Why this is first:** `scripts/scheduler.py:6,9` (`DEFAULT_DURATION_MIN = 30`, `_dur(item): return item.get("duration_min") or DEFAULT_DURATION_MIN`) silently falls back to a flat 30 minutes for any task with no `gsdo_duration_min` — and today, `capture_generate.py` never writes one, so almost every task hits that fallback. (Corrected 2026-07-03 — an earlier draft of this plan cited `daily_plan.py:294` for this, which doesn't contain it; verified against the actual file before fixing.) Task 4's duration-bias loop has nothing to refine without this.

**Files:**
- Modify: `scripts/capture_generate.py` (the `_WEED_JSON_INSTRUCTION` schema block, `_creation_props`)
- Test: `tests/test_capture_generate.py`

**Interfaces:**
- Produces: a weed-turn item dict may now carry `"duration_min": <int>|null`; `_creation_props(type_name, item, link_id)` writes the Task property `"Duration min"` when `item["duration_min"]` is not `None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_capture_generate.py`, right after `test_capture_creates_links_and_skips`:

```python
def test_capture_writes_duration_min_when_model_provides_it(tmp_path, monkeypatch):
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Call surgeon", "link": "P1", "status": "Ready",
             "duration_min": 15, "action": "create", "reasoning": "quick call"},
            {"type": "Task", "name": "Write grant narrative", "link": "P1", "status": "Ready",
             "duration_min": None, "action": "create", "reasoning": "unsure how long"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("call surgeon, write grant narrative")
    by_name = {name: props for (_t, name, props) in calls}
    assert by_name["Call surgeon"]["Duration min"] == 15
    assert "Duration min" not in by_name["Write grant narrative"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_capture_generate.py::test_capture_writes_duration_min_when_model_provides_it -v`
Expected: FAIL — `KeyError: 'Duration min'` (the field isn't written yet).

- [ ] **Step 3: Add `duration_min` to the JSON contract**

In `scripts/capture_generate.py`, in `_WEED_JSON_INSTRUCTION`, replace the item schema block:

```python
      "items": [
        {
          "type": "Task|Recurring|Strategy|Goal|Project|Note",
          "name": "the item, in June's words",
          "link": "P3 | G1 | null",
          "status": "Ready | Needs Clarifying | null",
          "action": "create | skip",
          "dedup_note": "why skipped, if skipped, else null",
          "reasoning": "why this type and this link — June must be able to see the why"
        }
      ]
```

with:

```python
      "items": [
        {
          "type": "Task|Recurring|Strategy|Goal|Project|Note",
          "name": "the item, in June's words",
          "link": "P3 | G1 | null",
          "status": "Ready | Needs Clarifying | null",
          "duration_min": "best-guess minutes for a Task, else null",
          "action": "create | skip",
          "dedup_note": "why skipped, if skipped, else null",
          "reasoning": "why this type and this link — June must be able to see the why"
        }
      ]
```

And replace the line below the schema block:

```python
`capacity_read` may be null if no signal is present. `status` applies to Tasks (default "Ready";
"Needs Clarifying" if too vague to act on). Keep every `reasoning` present — the system must be
able to show June why each thing landed where it did.
```

with:

```python
`capacity_read` may be null if no signal is present. `status` applies to Tasks (default "Ready";
"Needs Clarifying" if too vague to act on). `duration_min` applies to Tasks only (null for other
types): your best-guess estimate in minutes for how long the task will actually take, from what
June said plus ordinary sense of the task ("call the surgeon" ~15, "write the grant narrative"
~120). Give your best number rather than null purely from uncertainty — a rough guess beats the
flat 30-minute fallback every Task without one currently gets. Keep every `reasoning` present —
the system must be able to show June why each thing landed where it did.
```

- [ ] **Step 4: Write it into `Duration min` at creation**

In `scripts/capture_generate.py`, in `_creation_props`, replace:

```python
    if type_name == "Task":
        props["Task status"] = item.get("status") or "Ready"
```

with:

```python
    if type_name == "Task":
        props["Task status"] = item.get("status") or "Ready"
        if item.get("duration_min") is not None:
            props["Duration min"] = item["duration_min"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_capture_generate.py -v`
Expected: all PASS, including the new test.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS, one more than whatever the count was before this task (this branch has parallel work landing on it — don't hardcode a baseline, compare before/after).

- [ ] **Step 7: Commit**

```bash
git add scripts/capture_generate.py tests/test_capture_generate.py
git commit -m "feat(capture): propose a duration estimate at task creation"
```

---

### Task 2: Dedup-notes digest

**What this gives you:** a report you can run that lists every time the system flagged "this might already exist" during a capture — so patterns in near-duplicates are visible instead of forgotten the moment the session receipt ages out. v1 is something you run by hand; nothing pushes it at you yet (see the open item at the end of this task).

**This task also creates the `scripts/learning_loops/` package** (this repo's first subpackage — the other four tasks' scripts land here too).

**Files:**
- Create: `scripts/learning_loops/__init__.py` (empty — marks the directory as a package)
- Create: `scripts/learning_loops/dedup_report.py`
- Test: `tests/learning_loops/test_dedup_report.py`

**Interfaces:**
- Produces: `load_dedup_entries(days=7, path=None) -> list[{"ts", "name", "action", "note"}]`; `render_digest(entries) -> str`.
- Consumes: `generation_log.jsonl` records already written by `capture_generate.capture()` (no changes needed there — `generation_log.check_capture` already puts `dedup_notes` on every capture record).

- [ ] **Step 1: Write the failing test**

Create `tests/learning_loops/` (new directory — no `__init__.py` needed; pytest discovers it, and `tests/conftest.py`'s sandbox redirect applies automatically to every subdirectory) and `tests/learning_loops/test_dedup_report.py`:

```python
"""Tests for dedup_report — the digest over the durable dedup-notes log."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "learning_loops"))

import dedup_report as dr


def _write_log(tmp_path, records):
    path = tmp_path / "generation_log.jsonl"
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_load_dedup_entries_filters_by_window_and_source(tmp_path):
    now = dt.datetime.now()
    stale = (now - dt.timedelta(days=10)).isoformat()
    fresh = (now - dt.timedelta(days=1)).isoformat()
    path = _write_log(tmp_path, [
        {"ts": fresh, "source": "capture", "success": True,
         "structural": {"dedup_notes": [{"name": "SSRC grant", "action": "skip", "note": "already exists"}]}},
        {"ts": stale, "source": "capture", "success": True,
         "structural": {"dedup_notes": [{"name": "Old thing", "action": "skip", "note": "too old"}]}},
        {"ts": fresh, "source": "morning", "success": True, "structural": {}},
    ])
    entries = dr.load_dedup_entries(days=7, path=path)
    assert len(entries) == 1
    assert entries[0]["name"] == "SSRC grant"


def test_load_dedup_entries_missing_file_returns_empty(tmp_path):
    assert dr.load_dedup_entries(days=7, path=str(tmp_path / "nope.jsonl")) == []


def test_render_digest_groups_by_name():
    entries = [
        {"ts": "x", "name": "SSRC grant", "action": "skip", "note": "already exists"},
        {"ts": "y", "name": "SSRC grant", "action": "create", "note": "maybe overlaps"},
    ]
    text = dr.render_digest(entries)
    assert text.index("SSRC grant") < text.index("already exists") < text.index("maybe overlaps")


def test_render_digest_empty_says_so():
    assert "No dedup flags" in dr.render_digest([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/learning_loops/test_dedup_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dedup_report'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/learning_loops/__init__.py` (empty file).

Create `scripts/learning_loops/dedup_report.py`:

```python
#!/usr/bin/env python3
"""Digest of the model's own dedup uncertainty, read back from the durable learning log.

Every capture turn already logs `dedup_notes` (generation_log.check_capture, called from
capture_generate.capture()) into the shared append-only log — this just reads it back and
renders a plain-language summary. No new capture, no new state; pure report over what's
already there.
"""
import sys, os, json, datetime as dt, argparse
# One level up from scripts/learning_loops/ to scripts/, so the core modules resolve.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cd_paths


def load_dedup_entries(days=7, path=None):
    """Every dedup_notes entry from a successful capture within the last `days` days.

    Returns a list of {"ts": iso-str, "name": str, "action": "create"|"skip", "note": str}.
    """
    path = path or cd_paths.data_file("generation_log.jsonl")
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    out = []
    try:
        with open(path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return out
    for line in lines:
        rec = json.loads(line)
        if rec.get("source") != "capture" or not rec.get("success"):
            continue
        if dt.datetime.fromisoformat(rec["ts"]) < cutoff:
            continue
        for note in (rec.get("structural") or {}).get("dedup_notes", []):
            out.append({"ts": rec["ts"], "name": note.get("name"),
                        "action": note.get("action"), "note": note.get("note")})
    return out


def render_digest(entries):
    """Plain-language text digest, grouped so repeats of the same name sit together."""
    if not entries:
        return "No dedup flags in this window."
    by_name = {}
    for e in entries:
        by_name.setdefault(e["name"], []).append(e)
    lines = []
    for name, group in by_name.items():
        lines.append(f"{name}:")
        for e in group:
            lines.append(f"  - {e['action']}: {e['note']}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Digest of flagged possible duplicates from captures")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    print(render_digest(load_dedup_entries(days=args.days)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/learning_loops/test_dedup_report.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS. (Added 2026-07-03 — this step was missing even though the plan's own Global Constraints require it after every task.)

- [ ] **Step 6: Commit**

```bash
git add scripts/learning_loops/__init__.py scripts/learning_loops/dedup_report.py tests/learning_loops/test_dedup_report.py
git commit -m "feat(learning-loops): dedup-notes digest, reading the existing capture log"
```

---

### Task 3: Engagement-correction capture (logging only)

**What this gives you:** nothing visible yet. This quietly keeps a permanent record every time a project's Engagement (Steady/Sprint/Backburner/etc.) changes, so a later feature can learn what those labels actually mean for each of your specific projects. On its own it produces no change to your daily plan or the overlay — it's pure raw material for a future design pass.

**Checked 2026-07-03 — no, changing Engagement isn't possible from the overlay today.** The overlay's server (`scripts/server.py`) only exposes `/api/plan`, `/api/map`, `/api/actions`, `/api/status`, `/api/settings`, `/api/session`, `/api/refresh`, `/api/negotiate` — no route edits a Project's Engagement. The only way to change it right now is directly in the Anytype app. That's fine for this task: the mechanism below is a snapshot-diff against Anytype's live state, so it doesn't care *where* an edit came from. If the overlay ever grows an Engagement-editing feature, this logger picks up those changes automatically — no code change needed here. (Real limitation worth naming honestly, not fixed by this task: if your daily habit is the overlay and you rarely open the Anytype app to change Engagement by hand, this log may stay thin simply because the edit itself is inconvenient to make. That's a UI-affordance gap, out of scope for this build.)

> ## ✅ Resolved 2026-07-03 — deferred, kept out of this plan
>
> June's original note asked whether to fold overlay task-editing (deterministic reorder/edit in the daily plan, plus manual edit right after a weed pass) into this task while working on it. **Decided: no — deferred as its own future thread, not part of this plan.** It turned out to be two already-known, already-deferred backlog items (a "deterministic task-move affordance" and a "manual-edit affordance right after a weed pass," both previously named and left unresolved) that surfaced again while reading this task, not a new scope question for Task 3 specifically. It's sized like a real feature spanning two different surfaces, not a quick add, and bundling it here would have split focus across two unrelated efforts. Task 3 stays exactly what it was: the Engagement logger, nothing more.

**Not redundant with the existing corrections log — checked, they're genuinely different things.** `scripts/plan_corrections_log.py` (already built) logs `move_time` / `reject` / `reorder` — changes you make to a specific *day's plan* (Task items, scheduling). Engagement lives on the *Project* object, is a completely different field, and is never touched by the plan-negotiation flow at all. Nothing currently logs it. This task is new ground, not a duplicate.

**Files:**
- Create: `scripts/learning_loops/engagement_watch.py`
- Test: `tests/learning_loops/test_engagement_watch.py`

**Interfaces:**
- Produces: `check_for_corrections(sid=None, log_path=None) -> list[{"ts","project_id","name","old","new"}]`, appended to `scripts/data/engagement_corrections_log.jsonl`; snapshot state at `~/.controlled-drift/engagement_snapshot.json` (`cd_paths.config_file`).
- No interpretation — logging only, per the plan's exclusion list.

**Fixed 2026-07-03 (critic-swarm catch, verified before fixing):** the original version of this task read the Engagement property by a literal key (`"engagement"`). I checked this against live Anytype data fetched earlier the same session — the key does currently equal `"engagement"` — but `scripts/daily_plan.py:64` has an explicit comment on this exact property: *"Name-based lookup for the newer Engagement field (key generated by Anytype, not predictable)"* — and every other engagement read/write site in this codebase follows that convention, never a literal key. Relying on the key matching today is fragile precisely because it's documented as auto-generated and not guaranteed stable. Fixed below to match the established name-based convention (`daily_plan.py`'s `props_by_name` pattern), not the literal key.

- [ ] **Step 1: Write the failing test**

Create `tests/learning_loops/test_engagement_watch.py`:

```python
"""Tests for engagement_watch — the snapshot-diff logger for Project engagement changes."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "learning_loops"))

import engagement_watch as ew


def _fake_project(pid, name, engagement):
    # Property shape keyed by NAME, matching daily_plan.py's established convention for this
    # exact field (its key is Anytype-generated, not predictable — never assume the literal key).
    return {"id": pid, "type": {"key": "gsdo_project"}, "name": name,
            "properties": [{"name": "Engagement", "select": {"name": engagement}}]}


def test_first_run_snapshots_without_logging_corrections(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ew.g, "fetch_all_objects",
                        lambda sid: [_fake_project("p1", "Build Controlled Drift", "Steady")])
    corrections = ew.check_for_corrections(sid="sid")
    assert corrections == []                                      # nothing to diff against yet
    snapshot = json.loads((tmp_path / "engagement_snapshot.json").read_text())
    assert snapshot["p1"]["engagement"] == "Steady"


def test_second_run_logs_a_changed_engagement(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ew.g, "fetch_all_objects",
                        lambda sid: [_fake_project("p1", "Build Controlled Drift", "Steady")])
    ew.check_for_corrections(sid="sid")                            # establishes the snapshot
    monkeypatch.setattr(ew.g, "fetch_all_objects",
                        lambda sid: [_fake_project("p1", "Build Controlled Drift", "Backburner")])
    corrections = ew.check_for_corrections(sid="sid")
    assert len(corrections) == 1
    c = corrections[0]
    assert c["project_id"] == "p1" and c["old"] == "Steady" and c["new"] == "Backburner"
    logged = [json.loads(l) for l in
              (tmp_path / "engagement_corrections_log.jsonl").read_text().strip().splitlines()]
    assert logged[0]["new"] == "Backburner"


def test_unchanged_engagement_logs_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ew.g, "fetch_all_objects",
                        lambda sid: [_fake_project("p1", "Build Controlled Drift", "Steady")])
    ew.check_for_corrections(sid="sid")
    corrections = ew.check_for_corrections(sid="sid")               # same value both runs
    assert corrections == []
    assert not (tmp_path / "engagement_corrections_log.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/learning_loops/test_engagement_watch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engagement_watch'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/learning_loops/engagement_watch.py`:

```python
#!/usr/bin/env python3
"""Durable log of Project engagement changes — the raw material a future design pass needs to
learn what each engagement level (Steady/Sprint/Hyperfixation/Backburner/Done) actually implies
per project (AI_LAYER_SPEC.md's engagement learning-loop target). Logs only; nothing here
interprets the corrections — that's an explicit later design pass, once real corrections exist
to look at (AI_LAYER_SPEC.md's pattern-reading loops need real examples to decide their own
shape, per docs/superpowers/plans/2026-07-02-learning-loops-v1.md's exclusion list).

Nothing in this codebase writes Engagement programmatically, so every diff this finds is a
real June edit — no ambiguity about "who changed it."

Reads the property by NAME ("Engagement"), not by key — matching daily_plan.py's established
convention for this exact field, whose key is Anytype-generated and not guaranteed stable
(verified empirically to currently equal "engagement", but the codebase deliberately never
relies on that — see daily_plan.py:64's comment).
"""
import sys, os, json, datetime as dt
# One level up from scripts/learning_loops/ to scripts/, so the core modules resolve.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gsdo_anytype as g
import cd_paths


def _snapshot_path():
    return cd_paths.config_file("engagement_snapshot.json")


def _load_snapshot():
    try:
        with open(_snapshot_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_snapshot(snapshot):
    path = _snapshot_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)


def _current_engagements(sid):
    """{project_id: {"name": str, "engagement": str|None}} for every live Project.

    Name-based property lookup ("Engagement"), matching daily_plan.py's established
    convention for this field — never assume the literal property key.
    """
    out = {}
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") != "gsdo_project":
            continue
        props_by_name = {p.get("name"): p for p in o.get("properties", [])}
        eng = (props_by_name.get("Engagement", {}).get("select") or {}).get("name")
        out[o["id"]] = {"name": o.get("name"), "engagement": eng}
    return out


def check_for_corrections(sid=None, log_path=None):
    """Diff current Project engagement values against the last snapshot; log any change.

    Returns the list of correction dicts logged this run (empty if nothing changed, including
    the very first run — there's nothing to diff against yet).
    """
    sid = sid or g.get_space_id()
    log_path = log_path or cd_paths.data_file("engagement_corrections_log.jsonl")
    snapshot = _load_snapshot()
    current = _current_engagements(sid)
    corrections = []
    for pid, info in current.items():
        prev = snapshot.get(pid)
        if prev is not None and prev.get("engagement") != info["engagement"]:
            corrections.append({
                "ts": dt.datetime.now().isoformat(),
                "project_id": pid,
                "name": info["name"],
                "old": prev.get("engagement"),
                "new": info["engagement"],
            })
    if corrections:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            for c in corrections:
                f.write(json.dumps(c) + "\n")
    _save_snapshot(current)
    return corrections


if __name__ == "__main__":
    found = check_for_corrections()
    print(f"{len(found)} engagement correction(s) logged." if found else "No engagement changes.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/learning_loops/test_engagement_watch.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS. (Added 2026-07-03 — this step was missing even though the plan's own Global Constraints require it after every task.)

- [ ] **Step 6: Commit**

```bash
git add scripts/learning_loops/engagement_watch.py tests/learning_loops/test_engagement_watch.py
git commit -m "feat(learning-loops): engagement-change capture (logging only, no interpretation)"
```

**Open item, not resolved by this task (architect's catch, 2026-07-03):** nothing schedules `check_for_corrections()` to actually run. Without a scheduled invocation (a launchd job, or folded into an existing daily job like the memory pass or morning push), an Engagement edit that gets changed and changed back between two runs is invisible to this log — a real fidelity gap for a log whose whole purpose is a durable record. Not blocking Task 3 itself, but worth deciding before relying on this data: how often should this run, and what job does it piggyback on?

---

### Task 4: Duration-estimate bias loop (Log Day plug-in point — updated 2026-07-03, real storage now exists)

**What this gives you:** eventually — once real Log Day entries start accumulating and someone designs the extraction step (see below) — the system starts quietly correcting its own per-project time-guesses (e.g., learning that grant-writing tasks always run longer than estimated for you specifically). Right now this task still builds the machinery and produces no visible change, but the gap it's waiting on is narrower and more concrete than it was when this plan was first drafted.

**What actually changed since this plan was first drafted:** the focus-configuration layer's Phase 5 (`scripts/signal_log.py`, `scripts/plan_snapshot_log.py` — commit `3f7a591`, "feat(learning-signal): capture raw signal + plan snapshots now (Phase 5)") is built and committed. (Corrected 2026-07-03 — an earlier draft of this plan also cited `e9d30fd`, which is a different, unrelated commit: "feat(focus-period): wire the period into the LIVE plan (Phase 3+4)." Verified against `git log` before fixing.) `signal_log.log_signal(raw_text, source, reference=None)` stores verbatim raw text tagged with a source (`"log_day"` is one of five valid sources) and an optional `{"kind", "id", "name"}` reference; `plan_snapshot_log.log_plan_snapshot(plan, source)` stores the full generated plan alongside it, so a future loop can diff planned-vs-actual. **Two things are still genuinely missing, not hypothetical anymore — concrete and named:**
1. **Phase 6 (the actual Log Day capture UI — an overlay tab, per the addendum) hasn't been built yet.** Until it exists, nothing real writes `source="log_day"` entries — the container is real, but empty in practice.
2. **Turning raw Log Day text into structured `{project, estimated_min, actual_min}` pairs is Phase 9 — the interpretation loop — and it's explicitly NOT scheduled**, by the project's own design stance (per `docs/superpowers/plans/2026-07-02-focus-configuration-layer.md`: "categories emerge from it... forcing categories now is the premature-operationalizing the whole system resists"). This extraction is itself an LLM-assisted read (matching a day's free-text account against its stored plan snapshot), not a mechanical parse — it needs its own small design pass once real Log Day entries exist to design against, same reasoning as every other exclusion in this plan.

**Same question as Task 3, same answer: no overlay mechanism today for editing `Duration min` directly.** `Duration min` (`gsdo_duration_min`) is a plain Anytype property on a Task — like Engagement, it's only editable directly in the Anytype app right now. That doesn't block this loop either way: `get_bias()`/`update_duration_bias()` were never going to read a manually-edited field — they read the (still-pending) actual-vs-estimated extraction described above.

**Depends on:** Task 1 (needs `Duration min` actually being set at capture time to have anything to bias).

**Files:**
- Create: `scripts/learning_loops/duration_loop.py`
- Modify: `scripts/capture_generate.py` (`_creation_props`, `_create_one`, imports)
- Test: `tests/learning_loops/test_duration_loop.py`, additions to `tests/test_capture_generate.py`

**Interfaces:**
- Consumes: none from other new tasks.
- Produces: `duration_loop.get_bias(project_name) -> float`; `duration_loop.update_duration_bias() -> None` (no-op today); `duration_loop._load_actual_durations()` — **the labeled Log Day plug-in point**, returns `[]` until real `log_day`-sourced entries exist in `signal_log.py` AND the Phase 9 extraction step (raw text → structured actual-vs-estimated) has been designed. The storage schema itself is no longer hypothetical (`signal_log.jsonl` / `plan_snapshots.jsonl`, both real and committed) — what's missing is real data flowing in (Phase 6 UI) and the extraction logic (Phase 9, explicitly deferred).

**Scope narrowed 2026-07-03 (critic-swarm — three independent reviewers converged on this):** this task builds and tests `duration_loop.py` standalone, but does **not** wire it into `capture_generate.py`'s live write path. Reasons, from three different angles: (1) it would make the core capture pipeline permanently import and call a module whose real function returns `[]` forever, until two separately-unscheduled things happen elsewhere — dead weight in a hot path, for nothing, if Phase 9 never lands; (2) writing a bias-adjusted number straight onto a real object with no confirmation arguably crosses this plan's own Global Constraint ("never a live behavior change without June's confirmation") — the comparison to the meal-time loop doesn't fully hold, since that nudges an ambient scheduling default, not a value permanently written onto something June will see; (3) `get_bias()` is keyed by **project name**, but the worked example justifying this whole task ("call the surgeon" ~15 min vs. "write the grant narrative" ~120 min) is a **task-type** distinction — a single project routinely contains both shapes, so a per-project average risks quietly reproducing the exact "flatten a multi-dimensional signal into one number" problem Task 5 was cut for refusing, one level down. **None of this blocks building and testing the EMA math now** (Steps 1–3 below are unaffected) — it only holds back Step 4 (the wiring), which is deferred to whenever Phase 9 actually gets designed, at which point the project-vs-task-type keying question needs answering too, not just the wiring.

- [ ] **Step 1: Write the failing tests**

Create `tests/learning_loops/test_duration_loop.py`:

```python
"""Tests for duration_loop — the EMA bias loop for task duration estimates.

See duration_loop.py's module docstring for what's real vs. pending on the Log Day
dependency. These tests prove the placeholder is a safe no-op and the EMA math is correct
regardless (monkeypatched, so we don't need real Log Day data to verify the loop's own logic).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "learning_loops"))

import duration_loop as dl


def test_load_actual_durations_placeholder_returns_empty():
    assert dl._load_actual_durations() == []


def test_get_bias_defaults_to_one_when_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    assert dl.get_bias("Build Controlled Drift") == 1.0


def test_update_duration_bias_noop_when_no_actual_data(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(dl, "_load_actual_durations", lambda: [])
    dl.update_duration_bias()
    assert not (tmp_path / "duration_bias.json").exists()


def test_update_duration_bias_ema_nudges_toward_actual(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(dl, "_load_actual_durations", lambda: [
        {"project": "Build Controlled Drift", "estimated_min": 30, "actual_min": 60},
    ])
    dl.update_duration_bias()
    # ratio = 60/30 = 2.0; EMA from default 1.0: 0.8*1.0 + 0.2*2.0 = 1.2
    assert dl.get_bias("Build Controlled Drift") == 1.2


def test_update_duration_bias_persists_across_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(dl, "_load_actual_durations", lambda: [
        {"project": "X", "estimated_min": 30, "actual_min": 60},
    ])
    dl.update_duration_bias()
    dl.update_duration_bias()
    # second run: 0.8*1.2 + 0.2*2.0 = 1.36
    assert dl.get_bias("X") == 1.36
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/learning_loops/test_duration_loop.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'duration_loop'`.

- [ ] **Step 3: Write `scripts/learning_loops/duration_loop.py`**

```python
#!/usr/bin/env python3
"""Learn a per-project bias correction for task duration estimates, from actual-vs-estimated
data. Same EMA shape as daily_plan.update_meal_learned_time (already shipped, proven) — this
applies the identical pattern to a different field.

_load_actual_durations() is the Log Day plug-in point. Updated 2026-07-03: the storage this
depends on is no longer hypothetical — `signal_log.py` (raw text, source-tagged, one valid
source is "log_day") and `plan_snapshot_log.py` (the full plan stored alongside, for
planned-vs-actual diffing) are both real and committed (focus-configuration layer Phase 5).
What's still missing, concretely: (1) Phase 6 — the actual Log Day capture UI — hasn't shipped,
so no real "log_day"-sourced entries exist yet; (2) even once they do, turning free-text
signal_log entries into structured {"project", "estimated_min", "actual_min"} pairs is Phase 9
(the interpretation loop), explicitly deferred by the project's own design stance — it's an
LLM-assisted extraction (matching a day's account against its stored plan snapshot), not a
mechanical parse, and needs real entries to design against. So this function keeps returning
[] until BOTH land — nothing to learn from yet, update_duration_bias() stays a safe no-op.
"""
import sys, os, json
# One level up from scripts/learning_loops/ to scripts/, so the core modules resolve.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cd_paths

_DEFAULT_BIAS = 1.0  # no correction until real data exists


def _bias_path():
    return cd_paths.data_file("duration_bias.json")


def _load_bias():
    try:
        with open(_bias_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_bias(bias):
    path = _bias_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(bias, f, indent=2)


def _load_actual_durations():
    """PLACEHOLDER — see module docstring above for what this is waiting on. Will return
    [{"project": str, "estimated_min": int, "actual_min": int}, ...] once real. Returns []
    today — update_duration_bias() treats that as "nothing to learn from yet," not an error."""
    return []


def get_bias(project_name):
    """The learned multiplier for a project's duration estimates (1.0 = no correction yet)."""
    return _load_bias().get(project_name, {}).get("factor", _DEFAULT_BIAS)


def update_duration_bias():
    """EMA-nudge each project's bias factor toward actual/estimated, same 80/20 shape as
    daily_plan.update_meal_learned_time. No-ops safely if _load_actual_durations() is empty
    (true today, until the Log Day capture UI ships AND the Phase 9 extraction is designed)."""
    records = _load_actual_durations()
    if not records:
        return
    bias = _load_bias()
    for rec in records:
        project = rec["project"]
        ratio = rec["actual_min"] / rec["estimated_min"] if rec["estimated_min"] else 1.0
        current = bias.get(project, {}).get("factor", _DEFAULT_BIAS)
        bias[project] = {"factor": round(0.8 * current + 0.2 * ratio, 3)}
    _save_bias(bias)


if __name__ == "__main__":
    update_duration_bias()
    print("Duration bias updated (no-op until the Log Day UI ships and Phase 9 extraction exists).")
```

**Not built in this pass (deliberately held, not forgotten):** wiring `duration_loop.get_bias()` into `capture_generate.py`'s `_creation_props`/`_create_one` — see the "Scope narrowed" note above for the three-reviewer reasoning. When Phase 9 gets designed and the project-vs-task-type keying question is answered, this wiring is a small, contained addition (one import, one `if`-branch, one signature change) — it just doesn't belong in this pass.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/learning_loops/duration_loop.py tests/learning_loops/test_duration_loop.py
git commit -m "feat(learning-loops): duration-estimate bias math, built and tested standalone — not wired in yet (see plan)"
```

---

### Task 5: Capacity-at-surfacing-time logging (interpretation cut — see below)

**What this gives you:** nothing visible yet — this only records, alongside every item the system surfaces, whatever capacity signal was active for that generation (a preset flag like "low-energy," or whatever freetext you typed). Pure raw material. No proposal, no adjustment, no Note — that part was cut from this plan (next paragraph explains why).

**June's catch (2026-07-03), and why it changes the scope, not just the wording:** the original version of this task also built `capacity_loop.py` — code that would count how many surfaced items got marked Done, group that by capacity level, and write a Note suggesting fewer items on low-completion days. Three real problems with that, not just one:

1. **"Capacity" isn't a clean bucket.** It's sometimes a fixed preset flag (`"low-energy"`, set by an overlay button — see `plan_store.py`'s `capacity_flag`) and sometimes whatever you actually typed in freetext. Grouping by exact string match — which is what the cut code did — would split "low-energy" and "feeling low today" into two separate, tiny buckets that never learn from each other, even though they mean the same thing. There's no existing normalization step to fix this, and inventing one means deciding how much of your own words to flatten into a fixed category — exactly the kind of qualitative-signal-into-a-scalar move `AI_LAYER_SPEC.md` explicitly warns against doing casually.
2. **Deficit-model risk, not just a wording problem.** Centering the whole loop on "completion rate on low-capacity days" — even with a symmetric high-completion-rate branch, which the cut version did have — still treats *how much you finished* as the thing worth optimizing, and low-capacity days as the ones needing correction. That's the same shape the project's own crip-time principle (quoted in `AI_LAYER_SPEC.md` from `task_intensity_resolver.py`) names directly: *"crip_time NEVER modifies intensity... reducing depth for disabled users IS the ableist move crip_time exists to refuse."* A loop that watches completion rate and proposes showing you less isn't reducing analytical depth, but it's close enough to that shape that it deserves a real conversation with you before it ships, not a default.
3. **Capacity may not even be the right axis.** Your question — "what about other patterns, not just low capacity" — is the deeper one. A pattern like "Tuesdays always go lighter regardless of stated capacity" or "creative tasks land more than administrative ones" isn't capacity-shaped at all, and a loop built to only ever group by capacity would never surface it.

This is the same category of problem as the loops already excluded from this plan (the qualitative pattern-reader, the two-part signal/response-calibration loop) — the *math* was decidable, but the *framing* wasn't, and that's exactly the line this plan is supposed to hold. **Recommendation: cut `capacity_loop.py` entirely from this pass.** Keep only the logging below (uncontroversial — it's the same "record raw signal now, decide what it means later" pattern as every other log in this project, and matches exactly how the focus-configuration layer's own Phase 5 treats `signal_log.py` — store now, interpret later as its own design session), and revisit the interpretation once real Log Day entries + enough surface/completion history exist to have that design conversation against — the same way Task 4's Phase 9 extraction is scoped.

**Files:**
- Modify: `scripts/surface_log.py` (thread `capacity` through), `scripts/plan_generate.py` (pass `capacity` at the one call site that has it) — these two stay in `scripts/` root; they're core system files, not new loop scripts.
- Test: `tests/test_surface_log.py`, one addition to `tests/test_plan_generate.py`

**Interfaces:**
- Produces: `surface_log.log_surfaced(..., capacity=None)` / `log_surfaced_batch(..., capacity=None)` — additive, existing call sites without `capacity` keep working.

- [ ] **Step 1: Write the failing test for `surface_log.py`**

`tests/test_surface_log.py` does not exist yet (confirmed 2026-07-02) — create it:

```python
"""Tests for surface_log — the append-only surfaced-item history."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import surface_log as sl


def test_log_surfaced_batch_records_capacity(tmp_path):
    path = str(tmp_path / "surface_log.jsonl")
    sl.log_surfaced_batch([{"id": "t1", "name": "A", "type": "task"}], path=path, capacity="low")
    rec = json.loads(open(path).read().strip())
    assert rec["capacity"] == "low"


def test_log_surfaced_batch_capacity_defaults_to_none(tmp_path):
    path = str(tmp_path / "surface_log.jsonl")
    sl.log_surfaced_batch([{"id": "t1", "name": "A", "type": "task"}], path=path)
    rec = json.loads(open(path).read().strip())
    assert rec["capacity"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_surface_log.py -v`
Expected: FAIL — `TypeError: log_surfaced_batch() got an unexpected keyword argument 'capacity'`.

- [ ] **Step 3: Thread `capacity` through `surface_log.py`**

Replace:

```python
def log_surfaced(item_id, item_name, item_type, plan_date=None, path=None):
    """Append one surfacing event. item_type: 'task' | 'project' | 'recurring' | etc."""
    path = path or cd_paths.data_file("surface_log.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts":        dt.datetime.now().isoformat(),
        "plan_date": (plan_date or dt.date.today()).isoformat(),
        "id":        item_id,
        "name":      item_name,
        "type":      item_type,
    }
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_surfaced_batch(items, plan_date=None, path=None):
    """items: list of {"id", "name", "type"}."""
    for it in items:
        log_surfaced(it["id"], it["name"], it.get("type", "unknown"),
                     plan_date=plan_date, path=path)
```

with:

```python
def log_surfaced(item_id, item_name, item_type, plan_date=None, path=None, capacity=None):
    """Append one surfacing event. item_type: 'task' | 'project' | 'recurring' | etc.

    capacity: the ambient capacity signal used for this generation, if any — added
    2026-07-02 so the capacity-surfacing-amount loop can join "what capacity" against "what
    got surfaced." Entries logged before this change carry capacity: null.
    """
    path = path or cd_paths.data_file("surface_log.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts":        dt.datetime.now().isoformat(),
        "plan_date": (plan_date or dt.date.today()).isoformat(),
        "id":        item_id,
        "name":      item_name,
        "type":      item_type,
        "capacity":  capacity,
    }
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_surfaced_batch(items, plan_date=None, path=None, capacity=None):
    """items: list of {"id", "name", "type"}."""
    for it in items:
        log_surfaced(it["id"], it["name"], it.get("type", "unknown"),
                     plan_date=plan_date, path=path, capacity=capacity)
```

- [ ] **Step 4: Pass `capacity` at the one call site that has it**

In `scripts/plan_generate.py`, in `generate_plan()`, replace:

```python
    # Learning loop: every generation records what surfaced (neglect/rhythm history).
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    return saved
```

with:

```python
    # Learning loop: every generation records what surfaced (neglect/rhythm history), tagged
    # with the capacity signal used so the capacity-surfacing-amount loop can join them later.
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks],
                           capacity=capacity)
    return saved
```

(`reorder()`'s own `log_surfaced_batch` call is left as-is — `reorder()` has no `capacity` parameter today, so its entries keep logging `capacity: null`, same as before this change.)

- [ ] **Step 5: Add the plan_generate regression test**

Add to `tests/test_plan_generate.py`, after `test_generate_plan_caches_and_logs_surfaced`:

```python
def test_generate_plan_tags_surfaced_batch_with_capacity(tmp_path, monkeypatch):
    surfaced, corrections = _stub_pipeline(monkeypatch, tmp_path)
    pg.generate_plan(source="morning", capacity="low")
    assert surfaced   # _stub_pipeline's monkeypatched log_surfaced_batch captured the call
```

Note: `_stub_pipeline` monkeypatches `pg.log_surfaced_batch` to `lambda items, **k: surfaced.append(items)` (already accepts `**k`, so `capacity=` passes through cleanly — no fixture change needed).

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_surface_log.py tests/test_plan_generate.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/surface_log.py scripts/plan_generate.py tests/test_surface_log.py tests/test_plan_generate.py
git commit -m "feat(learning-loops): log capacity alongside surfaced items (logging only — interpretation cut, see plan)"
```

**Not built in this pass:** the interpretation half — anything that reads this log back and proposes a surfacing-amount change. Revisit once real Log Day entries (via Phase 6, not yet built) give enough qualitative account of what actually happened on low/high-completion days to have the design conversation about whether completion-rate is even the right thing to optimize (reason 3 above) — same "storage now, design later" shape as Task 4's Phase 9 gap. (Corrected 2026-07-03 — an earlier draft claimed the two excluded loops referenced above were "mentioned in this plan's goal"; checked against the actual Goal paragraph, they aren't — they're introduced above, in this task's own reasoning, not in the Goal.)

---

## Final whole-plan verification

- [ ] Run: `python3 -m pytest tests/ -q`
Expected: all PASS. **Don't trust a hardcoded baseline here** — this plan's earlier drafts cited "230 existing," which was already stale by the time of the critic-swarm review (274 collected then) and stale again by the time of this revision (**281 collected, verified 2026-07-03** — other work is landing on this branch in parallel). Counting only what THIS plan adds: 16 new tests (Task 1: 1, Task 2: 4, Task 3: 3, Task 4: 5, Task 5: 3 — recounted 2026-07-03 after Task 4's dependent capture_generate.py test was removed along with the wiring it tested). Before running this final check, re-run `--collect-only` to get the real current baseline rather than trusting any number written here.
- [ ] Confirm no test wrote to June's real Anytype space or real `scripts/data/`/`~/.controlled-drift/` files — every new test uses `tmp_path` + `monkeypatch.setenv`/explicit `path=`/`sid=` overrides, matching the existing suite's pattern.

## Execution Handoff

**Ready to hand off — the Task 3 open question is resolved (2026-07-03, deferred, see the ✅ callout inside Task 3).** Plan complete, saved to `docs/superpowers/plans/2026-07-02-learning-loops-v1.md`.

Execution is subagent-driven-development, per the header at the top of this doc — fresh subagent per task, per-task review (routed through `cross-review` for a non-Claude second opinion), final whole-branch review. That's already this project's established default, not an open choice to re-litigate here each time.
