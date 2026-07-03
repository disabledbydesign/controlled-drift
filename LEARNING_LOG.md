# LEARNING_LOG — Critic Swarm Sessions

---

## 2026-07-03 — Learning Loops v1 build plan

**Artifact:** `docs/superpowers/plans/2026-07-02-learning-loops-v1.md`
**Stack:** design_spec (future build agent + skeptical architect) + one custom lens (design-docs keeper) + author-informed (no formal profile exists for a Claude-authored technical plan — substituted `~/.claude/CLAUDE.md` + this project's own memory feedback-files as the closest real equivalent, per the persona's own "reads from the inside, knows documented failure patterns" definition).
**Personas dispatched (4, parallel):** future build agent (plan + every file it modifies/cites, cross-checked diffs and citations against live on-disk state); skeptical architect (plan + AI_LAYER_SPEC + ROADMAP + focus_configuration_addendum + the focus-configuration-layer sibling plan + core scripts); design-docs keeper (custom — reads AI_LAYER_SPEC/ROADMAP/addendum/sibling-plan first, reacts to the plan as the person who's held those documents across months, not a checklist); author-informed (CLAUDE.md + memory feedback files as profile substitute).

**Author corrections to swarm design:** June cut the always-run intelligibility and jargon reviewers ("only matters if a build agent can read it" — folded into the build-agent lens instead); kept author-informed but redirected its profile source since no formal one exists for this artifact type. Session also self-corrected mid-flow: dispatched the first swarm pass before finishing June's own inline plan comments, caught by June ("we should have addressed my comments first"), stopped all three in-flight agents via TaskStop, finished the notes, then redispatched clean.

**Convergent flags (2–3 reviewers, load-bearing):**
1. **The plan cannot honestly claim "complete"** (design-docs keeper + author-informed, reading completely different source material, same conclusion). A live, unanswered design question in June's own words sits inside Task 3 (whether to also build overlay task-editing) and the plan proceeds past it silently. Fixed: converted to an unmissable 🛑 callout; Execution Handoff now explicitly refuses to hand off until it's answered.
2. **Task 4's live wiring is premature** (architect: permanent dead-weight coupling for data that can't exist yet + future-build-agent: silently writes a live behavior change with no confirmation, arguably violating the plan's own Global Constraint + design-docs keeper: per-project bias grain risks the same qualitative-flattening problem Task 5 was just cut for refusing). Three independent angles, same fix: build and test the EMA math, hold the wiring.
3. **Two independent factual citation errors**, each caught by two reviewers separately: `daily_plan.py:294` doesn't contain the duration-fallback code it's cited for (real location: `scripts/scheduler.py`); a wrong commit hash was cited for Phase 5. Both corrected in-place with a note on what was wrong and how it was verified.
4. **Test-count arithmetic was wrong throughout**, compounding across two reviewers: stale "230 existing" baseline (274 at swarm time, 281 by revision time — parallel work landing on the branch), and the plan's own per-task test specs summed to 17 (later 16, after Task 4's dependent test was removed with the wiring), not the "~9" claimed. Fixed by refusing to hardcode a baseline at all — the plan now instructs re-running `--collect-only` at build time instead.

**Single-reviewer, high-severity (verified before accepting):** future-build-agent found `engagement_watch.py` reading the Engagement property by a literal key, contradicting this codebase's own documented convention (`daily_plan.py:64`'s comment: key is Anytype-generated, not predictable) for this exact field — ships with green tests (the mock fabricates the same wrong key) and silently logs zero real corrections forever. I verified independently against live Anytype data already in session context: the key does currently equal the literal string, but the codebase deliberately never relies on that for this property. Fixed to match the established name-based convention.

**Load-bearing, protect (design-docs keeper):** Task 5's cut is "the system working exactly as intended" — it extended the crip-time/capacity-flattening guard to a site (a learning loop *about* capacity, not a capacity field) the original spec hadn't explicitly anticipated, and the plan caught it, quoted the guard accurately, and cut code rather than softening the wording. This reasoning was left untouched in revision.

