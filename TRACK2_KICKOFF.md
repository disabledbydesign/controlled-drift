# Track 2 kickoff — detailing the GSDO spec to buildable

**Who this is for:** a fresh Claude instance, or June returning without this session in working memory. It explains where things stand and what the next phase has to do, in plain terms — not shorthand.

## Where we are

The work got split into two parallel workstreams:

- **Track 1 — the build *process* (how we build): COMPLETE.** We decided to build lightweight on native Claude Code rather than adopt a whole framework, then installed and locally-adapted a small toolchain and verified it. The rationale and the map live in memory: `build-process-frameworks-research`, `skill-integration-map`, plus two corrections worth knowing — `affect-inference-both-channels` and `automate-automatable-human-gate-situated`.
- **Track 2 — the *product* (what we build): BUILD PLAN READY (session 5, 2026-06-17).** MCP live. Test objects deleted. Data model inventory complete. Weeding ontology fork resolved. Spec hardened (session 5 — see below). **The build plan is written:** `docs/superpowers/plans/2026-06-17-gsdo-data-model-and-scaffolding.md` (10 tasks, cold-buildable). **Next: commit the current edits on a branch (repo is on `main`), then execute the plan via `/subagent-driven-development` in a fresh session.** Do NOT re-run `/writing-plans` — the plan exists.

  **Session-5 spec changes the plan already reflects (re-read `AI_LAYER_SPEC.md §2` before building):** `Recurring` gained `day_of_week`/`time_of_day`/`duration` (fixed appointments, e.g. therapy); `embodiment` became the open `access` field (two tags + `access_notes` annotations → §6 promotion loop); two-senses-of-strategy note + weeding type-routing; §8a closed. Weeding prompt was changed and **still needs sample-output re-validation with June** (non-blocking).

## What Track 1 hands you (the build toolchain, ready to use)

Described by what each does, since the names alone won't tell you:

- **`writing-plans`** — turns a chosen approach into a task list a low-context builder (e.g. a cheaper model like Sonnet) can execute: exact file paths, code, verification commands. That makes a spec *buildable by someone without the design conversation in their head*.
- **`subagent-driven-development`** — the build loop. Runs a plan one task at a time with a fresh implementer subagent per task, a fresh reviewer per task, fix-and-re-review, and a final whole-branch review. It has a **layered stop** (automate the mechanical; surface situated decisions to June), **no-silent-failure** rules, and **self-repair** via a progress ledger that survives crashes/compaction. Read its top "local adaptations" block first.
- **`requesting-code-review`** — a fresh-context code reviewer (judges work against its own stated plan, never your session history).
- **`github_models_review.py`** (in the `requesting-code-review` skill dir) — a *different model family* reviewer (via GitHub Models, token already configured) for code a Claude model generated, to catch the blind spots a Claude reviewer shares with a Claude builder.
- **`critic-swarm`** — for non-code artifacts (specs, prompts, designs). It now has a mandatory step where June confirms the critic design *before* the review runs, so the critique is grounded in the project's values rather than an instance's default framing.
- **The 7 prompting disciplines** every GSDO prompt should be written by (in `build-process-frameworks-research`). The load-bearing one: **ground prompts in the work's goals, never in pre-defined categories** — naming the categories up front forecloses what the model would otherwise discover from the material.

## What Track 2 had to resolve (status as of 2026-06-16)

1. **✅ The delivery vehicle — DECIDED.** Interaction surface: Claude Code + anytype-mcp (MCP was already primary per §1 of the spec — this was confirmed, not re-decided). Persistence/learning loops: Python scripts in `scripts/` (deterministic things stay in Python; LLM handles what needs judgment). anytype-mcp is **installed** (`@anyproto/anytype-mcp` v1.2.8, added to `~/.claude.json`, defaults to `127.0.0.1:31009` — no URL config needed). MCP confirmed live in session 3 — tools are available and responding.

2. **The three v1 prompts — IN PROGRESS (session 4).** For a thin AI layer, the prompts *are* the product. Live in `prompts/`.
   - ✅ **`weeding_gate.md`** — DONE, iterated to a format June validated. Testable standalone.
   - 🔶 **`daily_list.md` (Daily Plan)** — rewritten to the richer v1 spec (§9); NOT yet validated by a sample-output run; depends on Python scaffolding (deterministic scheduler + neglect-resurfacing) that doesn't exist yet.
   - ⬜ **drift detection (§8b scale-2)** — NOT started.
   **Method that worked:** June reacts to a *sample output* (run the draft on her real brain-dump), not the prompt text; iterate output→react until she validates, THEN lock the prompt. Do NOT pre-enumerate the weeding buckets.

3. **✅ The weeding ontology fork — RESOLVED (session 3, 2026-06-16).** Non-task/non-recurring items from a brain-dump land in Anytype's built-in **Note** type (already exists — no new type needed). Needs-Clarifying → Clarified flow: AI asks one targeted question, June answers, item gets rerouted to correct type or status updates to Active. **Parked (see `AI_LAYER_SPEC.md §10`):** how mindsets/strategies/disciplines connect to learning loops or AI calibration cannot be designed without real examples from use.

