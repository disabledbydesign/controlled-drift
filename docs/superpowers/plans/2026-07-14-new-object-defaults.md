# New-object defaults Implementation Plan

> **⚠️ ADAPTED 2026-07-14 — READ THIS FIRST. This plan is no longer built as-written.**
> The problem it solved ("a new Project vanishes from the daily plan unless born with the right
> engagement") is now solved upstream by the **input-structure seam redesign**
> (`docs/plan_input_seam_design.md`): the daily plan feeds the LLM **all _active_ items**, so an
> active-engagement Project (`Open`) is **in the input by construction** — it can't vanish at a gate,
> because the hiding gate is *removed*. What that means for the tasks below:
>
> - **ABSORBED into the seam build** (built there, not here): the **born-`Open` chokepoint** (Task 1),
>   **retiring the hardcoded `Steady`** (Tasks 3 & 7 — `capture_generate`, `gsdt_bind`, `daily_plan`
>   prose), and the **backfill** of unset-engagement Projects (Task 8, with the Daily-life exception).
>   Their *purpose* shifts: born-`Open` now means **born-active → born-in-the-input**, not "born with a
>   value so the gate won't hide it." Same code, cleaner reason.
> - **STILL STANDALONE new-object work** (NOT in the seam build — this is what "coming back to it"
>   picks up): the **capture-side intelligent proposal** (weeding infers a per-Project engagement,
>   Task 2), the **tap-to-change chip + `/api/project/engagement` endpoint** (Task 5), and the
>   **`engagement_log`** collect-now learning signal (Task 4). These are the *proposal + correction +
>   learning* half; the seam doesn't need them to function. The tap-to-change chip is the **seed of the
>   deferred field-upkeep generalization** (see the handoff's "generalization" section, Direction A/B).
> - **DEAD — drop:** **Task 6** (neglect backstop for `Open`) — inert then, moot now (no gate hides
>   `Open`). The **"Mesh with the display-grain blocks plan"** section and the **"Changing the gate's
>   treatment of `Open`" out-of-scope line** are **obsolete** — that gate is exactly what the seam
>   redesign removes. Ignore them.
>
> Re-derive every line anchor against live HEAD when this is picked up; the numbers below are stale.

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. **Subagents here can WRITE files but CANNOT run Bash — the main agent runs every test / read-back / `verify` gate.** Bash-only steps are marked **(main agent, Bash)**. Line anchors are from HEAD `e851810` (2026-07-13/14); re-derive each at its live line before editing.

**Goal:** Make every newly-created Project be born well-formed — with a real `Engagement` value instead of blank or a blind hardcoded `Steady` — so a new project never silently floods the daily plan nor vanishes from it. The value is proposed (LLM-inferred from June's words at capture, `Open` by default), tap-to-change on the capture receipt, and every change is logged as a learning signal.

**Architecture:** Two layers that together make an unset-engagement Project structurally impossible. (1) A **chokepoint default** in the single low-level writer `gsdo_objects.create_object`: creating a Project with no `Engagement` fills in `Open` — so *every* creation path (capture, bind, MCP, surface-paste, drift, memory-pass) inherits a safe default even if it passes nothing. (2) An **intelligent proposal** at capture: the weeding contract gains a per-item `engagement` the LLM infers from June's language (default `Open`), written instead of the old hardcoded `Steady`. June verifies **after** the immediate write via a tap-to-change engagement chip on the receipt (mirroring the existing when-chip), and each change appends to an engagement-corrections log (the collect-now-mine-later learning signal). A minimal neglect backstop resurfaces a never-touched `Open` project; the old implicit `Steady` defaults (bind, LLM-prose) are retired; the 21 existing blank projects are backfilled with June's confirmation.

**Tech Stack:** Python 3 stdlib only (`python3`, never `python`); existing modules `gsdo_objects`, `gsdo_anytype`, `capture_generate`, `memory_pass`, `gsdt_bind`, `daily_plan`, `plan_generate`, `neglect`, `session_store`, `server`; vanilla JS/HTML in `docs/overlay_daily.html`; pytest with the repo `conftest.py` sandbox redirect. No new dependencies.

## Mesh with the display-grain blocks plan (`docs/superpowers/plans/2026-07-13-daily-plan-blocks.md`) — read before building

> **OBSOLETE (see top banner).** This whole section reasons about a gate that the seam redesign removes. Disregard.

These two plans are **separate builds that touch the same three files** (`plan_generate.py`, `overlay_daily.html`, `server.py`) in different spots. They **cannot be built in parallel on one tree.** Sequencing decision (confirm with June at build time): **this plan builds first**, so the blocks plan's `Steady`/`Open` → block logic rests on a populated, coherent engagement signal rather than 22 blank projects.

- The blocks plan **already resolves** the display-grain spec's open question #1 its own way (Task 3: `Side = Daily life` is always-eligible in the gate, regardless of engagement). This plan does **not** need to solve daily-life eligibility — do not duplicate it.
- **The Open-gate seam (decide once, here):** today the gate hides non-foregrounded `Open` (`plan_generate.py:537-538` `if eng == "Open": continue`), while the blocks plan wants `Open` → a visible block. This plan does **NOT** change that gate line — changing what `Open` renders as is the blocks plan's job. This plan only guarantees projects *have* an `Open` value and adds a neglect backstop so an `Open` project is never permanently silent. Leave the gate's Open-hiding untouched; the blocks plan owns the render change.

---

## Decisions from June (these govern the tasks)

1. **Default `Open`, infer when possible, learn from changes.** A new Project defaults to `Open` (present/findable, not pushed, not lost). When a dump item is a Project and June's words signal engagement ("I need to start X" → `Steady`), the LLM proposes that instead; `Open` when unsure. This is not a fork — inference-when-possible + default-Open + log-every-change is one loop.
2. **Verify = tap-to-change-after, not confirm-before.** Capture writes immediately (a dump is never lost). June adjusts a proposed engagement *after* the write via a tappable chip on the receipt (the when-chip idiom). No pre-write confirm gate — that would add friction to the thing she does most.
3. **Bind is dialogic.** `gsdt_bind` is an interactive terminal process; it should *ask* for engagement rather than hardcode `Steady` (falling back to the `Open` chokepoint default if she doesn't answer).
4. **Backfill is proposed-values-June-confirms.** The 21 existing blank-engagement projects are her real data; propose a per-project value (Inactive-status → `Backburner`, else `Open`), show her the mapping, write only on her confirmation.

---

## Explicitly out of scope (state and hold)

- **The grain/block rendering, block durations, did-a-chunk completion** — the blocks plan owns all of it. This plan changes no rendering of the *plan*; it only adds a chip to the capture *receipt*.
- **Changing the gate's treatment of `Open`** (`plan_generate.py:537-538`) — the blocks plan owns whether `Open` renders as a visible block. This plan leaves it as-is.
- **Building the learning *loop* that reads the corrections log** — that is the deferred learning-loops subsystem (`docs/superpowers/plans/2026-07-02-learning-loops-v1.md`). This plan writes the log (collect-now); mining is later, per June ("collect data on the patterns in which I change it").
- **A full engagement picker** (all 7 values) on the chip — v1 cycles the three real ones (`Open`/`Steady`/`Backburner`); the rest are set elsewhere.
- **`Side` defaults** — only `Engagement` is in scope. `Side` inheritance is its own concern; do not add Side-default logic here.

---

## Global Constraints

- **`python3`, not `python`.** Suite: `python3 -m pytest -q` from repo root.
- **`gsdo_objects.create`/`update` take DISPLAY names** (`"Engagement"`), resolving select values **by option name**. Never pass a property key or tag id. Valid `Engagement` values (`build_project.py:24-26`): `Steady, Open, Sprint, Hyperfixation, Needs Clarifying, Backburner, Done`.
- **Read engagement by DISPLAY name, not key.** `daily_plan.py:75` / `neglect.py:100` read by name `"Engagement"` because the Anytype key is generated/unpredictable. Any read-back here follows the by-name convention (not the by-key access at `task_actions.py:106`).
- **Idempotent writes; no silent failures — raise, don't `assert`; verify against the live space with read-back** after every write (reuse `_get_object` + name/value assert).
- **Tests self-clean — NEVER leave artifacts in June's real space.** Unit tests mock the LLM and Anytype; `conftest.py` redirects data/config to a sandbox and *fails the suite* on any write to the real data dir. The end-to-end task (Task 9) creates real objects and **deletes them in the same run**.
- **Additive only.** Every existing capture with no engagement signal must behave as before *except* that the born value is now `Open` instead of `Steady` (the intended change). Delete no unrelated behavior.
- **One decision, many paths — never diverge.** The chokepoint default in `gsdo_objects.create_object` is the single structural guarantee; callers that have a better value pass it, callers that pass nothing inherit `Open`.

---

## File Structure

- `scripts/gsdo_objects.py` — `create_object` gains a Project-engagement chokepoint default (Task 1).
- `scripts/capture_generate.py` — weeding contract gains per-item `engagement`; `parse_weed` defaults it; `_creation_props` writes it instead of hardcoded `Steady`; the capture session entry carries `type` + `engagement` so the receipt can render the chip (Tasks 2, 3, 5).
- `prompts/weeding_gate.md` — a real Project definition + an engagement-noticing line (Task 2).
- `scripts/memory_pass.py` — `apply_candidate` writes a proposed engagement via the same item field (Task 3).
- `scripts/engagement_log.py` — **NEW.** Append-only jsonl learning-signal store for engagement changes (Task 4).
- `scripts/server.py` — **NEW** route `POST /api/project/engagement` (Task 5).
- `docs/overlay_daily.html` — an engagement chip on Project receipt lines, tap-to-change (Task 5).
- `scripts/neglect.py` — `Open` backstop on the surface-recency path (Task 6).
- `scripts/gsdt_bind.py` — dialogic engagement instead of hardcoded `Steady` (Task 7).
- `scripts/daily_plan.py` — LLM-prose engagement default `Steady` → `Open` for coherence (Task 7).
- `scripts/backfill_engagement.py` — **NEW.** June-confirmed backfill of the 21 blank projects (Task 8).
- Tests: `tests/test_new_object_defaults.py`, `tests/test_engagement_log.py`, plus additions to `tests/test_capture_generate.py`, `tests/test_memory_pass_fields.py`, `tests/test_neglect_active.py`.

---

### Task 1: Chokepoint default — a Project is never born with blank Engagement

**Files:**
- Modify: `scripts/gsdo_objects.py` — `create_object` (`:119-155`).
- Test: `tests/test_new_object_defaults.py` (NEW).

**Interfaces:**
- Produces: `create_object(type_key, name, ...)` — when `type_key == "gsdo_project"` and `properties` has no `"Engagement"` (by display name) with a truthy value, injects `"Engagement": "Open"` before writing. Any caller-supplied Engagement wins untouched.

- [ ] **Step 1: Write the failing tests.** Mock the network so no real write happens; assert on the props passed to the POST.

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdo_objects as go


def _capture_payload(monkeypatch):
    """Stub the live-space calls; return a dict the fake POST fills with the props it saw."""
    seen = {}
    monkeypatch.setattr(go, "find_existing", lambda tk, n: None)
    monkeypatch.setattr(go, "guard_link_kinds", lambda sid, tk, props: props)
    monkeypatch.setattr(go.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(go.g, "find_property",
                        lambda name: {"id": "p", "key": "k", "name": name, "format": "select"})
    # _tag_id / select resolution: return the option name as a fake id so we can read it back
    monkeypatch.setattr(go, "_value_field",
                        lambda prop, value: {"key": prop["key"], "select": value})

    def fake_call(method, path, payload=None):
        if method == "POST":
            seen["props"] = {p["key"]: p for p in payload.get("properties", [])}
            seen["type_key"] = payload.get("type_key")
        return 200, {"object": {"id": "oid-1"}}
    monkeypatch.setattr(go, "call", fake_call)
    return seen


def test_project_born_open_when_engagement_absent(monkeypatch):
    seen = _capture_payload(monkeypatch)
    go.create_object("gsdo_project", "New thing", properties={})
    assert seen["props"]["k"]["select"] == "Open"


def test_project_keeps_caller_supplied_engagement(monkeypatch):
    seen = _capture_payload(monkeypatch)
    go.create_object("gsdo_project", "New thing", properties={"Engagement": "Steady"})
    assert seen["props"]["k"]["select"] == "Steady"


def test_non_project_gets_no_engagement_default(monkeypatch):
    seen = _capture_payload(monkeypatch)
    go.create_object("task", "A task", properties={})
    assert "k" not in seen.get("props", {})   # no Engagement injected for a Task
```

*Implementer: `create_object` resolves each prop through `g.find_property` + `_value_field`; confirm the real attribute names (`go.g`, `go.call`, `go._value_field`) and adjust the stubs to the live module, keeping the assertions (born-Open / caller-wins / task-untouched) intact.*

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -v`
Expected: FAIL (no default injected).

- [ ] **Step 3: Implement.** In `create_object`, immediately after the `find_existing` early-return and before `guard_link_kinds`/prop-building, add:

```python
    # Chokepoint default: a Project must never be born with a blank Engagement (else the daily-plan
    # gate treats unset as dormant and hides it indefinitely). Every creation path funnels through
    # here, so this one line makes an unset-engagement Project structurally impossible. A caller with
    # a better value (capture's LLM proposal, bind's dialogic answer) passes it and wins; a caller
    # that passes nothing (MCP, surface-paste, drift) inherits Open. (June, 2026-07-14.)
    if type_key == "gsdo_project":
        properties = dict(properties or {})
        if not (properties.get("Engagement") or "").strip():
            properties["Engagement"] = "Open"
```

*Note: guard the `.strip()` for non-str values — use `if not properties.get("Engagement"):` if a non-string could appear; the display-name convention here only ever carries option-name strings or absence.*

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/gsdo_objects.py tests/test_new_object_defaults.py
git commit -m "feat(defaults): Project born with Engagement=Open at the shared write chokepoint"
```

---

### Task 2: Weeding contract proposes a per-item engagement (+ a real Project definition)

**Files:**
- Modify: `scripts/capture_generate.py` — the `_WEED_JSON_INSTRUCTION` per-item object (`:169-183`), its per-item prose bullet (`:145-153`) and schema notes (`:190-194`); the `parse_weed` per-item default loop (`:265-271`).
- Modify: `prompts/weeding_gate.md` — add a Project definition (there is currently **no** "when to mint a Project vs a Task" bullet; classification rides only on the enum) and an engagement-noticing line.
- Test: `tests/test_capture_generate.py` (parse-only; no network).

**Interfaces:**
- Produces: each parsed item dict may now carry `"engagement"` (str). Meaningful only when `type == "Project"`; defaults to `"Open"`. Additive to existing item keys.

- [ ] **Step 1: Write the failing parse tests** (append to `tests/test_capture_generate.py`).

```python
def test_parse_weed_reads_project_engagement():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"Learn woodturning","link":null,"status":null,"action":"create",
       "reasoning":"r","engagement":"Steady"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Steady"


def test_parse_weed_engagement_defaults_open_when_absent():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"X","link":null,"status":null,"action":"create","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Open"
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k engagement -v`
Expected: FAIL (KeyError / default absent).

- [ ] **Step 3: Add `engagement` to the JSON contract.** In `_WEED_JSON_INSTRUCTION`, inside the per-item object (after `"status"`), add:

```
          "engagement": "<ONLY for type==Project: how June is engaging with this thread. Read her words: 'I need to start/focus on X' or a deadline → \"Steady\" (a normal daily move); a thing she's naming but not necessarily starting → \"Open\" (available, not pushed). Default \"Open\" when she gives no signal — NEVER guess Steady. Omit/ignore for Tasks.>",
```

Add a per-item prose bullet after the existing Per-item fields bullet (`:145-153`):

```
- **Project engagement (type==Project only).** When an item becomes a Project, set `engagement`
  from June's words: clear "I'm starting / focusing on / this is due" → "Steady"; a thing she
  names but isn't necessarily starting now → "Open". Default "Open" when unsure — a new project
  should be available and findable, never pushed at her uninvited and never a guess of Steady.
  Tasks carry no engagement.
```

Add to the schema notes (`:190-194`): a line that `engagement` applies only to Projects (mirroring the existing "status applies to Tasks" note).

- [ ] **Step 4: Default `engagement` in `parse_weed`.** Add to the per-item `setdefault` loop (`:265-271`):

```python
            item.setdefault("engagement", "Open")
```

- [ ] **Step 5: Add the Project definition + noticing line to `prompts/weeding_gate.md`.** In the type-routing prose (near `:34-40`, which lists Goal/Task/Recurring/Strategy/Note but has no Project bullet), add:

```
- **Project** — a "work on this over time" thread that holds tasks: an ongoing effort with an arc,
  not a single do-it-once action. Mint a Project when the item is a body of work you return to
  (e.g. "learn leatherworking", "the job search"), not a discrete task. When you mint a Project,
  set its `engagement` (see the JSON contract): "Open" by default, "Steady" only when June's words
  say she's actively starting/feeding it.
```

- [ ] **Step 6: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k engagement -v`
Expected: PASS.

- [ ] **Step 7: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py prompts/weeding_gate.md tests/test_capture_generate.py
git commit -m "feat(capture): weeding gate proposes per-project engagement (Open default) + Project definition"
```

---

### Task 3: Capture + memory-pass write the proposed engagement (retire hardcoded Steady)

**Files:**
- Modify: `scripts/capture_generate.py` — `_creation_props` Project branch (`:299-300`).
- Modify: `scripts/memory_pass.py` — `apply_candidate` props block (write engagement from the candidate if present; else the chokepoint default applies).
- Modify: `prompts/daily_memory_pass.md` — allow an optional `engagement` on a Project candidate (verbatim-from-body only; null otherwise).
- Test: `tests/test_capture_generate.py`, `tests/test_memory_pass_fields.py`.

**Interfaces:**
- Consumes: parsed item `engagement` (Task 2).
- Produces: a captured Project's props carry `Engagement = item["engagement"]` (default `"Open"`), never the old constant `"Steady"`. Memory-pass Projects carry a proposed engagement when the entry states one, else rely on the Task-1 chokepoint.

- [ ] **Step 1: Write the failing tests.** In `tests/test_capture_generate.py`, using the file's `_stub` pattern:

```python
def test_capture_project_writes_proposed_engagement(monkeypatch, tmp_path):
    canned = json.dumps({"opening":"o","capacity_read":None,"groups":[{"label":"g","through_line":"t","items":[
        {"type":"Project","name":"Learn woodturning","link":None,"status":None,"action":"create",
         "reasoning":"r","engagement":"Steady"},
        {"type":"Project","name":"Maybe-someday garden","link":None,"status":None,"action":"create",
         "reasoning":"r"},   # no signal -> parse_weed defaulted engagement to "Open"
    ]}]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("start learning woodturning; maybe a garden someday")
    props = {name: p for (typ, name, p) in calls}
    assert props["Learn woodturning"]["Engagement"] == "Steady"
    assert props["Maybe-someday garden"]["Engagement"] == "Open"    # NOT the old hardcoded Steady
```

*Implementer: match `_stub`'s real return shape; `parse_weed` runs inside `capture`, so the second item arrives with `engagement=="Open"` from Task 2's default.*

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k proposed_engagement -v`
Expected: FAIL (still writes `"Steady"`).

- [ ] **Step 3: Implement.** Replace the hardcoded Project branch in `_creation_props` (`:299-300`):

```python
    elif type_name == "Project":
        # Born with the LLM's proposed engagement (Open by default; Steady only when June's words
        # said she's starting it). Replaces the old blind hardcoded Steady that flooded the plan.
        props["Engagement"] = item.get("engagement") or "Open"
```

In `memory_pass.apply_candidate`, in the props block, add (Projects only):

```python
    if candidate.get("proposed_type") == "Project" and candidate.get("engagement"):
        props["Engagement"] = candidate["engagement"]
    # (else: no engagement passed -> gsdo_objects chokepoint fills Open. No hardcoded Steady here.)
```

In `prompts/daily_memory_pass.md`, add to the candidate JSON contract: `"engagement": "for a Project only, from the entry's own words ('start', 'focus on', a deadline) -> \"Steady\"; else null (born Open)"`.

- [ ] **Step 4: Run tests to verify they pass, then the full capture + memory-pass suites (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py tests/ -k "proposed_engagement or memory_pass" -v`
Expected: PASS, no regressions.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py scripts/memory_pass.py prompts/daily_memory_pass.md tests/test_capture_generate.py tests/test_memory_pass_fields.py
git commit -m "feat(capture): write proposed engagement on new Projects, retire hardcoded Steady"
```

---

### Task 4: The engagement-corrections log (the learning signal)

**Files:**
- Create: `scripts/engagement_log.py`.
- Test: `tests/test_engagement_log.py` (NEW).

**Interfaces:**
- Produces (record shape reused from the never-built `engagement_watch` spec, `learning-loops-v1` Task 3, so a future learning loop finds the shape it expected):
  - `log_change(project_id, name, old, new, path=None) -> None` — append `{"ts": <iso>, "date": <iso>, "project_id", "name", "old", "new"}` **only when `old != new`** (a no-op re-tap logs nothing).
  - `read_changes(path=None) -> list[dict]` — tolerant reader (missing file → `[]`).
- Store: `scripts/data/engagement_corrections_log.jsonl`, resolved via `cd_paths.data_file(...)` at call time (sandbox-safe), append-only, `os.makedirs(exist_ok=True)`.

**Honesty note (in the module docstring):** this is the *collect* half. No reader consumes it yet — the mining loop is the deferred learning-loops subsystem. Log rich now, mine later (June's decision; mirrors `display_grain_design.md` decision 2). Do NOT claim a live loop.

- [ ] **Step 1: Write the failing tests.**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import engagement_log as el


def test_logs_a_real_change(cd_sandbox):
    el.log_change("oid1", "Job search", "Open", "Steady")
    recs = el.read_changes()
    assert recs and recs[-1]["old"] == "Open" and recs[-1]["new"] == "Steady"
    assert recs[-1]["project_id"] == "oid1" and recs[-1]["name"] == "Job search" and "ts" in recs[-1]


def test_noop_when_unchanged(cd_sandbox):
    el.log_change("oid1", "Job search", "Open", "Open")
    assert el.read_changes() == []


def test_read_missing_file_is_empty(cd_sandbox):
    assert el.read_changes() == []
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_engagement_log.py -v`
Expected: FAIL (`No module named 'engagement_log'`).

- [ ] **Step 3: Implement** (copy the `completion_log.py` / `surface_log.py` append idiom).

```python
"""Engagement-change log — the learning SIGNAL for new-object-defaults.

When June changes an AI-proposed engagement (tap-to-change on the capture receipt), the
old->new change is appended here. This is the COLLECT half: no reader consumes it yet — the
mining loop is the deferred learning-loops subsystem (docs/superpowers/plans/2026-07-02-
learning-loops-v1.md, its engagement_watch was never built). Log rich now, mine later
(June, 2026-07-14). Record shape matches that spec's {ts, project_id, name, old, new} so the
future loop finds what it expected. Do NOT treat this as a live feedback loop.
"""
import os, json, datetime as dt
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("engagement_corrections_log.jsonl")


def log_change(project_id, name, old, new, path=None):
    if old == new:
        return   # a re-tap that lands on the same value is not a correction
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "project_id": project_id, "name": name, "old": old, "new": new}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_changes(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []
```

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_engagement_log.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/engagement_log.py tests/test_engagement_log.py
git commit -m "feat(learning): engagement-change log (collect-now-mine-later signal)"
```

---

### Task 5: Tap-to-change-after — receipt chip + `/api/project/engagement`

**Files:**
- Modify: `scripts/capture_generate.py` — the session-log weed entry so a created Project receipt carries `type` + `engagement` (near `:461-469`, the entry with the `"corrections": []` placeholder).
- Modify: `scripts/server.py` — new route `POST /api/project/engagement`.
- Modify: `docs/overlay_daily.html` — an engagement chip on Project receipt lines (`renderSession` `:2212-2251`), cycling like the when-chip (`cycleWhen` `:2263-2286`).
- Test: `tests/test_new_object_defaults.py` (append — the endpoint handler logic).

**Interfaces:**
- Consumes: `gsdo_objects.update`, `engagement_log.log_change` (Task 4), the read-back helper.
- Produces: `POST /api/project/engagement` body `{"id": str, "old": str, "new": str}` → updates the Project's `Engagement` in Anytype, reads it back (by display name) and raises on mismatch, logs the change, returns `{"ok": True, "id", "engagement": new}`.

- [ ] **Step 1: Make the receipt carry engagement.** In `capture`, where the per-created-item session entry is built (`:461-469`), include for Projects the created object's `type` and `engagement` so the client can render a chip:

```python
        entry_item = {..., "type": type_name}
        if type_name == "Project":
            entry_item["engagement"] = props.get("Engagement", "Open")
```
*(Re-derive the real entry-building shape; add these keys additively next to the existing name/link/when keys — do not disturb `"corrections": []`.)*

- [ ] **Step 2: Write the failing endpoint-logic test.** Factor the route body into a testable helper `server.set_project_engagement(id, old, new)` (or test the handler via the existing `test_server_*` pattern if present). Mock Anytype + the log:

```python
def test_set_project_engagement_updates_and_logs(monkeypatch):
    import server
    updates, logged = {}, {}
    monkeypatch.setattr(server.gsdo_objects, "update",
                        lambda oid, properties: updates.update({oid: properties}))
    monkeypatch.setattr(server, "_read_engagement_by_name", lambda oid: "Steady")  # read-back
    monkeypatch.setattr(server.engagement_log, "log_change",
                        lambda pid, name, old, new: logged.update({"c": (pid, old, new)}))
    monkeypatch.setattr(server, "_object_name", lambda oid: "Job search")
    out = server.set_project_engagement("oid1", "Open", "Steady")
    assert updates["oid1"]["Engagement"] == "Steady"
    assert out["engagement"] == "Steady" and logged["c"] == ("oid1", "Open", "Steady")
```

*Implementer: name the read-back/name helpers to match what you add; the contract is update-by-name + read-back-raises-on-mismatch + log-the-change.*

- [ ] **Step 3: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -k engagement_updates -v`
Expected: FAIL.

- [ ] **Step 4: Implement the route.** In `server.py`, add a handler (mirroring the `/api/task/reschedule` shape the when-chip already posts to):

```python
elif self.path == "/api/project/engagement":
    body = self._json_body()
    result = set_project_engagement(body["id"], body.get("old"), body["new"])
    self._send(200, result)
    return
```
and the helper (module level), using the by-name read-back convention:

```python
def _read_engagement_by_name(oid):
    obj = capture_generate._get_object(oid)
    by_name = {p.get("name"): p for p in obj.get("properties", [])}
    return ((by_name.get("Engagement") or {}).get("select") or {}).get("name")

def set_project_engagement(oid, old, new):
    gsdo_objects.update(oid, properties={"Engagement": new})
    got = _read_engagement_by_name(oid)
    if got != new:
        raise RuntimeError(f"set_project_engagement({oid!r}): Engagement did not persist (read-back={got!r})")
    engagement_log.log_change(oid, _object_name(oid), old, new)   # no-op if old==new
    return {"ok": True, "id": oid, "engagement": new}
```
*(Add `import engagement_log` and reuse/define `_object_name`; confirm `gsdo_objects` is already imported in server.)*

- [ ] **Step 5: Add the overlay chip.** In `renderSession` (`:2212-2251`), for a receipt line whose item `type === "Project"`, render an engagement chip beside the when-chip. Mirror `whenChipHtml`/`cycleWhen`:

```javascript
function engChipHtml(item){
  const v = item.engagement || "Open";
  return `<button class="chip eng-chip" onclick="cycleEng(this)"
            data-id="${item.id}" data-eng="${v}">${v}</button>`;
}
function cycleEng(btn){
  const order = ["Open","Steady","Backburner"];         // v1: the three real ones
  const old = btn.dataset.eng;
  const next = order[(order.indexOf(old)+1) % order.length];
  btn.dataset.eng = next; btn.textContent = next; btn.classList.add("changed");
  fetch("/api/project/engagement",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id:btn.dataset.id, old, new:next})})
    .then(r=>r.json()).then(j=>{ if(!j.ok){ btn.textContent="!"; } })
    .catch(()=>{ btn.textContent="!"; });   // never leave her wondering whether it saved
}
```
Insert `engChipHtml(item)` into the Project receipt line render (only when `item.type === "Project"`). Reuse the existing chip CSS + the `.changed`/`reflect-changed` "changed" badge idiom (`:238`).

- [ ] **Step 6: Run tests to verify pass (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -v`
Expected: PASS. (The chip JS is exercised live in Task 9.)

- [ ] **Step 7: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py scripts/server.py docs/overlay_daily.html tests/test_new_object_defaults.py
git commit -m "feat(capture): tap-to-change engagement chip on the receipt + /api/project/engagement (logs the change)"
```

---

### Task 6: Neglect backstop — a never-touched Open project resurfaces  **(DROPPED — see top banner)**

**Files:**
- Modify: `scripts/neglect.py` — the surface-recency (dormant) path so `Open` is caught, and wire that catch into the daily plan without disturbing the active cohort.
- Test: `tests/test_neglect_active.py` (append) or `tests/test_new_object_defaults.py`.

**Context (from the code map):** `Open` is in `_NON_CANDIDATE_ENGAGEMENT = {"Done","Open"}` (`:66`) so the dormant cohort excludes it, AND `Open` is absent from `_ACTIVE_ENGAGEMENT` (`:71`) so the active cohort ignores it — a never-foregrounded `Open` project is invisible to neglect. The dormant cohort (`dormant_neglected`, surface-recency via `surface_log`) is **unwired** from the daily plan; only the active cohort is wired (`daily_plan.py:210`). **Minimal, targeted fix:** add an `Open`-specific resurfacing on the surface-recency signal, exposed through the already-wired neglect load — do NOT wire the whole dormant cohort (that risks re-crowding).

- [ ] **Step 1: Write the failing test.** An `Open` project not surfaced in > N days is returned as neglected; one surfaced recently is not.

```python
import datetime as dt
import neglect


def test_open_project_resurfaces_when_untouched():
    now = dt.datetime(2026, 7, 14)
    projects = [{"id": "op", "name": "Sell phone case", "engagement": "Open"}]
    surface_dates = {"op": dt.date(2026, 6, 1)}   # ~6 weeks stale
    out = neglect.open_untouched(projects, surface_dates, now=now, days=16)
    assert any(n["name"] == "Sell phone case" for n in out)


def test_recent_open_project_not_resurfaced():
    now = dt.datetime(2026, 7, 14)
    projects = [{"id": "op", "name": "Sell phone case", "engagement": "Open"}]
    surface_dates = {"op": dt.date(2026, 7, 13)}
    assert neglect.open_untouched(projects, surface_dates, now=now, days=16) == []
```

*Implementer: match the real signatures — `surface_dates` shape from `surface_log.surfaced_dates()` / `effective_last_surfaced`; reuse `find_neglected`'s staleness core (`:43-53`) rather than re-implementing the cutoff.*

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_neglect_active.py -k open_ -v`
Expected: FAIL (`neglect has no attribute 'open_untouched'`).

- [ ] **Step 3: Implement** a small `open_untouched(projects, surface_dates, now, days=16)` that filters to `engagement == "Open"` and applies the existing staleness core (never-surfaced OR last-surfaced < cutoff). Then include its output in the neglected set the gate receives — via `daily_plan.load_neglected` (union the `Open` backstop with the existing `active_untouched()` result). Keep it a **union**, additive; do not change `active_untouched` or the active cohort.

- [ ] **Step 4: Run tests to verify pass, then the neglect suite (main agent, Bash).**
`python3 -m pytest tests/test_neglect_active.py -v`
Expected: PASS, no regressions.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/neglect.py scripts/daily_plan.py tests/test_neglect_active.py
git commit -m "feat(neglect): backstop resurfaces a never-touched Open project"
```

*Scope note: if wiring the union into `load_neglected` proves to entangle the block/grain gate logic the blocks plan is mid-changing, STOP and coordinate sequencing rather than force it — this is the one task most likely to collide.*

---

### Task 7: Retire the old implicit Steady defaults (bind dialogic + LLM-prose)

**Files:**
- Modify: `scripts/gsdt_bind.py` — `init_binding` (`:204-211`): stop hardcoding `Engagement="Steady"`; ask in the terminal, default `Open`.
- Modify: `scripts/daily_plan.py` — the LLM-prose engagement default `or "Steady"` (`:302`, `:328`) → `or "Open"`, so a stray unset reads consistently with the new born-default (post-backfill there should be none, but the prose must not mislead the LLM into calling an unset project "a normal daily move").
- Test: `tests/test_new_object_defaults.py` (append — a small unit for the prose default; bind's prompt is verified live in Task 9).

**Interfaces:**
- Produces: `gsdt_bind.init_binding` no longer forces `Steady`; the LLM-prose project/goal lines default an unset engagement to `Open`.

- [ ] **Step 1: Write the failing test** for the prose default (the cheap, deterministic half):

```python
def test_project_line_defaults_unset_engagement_to_open():
    import daily_plan
    line = daily_plan._project_line({"name": "Ghost", "engagement": None})
    assert "[Open]" in line and "[Steady]" not in line
```
*Implementer: `_project_line` is a nested/closure helper (`daily_plan.py:327`); if not importable, assert via the context-builder that renders it, or lift the default into a tiny module-level `_eng_or_default(p)` and test that.*

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -k project_line -v`
Expected: FAIL (renders `[Steady]`).

- [ ] **Step 3: Implement.**
  - `daily_plan.py:302` and `:328`: change `or "Steady"` → `or "Open"`.
  - `gsdt_bind.py:204-211`: replace `props = {"Engagement": "Steady"}` with a dialogic prompt. Since bind runs in the terminal, prompt for engagement and only set it if answered; otherwise leave it out and let the Task-1 chokepoint fill `Open`:
    ```python
    props = {}
    eng = _prompt_engagement(project_name)   # terminal prompt: "Engagement for '<name>'? [Open]/Steady/Backburner: "
    if eng:
        props["Engagement"] = eng
    # (unset -> gsdo_objects chokepoint writes Open)
    ```
    Add `_prompt_engagement` (uses `input()`, tolerates empty = accept default, validates against the three offered values; non-interactive callers pass through to the chokepoint). Keep the existing Goal/Parent/Context props.

- [ ] **Step 4: Run tests to verify pass (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/gsdt_bind.py scripts/daily_plan.py tests/test_new_object_defaults.py
git commit -m "feat(defaults): bind asks for engagement; LLM-prose default Open, not Steady"
```

---

### Task 8: Backfill the 21 existing blank-engagement projects (June-confirmed)

**Files:**
- Create: `scripts/backfill_engagement.py` — proposes a value per blank project, prints the mapping for June, writes only on confirmation, reads back each write.
- Test: `tests/test_new_object_defaults.py` (append — the pure proposal function).

**Interfaces:**
- Produces:
  - `propose_backfill(projects) -> list[dict]` — pure: for each Project with unset `Engagement`, propose `"Backburner"` if `Project status == "Inactive"`, else `"Open"`. Returns `[{"id","name","current":None,"proposed":...}]`. (Fun/hobby projects are excluded from the *plan* by the blocks plan regardless, but still get a tidy `Open` here so no project is blank.)
  - `apply_backfill(proposals) -> list[dict]` — idempotent `gsdo_objects.update` + by-name read-back per item; raises on mismatch; skips any project that already has an engagement (re-run safe).

- [ ] **Step 1: Write the failing test** (proposal logic only; no network):

```python
def test_backfill_proposes_backburner_for_inactive_else_open():
    import backfill_engagement as bf
    projs = [
        {"id": "a", "name": "Industry positions", "engagement": None, "project_status": "Inactive"},
        {"id": "b", "name": "Job search", "engagement": None, "project_status": None},
        {"id": "c", "name": "Already set", "engagement": "Steady", "project_status": None},
    ]
    out = {p["name"]: p["proposed"] for p in bf.propose_backfill(projs)}
    assert out == {"Industry positions": "Backburner", "Job search": "Open"}   # 'Already set' skipped
```

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -k backfill -v`
Expected: FAIL.

- [ ] **Step 3: Implement** `propose_backfill` (pure) + `apply_backfill` (update + read-back, skip-if-set for idempotency) + a `__main__` that fetches live projects (`gsdo_anytype.fetch_all_objects`), prints the proposed mapping as a table, and applies only after an explicit `--apply` flag (so a bare run is a dry-run June reviews).

- [ ] **Step 4: Run tests to verify pass (main agent, Bash).**
`python3 -m pytest tests/test_new_object_defaults.py -k backfill -v`
Expected: PASS.

- [ ] **Step 5: DRY-RUN for June (main agent, Bash).** `python3 scripts/backfill_engagement.py` (no `--apply`) → present the mapping to June. **Do not `--apply` until she confirms the values.** This is her real data (Task decision 4).

- [ ] **Step 6: Commit the script (main agent, Bash)** (the *apply* against her space happens in Task 9 after her confirmation):
```bash
git add scripts/backfill_engagement.py tests/test_new_object_defaults.py
git commit -m "feat(defaults): June-confirmed backfill for blank-engagement projects (dry-run by default)"
```

---

### Task 9: Integration & end-to-end verify (REQUIRED — do not skip)

A plan is done only when the feature is wired into the running system and observed working end-to-end.

**Wiring this feature connects to:**
- `POST /api/capture` → `capture_generate.capture()` → `_create_one` → `_creation_props` (proposed engagement) → `gsdo_objects.create_object` (chokepoint default backstop) → object born with a real `Engagement`.
- Capture session entry now carries `type`+`engagement` → `GET /api/session` → `renderSession` → the engagement chip → `POST /api/project/engagement` → `gsdo_objects.update` + read-back + `engagement_log.log_change`.
- `daily_plan.load_neglected` now unions the `Open` backstop.
- `gsdt_bind.init_binding` asks in the terminal; every other path inherits the chokepoint `Open`.

- [ ] **Step 1 (main agent, Bash): restart the server** and load `docs/overlay_daily.html` (memory flags a possibly-stale server).

- [ ] **Step 2 (main agent): drive a real capture** through the Add tab via the `verify` skill with a dump containing one clearly-Steady project and one no-signal project, both prefixed `CD-TEST`, e.g.:
  *"CD-TEST start learning woodturning this week — I want to focus on it; and CD-TEST maybe sell the old phone case someday."*

- [ ] **Step 3 (main agent, Bash): read the created objects back** and confirm: `CD-TEST start learning woodturning` has `Engagement = Steady` (her words said start/focus); `CD-TEST maybe sell the old phone case someday` has `Engagement = Open` (no signal → default, NOT the old Steady). Neither is blank.

- [ ] **Step 4 (main agent): exercise the tap-to-change chip** — on the woodturning receipt line, tap the engagement chip to change `Steady → Open`; confirm (Network tab) the `POST /api/project/engagement` fires, the object updates in Anytype (read back), and a record lands in `scripts/data/engagement_corrections_log.jsonl` with `old:"Steady", new:"Open"`. Tap again to the same value → no new log record (no-op guard).

- [ ] **Step 5 (main agent, Bash): the chokepoint backstop** — create a Project via the MCP/`gsdo_objects.create` path with NO engagement (`python3 -c "import sys; sys.path.insert(0,'scripts'); import gsdo_objects as go; print(go.create('Project','CD-TEST bare project'))"`), read it back, confirm `Engagement == "Open"`.

- [ ] **Step 6 (main agent, Bash): the backfill** — with June's confirmation of the Task-8 dry-run mapping, run `python3 scripts/backfill_engagement.py --apply`, then re-fetch and confirm the 21 projects now carry their agreed values and none remains blank. (If June has not confirmed, STOP here and hold — do not write her space.)

- [ ] **Step 7 (main agent, Bash): delete ALL `CD-TEST` objects** from her real space and re-fetch to confirm they're gone. Nothing this task created may remain.

- [ ] **Step 8 (main agent, Bash): full suite, clean tree.**
`python3 -m pytest -q`
Expected: all green; the conftest real-data tripwire did not fire.

- [ ] **Step 9: Commit, then cross-family review (main agent, Bash).** Request the non-Claude review (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file with its tests) before the thread closes; triage findings, apply the real ones.
```bash
git add -A
git commit -m "test(defaults): end-to-end verify new Projects born well-formed + tap-to-change + backfill"
```

---

## Self-Review (author checklist — done)

- **Spec coverage:** (1) default Open + infer when possible — Task 2 (contract) + Task 3 (write) + Task 1 (chokepoint backstop) ✓; (2) tap-to-change-after, not confirm-before — Task 5 (receipt chip + endpoint), capture still writes immediately ✓; (3) log every change — Task 4 (log) + Task 5 (endpoint fires it, no-op guard) ✓; (4) one shared path, can't diverge — Task 1 chokepoint, every caller inherits ✓; (5) bind dialogic — Task 7 ✓; (6) backfill June-confirmed — Task 8 dry-run + Task 9 gated apply ✓; (7) Open neglect backstop — Task 6 ✓. Mesh with blocks plan: same-file seams named, Open-gate left to blocks, daily-life not duplicated ✓. Out-of-scope (grain rendering, gate Open-hiding, learning loop reader, Side defaults) enumerated ✓.
- **Placeholder scan:** every code step carries real code; the few spots depending on live shapes (`_stub` return, `_project_line` closure, session-entry builder, `load_neglected` union) say "re-derive the real shape and extend additively" with the exact behavior specified — honest instruction, not hand-wave.
- **Type consistency:** `engagement` item key flows contract (Task 2) → parse default (Task 2) → `_creation_props`/`apply_candidate` write (Task 3) → session entry (Task 5). `engagement_log.log_change(project_id, name, old, new)` used identically in Task 4 and Task 5. `Engagement` always the display name; read-back always by name. Chip posts `{id, old, new}`; endpoint consumes the same.
- **DRY / one-guard:** the chokepoint (Task 1) is the single structural guarantee; no creation path re-implements the default. The corrections log is one module; the endpoint is its only writer.
