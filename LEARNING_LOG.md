# LEARNING_LOG — Critic Swarm Sessions

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
