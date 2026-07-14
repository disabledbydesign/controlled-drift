# Block as a render layer (not selection) — Implementation Plan

> **For agentic workers:** build task-by-task via the build-loop — fresh subagent per task where isolated, orchestrator does QC (runs the suite, live-verifies), per-task commit, final cross-family review. Subagents can't run pytest here → the orchestrator runs it and gates. Line numbers are from 2026-07-14 and may shift; each subagent reads the live file at its point.

> **Design authority:** `docs/display_grain_design.md`, especially the `## REVISION 2026-07-14` section. This plan implements that revision. **Read it first** — the whole point is that the block is a *rendering* over real selected tasks, never a synthetic unit inside selection.

**Why this rework exists (the bug it fixes).** The shipped build inserted `_blockify` into task *selection*: it replaced a project's real next-task with a synthetic `block:<project_id>` unit in the list the LLM orders and `_resolve_ids` resolves. Live regeneration of June's real plan showed the failure: the LLM composes from the full-hierarchy context (which still lists the real tasks), named them, but they had no ref token (only the block did) → `_resolve_ids` couldn't find their ids → **uncheckoffable ghost rows**. Also the arc carried no task ids, so even a rendered block's steps weren't checkoffable. Root cause: **blockify displaced real tasks in selection instead of grouping them at render time.**

**Goal.** Task selection returns to exactly its pre-block behavior (real tasks, real ids, resolvable, checkoffable). A non-Daily-life project's ordered tasks are **displayed** grouped under a "Work on X" block header with a checkoffable arc. A task-less container project (scholarly writing) is the **only** remaining synthetic unit — a bare "did a chunk today" block. Every task the model names resolves to a real id.

**The corrected data flow (the spine — hold this the whole build):**
- **Order-list / resolvable set** = real tasks (for task-having projects, block *and* daily) **+** synthetic container-blocks **only** for task-less block-projects. NO synthetic block replaces a real task.
- **`_resolve_ids`** name-matches against **all active tasks**, so any named real task resolves (kills ghosts).
- **`format_context`** presents the full hierarchy split into two labeled categories: "Block-organized work" (non-Daily-life projects → their tasks) and "Daily tasks" (chores).
- **Rendering** (overlay): a block-project's ordered task rows group under a gold "Work on X" header (project-level did-a-chunk + duration) whose arc = that project's tasks (`{text, state, id}`), each step a checkbox (check + undo). Daily-life tasks render flat. A container block renders as a bare did-a-chunk (no arc).

**Tech / constraints (repo bar).** `python3`; `python3 -m pytest -q` from root; **green baseline: 596.** Tests self-clean (`cd_sandbox`, mock `gsdo_objects`, never write Anytype in a test). No silent failures — raise, don't `assert`. June-facing copy: plain words, no metaphors. Reuse existing mechanisms (groupByProject, toggleItem complete/uncomplete, the id-map machinery) — do not build parallels. Every task commits atomically; final cross-family review (`github_models_review.py`, chunked per file+tests).

---

### Task 1: Arc steps carry the real task id

`grain.project_arc` returns `{text, state}` per step — add `id`. This is the field whose absence made arc steps un-checkoffable.

**Files:** `scripts/grain.py` (`project_arc`); `tests/test_grain.py`.

- [ ] **Step 1 (failing test):** extend `test_project_arc_states_in_order` (and add one) to assert each step has the source task's `id` (`"task-Outline"` etc. from the fixture).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** In `project_arc`, carry `o["id"]` into each `steps` entry and emit `{"text", "state", "id"}`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(grain): arc steps carry the real task id (checkoffable)`.

---

### Task 2: `_blockify` — stop displacing real tasks; keep only the container synthetic block

Rework `_blockify` so it **no longer replaces a task-having project's tasks** with a synthetic unit. Its ONLY remaining job: emit a synthetic `block_unit` for a **task-less** block-project (the container / scholarly-writing case). Task-having block-projects: leave their real tasks in the list untouched (Task 3 attaches render metadata).

**Files:** `scripts/plan_generate.py` (`_blockify`); `tests/test_block_selection.py`.