**Cuts applied (author-informed):** Task-1-depends-on fact de-duplicated from 3 statements to 1 (Task 4's "Depends on" line, the authoritative location); the top-of-doc revision note trimmed from a redundant/incomplete restatement to a pointer; the Phase 6/9 explanation trimmed from 4 verbatim repetitions in ~150 lines to 2 (plan-prose + module docstring; function docstring and test docstring now point back rather than restate); opening-directive-vs-closing-"which approach?" contradiction resolved by removing the reopened toggle (precedent already answers it) — folded into the same edit that added the Task 3 handoff-block callout.

**Persona performance:** future-build-agent found the single most severe issue (the engagement-key bug) via direct code-quote evidence, and independently corroborated two factual errors the author-informed reviewer also caught with sharper arithmetic. Design-docs keeper and author-informed converged on the same "not actually complete" finding from entirely different reading material — the strongest cross-lens signal of the session. Architect's three-angle case against Task 4's wiring, combined with the other two reviewers' independent angles on the same task, was the clearest instance of convergence marking something load-bearing rather than redundant.

**Status:** all identified fixes applied directly (factual corrections, redundancy cuts, Task 4 rescoped to build-not-wire, Task 3's engagement lookup corrected, missing verification steps added). The Task 3 open design question is NOT resolved — genuinely June's call, not something a revision pass can close. Plan not yet handed to the build loop pending that answer.

---

## 2026-07-02 — Focus-configuration build plan

**Artifact:** `docs/superpowers/plans/2026-07-02-focus-configuration-layer.md`
**Stack:** design_spec, customized. Cut-hunting disabled (June: design spec, don't look for cuts). Intelligibility/jargon folded into the build-agent lens (June: readability only matters as "what the builder needs").
**Personas dispatched (4, parallel):** cold build agent (plan only); skeptical architect (plan + addendum + AI_LAYER_SPEC + real code); design steward (plan + addendum + Parameters.md + Parameters_v2.md — June's fidelity ask); June-fit lens (deep read of `/github/profile/` then the plan — June's serve-her-better ask).

**Author corrections to swarm design:** skip standard cut-reviewer (bloch.md); fold jargon+intelligibility into build-agent; June specifically requested the fidelity lens read both Parameters versions and the June-fit lens run from profile docs.

**Convergent flags (multiple lenses, load-bearing):**
1. **Wrong entry point** (architect headline + build-agent). Phases 3–4 wired to `daily_plan.run()` (dead interactive terminal path); the live overlay + morning push run through `plan_generate.generate_plan` → `build_context`, which calls the 7-arg `format_context` and drops the raw objects. Defaulted kwargs mean the feature is invisible on June's phone though all tests pass.
2. **Priority-list output shape is the harder half, under-scoped** (architect + steward + build-agent). It's a new output contract (`_JSON_INSTRUCTION` demands verbatim clock times) + a new overlay renderer branch, not "reuse scheduler + prompt tweak." Mis-triggered (`if in_window → priority` forces fragmented output on a *sprint* week too); ambiguous who owns ordering.
3. **June's "a period can be MORE, not less" reframe dropped** (steward headline + build-agent + architect). `Workday end` parsed but never applied (scheduler already accepts `end_time`); `is_off` a dead param; window auto-equated with diminishment.
4. **Foreground/paused is a prose hint, not structural reprioritization** (architect + build-agent). Reorders description lines only; task selection is a date-seeded hash independent of the period; name-keyed, discards stable ids. The exact soft-hinting the addendum said was insufficient.
5. **Authoring-from-blank vs react-don't-generate** (June-fit deepest + threads architect's stubbed `author_focus_period` + steward's staleness gap). System value gated behind a recurring generative executive-function act June is least reliable at.
6. **Staleness silently reverts to un-fixed baseline** (steward + June-fit). Lapsed period → `None` → plan draws from whole pile again = the exact failure the layer fixes; new trust-gap; no v1 nudge.

**Divergent gifts (single lens):** survival-obligation neglect risk → per-period "don't chase me about this" override (June-fit); Log Day/planned-vs-actual surveillance-framing risk (June-fit); Side binary pinches income-generating creative work — cuffs/dev (June-fit, needs June); reflect-back overwhelm → radically compressed echo (June-fit); NL keyword-scan in `resolve_output_shape` violates the plan's own no-NL rule + fits the edge-case example "couple hours" (steward); malformed day-off JSON silently plans a workday on a day off — punitive, invisible to June (steward); linear/nonlinear guard absent (not just deferred) in v1 (steward); type-key `gsdo_focus_period` is the unverified activation hinge (architect); "one settings file" conflates config_dir vs data_dir (architect); reuse existing `pvn` accessor not a new `_by_name`, and get a real object dump before writing `parse_focus_period` (build-agent).

**Load-bearing, protect (convergent praise):** the pure `focus_period.py` resolution module + `is_day_off` precedence; Phase 5 capture-now-interpret-later stores (refuses to classify); facts-travel-with-meaning in `format_context`; date-fields + free-text split; the Decisions/phasing/sequencing honesty; overall design *fit* (June-fit: "one of the best-fit designs I've seen for her").

**Through-line (synthesis):** the plan holds firm where the design made an *unconventional* commitment loud (don't classify signal; carry meaning as free text) and drifts where a commitment cut quietly against the conventional engineering shape (availability-as-neutral-override reflexively became bounded-window-as-less; soft judgment reflexively became a keyword list; alignment reflexively became an LLM hint instead of structural reordering; the real backend path was mistaken for the terminal one).

**Persona performance:** architect sharpest (found the entry-point fault with file:line evidence + traced the output-contract chain); steward caught the reframe-erosion the others missed and verified two wiring claims against code; June-fit built genuine texture and threaded the authoring-seam risk; build-agent's cold read independently corroborated the entry-point + ordering-contradiction. All four earned their place; none shallow.

**Status:** synthesis delivered to June; plan revision pending her decisions (entry-point re-point is mandatory; priority-list-in-v1, v1 staleness stopgap, Side binary for income-creative work, and the Saturday-deadline-vs-second-sprint tension are June's calls).

---

## 2026-06-15 — AI_LAYER_SPEC.md

**Artifact:** `/Users/june/Documents/GitHub/cyborg-memory/controlled-drift/AI_LAYER_SPEC.md`
**Stack:** design_spec (future build agent + skeptical architect + intelligibility + jargon)
**Author-informed:** skipped (no profile)

### Personas dispatched
- Future build agent
- Skeptical architect
- Intelligibility reviewer
- Jargon reviewer

### Convergent flags (3+ reviewers)

1. **PMA / `reaching_for` underspecification** — build agent (what does "pointing" mean?), intelligibility (concept never introduced), jargon (unexplained to all three camps). Most load-bearing gap in the spec.

2. **Subsystems are stubs not specs** — build agent (7a, 7b, 7e explicitly "to design"), architect (nucleus inverted: schema complete, behaviors incomplete), intelligibility (no dependency map or build sequence). The spec is a design document and a weak build brief simultaneously.

3. **LLM is dangerously over-relied upon** — build agent (guards aren't testable; no system prompts exist), architect (six behaviors all delegated to unspecified LLM judgment). Convergent identification of the deepest structural risk.

### Notable flags (single reviewer, high signal)

- **Slider UX has no implementable surface** (build agent — blocker): the spec prohibits numeric entry but all current surfaces (MCP terminal, Anytype chat-stream) are text-only. No specified third option.
- **Task type does too much** (architect): "bare by default" + eight pre-defined optional fields is contradictory. Should be two subtypes or fields held back until promotion loop fires.
- **"Higher-priority Goal" imports undefined ordering** (intelligibility): no priority field on Goal; phrase references a mechanism with no formal grounding.
- **§7 has no dependency map** (intelligibility): subsystems listed without sequencing or interdependencies. Build agent can't tell what to build in what order.
- **Records-level vs. system-level learning loop distinction never introduced** (intelligibility): used as a known distinction in §4 and §5 before being defined anywhere.

### What author addressed vs. held
*Not yet updated — pending June's review.*

### Persona performance notes
- Build agent: sharp and operational; the slider blocker and embodiment/associational-input tension were the two most precise finds.
- Skeptical architect: strongest single contribution — naming "schema without behavior" as the true failure mode, not infinity drift. The build-priority inversion (capacity picker and weeding before schema completeness) is the highest-leverage single critique.
- Intelligibility: caught structural gaps (PMA concept never introduced, learning loop tier distinction, §7 no dependency map) that the build agent and architect both missed.
- Jargon: methodical; the "activation function" metaphor failing disability scholars is worth flagging. Low-cost fixes throughout — mostly gloss-not-replace.

### Cross-stack generalization flag
**Design specs without behavior specs are not build-ready, even when the data model is thorough.** A spec that fully designs schema and stubs all behavior subsystems produces a beautiful architecture doc that fails as a build brief. Pattern to watch for in future design-spec reviews: is the ratio of schema to behavior spec appropriate for the intended use of the document?
