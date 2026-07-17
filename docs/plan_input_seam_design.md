# Daily-plan input structure — authoritative design (the selection→LLM seam)

*Settled 2026-07-14 (June). This is the source of truth for **how the daily plan's input is
structured and handed to the LLM**. It supersedes the "eligible list" gate. Companion to
`display_grain_design.md` (which owns the *render* side — the block, the arc) and `AI_LAYER_SPEC.md`
§2 (the data model). Where this and an older doc disagree about what the LLM is fed, this governs.*

---

## The principle June set (the whole design in one line)

**Python does not gate the LLM's input to shrink the day. It *structures* the input so the LLM
naturally does the right thing.** Day-size protection lives in composition + render (the output),
not in a pre-gate. The input's *formatting* enforces the semantics — daily-life work and block work
arrive as visibly different kinds of things, so the model treats them differently without being told
"don't conflate them." Positive, structure-matched instructions; never a negative "don't."

### The day-size mechanism, named (so it is not hand-waved)

"Protection lives at output" is not a hope that the LLM behaves — it is a concrete mechanism that
already exists in the runtime, plus the LLM's time-aware composition. Spelled out so no reader (human
or agent) concludes it is missing:

1. **The workday window is the deterministic bound.** `build_context` computes `start_time` and
   `end_time` (default 18:00; a Focus Period's `workday_end` can widen or narrow it). The scheduler
   (`build_schedule`) places items into clock slots only within that window; **whatever does not fit
   overflows into `still_here`** ("Didn't fit before <end_time>") — held, not scheduled. So the
   *scheduled* day is bounded by the hours in it, **regardless of backend** — even a sloppy model
   physically cannot schedule more than the window holds. The unit that matters is **time**, not a
   count of `Steady`/`Open` projects; there is deliberately **NO count/length cap** (that would be
   redundant with the window and re-impose the deterministic gate this design retires).
2. **Capacity signals shrink the day, via LLM judgment.** The Low-energy button sets a capacity
   signal the prompt already responds to (lead with lying-down tasks, insert a rest block, reduce
   total scheduled work); a Focus Period's gentle/low-spoon intent does the same. This is the LLM
   adapting to *stated* capacity — the intelligence the design wants used, not a hardcoded rule.
3. **The prompt tells the model to compose time-aware, not fit-everything.** Three rules
   (Task 10): build the schedule from the available hours; prioritize `Steady` unless the Focus
   Period overrides; do NOT try to fit every item — overflow to `still_here` is the correct answer,
   not failure.

The only residual concern (from the 2026-07-14 critic swarm) that survives contact with these
mechanics is **observability, not a cap**: nothing records how loaded a generated day came out, so
silent model drift would be invisible. If desired, add day-load *logging* (collect-now, mine-later —
like the other signal logs), never a gate. Optional.

---

## What was wrong (diagnosis — runtime-verified on June's real data, 2026-07-14)

Driving the real generation, not reading the spec, surfaced these:

1. **A Python "eligible list" gated the LLM input for day-size** — the wrong place, by June's
   principle — **and it was leaky**: id-resolution matched *all* active tasks, so the LLM pulled in
   off-focus `Backburner` work. On June's live *recovery / low-energy* week it scheduled leatherworking
   (dye), the phone case, and a paper response — none foregrounded, all against the rest intent.
2. **Blocks were represented as collapsed proxy tasks** ("Check messages from my doctor · 2 more"),
   not as blocks — the display collapse leaking into the LLM's scheduling unit.
3. **The goal→project chain never reached the LLM.** 34 projects carry a `Goal link` in Anytype,
   but the loader drops it — every project arrived goal-less, so the "how does today advance her
   goals" instruction had nothing to work from. (Same bug family as the earlier empty task→project links.)
4. **Task durations mostly missing** → the clock schedule came out empty.
5. **The one-next-action collapse (a display rule) was gating the LLM input.**

Good news that holds: the **focus period works** (it did the real day-shaping), and the **IOP block
renders correctly** as one "Work on X" chunk with a checkoffable arc.

---

## Locked decisions (June, 2026-07-14)

1. **INPUT = ACTIVE ITEMS ONLY.** Python excludes `Backburner` / `Done` / paused / `Inactive`-status
   before the LLM sees anything. Feeding everything and letting resolution accept it was an
   **overcorrection** — active-only is the fix. This is a *relevance* filter, not a day-size gate.

2. **NO SEPARATE ELIGIBLE LIST.** The structured active tree **is** the input; it replaces the
   `T1…Tn` gated list. The LLM does the selecting and composing.

3. **STRUCTURAL SEPARATION BY FORMATTING (the core move).** Python organizes the input into
   **entirely separate subsections** that read as *different kinds of things* — not one uniform task
   list. The format does the semantic cleaving:
   - **Daily-life subsection → scheduled BY TASK.** Each chore is its own schedulable item.
   - **Block-work subsection → scheduled BY PROJECT.** Each project is one "Work on X" block; its
     tasks are the **arc** (display), not separate schedulable items.
   We do **not** instruct "don't conflate them." We make them structurally distinct categories so the
   right behavior is the path of least resistance.

4. **GOAL-EXPLAINED PROJECTS.** Each project is presented *with the goal it serves* (requires fixing
   the loader that drops `Goal link`). The block-work subsection reads as goal-framed projects, not
   bare task piles — this is the point of the nested structure, finally realized for the LLM.

5. **THE PROMPT EXPLAINS EACH CATEGORY.** Positive, per-subsection handling: daily-life → schedule by
   task; block-work → schedule by project as one chunk carrying a duration; the arc is for June's
   display, not enumeration.

6. **THE LLM APPLIES THE LOGIC.** Selection, ordering, honoring the focus period, and daily-vs-block
   handling are the LLM's judgment over clean structured input. Python prepares; the model decides.

7. **FOCUS PERIOD GOVERNS.** Foregrounded → elevate. Rest / low-energy → suppress optional work.
   Authoritative over "there's room."

8. **OPEN = AVAILABLE-IF-ROOM, SUBORDINATE TO FOCUS.** `Open` is active, so it *is* in the input.
   The LLM may include it when there is room — but a rest / low-energy focus **suppresses it
   regardless of room**. When not scheduled, it stays findable in the Map. (Folds in the
   Open-surfacing decision; born-`Open` never vanishes because active = in-the-input.)

9. **THE COLLAPSE MOVES TO DISPLAY ONLY.** One-next-action-per-thread is how June's *screen* renders;
   it is never a filter on the LLM's input.

10. **RESOLUTION IS CORRECT BY CONSTRUCTION.** Because the input equals the active set, every item the
    LLM can name is active — no ghost rows, no all-tasks escape hatch needed. Block-work resolves by
    project ("Work on X" → block + arc); daily-life resolves by task.

---

## REFINEMENT 2026-07-14 — engagement is universal; `Side` is only grain (the Donna Haraway stress-test)

June's test case: **"Email Donna Haraway"** should live as a discrete daily-life *task* (not a "Work on X"
block), but should **not** appear every day — whereas **"do the dishes"** *should*. Both are "daily life."
The current rule can't tell them apart: it makes **all** `Side = Daily life` work *always eligible*, exempt
from engagement (`display_grain_design.md` decision 1). That conflates two independent things.

