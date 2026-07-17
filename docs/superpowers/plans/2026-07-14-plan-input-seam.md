# Plan-input seam (selection→LLM redesign) Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per
> task, per-task review, final whole-branch review (the `subagent-driven-development` pattern).
> Steps use checkbox (`- [ ]`) syntax for tracking. **Subagents WRITE files but CANNOT run Bash —
> the main agent runs every test / read-back / live-verify step.** Bash steps are marked
> **(main agent, Bash)**. Line anchors are from HEAD `2e88b58` (2026-07-14/16) — re-derive each at
> its live line before editing; they drift.

**Goal:** Stop Python from gating the daily plan's LLM input to shrink the day. Feed the LLM the
full **active** set (Backburner/Done/future-Scheduled excluded at load; nothing else), structured
into two subsections that read as *different kinds of things* — daily-life chores (scheduled by
task) and block-organized project work (presented by project, with its tasks as an arc). Fix the
loader bug that drops every project's `Goal link`. Remove the Python engagement hide-gate and the
one-next-action collapse from the input path (they move to display). Preserve the shipped zero-ghost
render layer: block-project **real tasks stay in selection, resolvable and checkoffable** — "one
block per project" is achieved as a **post-LLM output property** (coded dedup), never by replacing
real tasks with a synthetic selection unit.

**Architecture:** Two phases. **Phase A (prep)** makes "active" unambiguous and goal data
reachable, independent of the rewrite: loader goal-link fix; active-only filter (Backburner
excluded for all projects); future-`Scheduled` exclusion; June-confirmed engagement backfill
(including the ~4 Daily-life projects + the `Networking and relationships` → Daily life + Open
end-state); duration right-sizing (existing tool). **Phase B (the rewrite)** restructures
`format_context` into the two subsections (each project's `[Engagement]` visible in both, so the
LLM applies room-logic to daily-life and block work alike, plus the goal it serves); removes the
engagement hide-gate + one-per-thread collapse from `_gate_and_collapse` while **keeping
block-project real tasks in selection** (zero-ghost); keeps the shipped `_blockify` (synthetic unit
*only* for task-less container projects); adds a **coded output dedup** (`_group_block_project_items`)
that collapses a block-project's scheduled tasks into ONE "Work on X" block — `chunk_min` allocated
once, scheduled tasks marked `→ here` in the arc, deduped by `project_id` so there is never a
block-header row beside a loose task row for the same project; rewrites the prompt to match. A
final live-verify task regenerates June's real plan end-to-end and reads the result — required per
the repo's build-frame guard, not optional.

### Day-size protection — the named mechanism (NO deterministic cap)
There is deliberately **no count/length cap** on the input or output (a cap would re-impose the
gate this design retires and be redundant with the window). Day-size protection is: (1) the
**scheduler's workday window** — `build_context` computes `start_time`/`end_time` (default 18:00,
widened/narrowed by a Focus Period `workday_end`); `build_schedule` places items only within it and
**overflows the rest into `still_here`**; (2) **capacity signals** the prompt already responds to
(low-energy → lead with lying-down tasks, insert a rest block, reduce work); (3) **three positive
prompt rules** (Task 10): build the schedule from the available hours; prioritize `Steady` unless
the Focus Period overrides; do NOT try to fit every item — deferring to `still_here` is correct, not
failure. No Python size gate anywhere.

