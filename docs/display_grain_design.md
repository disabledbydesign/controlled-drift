# The display grain — authoritative design spec

*Single source of truth for **what unit the daily plan surfaces per project**, and for the **"work on X" block** that unit becomes for ongoing work. Read this before changing `_gate_and_collapse` in `scripts/plan_generate.py`, `partition_by_side` in `scripts/daily_plan.py`, or how the daily overlay renders a project. Update this file when June settles a new decision — do not carry these decisions only in session memory. Companion to `map_design.md` (which owns the map/arc rendering); this owns the daily-plan grain + the block. Originating note: June's own, `docs/controlled_drift_changes.json` item `id: 5h5p3u`. Session where this was worked: 2026-07-13/14.*

> **⟳ Build status (2026-07-14, rework SHIPPED + live-verified):** the block is now a **rendering layer over real, still-selected tasks** (the `## REVISION` frame below), replacing the first build's synthetic-block-in-selection that caused uncheckoffable ghost rows. Rework landed in 8 commits, cross-family-reviewed (`docs/superpowers/plans/2026-07-14-block-render-layer.md`). **Live-verified by regenerating June's real plan:** zero ghost rows; a block-work project (IOP) renders as ONE "Work on X" block whose arc steps are the real tasks — checking a step marks the real Anytype task Done (round-tripped Done→undo→Ready); no duplicate loose rows; a task-less container stays a bare did-a-chunk block. Decisions 1–4 hold; 5–8 refined by the REVISION. Deferred: the Map-tab drill-down for containers (needs a data-cleanup pass).

---

## The diagnosis (why this exists)

A structure that worked well for June: **projects, with the next concrete task highlighted, and the whole arc scannable — where you are and where you're going.** That is a *display* principle. Somewhere it became a *backend selection* principle: `_gate_and_collapse` doesn't *highlight* the next task, it **selects only that one task and discards the rest**, leaving a bare "· N more" count where the scannable arc used to be. Same words ("show the next task"), opposite effect — highlighting-within-context became selecting-and-hiding-context. The grain problem sits on top of this: the plan also emits a single grain (one task) for every project, when June's data needs two different grains.

The arc data is not lost — the collapse already stashes the hidden tasks as `held_back` / `held_back_names`. It's discarded from the *view*, not the pipeline. So restoring the arc is re-surfacing what's already computed.

---

## REVISION 2026-07-14 (post-build, June-approved) — the block is RENDERING, not SELECTION

**What the first build got wrong, and how it was found.** The shipped build inserted `_blockify` *inside task selection* (`build_context`, after the gate): it **replaced** a project's real next-task with a synthetic block unit (`block:<project_id>`) in the list the LLM orders and `_resolve_ids` resolves. Regenerating June's real plan exposed the failure concretely:

- The plan's context (`format_context`) already lists the **full hierarchy** — every project → its tasks. The LLM composes from that. But blockify had removed those tasks from the *resolvable* order-list (only the block had a ref token). So when the model named a real task (e.g. "Verify the disability payment process"), `_resolve_ids` couldn't find its id → the row rendered as an **uncheckoffable ghost**. The task *exists in Anytype*; the block-in-selection severed it from resolution.
- The block's **arc carried no task ids** (`{text, state}` only), so even a rendered block's arc steps weren't checkoffable.
- Two representations of the same project (a synthetic block in the order-list; the real tasks in the context hierarchy) **disagreed** — a parallel structure bolted on, not fitted into the system that already worked.

**The corrected frame (June, 2026-07-14):**

### A. The block is a rendering layer, not a selection layer.
**Task selection stays exactly as it worked before the block build** — the gate + collapse produce **real tasks with real ids, resolvable and checkoffable.** `_blockify` must NOT emit synthetic units into the selection/resolution pipeline. Instead, a non-Daily-life project's selected task(s) are **displayed** grouped under a "Work on X" block header at render time. The tasks stay real underneath.

