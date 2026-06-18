# Parameters v2 — get-shit-done-o-tron

**What this is.** The updated brief for get-shit-done-o-tron after the Design-Time **synthesis** step (Workshop Session 1, 2026-06-14). Per the process in the original `Parameters.md`, this step read June's cross-material and talked it through with her to surface *further parameters, design decisions, and research* — so the **design agent inherits them instead of re-deriving them cold.** This is still pre-design: no spec has been written.

**This v2 does not restate the original brief.** Read these in order:
1. **`Parameters.md`** — the original brief: the concept, the 16 parameters, soft blockers, and the step-by-step process. *June's note: the design agent should read this directly; the synthesis summary is good but go to source.*
2. **`SYNTHESIS_design_time.md`** — who June is, her needs read through her profile, how to work with her, and the design DNA drawn from her own systems (PMA, Reframe). Start here for context.
3. **`DESIGN_v1_emerging.md`** — the design-*informing* decisions and parameters that surfaced in the workshop (NOT a design — a feed into one). Has a "terms a cold reader needs" block.
4. This doc — the consolidated additions + open forks + handoff.

---

## A. Settled directions (workshop output — inputs to the design, not the design)

- **Core telos: alignment lives outside June's head.** The system holds the goal→strategy→alignment so she doesn't have to carry it; the anxiety drop comes from *trusting she's aligned without remembering all of it at once.* It's distributed cognition (she + AI + stored context jointly hold what no part holds alone).
- **Architecture: a Python core + an AI interface layer + a learning loop.** Python = the list, tracking, database, deadlines, calendar (real stakes → reliable/checkable). AI = generates lists from parameters + capacity-state + goal-alignment, breaks tasks into step-trajectories, checks drift. Learning loop = self-tunes beyond what June can specify upfront (its own design session).
- **The list is load-bearing and earns its place.** A to-do list has real stakes (tracking what's actually done matters; she needs the list to externalize what she can/must do). So the conventional checkable list is kept — *not* reinvented — while the relational-project structure and capacity-first organization layer on top.
- **Project model: Goal (simple) + `reaching_for` (the philosophy/what-it's-for, open field) + Tasks (checkable) + Capacity profile.** `reaching_for` doubles as the **ground truth for judging drift vs. flexibility** (June's idea): a change that pulls away from it = drift (surfaced, never blocked); a new step that still serves it = fine flexibility; and `reaching_for` itself may legitimately evolve (the system asks, doesn't enforce).
- **AI-assisted task breakdown.** The AI lays out a step-trajectory so June needn't enumerate steps upfront; it's living (re-runnable mid-stream), capacity-tagged per step, collapsible (one-step vs. whole-arc by capacity), and the attach point for the duration learning loop. "Waiting on someone" is a first-class next-step state.
- **Rest is checkable — with inverted friction (June's correction).** Not non-checkable to avoid "failing at rest" (Claude's wrong first instinct); checkable so that *not*-resting becomes gently visible and she **notices the pattern.** The friction points at under-resting, not at failure.
- **PMA integration: thin-now, rich-later (June chose).** gsdo keeps a *thin* `reaching_for` field now (so it works before PMA runs), designed to point at PMA's rich version once PMA exists — PMA's own "point, don't duplicate" ethic on this seam.
- **Non-negotiable guards (satisfy/violate boundaries):** nothing punitive (no streaks/overdue-red/rollover-shame; undone tasks compost or roll forward); offer-don't-impose (permission-granting register, never imperative/nagging); capacity is multi-dimensional, never one scalar; the goal-alignment check must not become surveillance (offered reflection, not a scold); don't flatten June's situated specifics into tidy numbers.

## B. Further parameters surfaced (additions to the original 16)

- **Voice / messy-brain-dump input is core.** Accept an unstructured voice-or-text dump; the AI organizes it into projects/tasks/steps. June does not pre-sort. (Her preferred input mode; mirrors Goblin Tools' "magic to-do"/compiler and Taskmaster — see §C.)
- **Reminding without nagging** — the central interface tension (she forgets → needs reminding; but must not feel watched). *How* the system reaches her is its own parameter.
- **Interface + platform undecided** — terminal / web / phone; calendar-sync is a phone problem; need her sister's framework + its platform (porting source — credit the sister).
- **Privacy — tiered, NOT a blanket local-first guard (resolved 2026-06-14).** Earlier draft said "local-first, likely a hard guard." Loosened: "local" was a proxy for *private-not-mined + portable + durable*, which hosted-with-export or tiered storage can also meet — and Julia's working ADHD system (the porting source) is fully hosted. So: privacy via *conscious tiering* (e.g. legal/health held locally, the rest can be hosted), decided deliberately, not a blanket rule. See `EVAL_adopt_adapt_build.md` §G and `JULIA_FRAMEWORK.md` §F.
- **Visual-first / slider-not-number input.** Capacity/effort input is via sliders or visual controls, never cold numeric entry (a slider is more accessible than a number June invents cold). Supported by Julia (needs visuals), the research (make capacity spatial), and Goblin's spiciness slider. See `JULIA_FRAMEWORK.md` §C.6.
- **Spatial time representation (near-non-negotiable — June: "I need that desperately").** *Time itself* shown as space, not numbers: duration as proportional blocks, time-remaining as a shrinking visual (cf. Tiimo's timeline, Time Timer's disc). This is the field's consensus fix for time-blindness and June flagged it as a deep personal need — treat it as a load-bearing display principle, distinct from the slider-input point above. (Caution from the research: externalized time must feel like a tool June holds, not a clock watching her — imposed/surveilling timers backfire. See `EVAL_adopt_adapt_build.md` §A.)
- **Cold-start** — useful before the learning loop has data (cf. Autograder's Bayesian cold-start).
- **Capacity is multi-dimensional:** energy · embodiment (lying-down/moving/sitting) · location (home/leaving) · duration (quick/deep) · social (solo/waiting/needs-someone) · sensory load · **affective weight** (e.g. job apps after the non-renewal are *heavy* in a way energy doesn't capture). Plus *modes* over axes (a "quick-wins/feel-productive" day; a "bed day").
- **Errand-batching with a spoon cap** (group leaving-house tasks, but cap the batch so it doesn't tip into exhausting over-cram).
- **"Feel-productive" days are legitimate** (quick-wins for momentum honored without guilt; maybe weave in one goal-aligned win).
- **Household/maintenance woven with project work**, not a second-class list (chores are real labor).

## C. Open forks for the design agent (not yet decided)

1. **Adopt / adapt / build — DONE, see `EVAL_adopt_adapt_build.md`.** Key shift from the original framing: the brain-dump/breakdown engine is now *commodity* (a local-LLM prompt — Goblin et al. just wrap it), so it's not the thing to "adapt." The scarce, un-adoptable thing is the **AI alignment + capacity-selection layer**. Resolved shape: **build only that thin layer; adopt a store for the commodity parts** (the checkable list/UI). Substrate still open — Notion / Obsidian / plain files / Super Productivity (§C, `JULIA_FRAMEWORK.md` §F). Local is no longer a hard guard (see §B privacy). *Original note retained:* off-the-shelf tools won't carry the guards or the `reaching_for` layer — which is exactly why only the layer gets built.
2. **Project `parameters` field + granularity.** Should a project carry an evolving `parameters` framework — or does that belong in PMA, tied to project directories? And: **does "wash the dishes" need parameters?** → tasks/projects should have a *variable, optional level of structure* (a one-off chore stays a bare checkable item; a major project gets the full apparatus). Imposing heavy structure on a light task is flattening from the other direction.
3. **The list-generation / "what do I do right now" picker** — gsdo's hardest problem (mirrors PMA's central unsolved relevance-picker): assemble a day from parameters + current state + goal-alignment + errand-batching + rest, *without* collapsing to a single priority scalar.
4. **Global vs. per-project/per-repo scope** (Param #14) — one system across all repos vs. dev-task sprawl; reconcile with existing trackers (job-search TRACKER, Canvas, Reframe Garden/OpenSpec).
5. **Capacity-axis set** — ~~port from June's sister's framework~~ **captured: see `JULIA_FRAMEWORK.md`** (Julia Cordero's framework, credited; duration · embodiment/location · priority · Area/Bucket/Status/Needs-Clarifying, used as day-to-day sort axes, not a fixed score).
6. **Learning-loop design** — own session; duration-estimation first.

## D. Research to conduct
- ✓ **DONE — Existing ND tools, for the adopt/adapt/build eval** (§C.1): see `EVAL_adopt_adapt_build.md` (field scan + frameworks + the adopt/adapt/build landscape).
- **Crip-time scholarship:** Ellen Samuels ("Six Ways of Looking at Crip Time"), Alison Kafer.
- **Emergent strategy** (adrienne maree brown) — small/iterative/adaptive over master-plans; a build-philosophy input.
- **Planning-fallacy / duration-estimation literature** — for the learning loop.

## E. For the next instance (handoff)

- **What's done:** the synthesis reading sweep + this dialogic workshop. Context is captured across `SYNTHESIS_design_time.md`, `DESIGN_v1_emerging.md`, and this doc. June's own margin notes (`//`) are live in the synthesis + design-inputs docs — incorporate them, don't strip them.
- **Source-fidelity hedge:** June's profile, the cyborg-methodologies INSIGHTS doc, and PMA's `DESIGN_PARAMETERS.md` were read in full; PMA's `VALUES.json` and `WORKSHOP_LOG.md` only partially; Reframe's `SESSION_MECHANICS_VISION.md` (the empirical STEP/PARK/WEAVE rationale) was **not read** — a fresh instance may still mine it.
- **An adversarial gap-check is still worth doing fresh** (June asked for a warm self-QC this session, which is done). The PMA record's own finding: the warm author who made the work can't reliably self-catch its own flattening — a fresh instance with an *aimed* prompt (where did the synthesis flatten June's specifics? which parameter got enacted shallowly? what cross-connection got missed?) is the right tool. `/critic-swarm` is built for this.
- **The decision waiting for June (per `Parameters.md` Design-Time step 3):** would the result be better if the next agent **plans how to write the spec first** (June reviews/approves the plan before drafting), **or drafts the spec directly**? Surface this to June; she decides. (A Reframe stage-skip nudge also flagged that planning often prevents rework — consistent with offering the plan-first option.)