### Cross-session ownership (avoid a file collision)
The **born-`Open` chokepoint** (`gsdo_objects.create_object`) and **retiring the hardcoded
`Engagement="Steady"`** in `capture_generate.py` / `gsdt_bind.py` are **owned by the parallel
new-object session** (`docs/handoff_2026-07-14_open-redefinition-and-new-object-rework.md`) and are
**NOT in this plan**. This seam KEEPS: the `daily_plan.py` prose `Steady`→`Open` (it lives inside
the `format_context` rewrite — the seam's file), the engagement backfill, durations, and all of
Phase B. **Dependency note:** the seam depends on the parallel session landing "born-active" so new
projects enter the input by construction — but this plan's live-verify runs on **backfilled existing
data**, so it is **not blocked** by that session.

**Tech Stack:** Python 3 stdlib only (`python3`, never `python`); existing modules `daily_plan`,
`plan_generate`, `grain`, `block_duration`, `when_resolve`, `gsdo_objects`, `gsdo_anytype`;
`prompts/daily_list.md`; pytest with the repo `tests/conftest.py` sandbox redirect. No new deps.

## Global Constraints

- **`python3`, not `python`.** Suite: `python3 -m pytest -q` from repo root.
- **`gsdo_objects.create`/`update` take DISPLAY names** (`"Engagement"`, `"Goal link"`, `"Side"`),
  resolving select values by option name and object-links by id list. Never a property key or tag id.
- **Read a display-generated-key field (Engagement, Side, Block chunk min) by NAME**; read a real
  fixed key (`gsdo_goal_link`, `gsdo_duration_min`, `gsdo_task_status`, `scheduled`) by key, as the
  loader already does.
- **Idempotent writes; no silent failures — raise, don't `assert`.** Read-back every Anytype write.
- **Tests self-clean — NEVER touch June's real space.** `tests/conftest.py` redirects
  `CD_DATA_DIR`/`CD_CONFIG_DIR` to a sandbox and fails the suite if the real data dir's mtimes
  change. Unit tests mock the LLM and Anytype (`monkeypatch`) — no network in `pytest -q`.
- **Subagents WRITE but CANNOT run Bash.** Every run/read-back/commit step is **(main agent, Bash)**.
- **No Python day-size/engagement gate reintroduced in the input path.** If a Phase-B step looks
  like it re-adds a hide-if-not-foregrounded or count cap, stop — that's the frame being retired.
- **Preserve the shipped zero-ghost render layer.** Block-project real tasks must stay resolvable
  and checkoffable (commit `13d14bf` / `ee0fdaf`: "block is a render layer — real tasks stay in
  selection; replacing them with a synthetic unit severed them → uncheckoffable ghost rows"). Never
  replace a task-having block project's real tasks with a synthetic selection unit.
- **Every landed build gets a non-Claude cross-family review** before its thread closes
  (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file with its
  tests). Triage, apply what's real.

---

## Wins to preserve (verify each STILL HOLDS on the Task 12 live regeneration — a survey flagged these as touched by this rework)

Unit tests are not enough; these are runtime properties the past week's builds shipped, and this
rework changes the exact `schedulable` shape they consume. Task 12 checks each on real data.

1. **HIGH — the silent-drop guards** `_ensure_all_tasks_accounted` + `_ensure_all_anchors_accounted`
   (`plan_generate.py:1147-1209`, commit `e3070e1` / `2026-07-16`) have **never run against the new
   shape**. Verify: nothing a block absorbed into its arc is falsely spammed to `still_here`, and
   nothing is silently dropped. (Task 9 fixes `_ensure_all_tasks_accounted` to count absorbed + arc
   ids; Task 12 confirms live.)
2. **`held_back` becomes always-zero** for block projects (the collapse is deleted). Verify the
   overlay renders no phantom "· N more" chip, and that retained `test_within_thread_pick.py` tests
   don't assert a mechanism nothing feeds.
3. **Open surfaces gently** — the `[Engagement]` label MUST render in BOTH subsections (block-work
   project lines AND daily-life project headers) or the LLM has no Open-vs-Steady signal. Preserve
   `test_engagement_visible_on_a_daily_life_project_header` (Task 6).
4. **Focus/low-energy genuinely suppresses** (not just reorders): decision 8 — an `Open` item is
   left off on a rest/low-energy focus "regardless of whether there's technically space." Verify live.
5. **Foreground now only SORTS, not gates** (its selection role left with the gate): verify the LLM
   still elevates a foregrounded/sprint project's *space*, not just its list position (prompt-level).
6. **Recurring stays distinct from engagement** — dishes/meds surface every day by Recurring
   cadence, NOT via a `Steady` daily-life project. Keep the prompt distinction crisp (Task 10); Task
   12 checks Recurring items still surface, none dropped.
7. **Deferred-drop guard** (`_drop_deferred_from_plan`, `plan_generate.py:692`) now faces a LARGER
   name-match surface (full active set). Verify a "not today" deferred item stays dropped (Task 11/12).
8. **Duration backfill is a Phase-A data PRECONDITION** — if skipped, "the day has no real times"
   looks like a rework regression but is a data issue. Say so in triage (Task 5 / Task 12).

---

## File Structure

- `scripts/daily_plan.py` — `load_active_items` (goal-link fix; active-only filter incl. Backburner
  for all projects; future-`Scheduled` exclusion); `format_context` (project-as-block +
  goal-explained; `[Engagement]` on both subsections; prose `Steady`→`Open`); `blocks_from_scheduled`
  (carry `absorbed_ids` on a block row).
- `scripts/plan_generate.py` — `_gate_and_collapse` (remove hide-gate + collapse; keep block-project
  real tasks; relevance-drop only tasks of a dormant project; `held_back`→0); `_surfaces` (deleted —
  both callers rewritten); `_blockify` (keep shipped: synthetic ONLY for task-less containers;
  surface every active task-less block project; skip paused); `_group_block_project_items` +
  `_mark_arc_here` (**new** — post-LLM output dedup into one "Work on X" per project); wiring in
  `_retime_clock_plan` + the priority path; `_ensure_all_tasks_accounted` (count absorbed + arc ids);
  `_resolve_ids` (confirmed correct-by-construction).
- `scripts/backfill_engagement.py` — **NEW.** Proposes + (June-confirmed) applies `Engagement` for
  the blank-engagement projects (block AND the ~4 Daily-life ones) + the required end-state
  `Networking and relationships` → Side=Daily life + Engagement=Open (writes Side too).
- `scripts/duration_backfill.py` — **existing, unmodified** — run as a data step in Phase A.
- `prompts/daily_list.md` — intro prose (no "selection already happened"); the two structural
  subsections; three day-size rules; Open room-logic; Recurring distinction; foreground elevates space.
- Tests: `tests/test_within_thread_pick.py`, `tests/test_rollover.py`, `tests/test_block_selection.py`,
  `tests/test_context_categories.py`, `tests/test_daily_plan_context.py`, `tests/test_retime_clock_plan.py`
  (extended/updated in place); `tests/test_backfill_engagement.py` (**NEW**).

---

# Phase A — prep (independent, low-risk; makes "active" clean + goals reachable)

### Task 1: Loader goal-link fix — a project's Goal link finally reaches the pipeline

**Files:**
- Modify: `scripts/daily_plan.py` — `load_active_items` (`:54-234`): `proj_id_to_name` pre-pass
  (`:58-62`) and the project-parsing block (`:87-122`).
- Test: `tests/test_within_thread_pick.py` (append — it already mocks `load_active_items`).

**Interfaces:**
- Consumes: the real fixed key `gsdo_goal_link` (confirmed by `orient_map.py:96-98,507`
  `_objs(pprops,"gsdo_goal_link")` and the write side `gsdt_bind.py:206` `props["Goal link"]`).
- Produces: every project dict gains `"goal_id"` (first linked goal id or `None`) and `"goal_name"`
  (resolved goal name or `None`). Additive.

- [ ] **Step 1: Write the failing tests.**

```python
# appended to tests/test_within_thread_pick.py

def _goal_obj(oid, name):
    return {"id": oid, "type": {"key": "gsdo_goal"}, "name": name, "properties": []}


def _project_obj_with_goal(oid, name, goal_ids=None, engagement=None):
    props = []
    if goal_ids:
        props.append({"key": "gsdo_goal_link", "objects": goal_ids})
    if engagement:
        props.append({"name": "Engagement", "select": {"name": engagement}})
    return {"id": oid, "type": {"key": "gsdo_project"}, "name": name, "properties": props}


def test_loader_resolves_goal_link_to_goal_name(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _goal_obj("g1", "Stay a scholar-builder"),
        _project_obj_with_goal("p1", "Leatherworking", goal_ids=["g1"], engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    proj = next(p for p in projects if p["name"] == "Leatherworking")
    assert proj["goal_id"] == "g1"
    assert proj["goal_name"] == "Stay a scholar-builder"


def test_loader_project_with_no_goal_link_has_none(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Household", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert projects[0]["goal_id"] is None and projects[0]["goal_name"] is None
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -k goal_link -v`
Expected: FAIL (`KeyError: 'goal_id'`).

- [ ] **Step 3: Implement.** After `proj_id_to_name` (`:61-62`), add a goal pre-pass:

```python
    goal_id_to_name = {o["id"]: o.get("name") for o in data
                       if isinstance(o.get("type"), dict) and o["type"].get("key") == "gsdo_goal"}
```

In the project-parsing block, after `side` is computed (`:104-105`) and before `parent_proj_ids`
(`:107`), add:

```python
            # Goal link -> goal_name (2026-07-14 fix): the loader used to drop this relation, so
            # every project arrived goal-less and the "how does today advance her goals" instruction
            # had nothing to work from (plan_input_seam_design.md, diagnosis 3). Real fixed key.
            goal_ids = pv("gsdo_goal_link", "objects") or []
            goal_id = goal_ids[0] if goal_ids else None
            goal_name = goal_id_to_name.get(goal_id) if goal_id else None
```

Add `"goal_id": goal_id, "goal_name": goal_name,` into the `projects.append({...})` dict.

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -k goal_link -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/daily_plan.py tests/test_within_thread_pick.py
git commit -m "fix(loader): resolve a project's Goal link to goal_id/goal_name (was dropped)"
```

---

### Task 2: Active-only filter at load — Backburner excluded for ALL projects (incl. Daily-life)

**Files:**
- Modify: `scripts/daily_plan.py` — `load_active_items`, project-parsing block (`:87-122`).
- Test: `tests/test_within_thread_pick.py` (append).

**Interfaces:**
- Produces: the returned `projects` list never contains an `engagement == "Backburner"` project —
  for ALL projects, **including `Side = Daily life`** (`plan_input_seam_design.md` REFINEMENT:
  engagement is a universal surfacing axis; `Side` is grain only; the old "Daily-life = always
  eligible, engagement-exempt" rule is retired). `Done` continues to be excluded. `Open` and unset
  engagement stay (relevance filter, not a day-size gate).

- [ ] **Step 1: Write the failing tests.**

```python
# appended to tests/test_within_thread_pick.py

def test_backburner_project_excluded_at_load(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Old hobby", engagement="Backburner"),
        _project_obj_with_goal("p2", "Job search", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Job search"}


def _daily_life_project_obj(oid, name, engagement=None):
    props = [{"name": "Side", "select": {"name": "Daily life"}}]
    if engagement:
        props.append({"name": "Engagement", "select": {"name": engagement}})
    return {"id": oid, "type": {"key": "gsdo_project"}, "name": name, "properties": props}


def test_daily_life_backburner_project_is_also_excluded(monkeypatch):
    # REFINEMENT: engagement is universal — a Backburner Daily-life project is dormant like any
    # other. No Daily-life exemption anymore.
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _daily_life_project_obj("p1", "Old chores", engagement="Backburner"),
        _daily_life_project_obj("p2", "Household", engagement="Steady"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Household"}


def test_open_and_unset_engagement_projects_stay_active(monkeypatch):
    import daily_plan as dp
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _project_obj_with_goal("p1", "Open thread", engagement="Open"),
        _project_obj_with_goal("p2", "Unset thread"),
    ])
    _, projects, _, _, _, _ = dp.load_active_items("sid")
    assert {p["name"] for p in projects} == {"Open thread", "Unset thread"}
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -k "backburner or daily_life_backburner or open_and_unset" -v`
Expected: FAIL.

- [ ] **Step 3: Implement.** After `side` is computed (`:104-105`), below the existing
`if engagement == "Done": continue`, add:

```python
            # Active-only at load (plan_input_seam_design.md decision 1 + REFINEMENT): Backburner is
            # off-focus by construction — excluded before the LLM sees it, for EVERY project,
            # Daily-life included (engagement is universal; Side is grain only, no exemption). Open /
            # unset stay active — this filter is relevance, not a day-size gate.
            if engagement == "Backburner":
                continue
```

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/daily_plan.py tests/test_within_thread_pick.py
git commit -m "feat(loader): active-only at load — Backburner excluded for all projects incl. Daily-life"
```

---

### Task 3: Future-`Scheduled` exclusion at load (June-ratified)

**Files:**
- Modify: `scripts/daily_plan.py` — `load_active_items`, task-parsing block (`:159-196`); add
  `import when_resolve`.
- Test: `tests/test_within_thread_pick.py` (append).

**Context:** `when_resolve.is_scheduled_for_today_or_earlier(scheduled_iso)` (`when_resolve.py:43`)
was written for the selection thread to wire into the loader and was **never wired** — future-dated
(`Scheduled`) tasks are not currently held off today. Phase A already edits `load_active_items`, so
this folds in here. The `Scheduled` property key is `"scheduled"` (`task_actions.py:22`
`SCHEDULED_KEY = "scheduled"`), distinct from the built-in `due_date` the loader already reads.

**Interfaces:**
- Consumes: `when_resolve.is_scheduled_for_today_or_earlier(scheduled_iso, today=None) -> bool`
  (undated or dated today-or-earlier → True; strictly future → False; tolerant of Anytype's
  `'2026-07-16T00:00:00Z'` form).
- Produces: `load_active_items` excludes any task whose `Scheduled` date is strictly in the future;
  undated and today-or-earlier tasks are unaffected.

- [ ] **Step 1: Write the failing tests.**

```python
# appended to tests/test_within_thread_pick.py

def _task_obj_scheduled(oid, name, scheduled=None):
    props = [{"key": "gsdo_task_status", "select": {"name": "Active"}}]
    if scheduled is not None:
        props.append({"key": "scheduled", "date": scheduled})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def test_future_scheduled_task_excluded_at_load(monkeypatch):
    import datetime as dt, daily_plan as dp
    future = (dt.date.today() + dt.timedelta(days=5)).isoformat()
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _task_obj_scheduled("t1", "Future thing", scheduled=future),
        _task_obj_scheduled("t2", "No date thing"),
    ])
    _, _, tasks, _, _, _ = dp.load_active_items("sid")
    assert {t["id"] for t in tasks} == {"t2"}          # the future-dated one is held off today


def test_today_or_earlier_scheduled_task_stays(monkeypatch):
    import datetime as dt, daily_plan as dp
    past = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    monkeypatch.setattr(dp.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(dp.g, "fetch_all_objects", lambda sid: [
        _task_obj_scheduled("t1", "Overdue-scheduled", scheduled=past),
        _task_obj_scheduled("t2", "Today", scheduled=dt.date.today().isoformat()),
    ])
    _, _, tasks, _, _, _ = dp.load_active_items("sid")
    assert {t["id"] for t in tasks} == {"t1", "t2"}
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -k scheduled -v`
Expected: FAIL (`Future thing` still present).

- [ ] **Step 3: Implement.** Add `import when_resolve` to the module imports. In the task-parsing
block, inside the `if status in (...)` branch, right after the `done` check (`:167-169`), add:

```python
                # Future-Scheduled exclusion (June-ratified 2026-07-16): a task with a Scheduled
                # date in the future is not eligible for TODAY's plan. Undated / today-or-earlier
                # pass. `Scheduled` = "start considering on/after this day" (distinct from Due). The
                # predicate was written for the loader (when_resolve) and finally wired here.
                scheduled = pv("scheduled", "date")
                if not when_resolve.is_scheduled_for_today_or_earlier(scheduled):
                    continue
```

- [ ] **Step 4: Run tests to verify they pass, then the loader suite (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/daily_plan.py tests/test_within_thread_pick.py
git commit -m "feat(loader): exclude future-Scheduled tasks from today (wire when_resolve predicate)"
```

---

### Task 4: Engagement backfill for the blank-engagement projects (June-confirmed)

**Files:**
- Create: `scripts/backfill_engagement.py`.
- Test: `tests/test_backfill_engagement.py` (**NEW**).

**Interfaces:**
- Produces:
  - `load_projects(sid=None) -> list[dict]` — live projects with `id`, `name`, `engagement`,
    `side`, `project_status` (legacy "Project status" — Active/Parked/Inactive — read by name).
  - `propose_backfill(projects) -> list[dict]` — pure. Covers block AND Daily-life projects (the
    REFINEMENT retires the Daily-life exemption). For each project with no `engagement`: a
    `Side = Daily life` project is proposed from a name-hint (household/medical/self-care → `Steady`;
    social/networking/other daily-life → `Open`); every other project → `"Backburner"` if
    `project_status == "Inactive"` else `"Open"`. Already-set projects are skipped. Plus fixed
    **required end-states** applied regardless of current value:
    `"Networking and relationships" → Side = "Daily life" + Engagement = "Open"` (the Donna-Haraway
    case). Each proposal `{"id","name","current","proposed"[,"side"]}`.
  - `apply_backfill(proposals) -> dict` — re-reads each project; a fill-the-blank proposal (no
    `side`) skips a project that gained an Engagement since the proposal (idempotent); a
    required-end-state (has `side`) applies regardless. Writes Engagement (+ Side when present),
    read-back-verifies both, returns `{"updated":int,"skipped":int,"failed":[{"id","name","error"}]}`
    — one failure never aborts the rest.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/test_backfill_engagement.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import backfill_engagement as be


def test_propose_backfill_inactive_to_backburner_else_open():
    projects = [
        {"id": "a", "name": "Old thing", "engagement": None, "side": None, "project_status": "Inactive"},
        {"id": "b", "name": "Job search", "engagement": None, "side": None, "project_status": None},
        {"id": "c", "name": "Already set", "engagement": "Steady", "side": None, "project_status": None},
    ]
    out = {p["name"]: p["proposed"] for p in be.propose_backfill(projects)}
    assert out == {"Old thing": "Backburner", "Job search": "Open"}
    assert "Already set" not in out


def test_propose_backfill_covers_daily_life_projects_by_name_hint():
    projects = [
        {"id": "d", "name": "household", "engagement": None, "side": "Daily life", "project_status": None},
        {"id": "e", "name": "Medical and self-care", "engagement": None, "side": "Daily life", "project_status": None},
        {"id": "f", "name": "Friendships and social", "engagement": None, "side": "Daily life", "project_status": None},
    ]
    out = {p["name"]: p["proposed"] for p in be.propose_backfill(projects)}
    assert out == {"household": "Steady", "Medical and self-care": "Steady",
                   "Friendships and social": "Open"}


def test_propose_backfill_forces_the_networking_end_state():
    projects = [
        {"id": "n", "name": "Networking and relationships", "engagement": "Steady",
         "side": "Wellbeing", "project_status": None},
    ]
    props = [p for p in be.propose_backfill(projects) if p["name"] == "Networking and relationships"]
    assert len(props) == 1
    assert props[0]["proposed"] == "Open" and props[0]["side"] == "Daily life"


def test_apply_backfill_writes_and_reads_back(monkeypatch):
    written = {}
    monkeypatch.setattr(be.gsdo_objects, "update",
                        lambda oid, properties: written.update({oid: properties}))
    calls = {"n": 0}

    def fake_get_project(oid):
        calls["n"] += 1
        val = None if calls["n"] == 1 else "Open"
        props = [{"name": "Engagement", "select": {"name": val}}] if val else []
        return {"id": oid, "properties": props}
    monkeypatch.setattr(be, "_get_project", fake_get_project)

    result = be.apply_backfill([{"id": "a", "name": "Old thing", "proposed": "Open"}])
    assert result == {"updated": 1, "skipped": 0, "failed": []}
    assert written["a"] == {"Engagement": "Open"}


def test_apply_backfill_skips_project_that_gained_engagement_since_proposal(monkeypatch):
    monkeypatch.setattr(be.gsdo_objects, "update", lambda oid, properties: (_ for _ in ()).throw(
        AssertionError("must not write — the project already gained a value")))
    monkeypatch.setattr(be, "_get_project", lambda oid: {
        "id": oid, "properties": [{"name": "Engagement", "select": {"name": "Steady"}}]})
    result = be.apply_backfill([{"id": "a", "name": "Old thing", "proposed": "Open"}])
    assert result == {"updated": 0, "skipped": 1, "failed": []}


def test_apply_backfill_required_end_state_writes_side_and_engagement_despite_current_value(monkeypatch):
    written = {}
    monkeypatch.setattr(be.gsdo_objects, "update",
                        lambda oid, properties: written.update({oid: properties}))
    calls = {"n": 0}

    def fake_get_project(oid):
        calls["n"] += 1
        if calls["n"] == 1:
            props = [{"name": "Engagement", "select": {"name": "Steady"}},
                     {"name": "Side", "select": {"name": "Wellbeing"}}]
        else:
            props = [{"name": "Engagement", "select": {"name": "Open"}},
                     {"name": "Side", "select": {"name": "Daily life"}}]
        return {"id": oid, "properties": props}
    monkeypatch.setattr(be, "_get_project", fake_get_project)

    result = be.apply_backfill([{"id": "n", "name": "Networking and relationships",
                                 "proposed": "Open", "side": "Daily life"}])
    assert result == {"updated": 1, "skipped": 0, "failed": []}
    assert written["n"] == {"Engagement": "Open", "Side": "Daily life"}
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_backfill_engagement.py -v`
Expected: FAIL (`No module named 'backfill_engagement'`).

- [ ] **Step 3: Implement.**

```python
#!/usr/bin/env python3
"""Backfill Engagement onto existing Projects with no value, so 'active' (plan_input_seam_
design.md decision 1 + REFINEMENT) is unambiguous going into daily_plan.load_active_items's
active-only filter.

Engagement is UNIVERSAL now — the old "Daily-life stays unset on purpose" exemption is retired, so
this covers the ~4 Daily-life projects too, each getting a real value June confirms. It also
applies June-ratified REQUIRED END-STATES (data changes set regardless of current value, held until
this seam is built): `Networking and relationships` -> Side=Daily life + Engagement=Open, so
"Email Donna Haraway" becomes a discrete daily-life task that surfaces if-room, not daily.

Reviewable, like duration_backfill.py: a bare run proposes + prints the mapping (no writes);
--run writes only after June confirms. Idempotent: a fill-the-blank proposal skips a project that
already gained a value; a required-end-state proposal applies regardless.
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
from anytype_test import call


_REQUIRED_END_STATES = {
    "Networking and relationships": {"side": "Daily life", "engagement": "Open"},
}
_DAILY_LIFE_HINT = {"household": "Steady", "chore": "Steady", "medical": "Steady",
                    "self-care": "Steady", "self care": "Steady"}


def _pv_by_name(obj, name, field):
    for p in obj.get("properties", []):
        if p.get("name") == name:
            return p.get(field)
    return None


def load_projects(sid=None):
    sid = sid or g.get_space_id()
    out = []
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") != "gsdo_project":
            continue
        out.append({"id": o["id"], "name": o.get("name"),
                    "engagement": (_pv_by_name(o, "Engagement", "select") or {}).get("name"),
                    "side": (_pv_by_name(o, "Side", "select") or {}).get("name"),
                    "project_status": (_pv_by_name(o, "Project status", "select") or {}).get("name")})
    return out


def _daily_life_hint(name):
    low = (name or "").lower()
    for kw, val in _DAILY_LIFE_HINT.items():
        if kw in low:
            return val
    return "Open"    # social / relationships / unknown daily-life -> available if-room, not daily


def propose_backfill(projects):
    out = []
    for p in projects:
        name = p["name"]
        req = _REQUIRED_END_STATES.get(name)
        if req:
            out.append({"id": p["id"], "name": name, "current": p.get("engagement"),
                        "proposed": req["engagement"], "side": req["side"]})
            continue
        if p.get("engagement"):
            continue
        if p.get("side") == "Daily life":
            proposed = _daily_life_hint(name)
        else:
            proposed = "Backburner" if p.get("project_status") == "Inactive" else "Open"
        out.append({"id": p["id"], "name": name, "current": p.get("engagement"), "proposed": proposed})
    return out


def _get_project(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def apply_backfill(proposals):
    result = {"updated": 0, "skipped": 0, "failed": []}
    for item in proposals:
        try:
            forced = "side" in item
            current = (_pv_by_name(_get_project(item["id"]), "Engagement", "select") or {}).get("name")
            if current and not forced:
                result["skipped"] += 1
                continue
            props = {"Engagement": item["proposed"]}
            if item.get("side"):
                props["Side"] = item["side"]
            gsdo_objects.update(item["id"], properties=props)
            back = _get_project(item["id"])
            got_eng = (_pv_by_name(back, "Engagement", "select") or {}).get("name")
            if got_eng != item["proposed"]:
                raise RuntimeError(f"Engagement read-back mismatch for {item['id']!r}: "
                                   f"wrote {item['proposed']}, read-back={got_eng!r}")
            if item.get("side"):
                got_side = (_pv_by_name(back, "Side", "select") or {}).get("name")
                if got_side != item["side"]:
                    raise RuntimeError(f"Side read-back mismatch for {item['id']!r}: "
                                       f"wrote {item['side']}, read-back={got_side!r}")
            result["updated"] += 1
        except Exception as e:
            result["failed"].append({"id": item["id"], "name": item["name"], "error": str(e)})
    return result


def format_proposal(proposals):
    if not proposals:
        return "No projects need an engagement backfill — nothing to do."
    lines = [f"{len(proposals)} project(s) to set:"]
    for p in proposals:
        side_bit = f"  (Side -> {p['side']})" if p.get("side") else ""
        lines.append(f"  - {p['name']}  ->  Engagement {p['proposed']}{side_bit}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Backfill blank Project Engagement (June-confirmed)")
    ap.add_argument("--run", action="store_true", help="write the proposed values (with read-back)")
    args = ap.parse_args()
    proposals = propose_backfill(load_projects())
    print(format_proposal(proposals))
    if args.run:
        print("\n--- applying ---")
        print(json.dumps(apply_backfill(proposals), indent=2))
    else:
        print("\nRun --run to write these values after June confirms the mapping above.")
```

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_backfill_engagement.py -v`
Expected: PASS.

- [ ] **Step 5: DRY-RUN for June (main agent, Bash) — do not skip.**
`python3 scripts/backfill_engagement.py` (no `--run`). Present the mapping plainly: block projects
(Inactive → Backburner, else Open); the ~4 Daily-life projects (household/medical/self-care →
Steady, social/networking → Open); and the required end-state `Networking and relationships` →
Side=Daily life + Engagement=Open (so "Email Donna Haraway" surfaces if-room, not daily). Call out
the Daily-life values and the Networking Side change specifically — those are the new, consequential
ones, and each Daily-life value is June's call. **Do not `--run` until she confirms.**

- [ ] **Step 6: Commit the script (main agent, Bash)** (the `--run` against her space happens in
Task 12 after her confirmation):
```bash
git add scripts/backfill_engagement.py tests/test_backfill_engagement.py
git commit -m "feat(defaults): June-confirmed Engagement backfill — block + Daily-life + Networking end-state (dry-run by default)"
```

---

### Task 5: Duration right-sizing — run the existing backfill (data step, no new code)

**Files:** none modified — `scripts/duration_backfill.py` exists, is tested
(`tests/test_duration_backfill.py`), has dry-run/`--preview`/`--run`.

**Why (win #8):** diagnosis #4 — most tasks carry no duration, so `scheduler.DEFAULT_DURATION_MIN =
30` (`scripts/scheduler.py:6`) flattens a 2-hour block and a 5-minute call, and the clock schedule
comes out empty/wrong. This is a **data precondition**, not code. If it is skipped, "the day has no
real times" in Task 12 is a data issue, not a rework regression — say so in triage.

- [ ] **Step 1 (main agent, Bash): see the gap.** `python3 scripts/duration_backfill.py`. If the
count is zero, skip the rest and note it. Otherwise continue.
- [ ] **Step 2 (main agent, Bash): preview (read-only).** `python3 scripts/duration_backfill.py --preview`.
- [ ] **Step 3: present the preview to June plainly** (tasks, estimated minutes, one-line reasons).
Do not proceed without her go-ahead.
- [ ] **Step 4 (main agent, Bash): on her confirmation, apply.**
`python3 scripts/duration_backfill.py --run` (writes labeled `Duration source = estimated`, with
per-task read-back). If unconfirmed, STOP and hold. Note the outcome for Task 12.

---

# Phase B — the structural rewrite

### Task 6: `format_context` — project-as-block, goal-explained; engagement in both subsections; prose Steady→Open

**Files:**
- Modify: `scripts/daily_plan.py` — `format_context` (`:275-507`): `_project_line` (`:363-382`),
  the projects-section hint (`:354-357`), the goal-line prose default (`:338`), and the tasks
  section (`:407-469`).
- Test: `tests/test_context_categories.py` (rewritten in place), `tests/test_daily_plan_context.py`
  (verify no regression).

**Interfaces:**
- Consumes: `project["goal_name"]` (Task 1), `project["arc"]` (already produced by
  `grain.project_arc` at `daily_plan.py:147`, `[{"text","state","id"}]` or `None`),
  `grain.classify(project)` (existing).
- Produces: `## Active projects` shows each project's goal (`| goal: <name>`) and an `[Open]`
  default for unset engagement (was `[Steady]`). The tasks section splits into `### Block-organized
  work` — one line per **project** classified `"block"`, with its `[Engagement]`, goal, and arc as
  context (or "a bare chunk of time" when it has no arc) — and `### Daily tasks` — one line per
  task grouped by daily-life project, **each header carrying its `[Engagement]`**. Engagement is
  visible in BOTH subsections (win #3).

**NOTE for the implementer (small fix E):** the header split `### Block-organized work` /
`### Daily tasks` **already exists** (commit `6e5ce06`). So the "run to fail" below fails on the
**goal / engagement / arc-vs-enumerated-tasks** assertions, NOT on the header split — the split is
already there. Do not suspect a broken test setup.

- [ ] **Step 1: Write the failing tests.** Replace the whole content of
`tests/test_context_categories.py`:

```python
"""format_context splits the active set into two structurally distinct categories
(plan_input_seam_design.md decisions 3 & 4): block-organized work is presented BY PROJECT (one
'Work on X' line, goal-explained, its tasks shown as an arc), daily-life work stays BY TASK. Each
project carries its [Engagement] in BOTH subsections."""
import daily_plan


def _proj(name, side, goal_name=None, arc=None, engagement="Steady"):
    return {"id": name, "name": name, "side": side, "is_workstream": False,
            "parent_project_id": None, "engagement": engagement, "goal_name": goal_name, "arc": arc}


def _task(name, proj):
    return {"id": "t-" + name, "name": name, "linked_projects": [proj], "status": "Active"}


def test_context_splits_block_work_from_daily_tasks():
    projects = [_proj("IOP and recovery", "Wellbeing"), _proj("Household", "Daily life")]
    tasks = [_task("Verify disability", "IOP and recovery"),
             _task("Clean the kitchen", "Household")]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)
    assert "### Block-organized work" in ctx and "### Daily tasks" in ctx
    block_hdr = ctx.index("### Block-organized work")
    daily_hdr = ctx.index("### Daily tasks")
    # the block PROJECT is listed in the block section (search FROM the header — the name also
    # appears earlier in `## Active projects`, so a plain .index finds that one).
    assert block_hdr < ctx.index("IOP and recovery", block_hdr) < daily_hdr
    assert ctx.index("Clean the kitchen") > daily_hdr    # a task name — only in Daily tasks


def test_block_work_shows_goal_and_arc():
    arc = [{"text": "Verify disability", "state": "here", "id": "t1"},
           {"text": "File paperwork", "state": "ahead", "id": "t2"}]
    projects = [_proj("IOP and recovery", "Wellbeing", goal_name="Stay stable", arc=arc)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "goal: Stay stable" in ctx
    assert "Verify disability" in ctx and "File paperwork" in ctx


def test_block_work_container_with_no_arc_reads_as_a_bare_chunk():
    projects = [_proj("Scholarly writing", "Wellbeing", arc=None)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "Scholarly writing" in ctx and "bare chunk of time" in ctx


def test_block_project_appears_even_with_zero_tasks_this_cycle():
    projects = [_proj("Scholarly writing", "Wellbeing")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "### Block-organized work" in ctx and "Scholarly writing" in ctx


def test_engagement_visible_on_a_block_project_line():
    projects = [_proj("Leatherworking", "Wellbeing", engagement="Steady")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "[Steady]" in ctx[ctx.index("### Block-organized work"):]


def test_engagement_visible_on_a_daily_life_project_header():
    projects = [_proj("Networking and relationships", "Daily life", engagement="Open")]
    tasks = [_task("Email Donna Haraway", "Networking and relationships")]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)
    daily_hdr = ctx.index("### Daily tasks")
    line = ctx.index("Networking and relationships", daily_hdr)
    assert "[Open]" in ctx[line:ctx.index("Email Donna Haraway")]


def test_unset_engagement_shows_open_not_steady():
    projects = [_proj("Ghost", "Wellbeing", engagement=None)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "[Open]" in ctx and "[Steady]" not in ctx


def test_active_projects_section_shows_goal():
    projects = [_proj("Leatherworking", "Wellbeing", goal_name="Stay a scholar-builder")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "## Active projects" in ctx and "goal: Stay a scholar-builder" in ctx
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_context_categories.py -v`
Expected: FAIL on the goal / engagement / arc assertions (NOT the header split — that already exists).

- [ ] **Step 3: Implement.**

Goal-line prose default (`:338`): `eng = g_.get("engagement") or "Steady"` → `... or "Open"`.

In `_project_line` (`:363-382`), change the default to `"Open"` and add the goal line:
```python
        def _project_line(p, indent=""):
            eng = p.get("engagement") or "Open"
            eng_notes = p.get("engagement_notes") or ""
            line = f"{indent}- {p['name']} [{eng}]"
            if p.get("side"):
                line += f" | side: {p['side']}"
            if p.get("goal_name"):
                line += f" | goal: {p['goal_name']}"
            if p["name"] in paused:
                line += " [paused this period]"
            if eng_notes:
                line += f" | {eng_notes}"
            rf = p.get("reaching_for") or ""
            ctx = p.get("context") or ""
            aff = p.get("affective") or ""
            if rf:
                line += f" | reaching for: {rf}"
            if ctx:
                line += f" | context: {ctx}"
            if aff:
                line += f" | affective: {aff}"
            return line
```

Replace the projects-section hint (`:354-357`):
```python
        lines.append("(engagement: Steady → a normal daily move; Open → available, not pushed;"
                     " unset → treat as active, never hidden. What's elevated right now is set by"
                     " the Focus Period foreground, not the tag — don't inflate a project's space"
                     " just for its label. Backburner projects are excluded before you see this.)")
```

Replace the entire tasks section (`:407-469`) with:
```python
    # Block-work subsection lists the schedulable block-grain projects — excluding any paused this
    # Focus Period (they aren't scheduled; a paused project still appears, marked, in the
    # `## Active projects` section above, so it isn't hidden).
    _paused_names = set((period or {}).get("paused") or [])
    block_projects = [p for p in projects
                      if grain.classify(p) == "block" and p["name"] not in _paused_names]

    if tasks or block_projects:
        lines.append("## Active tasks by project/thread")
        lines.append("(The LLM should organize the plan by these project/thread groupings,")
        lines.append(" NOT by activity category like 'writing' or 'admin'.)")

        def _task_extras(t):
            extras = []
            if t.get("status") == "Needs Clarifying":
                extras.append("needs clarifying")
            if t.get("blocked_on"):
                extras.append(f"blocked on: {t['blocked_on']}")
            if t.get("duration_min"):
                extras.append(f"~{t['duration_min']}min")
            if t.get("affective"):
                extras.append(f"affective: {t['affective']}")
            if t.get("access"):
                extras.append(f"access: {', '.join(t['access'])}")
            return f" ({'; '.join(extras)})" if extras else ""

        project_tasks: dict = {}
        no_project = []
        for t in tasks:
            projs = t.get("linked_projects") or []
            if projs:
                for pn in projs:
                    project_tasks.setdefault(pn, []).append(t)
            else:
                no_project.append(t)

        proj_by_name = {p["name"]: p for p in projects}

        def _grain_of(pname):
            p = proj_by_name.get(pname)
            return grain.classify(p) if p else "task"        # no-project → discrete, daily-side

        daily_projects = {pn: ts for pn, ts in project_tasks.items() if _grain_of(pn) == "task"}

        if block_projects:
            lines.append("### Block-organized work — one 'Work on X' unit per project, scheduled as"
                         " ONE chunk of time (not a task list). Each carries its [Engagement]"
                         " (Steady → a normal daily move; Open → pull in only if there's room, and"
                         " never on a rest/low-energy focus). Its steps are shown below as its arc —"
                         " context for you, not separate plan items.")
            _STATE_MARK = {"done": "[x]", "here": "[ ] (next)", "ahead": "[ ]"}
            for p in block_projects:
                eng = p.get("engagement") or "Open"
                goal_bit = f" — goal: {p['goal_name']}" if p.get("goal_name") else ""
                lines.append(f"- **{p['name']}** [{eng}]{goal_bit}")
                arc = p.get("arc")
                if arc:
                    for step in arc:
                        lines.append(f"  - {_STATE_MARK.get(step.get('state'), '[ ]')} {step['text']}")
                else:
                    lines.append("  - (no individual steps tracked — a bare chunk of time)")
        if daily_projects or no_project:
            lines.append("### Daily tasks — discrete chores + standalone actions, scheduled one at a"
                         " time. Each project header carries its [Engagement] (Steady → its chores"
                         " belong today; Open → pull one in only if the day has room, never on a"
                         " rest/low-energy focus). True every-day chores (dishes, meds) come through"
                         " as Recurring items by their own cadence, not from engagement.")
            for pname, ptasks in daily_projects.items():
                dproj = proj_by_name.get(pname)
                eng = (dproj.get("engagement") if dproj else None) or "Open"
                lines.append(f"- **{pname}** [{eng}]")
                for t in ptasks:
                    lines.append(f"  - {t['name']}{_task_extras(t)}")
            if no_project:
                lines.append("- **[No project]**")
                for t in no_project:
                    lines.append(f"  - {t['name']}{_task_extras(t)}")
        lines.append("")
```

- [ ] **Step 4: Run tests to verify they pass, then the wider context files (main agent, Bash).**
`python3 -m pytest tests/test_context_categories.py tests/test_daily_plan_context.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/daily_plan.py tests/test_context_categories.py
git commit -m "feat(context): block-work project-as-block + goal-explained; engagement in both subsections; unset→Open prose"
```

---

### Task 7: `_gate_and_collapse` — remove the hide-gate + collapse; KEEP block-project real tasks in selection

**Files:**
- Modify: `scripts/plan_generate.py` — `_gate_and_collapse` (`:518-631`).
- Test: `tests/test_within_thread_pick.py` (precise surgery, below), `tests/test_rollover.py`
  (rewrite two tests), `tests/test_block_selection.py` (rename/adjust
  `test_non_daily_life_unset_engagement_still_hidden` — its assertion changes, see below).

**Interfaces:**
- Consumes: active-set membership (`projects`), `_match_extra` (existing).
- Produces: `_gate_and_collapse(tasks, projects, neglected, period, extra=None, surface_dates=None,
  rollover_ids=None)` — same signature. New behavior: the engagement hide-gate and the
  one-move-per-thread collapse are **removed** (decisions 9 & 10). A task is dropped **only** if
  every linked project is not in the active `projects` list (its project was excluded at load —
  Backburner/Done/future) — so off-focus work can't leak in via a task whose project was excluded.
  A discrete (no-project) task always stays. A task June named (`extra`) or carried over undone
  (`rollover_ids`) is kept even if its project is dormant. **Block-project real tasks whose project
  is active pass through unchanged** — resolvable, checkoffable (the shipped zero-ghost design; NOT
  replaced by a synthetic unit). Nothing collapses, so `held_back`/`held_back_names` are always
  `0`/`[]` (win #2). `_pick_within_thread` is no longer called from here (left in place, still
  directly tested — a deliberate retain).

**The concrete duplicate-row bug this avoids (name it up front):** replacing a task-having block
project's real tasks with a synthetic "Work on X" selection unit **severs the tasks from
resolution** → uncheckoffable ghost rows (commit `13d14bf`/`ee0fdaf`). Separately, emitting a
synthetic block-header row AND leaving a loose row for one of that project's own tasks schedules the
project twice. This task keeps real tasks in selection (no ghost); Task 9's coded dedup guarantees
no double row.

- [ ] **Step 1: Test surgery in `tests/test_within_thread_pick.py`.**
  - **DELETE** the gate-collapse tests: `test_gate_picks_the_signal_winner_not_storage_order`,
    `test_gate_records_held_back_count`, `test_gate_forced_task_still_passes_through` (the `:95-149`
    block before `test_task_ref_line_carries_held_back`), plus `test_gate_records_held_back_names`
    and `test_gate_no_held_names_when_thread_is_alone` (`:163-182`).
  - **KEEP untouched**: the `_pick_within_thread` pure-function tests (`:1-95`);
    `test_task_ref_line_carries_held_back` (`:152` — tests `_task_ref_line` with a hand-set
    `held_back`, a still-present renderer, independent of the gate); the two `_resolve_ids` held_back
    tests (`:185-208` — same). These pass because they set the field explicitly.
  - **ADD** the new gate tests (the `_proj` here replaces the deleted one at `:98` — the retained
    tests don't call `_proj`):

```python
def _proj(name, eng="Steady", side="Wellbeing"):
    return {"name": name, "engagement": eng, "side": side}


def test_block_project_task_stays_in_selection():
    # Reconciled 2026-07-16: a block-project's REAL tasks stay resolvable/checkoffable in selection
    # (the shipped zero-ghost design) — NOT dropped, NOT replaced by a synthetic unit.
    tasks = [{"id": "a", "name": "Cut", "linked_projects": ["Leatherworking"]}]
    projects = [_proj("Leatherworking")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


def test_task_of_a_dormant_project_is_dropped():
    # A Backburner project was excluded at load (Task 2), so it isn't in `projects`; its task must
    # not leak into the input (the recovery-week off-focus leak the seam fixes).
    tasks = [{"id": "t1", "name": "Dye", "linked_projects": ["Old hobby"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={})   # "Old hobby" not active
    assert kept == []


def test_dormant_project_task_survives_when_rolled_over():
    tasks = [{"id": "t1", "name": "Email editor", "linked_projects": ["Paper"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={}, rollover_ids={"t1"})
    assert [t["id"] for t in kept] == ["t1"]


def test_dormant_project_task_survives_when_named():
    tasks = [{"id": "t1", "name": "Email editor", "linked_projects": ["Paper"]}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={}, extra="email editor today")
    assert [t["id"] for t in kept] == ["t1"]


def test_no_project_task_always_kept():
    tasks = [{"id": "a", "name": "Call surgeon", "linked_projects": []}]
    kept = pg._gate_and_collapse(tasks, [], [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]


def test_held_back_is_always_zero_now():
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"]},
             {"id": "b", "name": "b", "linked_projects": ["P"]}]
    projects = [_proj("P")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"a", "b"}          # no collapse — both stay
    assert all(t["held_back"] == 0 for t in kept)


def test_daily_life_task_kept():
    tasks = [{"id": "a", "name": "Dishes", "linked_projects": ["Household"]}]
    projects = [_proj("Household", eng="Steady", side="Daily life")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert [t["id"] for t in kept] == ["a"]
```

Rewrite `tests/test_rollover.py`'s two affected tests (keep the two `rollover_log` tests untouched):

```python
def test_rollover_carries_a_dormant_project_task_into_today():
    # "Paper" is dormant (excluded at load -> not in `projects`). Its undone task would be dropped;
    # rollover makes it eligible so "email editor rolls to today" works.
    tasks = [{"id": "t1", "name": "Email the editor", "linked_projects": ["Paper"]}]
    dropped = pg._gate_and_collapse(tasks, [], neglected=[], period=None, surface_dates={})
    assert dropped == []
    carried = pg._gate_and_collapse(tasks, [], neglected=[], period=None,
                                    surface_dates={}, rollover_ids={"t1"})
    assert [t["id"] for t in carried] == ["t1"]


def test_active_project_tasks_all_survive_uncollapsed():
    # No collapse anymore: both tasks of an active project stay (Task 9 groups them into one block
    # at OUTPUT). This gate no longer picks one representative.
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"]},
             {"id": "b", "name": "b", "linked_projects": ["P"]}]
    projects = [{"name": "P", "engagement": "Steady", "side": "Wellbeing"}]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"a", "b"}
```

In `tests/test_block_selection.py`, replace `test_non_daily_life_unset_engagement_still_hidden` —
its ASSERTION changes (an active unset-engagement project's task now STAYS; only a task whose
project is absent from the active set is dropped):
```python
def test_non_daily_life_unset_engagement_task_stays_when_project_active():
    # Reconciled: the engagement hide-gate is gone. An unset-engagement project that IS in the
    # active set keeps its task (Task 9 renders it as a block at output). Only a task of a project
    # absent from the active set (dormant) is dropped.
    projects = [_proj("Some project", eng=None, side="Wellbeing")]
    tasks = [_task("t1", "A task", "Some project")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"t1"}
```

- [ ] **Step 2: Run to verify failures (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py tests/test_rollover.py tests/test_block_selection.py -v`
Expected: FAIL (old collapse behavior still in place).

- [ ] **Step 3: Implement.** Replace `_gate_and_collapse` (`:518-631`) with:

```python
def _gate_and_collapse(tasks, projects, neglected, period, extra=None, surface_dates=None,
                       rollover_ids=None):
    """Relevance pass-through (seam 2026-07-14/16). The engagement hide-gate and the
    one-move-per-thread collapse are REMOVED (plan_input_seam_design.md decisions 9 & 10):
    active-only-at-load (daily_plan.load_active_items) is the sole engagement filter, and the LLM
    applies the room-logic from the visible [Engagement] label (format_context). Here we drop only a
    task whose EVERY linked project is not in the active `projects` list — i.e. its project was
    excluded at load (Backburner/Done/future) — so off-focus work can't leak in via a task whose
    project is dormant. A discrete (no-project) task always stays. A task June named (`extra`) or
    carried over undone (`rollover_ids`) is kept even if its project is dormant (an explicit ask /
    carry-over overrides). Block-project real tasks whose project is active pass through UNCHANGED —
    resolvable and checkoffable (the shipped zero-ghost design; they are never replaced by a
    synthetic selection unit). Nothing collapses, so held_back is always 0 (the overlay must render
    no phantom '· N more'). `neglected`, `period`, `surface_dates` are accepted for call-site
    compatibility but gate nothing. `_pick_within_thread` is intentionally not called (retained,
    still directly tested)."""
    active_names = {p.get("name") for p in projects}
    named = _match_extra(extra, projects, tasks)
    rollover_ids = set(rollover_ids or [])

    def is_forced(t):
        return t.get("id") in named["task_ids"] or t.get("id") in rollover_ids

    kept = []
    for t in tasks:
        projs = t.get("linked_projects") or []
        if projs and not is_forced(t) and not any(pn in active_names for pn in projs):
            continue                                   # every linked project dormant -> off today
        t["held_back"], t["held_back_names"] = 0, []
        kept.append(t)
    return kept
```

- [ ] **Step 4: Run tests to verify they pass, then the wider selection suite (main agent, Bash).**
`python3 -m pytest tests/test_within_thread_pick.py tests/test_rollover.py tests/test_block_selection.py tests/test_plan_generate_selection.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/plan_generate.py tests/test_within_thread_pick.py tests/test_rollover.py tests/test_block_selection.py
git commit -m "feat(selection): remove engagement hide-gate + collapse; keep block-project real tasks in selection (zero-ghost)"
```

---

### Task 8: `_blockify` — keep the shipped synthetic unit for task-LESS containers only; surface every active such project

**Files:**
- Modify: `scripts/plan_generate.py` — `_blockify` (`:634-667`); delete `_surfaces` (`:499-515`,
  now dead — its callers were `_gate_and_collapse` (Task 7) and this container pass); call site in
  `build_context` (`:727`) + `daily_plan.run` (`:962`).
- Test: `tests/test_block_selection.py` (rewrite the `_blockify` tests, `:63-102`).

**Interfaces:**
- Consumes: `grain.classify`, `grain.block_unit(project, shape, arc, chunk_min)`,
  `block_duration.get_chunk_min(project)` (all existing, unchanged).
- Produces: `_blockify(kept, projects, paused=None) -> list` — **keeps the shipped shape**: real
  tasks in `kept` pass through UNCHANGED; the ONLY synthetic unit emitted is one bare-chunk block
  for a **task-LESS container** block project (`project.get("arc")` falsy AND no task of it is in
  `kept`). A project that already has a real task in `kept` is skipped (no synthetic — the real task
  represents it; Task 9 renders the block at output). **`period`/`neglected` are dropped from the
  signature** (their only purpose was `_surfaces`, deleted); surfacing is by active-only-at-load, so
  every active task-less block project surfaces (decision 8). A project **paused** this Focus Period
  is skipped (decision 7). Workstreams / Fun-hobby / Daily-life never emit (grain).

- [ ] **Step 1: Write the failing tests.** Replace `tests/test_block_selection.py`'s `_blockify`
tests (`test_blockify_block_project_tasks_pass_through_unchanged` through
`test_blockify_workstream_never_emitted`, `:63-102`) with:

```python
def test_blockify_block_project_tasks_pass_through_unchanged():
    # A block-project's REAL tasks stay in the list (checkoffable) — NOT replaced by a synthetic
    # unit (the shipped zero-ghost design). The block is a render grouping (Task 9), not selection.
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing",
                  arc=[{"text": "Cut", "state": "here", "id": "t1"}], chunk_min=120)
    kept = [_task("t1", "Cut", "Leatherworking"), _task("t2", "Stitch", "Leatherworking")]
    out = pg._blockify(kept, [proj])
    assert out == kept                                   # both real tasks pass through, keep ids
    assert not any(o.get("block") for o in out)          # no synthetic block emitted


def test_blockify_daily_life_stays_task():
    proj = _bproj("hh", "Household", eng=None, side="Daily life")
    kept = [_task("t1", "Dishes", "Household")]
    assert pg._blockify(kept, [proj]) == kept


def test_blockify_container_bare_chunk_for_taskless_project():
    proj = _bproj("sw", "Scholarly writing", eng="Steady", side="Wellbeing")   # arc None, no tasks
    out = pg._blockify([], [proj])
    assert len(out) == 1 and out[0]["shape"] == "chunk" and out[0]["id"] == "block:sw"
    assert out[0]["duration_min"] == block_duration.BLOCK_DEFAULT_MIN


def test_blockify_container_surfaces_every_active_taskless_project():
    # No _surfaces gate anymore — active-only-at-load is the filter, so an Open task-less block
    # project surfaces as a container (decision 8: Open is in the input, available if-room).
    proj = _bproj("q", "Quiet project", eng="Open", side="Wellbeing")
    out = pg._blockify([], [proj])
    assert len(out) == 1 and out[0]["id"] == "block:q"


def test_blockify_container_with_a_survivor_is_not_double_emitted():
    # If a block project already has a real task in `kept`, it is NOT a task-less container -> no
    # synthetic unit (dedup at the source; no survivor row + synthetic header for one project).
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing")   # arc None
    kept = [_task("t1", "Cut", "Leatherworking")]
    out = pg._blockify(kept, [proj])
    assert out == kept and not any(o.get("block") for o in out)


def test_blockify_paused_taskless_project_skipped():
    proj = _bproj("q", "Paused", eng="Steady", side="Wellbeing")
    assert pg._blockify([], [proj], paused={"Paused"}) == []
    assert len(pg._blockify([], [proj])) == 1             # not paused -> one container


def test_blockify_workstream_never_emitted():
    proj = _bproj("ws", "A workstream", eng="Steady", side="Wellbeing", ws=True)
    assert pg._blockify([], [proj]) == []
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py -v`
Expected: FAIL (`_blockify` still takes `period`/`neglected`; still calls `_surfaces`).

- [ ] **Step 3: Implement.** Delete `_surfaces` (`:499-515`). Replace `_blockify` (`:634-667`) with:

```python
def _blockify(kept, projects, paused=None):
    """Emit the ONE remaining synthetic block: a task-LESS container project (e.g. scholarly
    writing — a bundle of subprojects with nothing to check off) becomes a bare 'did a chunk today'
    block. Everything else passes through UNCHANGED — a block-project's REAL tasks stay in selection,
    resolvable and checkoffable (the shipped zero-ghost design, commit 13d14bf: block is a RENDER
    layer, not a synthetic selection unit for task-having projects; replacing real tasks with a
    synthetic unit severed them -> ghost rows). 'One block per project' for task-HAVING projects is
    an OUTPUT property applied post-LLM (_group_block_project_items, Task 9), NOT here.

    Surfacing is by active-only-at-load: every project reaching here is active, so every task-less
    block project surfaces (no engagement/_surfaces gate — deleted; decision 8: an Open task-less
    block project is in the input). A project with a real task already in `kept` is NOT a task-less
    container (its task represents it -> no synthetic). A project PAUSED this Focus Period is skipped
    (decision 7)."""
    paused = paused or set()
    out = list(kept)
    projects_with_survivors = {pn for t in kept for pn in (t.get("linked_projects") or [])}
    for proj in projects:
        name = proj.get("name")
        if name in projects_with_survivors or grain.classify(proj) != "block":
            continue
        if name in paused:
            continue
        if proj.get("arc"):                              # has direct tasks (in selection) -> not a container
            continue
        out.append(grain.block_unit(proj, "chunk", None, block_duration.get_chunk_min(proj)))
    return out
```

Update the call site in `build_context` (`:727`): compute paused from the period and pass it:
```python
    _paused = set((period or {}).get("paused") or [])
    schedulable = _blockify(schedulable, projects, paused=_paused)
```
Update `daily_plan.run` (`:962`), which already calls `_gate_and_collapse` — add the `_blockify`
call right after it (it currently doesn't call `_blockify`; without it the chat path shows no
task-less container blocks):
```python
    schedulable = plan_generate._gate_and_collapse(schedulable, projects, neglected, period,
                                                   surface_dates=surfaced_dates())
    _paused = set((period or {}).get("paused") or [])
    schedulable = plan_generate._blockify(schedulable, projects, paused=_paused)
```

- [ ] **Step 4: Run tests to verify they pass, then the plan_generate suite (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py tests/test_plan_generate.py tests/test_plan_generate_selection.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/plan_generate.py scripts/daily_plan.py tests/test_block_selection.py
git commit -m "feat(blockify): keep shipped synthetic-for-taskless-only; surface every active container; skip paused; delete dead _surfaces"
```

---

### Task 9: Output "one block per project" — coded dedup grouping (chunk_min once, arc → here, absorbed ids)

**Files:**
- Modify: `scripts/plan_generate.py` — add `_group_block_project_items` + `_mark_arc_here`; call
  from `_retime_clock_plan` (before `build_schedule`, `:1165`) and the priority path in
  `generate_plan`/`reorder`; update `_ensure_all_tasks_accounted` (`:1147-1172`).
- Modify: `scripts/daily_plan.py` — `blocks_from_scheduled` block branch (`:798-806`): carry
  `absorbed_ids` onto the row.
- Test: `tests/test_block_selection.py` (append the dedup + accounting tests),
  `tests/test_retime_clock_plan.py` (append a retime-grouping test).

**Why this task exists (the coded invariant a build-agent critic required):** "one block per
project" (decision 3) is an OUTPUT property, not a synthetic selection unit. Real block-project
tasks stayed resolvable through selection (Task 7); here their scheduled rows collapse into ONE
"Work on X" block per `project_id` — `chunk_min` allocated ONCE (not summed per task), scheduled
tasks marked `→ here` in the arc, **deduped by `project_id` so there is never a block-header row
beside a loose row for the same project** (the project scheduled twice). Coded + tested, not prompt
prose.

**Interfaces:**
- Produces:
  - `_mark_arc_here(arc, task_id) -> None` — in place; sets the arc step whose `id == task_id` to
    `"here"`. No-op if the id isn't a step.
  - `_group_block_project_items(items) -> list` — collapses items carrying `block_project`/`block`
    with a `project_id` into ONE block-shaped dict per `project_id`
    (`{"task":"Work on X","block":True,"project_id","arc","chunk_min","duration_min":chunk_min,
    "shape","absorbed_ids":[...], "_composed"}`); each scheduled task's arc step marked `here`; real
    ids collected in `absorbed_ids`. Non-block items pass through unchanged; order preserved (a
    project anchors at its first item's position).
- Consumes: the block-render metadata the shipped `build_context` loop (`:736-746`) already
  attaches to real block-project tasks (`block_project`, `project_id`, `arc`, `chunk_min`) and
  `_resolve_ids` re-attaches by id (`:1061-1067`).

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_block_selection.py`:

```python
def test_group_block_project_items_dedups_two_tasks_into_one_block():
    # THE dedup invariant: an LLM plan naming TWO individual tasks of one block project resolves to
    # ONE 'Work on X' block, both marked '→ here' in its arc — never two rows, never a duplicate.
    arc = [{"text": "Cut", "state": "done", "id": "t1"},
           {"text": "Dye", "state": "here", "id": "t2"},
           {"text": "Stitch", "state": "ahead", "id": "t3"}]
    items = [
        {"id": "t2", "task": "Dye", "project": "Leatherworking", "block_project": True,
         "project_id": "lw", "arc": arc, "chunk_min": 120, "_composed": True},
        {"id": "t3", "task": "Stitch", "project": "Leatherworking", "block_project": True,
         "project_id": "lw", "arc": arc, "chunk_min": 120, "_composed": True},
    ]
    out = pg._group_block_project_items(items)
    assert len(out) == 1                                  # ONE block, not two rows
    blk = out[0]
    assert blk["block"] is True and blk["project_id"] == "lw"
    assert blk["duration_min"] == 120                     # chunk_min ONCE, not 240
    assert set(blk["absorbed_ids"]) == {"t2", "t3"}       # both real ids retained (accounting)
    states = {s["id"]: s["state"] for s in blk["arc"]}
    assert states["t2"] == "here" and states["t3"] == "here" and states["t1"] == "done"


def test_group_block_project_items_passes_non_block_through():
    items = [{"id": "d", "task": "Dishes", "project": "Household"},
             {"id": "c", "task": "Call", "project": None}]
    assert pg._group_block_project_items(items) == items


def test_ensure_all_tasks_accounted_counts_block_absorbed_and_arc_ids():
    # win #1: a task a block absorbed into its arc must NOT be spammed to still_here.
    plan = {"blocks": [{"items": [{"block": True, "project_id": "lw", "absorbed_ids": ["t2"],
                                   "arc": [{"id": "t3", "state": "ahead"}]}]}], "still_here": []}
    tasks = [{"id": "t2", "name": "Dye"}, {"id": "t3", "name": "Stitch"}, {"id": "t9", "name": "Loose"}]
    pg._ensure_all_tasks_accounted(plan, tasks)
    labels = {sh["label"] for sh in plan["still_here"]}
    assert "Dye" not in labels and "Stitch" not in labels   # absorbed + in-arc -> accounted
    assert "Loose" in labels                                # genuinely unplaced -> parked
```

Append to `tests/test_retime_clock_plan.py`:

```python
def test_retime_groups_block_project_tasks_into_one_chunk():
    # Two block-project tasks the LLM scheduled collapse to ONE "Work on X" chunk (chunk_min once).
    arc = [{"text": "Dye", "state": "here", "id": "t2"},
           {"text": "Stitch", "state": "ahead", "id": "t3"}]
    tasks = [{"id": "t2", "name": "Dye", "duration_min": 45},
             {"id": "t3", "name": "Stitch", "duration_min": 45}]
    plan = _clock_plan([
        {"time": "x", "task": "Dye", "project": "Leatherworking", "why": "w", "interstitial": False,
         "id": "t2", "block_project": True, "project_id": "lw", "arc": arc, "chunk_min": 90},
        {"time": "x", "task": "Stitch", "project": "Leatherworking", "why": "w", "interstitial": False,
         "id": "t3", "block_project": True, "project_id": "lw", "arc": arc, "chunk_min": 90},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 16, 10, 0),
                          end_time=dt.datetime(2026, 7, 16, 18, 0))
    rows = [it for b in plan["blocks"] for it in b["items"]]
    block_rows = [r for r in rows if r.get("block")]
    assert len(block_rows) == 1                            # one "Work on X" row for the project
    assert block_rows[0]["time"] == "10:00 – 11:30"        # chunk_min=90 ONCE, not 45+45 twice
    # neither absorbed task appears as its own loose row
    assert not any(r.get("task") == "Stitch" and not r.get("block") for r in rows)
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py -k "group_block or ensure_all_tasks_accounted_counts" tests/test_retime_clock_plan.py -k groups_block -v`
Expected: FAIL (`_group_block_project_items` undefined; retime doesn't group yet).

- [ ] **Step 3: Implement.** Add, above `_retime_clock_plan`:

```python
def _mark_arc_here(arc, task_id):
    """Mark the arc step whose id == task_id as the current focus ('here'). In place; a no-op if the
    id isn't a step (defensive, not an error)."""
    for step in (arc or []):
        if step.get("id") == task_id:
            step["state"] = "here"
            return


def _group_block_project_items(items):
    """Collapse a block-project's scheduled task items into ONE 'Work on X' block per project_id
    (plan_input_seam_design.md decision 3, reconciled 2026-07-16: 'one block per project' is an
    OUTPUT property, NOT a synthetic selection unit — real tasks stayed resolvable through selection
    and here group at output). DEDUP by project_id: a block project yields EXACTLY ONE block row,
    never a 'Work on X' header row beside a loose row for one of that project's own tasks (the
    project scheduled twice). The block's duration is chunk_min allocated ONCE (never the sum of the
    tasks); every scheduled task's step is marked '→ here' in the arc; the absorbed real task ids are
    retained (`absorbed_ids`) so the silent-drop guard counts them placed. Non-block items pass
    through unchanged, order preserved (a project anchors at its first item's position). A task-LESS
    container synthetic block (already block=True, one per project) folds through idempotently."""
    grouped, by_pid = [], {}
    for it in items:
        pid = it.get("project_id") if (it.get("block_project") or it.get("block")) else None
        if not pid:
            grouped.append(it)
            continue
        block = by_pid.get(pid)
        if block is None:
            label = f"Work on {it.get('project') or ''}".rstrip()
            block = {"task": label, "name": label, "project": it.get("project"),
                     "why": it.get("why"), "block": True, "project_id": pid,
                     "arc": [dict(s) for s in (it.get("arc") or [])],
                     "chunk_min": it.get("chunk_min"), "duration_min": it.get("chunk_min"),
                     "shape": "arc" if it.get("arc") else "chunk",
                     "interstitial": False, "_composed": bool(it.get("_composed")),
                     "absorbed_ids": []}
            by_pid[pid] = block
            grouped.append(block)
        if it.get("id"):
            _mark_arc_here(block["arc"], it["id"])
            block["absorbed_ids"].append(it["id"])
    return grouped
```

In `_retime_clock_plan`, right before `scheduled = dp.build_schedule(composed, ...)` (`:1165`), add:
```python
    composed = _group_block_project_items(composed)   # one 'Work on X' per project, chunk_min once
```

In `generate_plan` and `reorder`, right after the `_retime_clock_plan(...)` call, add the priority
path (retime is a no-op for priority, so its flat items are grouped here):
```python
    if plan.get("shape") == "priority":
        plan["items"] = _group_block_project_items(plan.get("items", []))
```

Update `_ensure_all_tasks_accounted` (`:1159-1162`) to also count absorbed + arc ids as placed:
```python
    placed_ids = set()
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            if item.get("id"):
                placed_ids.add(item["id"])
            placed_ids.update(item.get("absorbed_ids") or [])
            for step in (item.get("arc") or []):
                if step.get("id"):
                    placed_ids.add(step["id"])
    for item in plan.get("items", []):                # priority shape (flat)
        if item.get("id"):
            placed_ids.add(item["id"])
        placed_ids.update(item.get("absorbed_ids") or [])
        for step in (item.get("arc") or []):
            if step.get("id"):
                placed_ids.add(step["id"])
```

In `daily_plan.blocks_from_scheduled`, the `it.get("block")` branch (`:798-806`), add so the row
carries the absorbed ids downstream:
```python
                    row["absorbed_ids"] = it.get("absorbed_ids", [])
```

- [ ] **Step 4: Run tests to verify they pass, then the retime + plan_generate suites (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py tests/test_retime_clock_plan.py tests/test_plan_generate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/plan_generate.py scripts/daily_plan.py tests/test_block_selection.py tests/test_retime_clock_plan.py
git commit -m "feat(output): one 'Work on X' block per project (chunk_min once, arc→here, dedup by project_id); account absorbed ids"
```

---

### Task 10: Prompt + JSON contract rewrite

**Files:**
- Modify: `prompts/daily_list.md` — intro (`:16`), the blocks paragraph (`:56`), and add the
  day-size + Open + Recurring + foreground rules.
- Verify (no edit expected): `scripts/plan_generate.py` `_JSON_INSTRUCTION` (`:256-341`) /
  `_JSON_INSTRUCTION_PRIORITY` (`:344-395`).
- Test: `tests/test_block_selection.py` (one confirmation test).

**Interfaces:**
- Produces: `daily_list.md` no longer says selection already happened; it names the two structural
  subsections, the three day-size rules (no cap), Open's focus-subordinate rule, the Recurring
  distinction, and that a foregrounded project gets more *space*, not just list position.
  `_task_ref_line` is confirmed already shape-agnostic (branches only on `t.get("block")`), so a
  task-less container block still renders as "a chunk of time" — no code change (Task 8 didn't
  change block units).

- [ ] **Step 1: Confirmation test (passes immediately).**

```python
# appended to tests/test_block_selection.py
def test_task_ref_line_block_reads_as_a_chunk():
    block = grain.block_unit({"id": "sw", "name": "Scholarly writing"}, "chunk", None, 240)
    line = pg._task_ref_line("T1", block)
    assert "Work on Scholarly writing" in line and "chunk of time" in line and "more" not in line
```

- [ ] **Step 2: Run it (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py -k reads_as_a_chunk -v`
Expected: PASS immediately (confirmation — no implementation follows for `_task_ref_line`).

- [ ] **Step 3: Rewrite `prompts/daily_list.md`.** Replace the `:16` sentence with:
```
- Active tasks/projects/goals with fields. **Everything here is active — nothing has been pre-filtered by engagement or by a day-size gate.** The context is split into two structurally different categories (see "Block-organized work" vs. "Daily tasks" below): daily-life chores you schedule one at a time, and ongoing project work you schedule as one "Work on X" chunk per project. **You** choose what fits today from this whole active set, guided by the Focus Period + Strategies + capacity. Each project shows its **[Engagement]** — use it (and its notes) to frame and weight a project, not to hide it; what's elevated is set by the Focus Period foreground, not the label.
```
Replace the `:56` blocks paragraph with:
```
**Two categories, two grains — structural, not a suggestion.** "Daily tasks" are scheduled BY TASK: each chore is its own item. "Block-organized work" is scheduled BY PROJECT: each project is marked in the TASK REFERENCE as `Work on X — a chunk of time (do not list its internal steps)`, whether or not steps are shown under it. For a block, "Work on X" is the CORRECT grain — do not make it a specific next action, do not break it into steps, do not enumerate what's inside it (its steps are shown for your context only). Order and narrate it as one chunk; it carries its own duration. The overlay renders its internal arc.

**Build the schedule from the hours the day actually has.** (1) Compose against the available time between now and the workday's end — Python places items in the clock, and whatever doesn't fit is held in `still_here`; you don't need a hard count. (2) Prioritize `Steady` work unless the Focus Period says otherwise — Steady is a normal daily move; a foregrounded or Sprint project should get MORE of the day's space (not just a higher spot in the list). (3) Do NOT try to fit every item — deferring to `still_here` is the correct answer on a full or low day, not a failure.

**`Open` is available if there's room — never assumed.** An `Open` project (block OR daily-life) is active, so it's in front of you; include it when the day has room. But a rest / low-energy Focus Period means an `Open` item is the first thing to leave for another day, **regardless of whether there's technically space** — the Focus Period's intent governs over "there was room." This applies to a Daily-life project's chores exactly as to block work.

**True every-single-day items come through as Recurring, not engagement.** Dishes, medications and the like arrive as Recurring items on their own cadence — never dropped, never inferred from a `Steady` daily-life project. Keep Recurring items in the plan every day; do not treat a Daily-life project's engagement as the mechanism for "daily."
```

- [ ] **Step 4: Verify the JSON contracts don't contradict the new framing (main agent — read, edit
only on a real conflict).** Read `scripts/plan_generate.py:256-395`; confirm neither block claims
"already gated" / "task-less only" / a count cap. (As written they only describe output JSON shape —
no edit expected; fix + note if a conflict is found.)

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add prompts/daily_list.md tests/test_block_selection.py
git commit -m "docs(prompt): two subsections; three day-size rules (no cap); Open room-logic; Recurring distinct; foreground elevates space"
```

---

### Task 11: `_resolve_ids` — confirm resolution is correct-by-construction; deferred-drop still holds

**Files:**
- Verify (no functional edit expected): `scripts/plan_generate.py` — `_resolve_ids` (`:964-1074`),
  `_drop_deferred_from_plan` (`:692`).
- Test: `tests/test_block_selection.py` (append two regression tests).

**Interfaces:**
- Consumes: `all_tasks` (the 7th `build_context` return — the full active task list, now genuinely
  active-only: Backburner projects' tasks are dropped at the gate, future-Scheduled at load).
- Produces: no code change — pins decision 10 (no ghost, no escape hatch needed) and win #7 (a
  deferred "not today" item stays dropped despite the larger name-match surface).

- [ ] **Step 1: Regression tests (pass immediately).**

```python
# appended to tests/test_block_selection.py
def test_resolve_ids_name_match_never_finds_a_dormant_task():
    # Correct-by-construction: a dormant project's task is dropped at the gate / load, so it isn't in
    # all_tasks — no name to match, ghost or otherwise.
    gated = [{"id": "t1", "name": "Organize letters"}]
    plan = {"blocks": [{"items": [{"task": "A task from a Backburner project"}]}]}
    pg._resolve_ids(plan, {}, gated, all_tasks=gated)
    assert plan["blocks"][0]["items"][0].get("id") is None


def test_deferred_item_stays_dropped_after_resolution():
    # win #7: a "not today" deferred label the model re-added from context is dropped, even with the
    # larger full-active name-match surface. _drop_deferred_from_plan is the guarantee.
    plan = {"blocks": [{"items": [{"id": "t1", "task": "Do the thing"}]}],
            "still_here": [{"label": "Do the thing", "note": "not today", "deferred": True}]}
    pg._drop_deferred_from_plan(plan)
    assert all(it.get("task") != "Do the thing"
               for b in plan["blocks"] for it in b["items"])
```

*Implementer: match `_drop_deferred_from_plan`'s real deferred-marker shape against live code
(`:692`); adjust the fixture's `still_here` entry to whatever field it keys on, keeping the
assertion (the deferred item is not in `blocks`).*

- [ ] **Step 2: Run (main agent, Bash).**
`python3 -m pytest tests/test_block_selection.py -k "never_finds_a_dormant or deferred_item_stays" -v`
Expected: PASS (confirmation).

- [ ] **Step 3: Commit (main agent, Bash).**
```bash
git add tests/test_block_selection.py
git commit -m "test(resolve): pin correct-by-construction resolution + deferred-drop under the larger name-match surface"
```

---

### Task 12: Integration + live-plan-regeneration verify (REQUIRED — do not skip)

Per the repo's build-frame guard: a green suite is not sufficient. Regenerate June's REAL plan on
REAL data and read it — the discipline that caught the synthetic-block-as-selection-unit bug 599
passing tests missed.

**Wiring:** `daily_plan.load_active_items` (goal-link + active-only + future-Scheduled, Tasks 1-3) →
`plan_generate.build_context` (`select_and_order_tasks` → `partition_by_side` → `_gate_and_collapse`
(Task 7) → `_blockify` (Task 8) → block-render-metadata loop `:736-746`, unchanged) →
`_build_task_refs`/`_assemble_prompt` (prompt, Task 10) → `generate` → `parse_plan` → `_resolve_ids`
(Task 11) → `_retime_clock_plan` (groups block-project tasks into one block, Task 9) →
`_ensure_all_tasks_accounted`/`_ensure_all_anchors_accounted` — the shape `generate_plan`/`reorder`
cache and the overlay renders.

- [ ] **Step 1 (main agent, Bash): confirm Phase A data landed.** With June's confirmation, run
`python3 scripts/backfill_engagement.py --run` (Task 4) and `python3 scripts/duration_backfill.py
--run` (Task 5). If either is pending her confirmation, proceed to Step 2 but **note in triage that
missing durations make "no real times" a DATA issue, not a rework regression** (win #8).

- [ ] **Step 2 (main agent, Bash): run the read-only regeneration** — mirrors `generate_plan`'s body
MINUS the cache/log/mirror writes at its tail (`plan_store.save_plan`, `plan_snapshot_log`,
`rollover_log`, `_log_scheduled_blocks`, `plan_mirror`, `log_surfaced_batch`) — read-only against
her space (calls the LLM + reads Anytype; writes nothing back):

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift && python3 -c "
import sys, json
sys.path.insert(0, 'scripts')
import plan_generate as pg
full_context, tasks, start_time, shape, all_anchors, end_time, all_active_tasks = pg.build_context()
ref_map, task_table = pg._build_task_refs(tasks)
prompt = pg._assemble_prompt(full_context, start_time, task_table=task_table,
                             request_kind='generate', shape=shape)
print('=== CONTEXT ==='); print(full_context)
print('=== GENERATING (live LLM) ===')
plan = pg.parse_plan(pg.generate(prompt))
mislabels, resolved = pg._resolve_ids(plan, ref_map, tasks, all_tasks=all_active_tasks)
pg._ensure_all_tasks_accounted(plan, tasks)
pg._retime_clock_plan(plan, tasks, all_anchors, start_time, end_time)
if plan.get('shape')=='priority': plan['items']=pg._group_block_project_items(plan['items'])
print('=== RESOLVED PLAN ==='); print(json.dumps(plan, indent=2, default=str))
print(f'resolved={resolved} mislabels={mislabels} n_input_tasks={len(tasks)}')
"
```

- [ ] **Step 3 (main agent): read the context + plan and confirm each — plainly, not just "it ran":**
  - **Only active items.** No Backburner/Done/future-Scheduled project or task anywhere.
  - **Two cleanly separated subsections;** nothing straddles both.
  - **Block-work by project — exactly ONE row per block project, NO duplicate.** A single `"block":
    true` "Work on X" row per project — never that row PLUS a loose row for one of its own tasks
    (the project scheduled twice), and never two block rows for one project. Its arc holds the real
    task ids (checkoffable — zero ghost); the scheduled ones show `here`. `chunk_min` once, not
    summed. **(Task 9's coded dedup — the highest-risk property; scrutinize it.)**
  - **Daily-life by task, engagement-driven.** Each chore its own checkoffable row. A `Daily life +
    Open` task (e.g. "Email Donna Haraway", if the Networking end-state was applied) is present with
    `[Open]` and NOT force-scheduled every day; a rest/low-energy focus suppresses it (**win #4**).
  - **Recurring items still surface, none dropped** (**win #6**) — dishes/meds appear by cadence, not
    from a Steady daily-life project.
  - **Nothing falsely in `still_here`** — a task a block absorbed into its arc is NOT spammed there
    (**win #1**); and nothing silently dropped (a real task is scheduled OR honestly in still_here).
  - **No phantom "· N more" chip** anywhere — `held_back` is 0 for block work (**win #2**).
  - **Foreground elevates space, not just order** — a foregrounded/Sprint project gets a real share
    of the day (**win #5**).
  - **Goals visible per project** in the context (block-work lines + `## Active projects`).
  - If anything looks bolted-on rather than fitted-in, stop and check the function (build-frame guard).

- [ ] **Step 4 (main agent, Bash): full suite, clean tree.**
`python3 -m pytest -q`
Expected: all green; the conftest real-data tripwire did not fire.

- [ ] **Step 5 (main agent, Bash): cross-family review** before the thread closes
(`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file with its tests).
Triage; apply the real findings — especially any on Task 9's dedup/accounting.

- [ ] **Step 6 (main agent, Bash): commit.**
```bash
git add -A
git commit -m "test(seam): live-verify the plan-input seam end-to-end + wins-preservation on real data"
```

---

## Self-Review

> **These ✓ mark SPEC COVERAGE, not runtime verification.** Runtime verification is Task 12's job
> (drive the real plan). A checked box here means "a task implements this decision," not "it works
> live."

**Spec coverage** (design decisions + REFINEMENT + the day-size mechanism):
1. Active-only input — Task 2 (Backburner all projects) + Task 3 (future-Scheduled) + task-status
   filter ✓.
2. No separate eligible list — Tasks 7-9 make `schedulable` = the active set restructured by grain ✓.
3. Structural separation by formatting — Task 6 + Task 9 (block-by-project as OUTPUT) + Task 10 ✓.
4. Goal-explained projects — Task 1 + Task 6 ✓.
5. Prompt explains each category positively — Task 10 ✓.
6. LLM applies the logic; no Python re-gate / no cap — Tasks 7-10 + the day-size section ✓.
7. Focus period governs — ordering + period block + Task 10 (Open subordinate; foreground elevates
   space) ✓.
8. Open available-if-room, subordinate to focus — Task 2 + Task 6 (label both subsections) + Task 10 ✓.
9. Collapse moves to display only — Task 7 removes input-side collapse; Task 9 is the display-side
   grouping ✓.
10. Resolution correct-by-construction — Task 11 ✓.
REFINEMENT (engagement universal, Side grain-only) — Tasks 2, 6, 7, 10, 4 (backfill incl. Daily-life
+ Networking) ✓. Day-size (no cap) — the design section + Task 10's three rules ✓.
Future-Scheduled exclusion (June-ratified) — Task 3 ✓.
**B (no synthetic-unit-per-project; dedup coded + tested):** Task 8 keeps the shipped synthetic ONLY
for task-less containers, block-project real tasks stay in selection (zero-ghost); Task 9 is the
coded output dedup (`_group_block_project_items`, chunk_min once, `absorbed_ids`) with the
two-tasks→one-block regression test ✓.
**F (chokepoint/capture/bind removed):** no task touches `gsdo_objects.create_object`,
`capture_generate.py`, or `gsdt_bind.py`; the dependency note names the parallel session ✓.
Wins 1-8 — woven into Task 12's live checks (and Task 9 for #1, Task 6 for #3, Task 11 for #7) ✓.

**Placeholder scan:** every code step has complete real code; the confirmation-only steps (Task 10
`_task_ref_line`, Task 11) state *why* no implementation follows.

**Type/name consistency (2 lines):** `_group_block_project_items` / `_mark_arc_here` / `absorbed_ids`
are defined in Task 9 and consumed identically by `_retime_clock_plan`, the priority path,
`_ensure_all_tasks_accounted`, and `blocks_from_scheduled`; `_blockify(kept, projects, paused=None)`
and `_gate_and_collapse(...)` signatures match every call site (`build_context`, `daily_plan.run`),
and `_surfaces` is deleted after both callers are rewritten.
