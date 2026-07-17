# Handoff — Open redefined + new-object-defaults needs rework (2026-07-14)

## ▶▶ PARALLEL BUILD — START HERE (fresh session, 2026-07-14)

**You are building the new-object / engagement-authoring pieces IN PARALLEL with another session that is building the daily-plan input-structure seam.** Both sessions edit the same working tree — **the file-ownership split below is load-bearing: do not touch the other session's files.** Read this whole section, then `docs/plan_input_seam_design.md` (the settled design you serve — especially "REFINEMENT 2026-07-14") and the top banner of `docs/superpowers/plans/2026-07-14-new-object-defaults.md` (the adapted plan: absorbed / standalone / dead split).

### Why this exists (the frame — read so your build integrates, not just compiles)
The daily plan now feeds the LLM **all _active_ items**, structured; there is **no hiding gate**. So a new Project must be born **active** (`Engagement = Open`) to be in the input — **born-Open = born-in-the-input**, not "born so a gate won't hide it." Your job: make every new Project born well-formed, let June author/correct engagement cheaply, and clean the existing data so "active" is unambiguous. **Engagement is now UNIVERSAL** — it governs surfacing for daily-life projects too, not just block work — and **`Side` is grain-only.** (Design doc "REFINEMENT 2026-07-14.")

