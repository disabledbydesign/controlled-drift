# Critic-swarm learning log — daily-plan plans

## 2026-07-17 — `2026-07-17-as-needed-reactivation.md` (as-needed reactivation build plan)

**Stack:** `design_spec` — personas: future build agent, skeptical architect, author-informed (bloch).
**Both always-runs (intelligibility + jargon) cut at June's direction** — audience is one build agent
with repo access; the three lenses read open-ended, so the "at least one open lens" requirement was met
by orienting each persona open. June also directed that every critic receive the *world* the spec lives
in (telos, feature friction, the load-bearing guards, the settled design doc) — this made all three
reads runtime-grounded rather than doc-surface.

**Convergent flag (3/3 — load-bearing):** Task 4 mis-locates the wiring seam. It points at a two-hop
path (`daily_plan.py:277` fold → `blocks_from_scheduled:914`) but the real runtime is three hops — the
`as_needed` flag dies at the LLM composition boundary because nothing re-attaches it by id in
`plan_generate.py:999/1054-55` the way `recurring` is. Result: `is_as_needed_item` always False →
completion falls to the cache-only flip → task resurfaces forever → silently dead, green suite, only
Task 7 catches it. **The exact reason-from-function failure the plan cites by name, reproduced inside
the plan that invokes the guard.** Fix (build agent): add an `as_needed_ids` set at `:999` + re-attach
at `:1055`. Build agent found two more missed row-origins (`:947`, `:981`) for a timed as-needed task.

**Convergent flag (2/3, exact — build agent + author-informed):** the `old`-arg dead guard.
`set_recurring_active(rid, active, old=None)` — no caller passes `old`, so the log no-op never fires AND
it contradicts Task 7 Step 5's `old:true` acceptance check. Fix: read the pre-write value in the
primitive (it already fetches for read-back), pass it as `old`.

**Convergent flag (2/3):** Task 4's test calls `server._complete_for_test` (doesn't exist); the HTTP
`live_server` idiom can't express the assertion. Route-test strategy is an undecided load-bearing fork.

**Divergent gifts (single lens):** *Architect* — the two-writer race (June's tick-list is a fourth
writer of the same `Active`; "shared contract" is a field name, not a protocol; stale-view lost-update
is live); the reserved scheduled-pause increment breaks the one-boolean abstraction (proposes a status
enum now); two access notes (LLM-matcher as vigilance tax; networked completion that can 500 from bed).
*Author-informed* — Task 1 is cram-everything in a build spec, so the "Tasks 1–4 minimal state machine"
cut line isn't clean (split the commit even if the file is edited once); T1 Step 4 verifies `Active`
present but not that mirrored fields share Task's keys; undo-of-reopen offers a contradictory option.
*Build agent* — "mirror Task's fields" prose vs. the code's 7-field subset diverge; false "Project link
# reused from Task" comment.

**Cuts (small — design-spec carve-out):** duplicate python3-not-python; has_target-no-reader stated 3×
(trim the Global Constraints one); Self-Review DRY paragraph. Author-informed gave a PROTECT list
(per-task one-writer restatements, re-derive warnings, reason-from-function's three distinct load
points) — designed substance, not repetition.

**Persona performance:** all three sharp; build agent + author-informed independently converged on both
the runtime seam and the dead guard (strong signal). Architect's two-writer-race + status-enum were the
divergent gifts no other lens reached. The "give them the world" briefing is why the reads were
runtime-grounded.

**Cross-stack generalization flag:** for build/design specs in a repo with a *reason-from-function*
guard, the highest-value convergent finding is reliably a wiring-seam the plan describes correctly at
the doc layer but mis-locates in the real runtime — and briefing critics with the actual runtime files
(not just the spec) is what surfaces it. Same shape as the 2026-07-14 entry below (the block-as-task
mis-joint). Worth making runtime-file briefing standard for the `design_spec` stack.

## 2026-07-14 — `2026-07-13-daily-plan-blocks.md` (display-grain build plan)

