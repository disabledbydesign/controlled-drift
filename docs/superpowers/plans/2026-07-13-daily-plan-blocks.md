# Daily-plan blocks (display-grain) — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (`subagent-driven-development`). Steps use checkbox (`- [ ]`) syntax. Each subagent reads the live file at its exact current line before editing — line numbers here are from 2026-07-13/14 and may shift.

> **⟳ Revised 2026-07-14 after a 4-critic swarm (build-agent, architect, author-informed, ND-UX).** The swarm caught a load-bearing frame error in the first draft: it modeled a block as an **identity-less unit** threaded through a pipeline that keys everything on Anytype task-ids, which (a) crashed `_build_task_refs`/`_resolve_ids`/`_retime`, (b) silently reset every block to 30 min, (c) had no path to emit bare-chunk container projects, and (d) in one variant bypassed the LLM — re-breaking the focus/strategy composition restored in commit `bbbb070`. **The fix (June, 2026-07-14): a block is a task-shaped item with a SYNTHETIC id (`block:<project_id>`) that rides the existing LLM-composition + ref-token/id machinery exactly like a task** — so the model orders every block by focus period and strategy, nothing is placed by Python behind the model's back, and the id-keyed stages just work. Swarm log: `docs/superpowers/plans/LEARNING_LOG.md`.