### B. Arc steps carry real task ids → individually checkoffable (with undo).
`grain.project_arc` returns `{text, state, id}` — each step **is** a real task. The overlay renders a checkbox per arc step wired to the existing `toggleItem` complete/uncomplete path (check-off **and undo**), exactly like any task row. (The missing `id` field was the whole reason arc steps weren't checkoffable — mechanical, not deep.) The block *header* still carries the project-level "did a chunk today" check (decision 3) + the duration (decision 2); the arc steps carry per-task done/undo.

### C. The LLM gets the full hierarchy, split into two labeled categories.
`format_context` presents the structure the model already has, but **organized so "block-organized work" (non-Daily-life projects → their tasks) is a distinct category from "daily tasks" (chores).** The model sees the whole picture *and* which category each item is. **Mechanical consequence that kills the ghosts:** every task in that hierarchy must be **resolvable** — `_resolve_ids`' name-match runs against *all active tasks*, not just the gated order-list — so anything the model names lands on a real id.

### D. Container / nonlinear projects = a bare did-a-chunk block; drill-down deferred to the Map tab.
A project with **no discrete tasks** (e.g. "scholarly writing" — a stack of papers, nothing to check off) renders as a **bare "did a chunk today" block** (no arc). Unfolding it to its subprojects/workstreams (a collapse/expand view) is the **Map-tab redesign, a later session** — it needs more work *and* a data-cleanup pass. This reaffirms decision 9 and decision 4: for now the container block holds the chunk; June picks the thread.

**Net effect on decisions 5–8:** the marker set (5), collapsible real-HTML arc (6), one-arc-rendering (7), and arc-vs-bare-chunk-by-having-direct-tasks (8) all still hold — they just apply to an arc **whose steps are the real tasks**, rendered as a grouping over selection rather than a synthetic unit inside it.

---

## Settled decisions (2026-07-13, June-approved — do not revert without her)

### 1. Two axes: Side marks the special tracks; engagement governs the rest (grain AND gate)
The daily plan reads two fields, in this order:

- **`Side = Fun / hobby`** → **excluded** from the daily plan (unchanged; `partition_by_side`, built).
- **`Side = Daily life`** → its **own track**: **always eligible (exempt from the engagement gate)** and rendered at **task grain** — the specific chore ("clean the kitchen"), ordinary done/not-done. A chore is discrete; no arc. Marks the Sustainable-daily-life subprojects (medical / household / self-care / social), which carry **unset Engagement on purpose** — `Side`, not engagement, governs them.
- **Everything else (real project work)** → **engagement governs, doing double duty:** it is both the **show/hide gate** (Done → excluded; Backburner/unset → hidden unless foregrounded or neglected; Open → self-paced; Steady/foregrounded → shows) **and** the **grain** (a surfacing `Steady`/`Open` project renders at **block grain** — a "work on X" chunk, one move, arc if it has direct tasks). **Workstreams (`is_workstream`) are filtered out** of the block-grain calculation. Standalone no-project tasks stay task grain (discrete actions, already handled).

**The through-line from the start of the design:** engagement is the logic that governs task-vs-block for real work; `Side` carves out the two tracks that *don't* follow engagement — hobby (out) and daily life (always-on chores, as tasks). The "keep coming back bit by bit, larger than a time estimate can hold" quality *is* what `Steady`/`Open` name.

### 2. The block is a chunk of time with a variable, learned duration
A "work on X" block is placed in the day as a **clock-time slot**, so it **must** carry a duration — the scheduler can't place a slot with no length. This is core to the block existing, not a later refinement.

**Duration model (decided):**
- **June sets the length manually** — she adjusts each block's chunk.
- **Every scheduling event is recorded, and timestamped.** The full timestamp is kept so day-of-week and time-of-day are derivable — June doesn't yet know what patterns matter (a project domain might turn out to want mornings, or longer chunks on certain days), so the raw material is captured *before* we know what we're looking for. Log rich now, mine later.
- **v1 proposal = a recency-weighted average** over a window of the recent times that block was scheduled. Simple, deterministic, no ML.
- **Later**, go back over the timestamped log for deeper patterns (day-of-week × domain, time-of-day × domain). Emergent — not pre-declared.

This follows the system's standing principle: the AI proposes from stored signal, June adjusts, and the settled value persists. "4 hours for writing, 2 for grading" is just the number she keeps landing on, remembered.

**Where it's stored (revised 2026-07-14, post-swarm): an Anytype Project field** (`gsdo_block_chunk_min`), alongside `Side`/`Engagement` — a durable per-project preference, backed up and visible to the map + agent surface. (An earlier draft put the number in a local file; the swarm correctly flagged that as forking the source of truth.) Only the **timestamped event log** stays local (`block_duration_log.jsonl`) — the raw material Plan 2's recency-weighted proposal reads. This is the Anytype-is-master principle: durable preference → Anytype; ephemeral/resetting state (did-a-chunk-today) → local.

### 3. Block completion is "did a chunk today," not done-forever
Checking a block means **"I worked on it today"** — it is *logged* and the block **returns tomorrow**; it does not mark the project finished. This is a **new completion semantic**, stored **separately** from a Task's `done` (which is complete-forever). A block check must never finish the underlying project.

### 4. June picks the thread inside the block (v1)
Within a "work on scholarly writing" chunk, **June does the picking-between manually** — the system holds the chunk and the arc, she chooses what to work on. The LLM-prioritizes-between-subprojects subsystem is **deferred** (June's words: "we haven't built yet"; "'work on scholarly writing' would also work, and I do the prioritization manually"). Not a v1 dependency.

### 5. No counts — the arc is a progression
**No "2 done, 4 to go."** A count assumes June entered all the tasks up front, which she generally can't. The arc shows position with the marker set from `map_design.md`: **`✓` done · `→` where you are (this is also "next") · `☐` a future step.** When no future steps are entered, the arc just shows where you are and stops — honest, not a fake checklist.

### 6. Arc rendering: collapsible, only-active-open, real HTML — not linked-pages
- **Collapsible (accordion), not linked pages.** Reasoning is June's own caveat: because she doesn't enter future steps up front, arcs are almost always **short** (mostly `→` with a couple `✓`). Linked-pages solves a *length* problem the data won't have; collapsing already handles it, without the navigate-away cost.
- **Only the block you're in opens by default** (the map's "arc only for the active stream" rule, applied to the daily plan) — so the surface stays calm, one arc open at a time.
- **Rendered as real wrapping HTML**, not the monospace map blob. The current Map tab dumps 66-column monospace into a 360px phone column and horizontal-scrolls; the block-arc must wrap and fit.

### 7. Unify the arc rendering (the through-line)
Today there are **three** renderings of "a project and its arc," two of which disagree (the map says "no separate next-step field, the `→` is next"; the daily overlay still prints a "Next step:" line). The block-arc should be **one** arc rendering (`✓ → ☐` as real HTML) reused in **both** the daily block-expand and the Map tab. The display-grain build and the arc surface become the same build; the fragmentation collapses into one component.

### 8. Two kinds of block — decided by the data, and the phone does NOT drill into workstreams (v1 scope, 2026-07-13)
From the mockup, June saw that not every block should expand. The v1 rule:

- **A block opens to its task arc when the project has its own direct (ordered) tasks to show** — e.g. **leatherworking**. Linear work; June genuinely needs to see the steps.
- **A block is just a bare chunk of time when the project is a bundle of subprojects/workstreams** — the nonlinear creative/dev/paper work (e.g. **"work on scholarly writing"**, a stack of papers). No drill-down on the phone.

**This is data-driven — no hand-classification, no linear/nonlinear field.** "Has direct tasks → open; is a container of subprojects → stay a chunk" reproduces June's own intuition on the real data. Do not build a linear/nonlinear flag; if a project ever needs forcing against its structure, add the field *then*. Carry **leatherworking as the linear test case**; don't specialize further.

**Load-bearing scope boundary (June, 2026-07-13):** the **overlay is June's daily plan** — deep drill-down (workstreams → their own arcs) belongs to the **agent-facing surface** in the project directories, reached through the `drift` skill, whose job is rendering information *for agents*, not for June. These are the two-surfaces-two-jobs already in `AI_LAYER_SPEC.md` (negotiation/artifact; and here, daily-plan/agent-workspace). Consequence: **v1 builds NO workstream-on-phone rendering.** The workstream data is a mess and uncleaned — that's fine, because it is never rendered for June. It degrades gracefully: a project with no clean task list just stays a bare chunk; nothing breaks.

**Data-cleanup consequence (not a build blocker):** to *verify* the leatherworking arc in the UI, June will clean up that one project's tasks. Everything else works regardless; the daily-plan interface does not break before she expands into cleaner data. So messy data does not block the build — it only bounds what can be visually verified until cleaned.

---

### 9. The Map tab becomes the navigator (v1.5 — scoped 2026-07-13, NOT v1)
The data confirmed a **third case** the two block-kinds don't cover: deeply-nested projects. **GRA (Grounded Recollection)** is a **~20+ subproject tree, multiple levels deep** (Metabolize the archive, Profile formation, Synthesize stranded design, Develop the two GRA papers, Learning loops design, Retrieval geometry design, …); **Build my own business** and **Build Controlled Drift** are the same shape. A bare chunk erases all of it; an inline accordion would be the exact cluttered wall the arc redesign removed. Neither fits.

**Resolution (June, 2026-07-13): the deep-navigation need is scoped to a redesign of the phone Map tab** — it is *not* folded into the daily plan and *not* v1.
- **Today tab stays simple** (the daily plan): chores as tasks; linear projects open inline to their short arc; deep projects show as a chunk with an "open in map ›" tap.
- **Map tab becomes a drill-in navigator** — replacing the current horizontal-scrolling monospace `<pre>` blob (`overlay_daily.html` `#tab-map`). Tap a project → its subprojects; tap one → its children; a leaf subproject shows its task arc; a breadcrumb walks back. **Page-by-page descent, not an accordion** — the shape depth-of-nesting needs on a phone. This also retires the blob (the fragmentation finding) in the same move.

**Why v1.5, not v1:** (a) it renders the subproject/workstream layer directly, and that data is **messy / uncleaned** — the daily-plan grain (v1) tolerates messy data, a navigator does not; it is **blocked on a data-cleanup pass**. (b) It is a genuinely bigger surface (a mini project-browser) and would re-expand scope right after v1 got right-sized. Sequence: **v1 = daily-plan grain (build now); v1.5 = navigable Map tab (after cleanup).**

Tracked in Anytype as the existing **"Map-tab redesign" item (In Design)** under *Build Controlled Drift* — update that item with this scope; do not create a duplicate. Owning design spec for the map: `map_design.md`.

---

## Still open (decide before/at build)

1. ~~Engagement-gate vs. Daily-life-renders-tasks.~~ **RESOLVED (June, 2026-07-13).** `Side = Daily life` is its own track: **always eligible, exempt from the engagement gate**, task grain (decision 1). Not a design question — the only work is the implementation line: `_gate_and_collapse` currently keys purely on engagement, so add the `Side = Daily life` bypass (the same always-eligible path discrete no-project tasks already take). Chosen over setting an explicit engagement on every chore subproject (less upkeep for June).
2. ~~Exact block-vs-task predicate / sprint edge.~~ **RESOLVED (2026-07-14).** A project foregrounded in a Focus Period (a "sprint") renders as a **block** (a sprint activates a Steady project → block). Arc-vs-bare-chunk is decided by **whether the project has direct tasks** — no separate container flag (the arc is pulled from Anytype, so a project with direct tasks shows them; a task-less container is a bare chunk). Arc **order = the `Step order` field** (the same field `orient_map` sorts by).
3. ~~The "Next step:" divergence.~~ **RESOLVED (2026-07-14).** Retired in the daily-plan build plan, Task 10 (folds into decision 7's one-arc-rendering).
4. **Workstream rule half-propagated**: honored in `orient_map.py`, **not** yet in the HTML tree surface (`review_surface.py` / `surface_template.html` → `docs/controlled_drift_tree.html`). Adjacent, tracked in `map_design.md:120`.

---

## Where it lives (build surface — the downstream ripple)

Changing the emitted unit + adding the block touches:
- **`scripts/plan_generate.py`** — `_gate_and_collapse` / `select_and_order_tasks`: emit a block unit vs. a task unit per the grain rule; keep `held_back_names` as the arc source.
- **`scripts/daily_plan.py`** — `partition_by_side` (already excludes Fun/hobby); Side + engagement reads; the scheduler (`build_schedule`) needs a **block duration** to place a clock-time slot.
- **`prompts/daily_list.md`** — the LLM prompt contract: a block is a thread's chunk, not an enumerated task list.
- **`docs/overlay_daily.html`** — render a block (gold header, chunk-length chip, expandable arc), the `✓ → ☐` arc as real HTML, the "did a chunk today" check distinct from a task done. Reuse the `.open` expand pattern already in the file.
- **Completion tracking** — a new "worked on it today" log, separate from Task `done`; feeds decision 3 and the duration-learning log (decision 2).
- **Duration log** — timestamped scheduling-event records + the recency-weighted-average proposal (decision 2).

This is a plan-first, multi-file build — not an inline edit. Cross-family review before the thread closes (repo bar).

---

## Pointers
- **`docs/map_design.md`** — the arc/map rendering spec (the `✓ → ☐` marker set, the calm-by-default rule, workstream filtering). The block-arc reuses its arc.
- **`docs/handoff_display_grain_2026-07-13.md`** — the factual handoff that opened this work.
- **June's originating note** — `docs/controlled_drift_changes.json`, `id: 5h5p3u`, field `noteForClaude`. Read verbatim; it carries the concept.
- **Interactive mockup (2026-07-13)** — the two grains + the block-arc, in the overlay's skin: https://claude.ai/code/artifact/2a922a5a-3e20-4c3d-9127-a40522377551
- **`AI_LAYER_SPEC.md` §2** — the reconciled selection model; the 4-value `Side` and the (this) not-yet-built grain rule.