- [ ] **Step 1 (failing tests):** update `test_blockify_*` — a block-project WITH a surviving task now leaves that real task in the output (NOT replaced by a `block:` unit); a task-LESS block-project still yields one synthetic container block (`shape="chunk"`, `arc=None`); daily-life + workstream unchanged.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Remove Path 1 (the thread-replacement). Keep Path 2 (container pass) — but only for block-projects with **zero** surviving tasks AND (per Task 1's arc) **no direct tasks at all** (`project.get("arc")` is falsy), so a project whose tasks were merely gated-out this cycle doesn't become a bare chunk. Real tasks pass through unchanged.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(block): blockify emits ONLY container synthetic blocks; real tasks stay in selection`.

---

### Task 3: Attach block-render metadata to block-project task rows

So the renderer can group a project's tasks as a block, each block-project task row (and the container synthetic block) carries the render fields — WITHOUT leaving the selection pipeline. Attach in `build_context` after `_blockify`, keyed off `grain.classify(project) == "block"`.

**Files:** `scripts/plan_generate.py` (`build_context`, `_resolve_ids` attach-by-id — mirror `held_back`); `scripts/daily_plan.py` (`blocks_from_scheduled` row copy); `tests/test_block_selection.py`.

**Row fields (a real task that belongs to a block-project):**
```
block_project: True, project_id, project (name), chunk_min,
arc: [{text,state,id}, ...], did_chunk_today  (project-level, from chunk_log)
```
The row keeps its own real `id` (its task) — check-off marks that task done. `block_project`/`arc`/`chunk_min` are Python-owned, re-attached by the task's id in `_resolve_ids` exactly as `held_back` is (the id-map already accepts real task ids — no synthetic id needed).

- [ ] **Step 1 (failing test):** a resolved block-project task row keeps its real `id` AND gains `block_project`/`project_id`/`arc`/`chunk_min`; `did_chunk_today` set from `chunk_log`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** In `build_context`, after `_blockify`, for each real task whose project `classify=="block"`, attach the render fields (arc via the project's already-attached `arc`, chunk via `block_duration.get_chunk_min`). Extend `_resolve_ids`' by-id attach (where `held_back`/`block` were) to carry `block_project`/`project_id`/`arc`/`chunk_min`. In `blocks_from_scheduled`, copy them onto the row + set `did_chunk_today`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(block): attach block-render metadata to real block-project task rows`.

---

### Task 4: `_resolve_ids` name-matches against ALL active tasks (kill the ghosts)

Its fallback name-match currently runs against only the gated order-list (`tasks` arg). Widen it to all active tasks so any real task the model names — from the full-hierarchy context — resolves to its id.

**Files:** `scripts/plan_generate.py` (`build_context` returns/threads the full task list; `generate_plan`/`_negotiate` pass it to `_resolve_ids`; `_resolve_ids` builds `by_name` from it). `tests/test_block_selection.py`.

- [ ] **Step 1 (failing test):** `_resolve_ids` with a plan item naming a real task that is NOT in the gated order-list but IS in the full-active set → resolves to that task's id (no ghost). Keep the STRICT exact-normalized match (a loose match could mark the wrong task done).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Thread the full active task list (already loaded in `load_active_items`) through `build_context`'s return into `_resolve_ids`; build `by_name` from it. Ref-token resolution unchanged; only the fallback set widens.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(plan): resolve named tasks against all active tasks — no more uncheckoffable ghosts`.

---

### Task 5: `format_context` — full hierarchy, split into two labeled categories

Present the structure the model already gets, organized so "Block-organized work" (non-Daily-life projects → tasks) is a distinct, labeled category from "Daily tasks" (chores). The model sees the whole picture and which category each item is.

**Files:** `scripts/daily_plan.py` (`format_context`); `tests/` (a format assertion — the two category headers appear; a Daily-life project's tasks sit under "Daily tasks", a block-project's under "Block-organized work").

- [ ] **Step 1 (failing test):** the rendered context contains both category headers, and a known Daily-life project is under the daily category, a block-project under the block category.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** In `format_context`, partition projects by `grain.classify` (Daily-life → daily category; block → block category; excluded → omit) and render two labeled sections. Keep the hierarchy (project → its tasks) within each.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(plan): context presents the hierarchy split into block-work vs daily-task categories`.

---

### Task 6: Overlay — render block-project groups as blocks; arc steps checkoffable; container = bare chunk

Rework the overlay so the block is a **rendering** over the real task rows.

**Files:** `docs/overlay_daily.html`. Local mockup: `docs/mockups/display-grain-arc-mockup.html` (visual target; the block CSS is already ported from the prior build — reuse it).

- [ ] **Step 1:** `groupByProject`/`renderGroup`: a group whose rows carry `block_project` renders as a **block** — gold "Work on <project>" header, the project-level did-a-chunk check (`toggleBlock(project_id)`, cache-only), the duration chip (`/api/duration`), and the **arc** (`row.arc`) as the expandable body. **Each arc step is a checkbox** wired to `toggleItem(step.id, ...)` — the existing task complete/uncomplete path, so check-off AND undo work per step. Daily-life groups render flat (as today).
- [ ] **Step 2:** A **container** block (the synthetic `block:` unit, `shape="chunk"`, no arc, no `block_project` rows) renders as a bare did-a-chunk block (largely the existing `renderBlock` chunk path). Keep it.
- [ ] **Step 3:** Remove the old assumption that a block ROW is atomic/replaces a task — a block-project now groups real task rows. Ensure `renderPriorityItem` and tap-to-place handle a block-group whose members are real tasks.
- [ ] **Step 4:** Manual browser smoke against a canned plan (sandbox server, `CD_PORT`): a block-project with an arc whose steps check off + undo; a container block as a bare chunk; a daily chore flat; the walk. Confirm no console errors. Commit `feat(block): overlay renders block-project groups with a checkoffable arc; container stays a bare chunk`.

---

### Task 7: Overlay polish — one "edit" affordance (reorder + duration), rename to "set duration"

June (2026-07-14): the separate **`move ›`** and **`set time`** chips are messy — both are about *time* (when an item is ordered, and for how long). Fold them into **one edit control** that opens both options, and rename the duration action **"set duration"** (not "set time").

**Files:** `docs/overlay_daily.html`.

- [ ] **Step 1:** Replace the two per-item chips with a single **`edit`** control (on any row that has either capability — a real task/block with a later slot to move to and/or an editable duration). Tapping it reveals a small inline panel with: **"move later ›"** (enters the existing tap-to-place placement mode, `startPlacing`) and **"duration: [__] min"** (the existing `openChunkInput` numeric input → `/api/duration`). Reuse both existing mechanisms unchanged — this only unifies the entry point.
- [ ] **Step 2:** Rename every user-facing "set time" / placeholder to **"set duration"** (the chip label when unset reads `set duration`; the input aria-label reads "duration in minutes"). Keep block chunk chips and task duration chips consistent under the one control.
- [ ] **Step 3:** Placement mode still shows its own "cancel" + tap-targets (one-thing-at-a-time); the edit panel collapses when placement starts. Manual browser smoke: open edit on a task → move works; open edit → set a duration → persists; the label reads "set duration".
- [ ] **Step 4:** Commit `feat(overlay): one edit control for reorder + duration; rename to 'set duration'`.

---

### Task 8: Integration, LIVE REGENERATION verify, cross-family review (REQUIRED)

The bug only showed in a real generation — so this task's live verify is non-negotiable.

- [ ] `python3 -m pytest -q` → ≥ 596 + new, no `_guard_real_data` pollution.
- [ ] Restart the server on new code; **regenerate June's real plan** (`POST /api/refresh`), then inspect: block-projects (IOP) show as a block whose arc steps are **real, checkoffable** tasks (have ids) — **zero ghost rows** (every substantive row has an id or is a labeled rest/anchor). A container project (scholarly writing) shows as a bare did-a-chunk block. The walk + daily chores render right.
- [ ] Drive it: check off an arc step → the real Anytype task goes Done (read-back), undo returns it to Ready. Tap the block header did-a-chunk → cache-only, no Anytype done-write. Edit a duration → persists.
- [ ] If any row renders as an uncheckoffable ghost, that's the original bug — STOP and report BLOCKED, don't ship.
- [ ] Cross-family review (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file+tests); triage; apply real findings.
- [ ] Update `docs/display_grain_design.md` build-status: rework shipped + live-verified.

---

## Self-Review

**Spec coverage (`display_grain_design.md` REVISION):** A (block is rendering) → Tasks 2/3/6. B (arc steps carry ids, checkoffable + undo) → Tasks 1/6. C (categorized hierarchy + resolve-all-tasks) → Tasks 4/5. D (container = bare chunk; drill-down deferred to Map) → Task 2/6 (container path kept; no drill-down built). Decisions 2/3 (duration, did-a-chunk) carried onto the block header, unchanged.

**What is deliberately NOT changed:** task selection (gate/collapse) mechanics; the duration edit + did-a-chunk log + routes (built + verified); the walk recurring. This rework touches only the block's *layer* (selection→render), the arc's *ids*, resolution's *breadth*, and context's *organization*.

**Deferred (later session):** the Map-tab redesign — unfolding a container project to its subprojects/workstreams (collapse/expand), blocked on a data-cleanup pass (design decision 9 / D).