**Goal:** Surface work at the right grain — daily-life chores as specific tasks; ongoing project work as a "work on X" *block* (a chunk of time that opens to its task arc when the project has direct tasks, or stays a bare chunk when it's a bundle of subprojects) — with a duration June sets that persists as a **Project field in Anytype**, and a "did a chunk today" check that logs locally and resets, never finishing the project.

**Architecture:** A deterministic grain classifier (`scripts/grain.py`) reads each project's `side` + `engagement` + `is_workstream` and decides task / block / excluded. In `build_context`, block units are emitted as **synthetic-id, task-shaped items** into the same list the LLM orders — one per surviving thread (arc block) plus one per task-less Steady/Open container (bare chunk) via a projects-pass. Because a block carries a real (synthetic) id, it flows through `_build_task_refs` → LLM → `_resolve_ids` → `_ensure_all_tasks_accounted` → `_retime_clock_plan` → `blocks_from_scheduled` untouched, with its block-only data (arc, chunk length, shape) attached by id in `_resolve_ids` exactly as `held_back`/`description` already are. The **arc content** is pulled from the already-fetched Anytype objects (done steps included), reusing `orient_map`'s arc *logic*; it is **rendered in the overlay's HTML** (the rose ✓/●/☐), not terminal text. Chunk length is a **Project field in Anytype** (durable preference, like Side/Engagement); "did a chunk today" is a local resetting log.

**Tech Stack:** Python 3 (`python3`, no `python` on PATH), pytest, vanilla JS/HTML overlay, Anytype local API (the chunk-length Project field is the only new Anytype write; the block *check* never writes Anytype).

## Global Constraints

- **`python3`** for all commands. Suite: `python3 -m pytest -q` from repo root. **Green baseline: 549 passed (~21s).**
- **Tests self-clean.** `tests/conftest.py` sandboxes `CD_DATA_DIR`/`CD_CONFIG_DIR` and FAILS the suite if any real `scripts/data/*` file changes; `CD_DISABLE_PLAN_MIRROR=1` blocks Anytype writes. New-store tests use `cd_sandbox`. Never write Anytype in a test — mock the write layer (`gsdo_objects`) as `tests/test_plan_mirror.py` does.
- **No silent failures — raise, don't `assert`.** No scalar-flattening of affect fields.
- **June-facing copy: plain words, no metaphors.** Block label is literally `Work on <project>`.
- **Integration over reinvention (June, 2026-07-14).** Every piece reuses an existing mechanism: synthetic-id blocks reuse the ref-token/id-map machinery (`held_back`/`description` are the template); the chunk-length field reuses the Side/Engagement Project-field pattern; the arc reuses `orient_map`'s arc logic; clock-time + less-structured-day reuse the existing scheduler + focus-period day-shape. **Do not build a parallel mechanism where one exists.**
- **The block check is cache-only, NEVER an Anytype done-write.** Reuses the `recurring`-anchor cache-flip (`server.py:425`, `plan_store.is_recurring_item`). The chunk-length *field* is the only new Anytype write, and it is a Project preference, not a completion.
- **Design authority:** `docs/display_grain_design.md`. This plan is **the daily-plan grain only**; the Map-tab navigator (deep subproject drill-down) is a SEPARATE v1.5 build June is planning in parallel. Build no navigator here; the block leaves a *data* seam (it knows its `project_id`) but **no visible "open in map" door in v1** (it would dead-end in the current monospace map — ND-UX flag).
- **Cold-start chunk default = 90 min** (`BLOCK_DEFAULT_MIN`), used only when the Project field is unset. June sets the real value; it persists in Anytype. The recency-weighted *proposal* from history is Plan 2 (this plan only captures the timestamped events).

---

### Task 1: Load `is_workstream` in the daily-plan path

Unchanged from the reviewed-solid first draft. `is_workstream` is read only in `orient_map.py`; add the read + nearest-ancestor inheritance to `load_active_items`, mirroring the `side` inheritance walk (`daily_plan.py:101-111`).

**Files:** Modify `scripts/daily_plan.py` (`load_active_items` project-append + a new `_inherit_is_workstream`). Test: `tests/test_grain.py`.

- [ ] **Step 1: Failing test**

```python
# tests/test_grain.py
import daily_plan
def test_is_workstream_inherits_from_ancestor():
    parent = {"id": "p", "name": "GRA", "is_workstream": True, "parent_project_id": None}
    child = {"id": "c", "name": "Metabolize", "is_workstream": False, "parent_project_id": "p"}
    daily_plan._inherit_is_workstream([parent, child])
    assert child["is_workstream"] is True
```

- [ ] **Step 2:** `python3 -m pytest tests/test_grain.py -q` → FAIL (no `_inherit_is_workstream`).
- [ ] **Step 3:** In the project-append (`~:91-99`) add `"is_workstream": bool((props.get("is_workstream") or {}).get("checkbox"))`. Add `_inherit_is_workstream(projects)` (walk `parent_project_id`, set True from nearest ancestor with it set) and call it right after the side-inheritance loop.
- [ ] **Step 4:** `python3 -m pytest tests/test_grain.py -q` → PASS.
- [ ] **Step 5:** `git add scripts/daily_plan.py tests/test_grain.py && git commit -m "feat(grain): load is_workstream + inherit in the daily-plan path"`

---

### Task 2: The grain classifier (`scripts/grain.py`) — trimmed

The one deterministic place that decides task / block / excluded. **Swarm cut:** the first draft carried `has_children`/`parents_with_children`, an `always_eligible` field, and a phantom `"engagement"` grain — all built and read by nothing. They're gone. The container-vs-arc question dissolves: the arc is pulled from Anytype including all a project's direct tasks (Task 6), so "has direct tasks → arc; no direct tasks → bare chunk" needs no separate container flag.

**Files:** Create `scripts/grain.py`. Test: `tests/test_grain.py` (append).

**Interfaces:**
- `classify(project) -> str` in `{"excluded","task","block"}`: `Fun / hobby` → `excluded`; `is_workstream` → `excluded`; `Daily life` → `task`; else → `block`. (The engagement *gate* still runs separately in `_gate_and_collapse`; `classify` decides grain, not visibility — except that `Daily life` also implies always-eligible, enforced in Task 3.)
- `project_arc(project_name, all_objects, proj_id_to_name) -> list[dict] | None`: the project's **direct** tasks ordered by `Step order` (done included), each `{"text","state"}` with `state` in `done`/`here`/`ahead` (first not-done = `here`). `None` when the project has no direct tasks (→ bare chunk). Reuses `orient_map`'s arc logic (`_arc_lines`, `orient_map.py:251-272`) as the reference; returns DATA for the overlay to render as HTML.

- [ ] **Step 1: Failing tests**

```python
# tests/test_grain.py (append)
import grain
def _p(name, side=None, ws=False):
    return {"name": name, "side": side, "is_workstream": ws}
def test_hobby_and_workstream_excluded():
    assert grain.classify(_p("Painting", side="Fun / hobby")) == "excluded"
    assert grain.classify(_p("Daily plan pipeline", ws=True)) == "excluded"
def test_daily_life_is_task():
    assert grain.classify(_p("Household", side="Daily life")) == "task"
def test_default_is_block():
    assert grain.classify(_p("Leatherworking", side="Wellbeing")) == "block"
```

- [ ] **Step 2:** run → FAIL (no `grain`).
- [ ] **Step 3:** Implement `classify` (four-line side/workstream branch) and `project_arc`. For `project_arc`, read the reference logic in `orient_map.py` (`_arc_lines` + how it collects a project's tasks and sorts by `Step order`) and return the `{text,state}` list from `all_objects` (the raw fetched objects, which include done tasks — do NOT source from the daily-plan `tasks` list, which drops done). Order authoritative field: `Step order` (same as `orient_map`); when absent, stable fetch order.
- [ ] **Step 4:** run → PASS. Add a `project_arc` test with fixture objects (one done, one not-done, one future) asserting `["done","here","ahead"]`.
- [ ] **Step 5:** `git add scripts/grain.py tests/test_grain.py && git commit -m "feat(grain): classifier + arc-from-Anytype-objects (data for the overlay)"`

---

### Task 3: Daily-life is always-eligible AND not collapsed

`_gate_and_collapse` hides unset-engagement projects and collapses each thread to one move. `Side = Daily life` projects must be exempt from **both**: always eligible (their engagement is unset on purpose) and *not* collapsed (a chore is a specific discrete task — decision 1 — so several chores under a Household project each surface, like no-project discrete tasks already do). Route the decision through `grain.classify` so there is genuinely "one deterministic place."

**Files:** Modify `scripts/plan_generate.py` (`_gate_and_collapse`, hide gate `:534-541` and collapse `:552-570`). Test: `tests/test_block_selection.py` (new).

- [ ] **Step 1: Failing test** — a Daily-life project with unset engagement and two chores surfaces both (not one).

```python
# tests/test_block_selection.py
import plan_generate as pg
def _proj(name, eng=None, side=None):
    return {"name": name, "engagement": eng, "side": side, "parent_project_id": None, "is_workstream": False}
def _task(tid, name, proj):
    return {"id": tid, "name": name, "linked_projects": [proj]}
def test_daily_life_chores_all_survive_uncollapsed():
    projects = [_proj("Household", eng=None, side="Daily life")]
    tasks = [_task("t1","Clean kitchen","Household"), _task("t2","Do dishes","Household")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} >= {"t1","t2"}
```

- [ ] **Step 2:** run → FAIL (hidden and/or collapsed to one).
- [ ] **Step 3:** Build `proj_side = {p["name"]: p.get("side") for p in projects}`. In the hide gate, `if proj_side.get(proj) == "Daily life": survivors.append(t); continue` (before the engagement checks). In the collapse pass, treat Daily-life tasks like no-project discrete tasks — append each, never route through `winner_id`. (Use `grain.classify(project_dict) == "task"` as the predicate so the rule lives in one place.)
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add scripts/plan_generate.py tests/test_block_selection.py && git commit -m "feat(grain): Daily life is always-eligible and never collapsed"`

---

### Task 4: Chunk length as an Anytype Project field (+ local event log)

**Swarm correction (architect):** the chunk length is a durable per-project preference like `Side`/`Engagement` — it belongs **on the Project in Anytype** (backed up, visible to the map and the agent surface), not a local JSON that forks the source of truth. Only the **timestamped event log** (raw material for Plan 2's recency-weighted proposal) stays local.

**Files:**
- Modify: `scripts/build_model.py` (add the Project field, idempotent) — follow how `Side`/`Engagement` selects are defined; this is a **number** field `gsdo_block_chunk_min` (display "Block chunk min").
- Modify: `scripts/daily_plan.py` (`load_active_items` project dict: read `pv("gsdo_block_chunk_min","number")` → `"chunk_min"`).
- Create: `scripts/block_duration.py` — `get_chunk_min(project, default=BLOCK_DEFAULT_MIN)` (reads the project dict's `chunk_min`, falls back to default); `set_chunk_min(project_id, minutes)` (writes the Anytype field via `gsdo_objects.update` AND appends a local timestamped event); `log_scheduled(project_id, minutes)`; `read_events(path=None)`.
- Test: `tests/test_block_duration.py` (new; `cd_sandbox` for the log; mock `gsdo_objects` for the Anytype write, per `test_plan_mirror.py`).

**Interfaces:** `BLOCK_DEFAULT_MIN = 90`. Event record `{"ts": <full isoformat>, "date": <today>, "event": "set"|"scheduled", "project_id": str, "minutes": int}` — full `ts` so weekday/time-of-day are derivable (decision 2).

- [ ] **Step 1: Failing tests** — `get_chunk_min` returns the field value when set, default when not; `set_chunk_min` mocks the Anytype update and appends an event; `log_scheduled` appends.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Add the idempotent field in `build_model.py` (read it back to verify, per the repo's build-model discipline). Read it in `load_active_items`. Implement `block_duration.py` — the Anytype write reuses `gsdo_objects.update`; the local event log copies the `completion_log.py` append idiom (`cd_paths.data_file("block_duration_log.jsonl")`, `os.makedirs`+append, `path=` injectable).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add scripts/build_model.py scripts/daily_plan.py scripts/block_duration.py tests/test_block_duration.py && git commit -m "feat(block): chunk length as an Anytype Project field + local event log"`

---

### Task 5: The "did a chunk today" log (`scripts/chunk_log.py`)

Unchanged from the reviewed-solid first draft — a daily, resetting, cache-only completion, netting last-event-per-project-per-day like `completion_log.completed_ids_on`.

**Files:** Create `scripts/chunk_log.py`. Test: `tests/test_chunk_log.py` (new).

- [ ] **Step 1:** Failing test — `log_chunk("a"); log_chunk("b"); unlog_chunk("a")` → `chunked_today_ids() == {"b"}`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement `log_chunk`/`unlog_chunk`/`chunked_today_ids(date=None)` copying the `completion_log` append + per-day net idiom, keyed on `project_id`, `cd_paths.data_file("chunk_log.jsonl")`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add scripts/chunk_log.py tests/test_chunk_log.py && git commit -m "feat(block): did-a-chunk-today log (daily, resetting, cache-only)"`

---

### Task 6: Emit synthetic-id block units into the LLM's list

The heart of the revision. In `build_context`, after `_gate_and_collapse`, transform the kept set so each block thread becomes ONE synthetic-id, task-shaped item — plus a projects-pass for task-less containers — all entering the `tasks` list the LLM orders.

**Files:** Modify `scripts/plan_generate.py` (`build_context`, after gate/collapse, before the return of `tasks`). Modify `scripts/grain.py` (add `block_unit`). Test: `tests/test_block_selection.py` (append).

**Interfaces — the block unit (a task-shaped dict):**
```python
{"id": f"block:{project['id']}", "name": f"Work on {project['name']}",
 "block": True, "project_id": project["id"], "project": project["name"],
 "shape": "arc"|"chunk", "arc": [{"text","state"}, ...] | None,
 "chunk_min": int,                 # from block_duration.get_chunk_min(project)
 "duration_min": int,              # == chunk_min (for the scheduler)
 "linked_projects": [project["name"]]}
```
The synthetic `id` is what makes every id-keyed stage work. `chunk_min`/`arc`/`shape`/`block` are Python-owned and re-attached by id in Task 7's `_resolve_ids` change — the LLM only ever echoes the ref token, exactly like `held_back`.

**Two emission paths (both feed the LLM's list — nothing is placed behind the model):**
1. **Arc/thread blocks** — for each project that `classify → "block"` and has ≥1 surviving task after the gate: replace that thread's kept task(s) with one `block_unit`, `shape="arc"` if `grain.project_arc(...)` is non-empty (it will be, since the thread had tasks), `arc` = that list.
2. **Container blocks** — iterate `projects`: for each `classify → "block"`, non-workstream project with **zero** surviving tasks AND that survives the engagement gate (Steady, or foregrounded in the focus period), emit a `block_unit` with `shape="chunk"`, `arc=None`. This is the GRA/scholarly-writing headline case; it enters the same `tasks` list, so the LLM orders it by focus/strategy.

- [ ] **Step 1: Failing tests**

```python
# tests/test_block_selection.py (append)
import grain
def test_block_unit_has_synthetic_id_and_arc():
    proj = {"id": "lw", "name": "Leatherworking"}
    arc = [{"text":"Cut","state":"done"},{"text":"Stitch","state":"here"}]
    u = grain.block_unit(proj, shape="arc", arc=arc, chunk_min=120)
    assert u["id"] == "block:lw" and u["block"] and u["duration_min"] == 120
    assert u["arc"][1]["state"] == "here"
def test_container_block_is_bare_chunk():
    u = grain.block_unit({"id":"sw","name":"Scholarly writing"}, shape="chunk", arc=None, chunk_min=240)
    assert u["arc"] is None and u["name"] == "Work on Scholarly writing"
```

- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement `grain.block_unit(project, shape, arc, chunk_min)`. In `build_context`: after the gate, build `by_name = {p["name"]: p for p in projects}`; for each block-classified thread with survivors, swap to a `block_unit` (arc via `project_arc(name, data_objects, proj_id_to_name)`); then the container-pass for task-less block projects that pass the gate. Use `block_duration.get_chunk_min(project)` for the length. Foreground/gate reuse the existing focus-period logic already in `_gate_and_collapse`/`build_context` — don't re-derive it.
- [ ] **Step 4:** run → PASS (`tests/test_block_selection.py tests/test_grain.py`).
- [ ] **Step 5:** `git add scripts/grain.py scripts/plan_generate.py tests/test_block_selection.py && git commit -m "feat(block): emit synthetic-id block units into the model's ordering list"`

---

### Task 7: Thread block data through resolve → retime → rows

Because a block has a synthetic id, the id-keyed stages already accept it. This task attaches the block's Python-owned data by id and emits the overlay row — mirroring `held_back`.

**Files:** Modify `scripts/plan_generate.py` (`_resolve_ids` `:895-931` — attach `block`/`project_id`/`chunk_min`/`arc`/`shape` by id, like `held_back_names`; `_retime_clock_plan` `:1006/1025` — a block's `dur_by_id[block_id]` = `chunk_min`, so its duration survives retime; `_build_task_refs` `:717` needs no change — `t["id"]` is the synthetic id). Modify `scripts/daily_plan.py` (`blocks_from_scheduled` `:720-745` — copy block fields onto the row + set `did_chunk_today` from `chunk_log.chunked_today_ids()`). Test: `tests/test_block_selection.py` (append — a resolved+retimed plan item for a synthetic-id block keeps `chunk_min` and `arc`).

- [ ] **Step 1:** Failing test — drive the id-map re-attach (`_resolve_ids` with a block in `tasks` + a plan item whose `ref` resolves to `block:lw`) and assert the item keeps `chunk_min`/`arc`; and that `_retime_clock_plan`'s `dur_by_id` yields `chunk_min` for the block id (not 30).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** In `_resolve_ids`, extend the id→data attach (where `held_back`/`description` are attached) to also carry `block`/`project_id`/`chunk_min`/`arc`/`shape`. In `_retime_clock_plan`, ensure `dur_by_id` includes synthetic-id blocks (it will, since they're in `tasks`); confirm the fallback path can't drop `chunk_min`. In `blocks_from_scheduled`, when `it.get("block")`, `row.update({...block fields..., "did_chunk_today": it["project_id"] in chunk_log.chunked_today_ids()})`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add scripts/plan_generate.py scripts/daily_plan.py tests/test_block_selection.py && git commit -m "feat(block): attach block data by synthetic id through resolve/retime/rows"`

---

### Task 8: Prompt contract — a block is a chunk, not a task list

Present a block as its own one-line "Work on X" chunk the LLM orders and narrates; never enumerate its internal tasks.

**Files:** Modify `prompts/daily_list.md` (a short "Blocks" paragraph). Modify `scripts/plan_generate.py` (`_build_task_refs` — a block's ref line reads `Work on X — a chunk of time (do not list its internal steps)`; no `· N more`). Test: `tests/test_block_selection.py` (append — extract `_task_ref_line(item)` and assert the block line says "chunk", no "more").

- [ ] Steps 1–5 as in the first draft (failing test on `_task_ref_line`; implement the branch + the prompt paragraph; run; commit `feat(block): prompt renders a block as a chunk, not a task list`).

---

### Task 9: Completion + duration routes (cache-only check; Anytype for the length)

The block check is cache-flip + `chunk_log`, never an Anytype done-write — the `recurring` branch shape. The duration route writes the Anytype Project field (Task 4) + logs the event.

**Files:** Modify `scripts/plan_store.py` (`is_block_item(project_id)`; `mark_block_chunked`/undo — cache-flip the row's `did_chunk_today`, no Anytype; `set_block_chunk(project_id, minutes)` — update the cached row's `chunk_min`). Modify `scripts/server.py` (inside `/api/complete` `:415` add `elif plan_store.is_block_item(task_id): chunk_log.log_chunk(task_id); ...`; mirror in `/api/uncomplete`; **new standalone route** `if self.path == "/api/block/duration":` — note **`if`, not `elif`**: top-level routes are standalone `if … return` blocks). Test: `tests/test_block_completion.py` (new).

**Swarm route fixes (build-agent):** the new route is a standalone `if` (an `elif` at that level is a `SyntaxError`); read the body with the real helper name and use `.get()` + a 400 on missing/blank `project_id`/`minutes` (every sibling route does — bare `body["x"]` → uncaught 500). `is_recurring_item(task_id)` runs first in `/api/complete`; harmless (a `project_id` won't match a recurring row), but the overlay must send the block's `project_id` in the `id` field.

- [ ] **Step 1:** Failing tests — `chunk_log.log_chunk` + `block_duration.set_chunk_min` (mock Anytype) behave; `is_block_item` matches a cached block row by `project_id`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement `plan_store` helpers + the three route changes with the fixes above.
- [ ] **Step 4:** run → PASS (route wiring proven live in Task 11).
- [ ] **Step 5:** `git add scripts/plan_store.py scripts/server.py tests/test_block_completion.py && git commit -m "feat(block): cache-only did-a-chunk + Anytype-field duration routes"`

---

### Task 10: Overlay — render blocks in the HTML we designed

Render a block per the mockup, in the overlay's own visual language (NOT ported terminal text): gold `Work on X` header, a "did a chunk today" check, an edit affordance for the chunk length (not a fixed cycle), and — for `shape="arc"` — the rose ✓/●/☐ arc reusing the `.open` toggle. **Swarm-driven fixes below.**

**Files:** Modify `docs/overlay_daily.html`. Local mockup source (now in repo): `docs/mockups/display-grain-arc-mockup.html`.

**Fixes the swarm requires:**
- **Branch `groupByProject`/`renderGroup` FIRST**, not just `renderFlatItem` — a block row must render atomic (it is the thread), never get grouped with a sibling task.
- **Handle the priority-shape day** — `renderPriorityItem` must branch on `item.block` too; and `build_context`'s priority branch must not degrade a block to a plain `"Work on X (~90min)"` text line. (Blocks must render on the less-structured focus-period day, per June: clock-time normally, focus period reshapes the day using existing infrastructure.)
- **Checked block does NOT dim** — replace the `.chunked` name-dim (which reads as "retired/done") with an additive `✓ today` trace at full presence. A chunk-check is not completion (decision 3).
- **No visible "open in map ›" in v1** — the current Map tab is the monospace blob this redesign retires; a door into it is a trap. Keep the `project_id` data seam for the v1.5 navigator; render no button now.
- **Arc from block data, rendered as HTML** — the `✓/●/☐` comes from `item.arc` (Task 6/7 data), rendered with the mockup's rose-glow CSS; hold `here` lightly (it reflects possibly-messy done-data; do not over-assert).
- **Retire `Next step:`** in `renderGroup` (`:1939`) per decision 7.

- [ ] **Step 1:** Copy the block CSS from `docs/mockups/display-grain-arc-mockup.html` into the overlay `<style>` (reuse `:root` tokens; don't retune). Chunk-length edit affordance = tap opens a small numeric input (free value), POST `/api/block/duration`.
- [ ] **Step 2:** Branch `groupByProject`/`renderGroup` and `renderFlatItem` on `item.block`; render arc for `shape="arc"`, bare chunk otherwise. Block check → POST `/api/complete {task_id: project_id}`.
- [ ] **Step 3:** Branch `renderPriorityItem` on `item.block`; retire `Next step:`; remove `.chunked` dim → additive trace.
- [ ] **Step 4:** Manual browser smoke against a canned plan JSON with one arc-block, one chunk-block, one chore — confirm the four render states, no dim on check, no map door, the chunk-edit + block-check POSTs fire. Commit `feat(block): overlay renders blocks + rose arc in the designed HTML`.

---

### Task 11: Integration & live verify (REQUIRED)

**Wiring:** `build_context` emits synthetic-id blocks into the LLM list (Task 6) → `generate_plan` runs the LLM round-trip (the model orders blocks by focus/strategy) → `_resolve_ids`/`_retime` attach + preserve block data by id (Task 7) → `blocks_from_scheduled` tags rows → `plan_store`/`load_plan` → `GET /api/plan` → overlay renders (Task 10). `POST /api/complete|block/duration` mutate cache + the Anytype chunk field + local logs.

**Verify (use the `verify` skill — drive the real app):**
- [ ] `python3 -m pytest -q` → ≥ 549 + new tests pass, no `_guard_real_data` pollution.
- [ ] Restart `scripts/server.py`; `POST /api/refresh` (tomorrow's plan, so the live 9am push is untouched).
- [ ] **Confirm the model actually ordered the blocks by focus/strategy** (not Python placement) — inspect the generated plan: blocks appear in a sensible focus-driven order, interleaved with tasks.
- [ ] In the overlay: a project with direct tasks → `Work on X` opening to a rose `✓/●/☐` arc; a task-less container (GRA/scholarly) → a bare chunk (no map door); a `Daily life` chore → its specific task; a `Fun / hobby` project → absent.
- [ ] Tap the block check → "✓ today", full presence (no dim), persists on reload, **no Anytype done-write**. Edit the chunk length → the **Anytype Project field** updates and the event log appends.
- [ ] If any state renders wrong, revert the renderer and report BLOCKED rather than ship a broken plan.
- [ ] Commit wiring fixes, then run the **cross-family review** (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file+tests); triage; apply the real findings.

---

## Self-Review

**Spec coverage (`display_grain_design.md`):** decision 1 (two axes; Daily-life always-eligible task grain; else block; workstreams filtered) → Tasks 1/2/3/6. Decision 2 (chunk length June-sets + persists → **Anytype field**; timestamped log local; learning deferred to Plan 2) → Tasks 4/9. Decision 3 (did-a-chunk, cache-only, resetting) → Tasks 5/9. Decision 5 (no counts; ✓/here/☐ arc, pulled from Anytype, rendered in overlay HTML) → Tasks 2(`project_arc`)/6/7/10. Decision 6 (collapsible, real HTML, rose current step) → Task 10. Decision 7 (retire `Next step:`; one arc rendering) → Tasks 2/10. Decision 8 (arc vs bare chunk by having direct tasks; deep nav is the v1.5 Map tab, not here — no visible door) → Tasks 2/6/10.

**Swarm findings resolved:** id-crash + 30-min duration collapse + container-unreachable → synthetic id + projects-pass (Tasks 6/7); LLM-composition preserved (no Python splice) → blocks in the ordered list (Task 6); duration source-of-truth → Anytype field (Task 4); arc source (done tasks dropped at load) → pulled from raw fetched objects (Task 2 `project_arc`); dead scaffolding (`has_children`/`always_eligible`/phantom grain) → cut (Task 2); route `elif`/error-handling/helper-name → fixed (Task 9); mockup unreachable → in-repo at `docs/mockups/` (Task 10); grouping + priority-shape unhandled → Task 10; dim-on-check + map-door + fidget-chip → Task 10 fixes; continuity-trace → dropped (it's the deferred wins mirror).

**Placeholder scan:** insertion points that a subagent resolves against the live file (Task 6 `build_context` threading; Task 7 `_resolve_ids`/`_retime`) are specified by behavior + the exact function/line, not left blank. **Type consistency:** the block-unit field set (`id, block, project_id, project, shape, arc, chunk_min, duration_min`) is identical across Tasks 6→7→9→10; `did_chunk_today` introduced Task 7, consumed 9/10; `classify` returns only `excluded|task|block`.

**Deferred to Plan 2:** the recency-weighted-average reader over `block_duration_log.jsonl` (proposes a length from history, replacing the cold-start default) + the weekday/time-of-day pattern-read. Plan 1 captures the timestamped events, so Plan 2 is additive.
