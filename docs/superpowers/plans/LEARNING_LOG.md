# Critic-swarm learning log — daily-plan plans

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