**The fix — two axes, fully decoupled:**
- **`Side` = GRAIN only** (how it's scheduled): `Fun / hobby` → excluded; `Daily life` → **by task**
  (discrete); everything else → **by project** ("Work on X" block). Side answers *task or block?* — nothing else.
- **`Engagement` = SURFACING, and it is UNIVERSAL** (whether/how often it shows today): `Steady` → every
  day; `Open` → available **if there's room**, focus can suppress; `Backburner` → dormant; `Done` → out.
  Engagement answers *does it show today?* — **for daily-life projects exactly as for block projects.**
- **`Recurring` type** = its own cadence mechanism (dishes, meds return by frequency), independent of
  engagement — this is what actually carries "every single day" for true chores.

**This RETIRES `display_grain_design.md` decision 1's "Daily-life = always eligible, unset engagement on
purpose."** Daily-life projects now carry a **real** engagement:
- `Networking and relationships` → `Side = Daily life` + `Engagement = Open` → "Email Donna Haraway" is a
  discrete task that surfaces **when there's room, not daily.** ✓
- `household` → `Side = Daily life` + `Engagement = Steady` → its tasks surface daily. ✓

**Build consequences:**
- The active-only + surfacing logic applies to daily-life projects too — no "always eligible,
  engagement-exempt" bypass. `grain.classify` still returns `task` for Side=Daily life (that's *grain*),
  but *surfacing* now reads engagement for it like any project.
- The **backfill must set engagement on the ~4 Daily-life projects** (household / medical / self-care /
  social+networking) — June decides each value; they can no longer be unset.
- **Data change owed:** `Networking and relationships` → Daily life + Open. **HOLD this write until the
  logic is built** — under *current* code, `Side = Daily life` = always-daily, which would make Donna
  Haraway appear *every day* (the opposite of the goal).

---

## Python's deterministic prep (this is *preparation*, never *selection*)

- **a.** Active-only filter (decision 1).
- **b.** Daily-vs-block classification + **structural separation into subsections** (decision 3) —
  reuses `grain.classify` (Fun/hobby → excluded; workstream → excluded; Daily life → task; else → block).
- **c.** **Attach durations** — a block carries its chunk length (`gsdo_block_chunk_min`); a standalone
  / daily task needs a duration too, or the clock schedule can't place it (the empty-times bug).
- **d.** **Fix the goal-link loader** so goals reach the LLM (decision 4).

---

## Folded-in threads (this seam subsumes them)

- **Open surfacing** → decision 8.
- **New-object-defaults** → born-active (`Open`) = born-in-the-input; retire the hardcoded `Steady`;
  backfill the unset-engagement projects to `Open` / `Backburner` so "active" is unambiguous. **Per
  the REFINEMENT above, Daily-life projects now carry a REAL engagement too** (household → `Steady`,
  social/`Networking and relationships` → `Open`, etc.) — the old "Daily-life stays unset-on-purpose,
  `Side` governs them" rule is RETIRED; `Side` governs grain, engagement governs surfacing, for
  daily-life exactly as for block work. The tap-to-change chip is the seed of the deferred field-upkeep
  generalization.
- **The grain/block render** (shipped) is the *display* side; this is the *input* side — consistent,
  two halves of one system. **Preserve every shipped win** — zero-ghost checkoffable arcs, block =
  render-layer (not a synthetic selection unit for task-having projects), did-a-chunk completion,
  chunk durations, focus/low-energy adaptation, still_here framing. The rework must meet the same
  underlying needs the past week's builds met; if code changes, verify each still holds.

## Known, chosen deferral (named so it is not a future surprise)

**Born-`Open` grows the "active" set monotonically** — new projects default into active, and nothing
moves them *out* (staleness detection is parked, Phase 8). Any given *day* is still bounded by the
workday window, but the "available if there's room" pool grows over months. This design's calm quietly
depends on "active" staying sane; the mechanism that would keep it sane (staleness) is deferred **on
purpose**. When the pool feels large, that is the signal to build staleness — not a bug in this seam.

---

## Build dependencies surfaced (runtime-verified, must be handled in the build)

1. **Loader `Goal link` fix** (34 projects affected).
2. **Task durations** (empty-schedule bug) — decide the default/learned source for standalone/daily tasks.
3. **Unset-engagement backfill** (~22 projects) so active-only is clean.

## Verification (the repo guard — non-negotiable)

The build's final step **regenerates June's real plan and reads the result**: active-only; two cleanly
separated subsections; block-work scheduled by project; daily-life by task; focus period honored;
off-focus `Backburner` work absent; clock times populated. A green test suite is not sufficient —
the function is verified by driving the real runtime (see repo `CLAUDE.md` build-frame guard).