4. **✅ §0 reframe — DONE (2026-06-16).** Two fixes applied to `AI_LAYER_SPEC.md` §0: (a) "The core problem" paragraph restored with updated closing — partnership framing at the end, strong original opening kept; (b) associational thinking reframed as a design input (the system's relational model is built around how June thinks, not despite it), separated from deficit traits. Sourced from SYNTHESIS_design_time.md Param #2.

5. **✅ Feelings-signal footer fix — DONE (2026-06-16).** §11 footer corrected: removed stale "author-first" framing; now reads "both affect channels (June stating + AI inferring via heuristics) are first-class — all inferences are labeled by source, surfaced for confirmation, and correctable before the system acts on them." Also added to §10 (parked): two-tier learning loop (signal detection + response calibration), with the key example that overwhelm → longer completable list, not shorter (must be learned, not predicted).

## How to pick up (fresh instance)

Read, in order: `AI_LAYER_SPEC.md` §0 (why) → §2 (data model) → §3 (the five guards) → §9 (build sequencing + what v1 is). Item 2 (three v1 prompts) is the one remaining open item — draft and test on real input after the data model is built; June co-authors, do not design in the abstract.

**Session 5 complete (2026-06-17):** spec dual-reviewed (broad gap-check + narrow archaeology dig) and hardened; build plan written. Do NOT build the data model via ad-hoc MCP calls — use the build loop.

**Carry-forward decided session 6 (2026-06-17) — surface-log companion to the daily-plan pipeline.** The data-model build uses a single `last_surfaced` (date) field on Task/Project — correct for THIS build, because the v1 neglect query (Task 9) reads it and nothing in this build ever *surfaces* an item. **When the daily-plan pipeline is built (later increment — the thing that actually surfaces items), add an append-only surface-log alongside the field**, mirroring the Task 10 plan-corrections logger: capture surfacing history from day one so the future rhythm/neglect learning loops have training data a single overwriting field can never reconstruct. The field stays as the fast "is it stale?" read; the log is the durable history. This is NOT a new design decision (it's the Task 10 pattern applied to a second signal) — just sequenced to where the data actually starts flowing. Rationale: June rejected "minimal" as self-justifying; the one who'd bear the cost of logging nothing is future-June, who could never learn her own neglect-rhythms once the history is gone.

**First move:** the build plan already exists at `docs/superpowers/plans/2026-06-17-gsdo-data-model-and-scaffolding.md` (it accounts for the Anytype inventory below — reuses existing properties, ignores test artifacts, covers the v1 Python scaffolding). **(1)** Commit the current spec/plan/prompt edits — repo is on `main`, so branch first. **(2)** Execute the plan via `/subagent-driven-development` (Task 1 first resolves the two unverified API shapes — select-option tags + property→type linking — empirically). **(3)** After the data model is built + verified: re-validate the weeding prompt on sample output with June, then draft the daily-plan pipeline (incl. the day_of_week/time_of_day→datetime anchor seam) and the remaining v1 prompts. The field lists in the inventory below are superseded where they disagree with `AI_LAYER_SPEC.md §2` + the build plan (session 5 added the `access`/`access_notes` fields, the `Recurring` time-anchors, and `description` on Project).

---

## Anytype state inventory (session 3, 2026-06-16)

**Space:** Get Started
**Space ID:** `bafyreibcf3vhpi2neqaf2rdb5yzu2qqlykabxohjc3puyezauvmll7b2n4.2c96yy1wokk27`
**API:** `localhost:31009/v1`, Bearer key in `.env` as `get_shit_done`, header `Anytype-Version: 2025-11-08`
**MCP:** `anytype` server in `~/.claude.json`, tools available as `mcp__anytype__API-*`

**Custom types that exist:**
- `gsdo_goal` (id: `bafyreigctlbnjbidalwz7nw4xwyf6jz4desxiapapah2w26viwpoeleloa`) — type shell exists, no GSDO-specific properties linked to it yet

**Built-in types being used:**
- `task` — already has: `done` (checkbox), `status` (select), `due_date` (date), `linked_projects` (objects). **Note:** `gsdo_duration_min` and `gsdo_needs_clarifying` exist as standalone properties in the space but are NOT formally linked to the Task type definition (they don't appear in list-types for Task). The build plan must link them to Task, not skip them assuming they're already wired.
- `note` — already exists, receives non-task/non-recurring weeding output (no new type needed)

**Types still to create:**
- `gsdo_project`
- `gsdo_recurring`
- `gsdo_strategy` (added session 4 — covers strategies/disciplines/mindsets; see `AI_LAYER_SPEC.md §2`. Fields: `name`, `status` (select: Active/Retired), `what_for` (text), `learning_notes` (text), `context` (text))

**GSDO properties already in the space (reuse by key where spec matches):**
- `gsdo_duration_min` (number) — Task duration estimate ✅
- `gsdo_needs_clarifying` (checkbox) — Task weeding signal ✅
- `gsdo_reaching_for` (objects-relation) — test artifact, NOT in final model, ignore
- `gsdo_location_mode` (select) — test artifact, wrong format (spec wants multi-select `embodiment`), ignore

**Properties still to create** (per `AI_LAYER_SPEC.md §2`):

> 📌 *Historical record — this list is as-of the kickoff and is no longer current. Three properties below were later **retired**: `excitement_level` (2026-07-17), `has_target` and `target` (2026-07-16/17). Do not build them. `AI_LAYER_SPEC.md` §2 is the live schema; `docs/review_reorganize_backend_spec.md` carries the current deltas.*
- **Goal:** `reaching_for` (text), `horizon` (select: Long-term / Medium-term / Short-term), `status` (select: Active / Parked / Achieved), `context` (text)
- **Project:** `goal_link` (objects), `reaching_for` (text), `status` (select: Active / Parked / Inactive), `deadline` (date), `parent_project` (objects), `excitement_level` (number), `affective` (text), `relevant_docs` (text — added session 4), `context` (text)
- **Task additions:** `blocked_on` (text), `affective` (text), `embodiment` (multi-select: Lying-down / Seated / Moving / Requires-leaving-house), `ai_autonomous` (checkbox), `relevant_docs` (text — filepaths/dirs the AI reads for this task; added session 4), `context` (text)
- **Recurring:** `frequency` (select: Daily / Weekly / As-needed), `has_target` (checkbox), `target` (text), `project` (objects), `context` (text)