### YOU BUILD (own these files)
1. **Born-`Open` chokepoint** — `scripts/gsdo_objects.py::create_object` (~lines 119-155; generic writer, currently NO per-type default). A Project with no `Engagement` → inject `"Open"`; a caller-supplied Engagement wins untouched; non-Project types untouched. Single structural guarantee.
2. **Retire hardcoded `Steady`** — `scripts/capture_generate.py:~300` (`_creation_props` Project branch) and `scripts/gsdt_bind.py:~204` (`init_binding`, `props={"Engagement":"Steady"}`). Use the proposed engagement, default `Open`; bind asks dialogically. **DO NOT touch `daily_plan.py`'s prose Steady defaults (~lines 338/364) — the seam session owns those (they're inside its format_context rewrite).**
3. **Capture-side engagement proposal** — `scripts/capture_generate.py` weeding contract + `prompts/weeding_gate.md`: LLM infers a per-Project engagement from June's words (Open default; Steady only on a clear "starting it" signal). Add a real Project definition to the weeding gate.
4. **Tap-to-change chip + endpoint + log** — `scripts/server.py` new `POST /api/project/engagement` (update + read-back + log); `docs/overlay_daily.html` an engagement chip on Project receipt lines (cycle Open/Steady/Backburner, write-immediately, read-back, error-visible); NEW `scripts/engagement_log.py` (append-only collect-now learning signal — honest docstring: no reader consumes it yet).
5. *(The engagement backfill — `scripts/backfill_engagement.py`, including the Daily-life engagement values and the `Networking and relationships` → Daily life + Open end-state — is **owned by the SEAM session**, not you: it needs a clean "active" set for the seam's live-verify, so the seam owns and sequences it. You do NOT build it. See "YOU DO NOT TOUCH" below.)*

### YOU DO NOT TOUCH (the seam session owns these)
`scripts/plan_generate.py` (all selection / refs / resolution / build_context), `scripts/daily_plan.py` (loader + format_context + its prose defaults), `prompts/daily_list.md`, the `_JSON_INSTRUCTION` in plan_generate, `scripts/scheduler.py`, `scripts/backfill_engagement.py` (engagement + duration backfill — seam-owned). If you think you need one of these — STOP and coordinate.

**Net: your files are `gsdo_objects.py`, `capture_generate.py`, `gsdt_bind.py`, `prompts/weeding_gate.md`, `server.py`, `docs/overlay_daily.html`, `engagement_log.py` — none of which the seam session touches. Clean split, no shared file.**

### Drop (dead): Task 6 (neglect backstop for Open), the "Mesh with the display-grain blocks plan" section — see the new-object plan's top banner for why.

### Build discipline (repo standard — non-negotiable)
- Subagents WRITE but CANNOT run Bash; the main agent runs every test / read-back / verify.
- `python3` (never `python`); `python3 -m pytest -q`. Tests self-clean via `tests/conftest.py` sandbox — NEVER leave artifacts in June's real space (a session tripwire fails the suite on any real-data write).
- `gsdo_objects.create/update` take DISPLAY names (`"Engagement"`), resolve select by option name. Idempotent writes; raise (don't `assert`); **read-back-verify every Anytype write.**
- Every landed piece gets a **non-Claude cross-family review** before its thread closes (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunk per file with its tests; ~8k-token cap).
- **Verify by driving the real runtime** (repo build-frame guard), not just tests: drive a real capture through the Add tab, read the created object back, confirm born-`Open`; tap the chip, confirm the Anytype write + a log record. Delete all `CD-TEST` objects after and re-fetch to confirm they're gone.

### Launch sequence
`python3 scripts/describe_model.py` + `python3 scripts/whats_open.py` (orient) → read `docs/plan_input_seam_design.md` + the adapted new-object plan → build task-by-task via `subagent-driven-development` → coordinate the backfill apply with the seam session + June.

### Coordination
- File ownership above prevents most collisions; commit ONLY your owned files.
- `docs/overlay_daily.html`: you add the chip; the seam session should not need it — if it does, coordinate before editing.
- Ordering: **engagement backfill apply (active clean) → THEN seam go-live.** Neither writes June's real space without her confirmation.

---

**Status:** design decision made by June; the `2026-07-14-new-object-defaults.md` plan is **on hold, needs rework** against current HEAD. Nothing built. Nothing written to June's Anytype space. This doc is the pickup point.

> **▶ UPDATE 2026-07-14 (later, same session) — the mechanics got settled, and bigger.** The "how does
> `Open` surface" question opened into a full **input-structure seam redesign**, now locked in
> `docs/plan_input_seam_design.md` (a build plan is being written from it). Resolution of the OPEN
> mechanical question below: `Open` = **active → in the LLM's input by construction** — no hiding gate;
> the daily plan feeds all *active* items, structured into daily-life-by-task vs block-by-project
> subsections, and the LLM composes to the focus period. So **step 2 below (tune `_surfaces`) is
> superseded** — the gate is *removed*, not tuned; and **step 1 (settle mechanics) is done.** Core
> new-object pieces (born-`Open`, retire hardcoded `Steady`, backfill) are **absorbed into the seam
> build**; the capture-side proposal + tap-to-change chip + `engagement_log` remain **standalone**
> new-object work. See the top banner of `2026-07-14-new-object-defaults.md` for the
> absorbed / standalone / dead split. Step 4 (spec reconcile) folds into the seam build.

## The decision (June, 2026-07-14)

**`Open` should be "available and can surface on its own."** An Open project **does appear in the daily plan** — gently: not a required daily move like `Steady`, but present and offered. It is **not** map-only.

This **supersedes** the prior definition, which both a design doc and the code currently enforce:
- `docs/spec_reconciliation_selection_2026-07-11.md:18` — "Open → available, self-paced: **no pushed daily move**… surfaces in the plan **only when foregrounded**."
- `scripts/plan_generate.py:502-503` — `_surfaces`: `if eng == "Open": return False` (unless foregrounded).

## Why it changed (traced, not blamed)

June's word for Open was **"self-paced."** That got operationalized into **"excluded from the daily plan unless foregrounded"** — the strong reading. June's actual intent: self-paced = *don't force it, don't nag me* — but *do show it.* The gate took "don't nag" all the way to "don't show," which is a step past what she meant. Classic "written-down ≠ ratified": the doc carries her name, but the operationalization overshot the intent.

## What this unlocks

The new-object-defaults problem was never really about the birth default. **Born-`Open` becomes correct** the moment `Open` surfaces on its own — the vanishing bug dissolves at the gate, not at creation. The center of gravity moves from `gsdo_objects.create` to `_surfaces`.

## OPEN mechanical question (settle with June before building)

**How does `Open` surface *differently* from `Steady`?** If it surfaces identically, the two categories collapse and born-Open re-creates the flood we were killing. Candidate framings (undecided — June's call):
- Open surfaces but is not a *pushed/required* daily move — offered, or ordered below Steady, or rendered as a "work on X" block she can pick up (connects to the display-grain block concept: `display_grain_design.md` decision 1 already says a *surfacing* `Steady`/`Open` project renders at block grain).
- The distinction is likely "Steady = one move the system commits to your day; Open = available option that shows without claiming your day."

## Critic-swarm findings on `2026-07-14-new-object-defaults.md` (3 critics, all read code + docs)

**Convergent (all three):**
1. **The plan didn't deliver its headline** — born-Open was hidden by the gate, so "a new project never vanishes" was false. *(Now moot once Open surfaces — but it was the core flaw.)*
2. **Stale anchors / meshed to a moved tree.** Plan was written against `e851810`; HEAD is now `b6bcb89` (~18 commits on). The blocks plan **shipped** (13+ commits), was found wrong on live regeneration, and is **mid-rework** via `docs/superpowers/plans/2026-07-14-block-render-layer.md`; `display_grain_design.md` now has a `## REVISION 2026-07-14` ("block is a *rendering* layer, not selection"). `scripts/plan_generate.py` is currently **uncommitted-modified**. Re-derive every anchor.

**Author-informed (reads June's intent):**
3. **Overclaim.** June asked to *generalize* ("every time we create a new project," "other fields — `Side`, maybe `Project status`"). The plan narrowed to **one field (`Engagement`) on one type (`Project`)** under a general title. Either generalize the seam or rename to what it is.

**Task-level (build agent + architect):**
4. **Task 6 (neglect backstop for Open) is INERT** — `_surfaces` rejects Open *before* consulting `neglected`, so unioning Open into the neglected set does nothing. **Drop it** (moot once the gate changes anyway).
5. **Task 8 backfill would erase an invariant** — Daily-life subprojects (medical/household/self-care/social) are `Side = Daily life`, made always-eligible **with unset engagement on purpose** (`plan_generate.py` grain bypass). The backfill (else→Open) has no Daily-life exception and would overwrite that. Add one.
6. `daily_plan.py` prose default is at `:338/:364`, not `:302/:328`; `_project_line` is a nested closure (Task 7 test as written throws). Task 3's `proposed_type == "Project"` guard misses that `apply_candidate` `.capitalize()`s the value. Task 5 assumes `server._json_body`/`_send` helpers — verify they exist.

**Keep / protect (all three agreed these are sound):**
- **Task 1 chokepoint** — `create_object` gives a Project a born value; single writer, churn-proof, still matches at HEAD. The one genuinely load-bearing move.
- **Retire hardcoded `Steady`** (`capture_generate.py:299-300`, `gsdt_bind.py:204`) — the real, standalone flood fix.
- **Tap-to-change-after** chip (write immediately, adjust on the receipt) — June-decided; no pre-write gate.
- **Backfill = propose / June-confirms / dry-run-gated** against her real data.
- **`engagement_log`** (collect-now-mine-later) — cheap, honest; owed to the deferred learning subsystem, delivers nothing to her daily life yet.

## Next steps (the rework)

1. **Settle the Open-surfacing mechanics** with June (the open question above) — this is the keystone.
2. **Change `_surfaces`** so `Open` surfaces gently. This is the same file (`plan_generate.py`) as the in-flight block-render-layer rework, currently uncommitted — **coordinate, don't collide.**
3. **Re-derive the new-object-defaults plan** against HEAD `b6bcb89`: keep the survivors, drop Task 6, add the Daily-life backfill exception, fix the memory_pass/server nits, and decide rename-vs-generalize (June's overclaim flag).
4. **Reconcile the spec** — update `spec_reconciliation_selection_2026-07-11.md:18` and `AI_LAYER_SPEC.md §2` so the Open definition matches the new decision once the mechanics are set (don't leave the old "foreground-only" line governing).

## The generalization (June, 2026-07-14) — where new-object-defaults actually belongs

June confirmed the swarm's overclaim flag: field-population is a **general** problem ("fields aren't getting populated in many different cases"), not an Engagement-on-Project one. The natural home / downstream is the **create-vs-update capture** design — the *update* side of "keep an object's fields populated" (recognizing new information about a thing that already exists), the twin of new-object-defaults' *create* side. Create-vs-update is **not a written plan yet** — it's a "design session owed" (`handoff_2026-07-13_next_session.md:26`); what's on record is (a) the core gap "nothing recognizes new information about an existing thing" and (b) the **affect-over-time upkeep** requirement (June can add/change affect over time; agents should notice-and-ask when things seem to have shifted — `capture-writes` out-of-scope note). This session's thinking below is the start of fleshing it out.

**The generalization goes TWO ways (June):**

- **Direction A — the edit/upkeep loop (DECIDED to extend).** One mechanism: assistant proposes a field value → June confirms or **taps to change** it → logged + revisited. `tap-to-change-engagement` (this plan, Task 5) is the seed; **June wants that tap-to-change structure extended into create-vs-update for sure** — generalized from "engagement" to *any* field. This is the edit primitive for the whole upkeep loop. Already flagged **foundational** in the selection handoff (the engagement/affective upkeep, "this seems stale, still true?" nudges all assume it; none built).

- **Direction B — inference-completeness (OPEN, assess first).** The weeding LLM should fill every field it can **infer from June's words** — not leave a field blank when her words carry the value. **Guardrail already in the system** (`capture-writes` Global Constraints): *only from her words, never invent a situated value; absent stays absent.* So the design question is narrow: *which fields are inferable-from-her-words but the weeding contract doesn't currently ask for?* — NOT "make the LLM guess more." (Note the situated/inferable line June holds: `capture-writes` found only ~3 of a Task's 14 / Project's 16 fields are ever written.)

  **June's sequence for B (her register — assess before deciding, don't force it):**
  1. **Assess whether it's actually an issue** — observe: which inferable-from-her-words fields come back empty on real captures? (A field-by-field audit vs. the live weeding contract; capture-writes' "3 of 14/16" is the starting evidence.)
  2. **Then decide scope** — does B fold into new-object-defaults / create-vs-update, or does it need its own design session?

**Ready next step for B (offered, not yet run):** the assessment in B.1 — audit each Task/Project field: *inferable from typical capture language? does the contract ask for it?* — answers "is it an issue" before any build.
