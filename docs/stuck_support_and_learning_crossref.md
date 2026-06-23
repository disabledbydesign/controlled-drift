# Cross-reference: stuck-support + learning loops → the streams

*Prepared session 16 (2026-06-23) at June's request: "make sure any relevant information,
concepting, architecture gets folded into those streams in /drift." Drafted here for her
approval rather than auto-written into Anytype — folding concepting into her real space is
hers to ratify (per `docs/drift_surface_boundary_stab_2026-06-21.md`: the boundary is hers,
don't over-route into Drift). On approval, these become stream context updates + case notes.*

---

## → Stream: "Design and build stuck-support mode" (Backburner, under Build Controlled Drift)

**Fold into its context (what-it-is / design notes):**
- **The overlay "I'm stuck" button is this stream's entry point.** Current payload (in
  `~/.controlled-drift/actions.json`): *"Offer one very small, concrete first step I can
  take right now — something doable in five minutes. Hold everything else. Don't ask me to
  decide anything."* This is a **stopgap, not the design** — it routes a stuck-moment to the
  generator, but the genuine stuck-support response is still undesigned.
- **Design shape so far (undesigned beyond this):** return ONE 5-minute step; hold
  everything else; ask June to decide nothing. Shift from *sorting* to *thinking with* her.
  Don't force a fuller design — collect case data (this stream's stated method).

**Add as a case note (Parked/Task under the stream):**
- **Case #2 — tractable-vs-goal displacement (2026-06-22).** June poured a session into a
  tractable, satisfying sub-problem (overlay color palettes, ~9 variants) while the
  load-bearing goal (a *usable* surface) stayed distant. She named it herself: "I'm
  building it, not using it." ADHD attentional pull toward the bounded-and-completable —
  **not a failing**, and naming it is useful data, not a correction. Same shape as the
  proactive-surface gap (passive invocation fails under hyperfocus). The gap between the
  tractable and the goal is exactly the territory a stuck-support *strategy* would address.
  (Full: memory `tractable-vs-goal-displacement`.)
- (Case #1, for continuity — session 15: June stuck, in pain, not eating; generic
  strategies didn't reach her in the moment.)

---

## → Learning-loop architecture (cross-cuts streams; suggest as a note on the active "Orientation map and arc rendering" stream, linked to stuck-support)

Five loops are now wired or designed. They share one principle (June's Autograder finding):
**learn the pattern from corrections over time; don't pre-spec it.**

1. **Interface learning loop — the variable button schema (the both-and).** Buttons live in
   `actions.json` (config, not code). Freetext requests are logged; a post-v1 pass clusters
   them → proposes new preset buttons June approves; unused presets surface for pruning. A
   learning loop on the *interface itself* — serves Param #11 ("help me find the axes — I
   can't track them all") + #12. **This is where stuck-support and the loops connect:** "I'm
   stuck" is one button in a schema that itself evolves from use.
2. **Correction learning.** Every negotiate logs `log_correction(kind, before, after)` —
   preset = clean categorical signal, freetext = the missing-button signal. (Wired.)
3. **Surface/neglect learning.** Every generation logs `log_surfaced_batch` → neglect +
   rhythm history. (Wired.)
4. **Duration learning (Param #5).** Move deltas (old→new item times) captured now; the
   estimator is post-v1. (Data captured; learner later.)
5. **Meal-time learning.** `update_meal_learned_time` nudges the learned lunch time from
   June's moves. (Wired.)

**Why fold this in:** the loops are real architecture now, not just an idea — and they're
the connective tissue between the overlay, the daily plan, and stuck-support. Captured in
the stream, the next instance sees the whole learning design without re-deriving it.

---

## Suggested mechanics (on approval)
- Update the stuck-support stream's `gsdo_context` to include the entry-point + design-shape
  notes above (additive; keep its existing "what it is").
- Add Case #2 as a `Parked` task (or note) linked to the stuck-support stream.
- Add the learning-loop architecture as context on the active overlay stream, with a
  cross-link to stuck-support.
- Nothing here restructures or deletes — all additive, all reversible.