**Stack:** `design_spec` — personas dispatched: future-build-agent, skeptical-architect, author-informed (bloch profile), + a custom **neurodivergent-UX specialist** (added by June). Always-runs (intelligibility, jargon) **skipped at June's direction** — "they're for prose, not a build plan."

**Corrections June made to the swarm design (the 4b gate did its job):**
- Cut cold-reader + jargon always-runs.
- Add a neurodivergent-UX specialist (the feature is a cognition-design decision, not plumbing).
- Require all critics to read the *actual code* and the high-level design docs, so they judge against what's being built, not in the abstract.
- (Standing) do not prime critics with the specific risks the author already suspected — keep the lenses open.

**Convergent flags (multiple lenses, load-bearing):**
- **The block was modeled as a task when it's a different kind of thing** — surfaced in three layers independently: architect (backend *identity*: id-less unit through an id-keyed pipeline → crashes, 30-min duration collapse, no container path), author-informed (*fidelity*: abandons the design's "render over what's computed" for a parallel source, unreconciled), ND-UX (*experience*: block dims-when-checked, clock-pinned, door into the old wall). One root, three surfaces.
- **Dead scaffolding** (architect + author-informed + build-agent): `has_children`/`parents_with_children`, an `always_eligible` field, a phantom `"engagement"` grain value — built and read by nothing.

**Divergent/specialty flags that changed the design:**
- Architect: chunk-length duration is a *durable preference* → belongs on the Anytype Project, not a local file (forks the source of truth). **Adopted.**
- ND-UX: dim-on-check contradicts "still open"; clock-time re-imposes rigidity; "open in map" dead-ends in v1; the chunk-chip is a fidget-toy / goal-displacement pull; the arc "here" over-asserts on messy done-data. **Adopted the ones that integrate; rejected the ones that reinvented.**

**What June addressed vs. held (the integration filter — June's, not the swarm's):**
- **Held/rejected as reinvention:** "band instead of clock time" (→ use the existing focus-period day-shape); "continuity trace" (→ that IS the deferred wins mirror); "defer the ✓-behind arc" (→ it's a simple Anytype read reusing `orient_map` logic, rendered in the overlay HTML).
- **The frame fix June supplied:** the block gets a **synthetic id** and rides the existing LLM-composition + id pipeline like a task — resolving the architect/build-agent crash cluster *without* the post-LLM Python splice that would have re-broken focus/strategy composition (the `bbbb070` regression). This is the load-bearing correction; the swarm found the crash, June found the integrated fix.
- **Adopted:** synthetic-id integration, Anytype chunk-length field, arc-from-Anytype-rendered-in-overlay, dead-code cuts, route bug fixes, dim→additive, no-map-door-in-v1, mockup-into-repo.

**Persona performance:**
- **skeptical-architect** — sharpest single review; named the id-keyed-spine mis-joint and the "third option" (render over what's computed) that the design doc itself pointed at. High value.
- **future-build-agent** — best at *concrete* failure (exact crash sites: `_build_task_refs:717`, `_retime:1006`; the task-less-container-unreachable path; the route `elif`/`.get()` bugs; the unreachable mockup). Complementary to the architect, not redundant.
- **author-informed (bloch)** — caught the silent divergences from the design's own stated approach (the adjudication-norm violation), the dead scaffolding, and protected the register (flagged the one "learning" overclaim). The profile's failure-patterns made it specific.
- **neurodivergent-UX (custom)** — highest-value *net-new* lens: the "checked/scheduled states borrow finished-clock-pinned-task grammar" synthesis was something no other lens reached, and June's own integration filter then sorted which fixes to keep. Worth keeping in the design_spec stack when the artifact is a cognition-facing UI.

**Cross-stack generalization flag:** on a build/design plan, run the swarm to find the *frame* problem, but the author/owner's **integration filter** ("does this fix reuse an existing mechanism or reinvent one?") must run *after* the swarm — several correct-sounding swarm suggestions were reinventions of already-built or already-deferred surfaces (the focus-period day-shape, the wins mirror). The swarm surfaces; the owner adjudicates against the built system. (Consistent with the divergence-adjudication memory + "integration over reinvention.")
