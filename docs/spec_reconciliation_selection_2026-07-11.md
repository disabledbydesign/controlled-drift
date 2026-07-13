# Spec Reconciliation — Daily-Plan Selection Model (2026-07-11)

**Status:** reconciliation, June-reviewed; her comments folded in (2026-07-11). Step A of the fix: make the selection design an accurate single source of truth again, so the code fix (step B) has one correct target and stops re-drifting. **Merge into `AI_LAYER_SPEC.md` §2 (engagement) + §9 (daily plan) — approved by June; to be done once this doc is final.** The spec is stale (pre-Side, pre-Focus-Period).

**Why this doc exists (the drift it closes):** the spec always specified the fix — the daily plan surfaces the *next tangible item per thread*, gated by `engagement` (§2: "Steady → one daily move; Backburner → invisible unless neglected; Done → excluded"; §9: "one move per thread, never the pile"), rendered as streams not a flat list (§8h). The code drifted: `select_and_order_tasks` (`plan_generate.py:318`) reads none of engagement — it surfaces every task, orders by a date-hash, renders flat. Then `Focus Period` was built as a *second* priority mechanism beside `engagement` without reconciling the two, so engagement's core job got orphaned and later fixes patched the hint layer instead of restoring the gate. This doc reconciles the two mechanisms into one model.

---

## The reconciled selection model

Three layers, composed at read time. None is a scalar; none overwrites another.

### Layer 1 — `engagement` (enduring per-project baseline)

The **grain gate**, kept to the minimal *queryable* set the selector filters on. Richer or ambiguous states are **not** new categories — they route through the qualitative entrypoint below.

- **Backburner → hidden** unless the neglect threshold fires (§9 neglect-resurfacing). "Put away."
- **Open → available, self-paced** (June, 2026-07-11): **no pushed daily move, and *not* nagged as neglected.** Lives in the map as available; surfaces in the plan only when foregrounded. The middle state between Backburner (put away, resurfaces if a neglected obligation) and Steady (active, one move/day). Maps to the "route self-directed work to the map, don't pick her threads" behavior. New Engagement option to add.
- **Steady → one next move** (the thread's next tangible action — not the pile). "Keep chipping daily."
- **Done → excluded. Needs Clarifying → flagged, not scheduled.**
- **unset → treat as Backburner-equivalent** (hidden unless neglected), so an unset project never floods; the AI proposes a real value (see upkeep below).
- **Sprint → retired from `engagement`.** Sprinting a project is a *phase* action — expressed via Focus Period **foreground** (Layer 2), not a stored per-project category. (One live project is currently Sprint; migrate it — trivial.)
- **Hyperfixation → not a priority category.** It's genuinely ambiguous (leverage, OR "I can't make myself do anything else"), so we don't nail it down. It — and states like "causing-june-anxiety" — route through the qualitative entrypoint + Strategies, not through more engagement values.

**Qualitative entrypoint (June's move — fewer categories, more room for her words).** Rather than adding engagement categories, give June one place to drop qualitative state ("hyperfixating but stuck," "this is making me anxious") that the LLM **reads when it plans**. This is the *existing* free-text `engagement_notes` (the situated specifics the select can't hold) and `affective` (emotional charge, non-scalar — June: "hyperfixation is an affective lens, as is anxiety") — both already loaded into context. No new field needed. Principle: an entrypoint for her qualitative information, not an enumerated category set.

**How June inputs & keeps this current (resolved — not a separate design conversation):**
- **Input → `/drift`.** June says it ("the AI-welfare paper is making me anxious"); the capture/weed path writes it to that project's `affective` / `engagement_notes`. The fields exist and the LLM already reads them in planning. **Not a trivial wire (June's catch):** the overlay's headless capture LLM must (a) know the existing projects, (b) distinguish "update *this project's* feeling" from "create a new task," and (c) have an *update* path — capture is create-only today. Same shape as the known weeding-dedup gap (§10: load existing items, propose update/merge, not just create). A real but bounded build item, not a design conversation.
- **Keep updated → the *same* upkeep loop as engagement** (AI proposes/asks, June confirms, response logged), pointed at `affective`. Not a new mechanism.
- **Parked (design-later):** proactive detection of affective *shifts over time* (the §2 affective learning loop — "tracks how a project's affective weight shifts and how fast"). Starts dead-simple (ask on the same check-in cadence); the smart version is its own pass.

### Layer 2 — `Focus Period` (temporary phase lens, laid over Layer 1)

Cross-cutting, time-bounded, June-authored (the keystone). Re-weights for the current stretch; **does not overwrite `engagement`** — when the period ends, the baseline is intact.

- **foreground → elevate.** **This is where "Sprint" lives** — foregrounding a project is how you intensify it for a phase.
  - **⟳ AMENDED (June, 2026-07-12): sprint and foreground are NOT identical.** Sprint means dedicating full or nearly-full focus to a project because it needs to get done — stronger than "elevated this phase." Foreground stays the general elevation; sprint is a distinct, stronger mode within the period layer (likely shape: a per-period flag on a foregrounded project that claims most of the day's real estate instead of one move). Design owed — tracked in Anytype ("Sprint mode design"). The Engagement-select cleanup (removing the old Sprint option) waits for this design so the concept has a home before the old label disappears.
- **foreground activates a Steady project.** A consequence June flagged as valuable: foreground is what makes a Steady project *active this phase* — which gives the mechanism to **rotate over Steady projects in a later build** (surface a different subset of Steady threads each phase, so they don't all compete every day). *Document this link when merging to the spec.*
- **paused → suppress** (a normally-active project drops this phase).
- **workday bounds / output format / availability** → as already built.
- Precedence: the period overrides engagement where they conflict (focus-config addendum, already decided).

### Layer 3 — `Side` (orthogonal filter) — THREE categories

`Obligation / Wellbeing / Fun-hobby` (the select defines all three; live objects currently use Obligation + Fun-hobby — **Wellbeing is defined but not yet populated**). Independent of grain; applied after Layers 1–2. Handling per category:

- **Obligation →** in the plan.
- **Fun-hobby →** the hobby block (excluded from the plan by default, `HOBBY_BLOCK_DEFAULT`).
- **Wellbeing → health / body / care: exercise & walks, medical, self-care — first-class, surfaced in the plan, distinct from Fun-hobby** (a new division June confirmed; 7-types-of-rest: a hobby is a form of rest but not always restful). Exact plan-handling isn't wired yet — an adjacent step-B item.

### Output

For each thread still showing, **one next tangible item**, rendered as named streams (Goal › Project › next-item), never a flat list (§8h). Picked-within-project by a real signal we already have — nearest deadline, else least-recently-surfaced — labeled honestly ("next in X · N more"), never a hash.

**Concrete effect on the live space:** honoring Layer 1 alone hides the 19 Backburner + 3 Done projects *before any new build* — the plan drops from ~100 surfaced tasks toward ~a dozen real next-moves.

---

## Keeping `engagement` current — via Strategy, with response logging

The baseline must not go stale again (10 projects sit unset today).

1. **AI proposes engagement changes; June confirms** (offer-don't-impose). Not hand-maintaining 44 fields; not the phase silently overwriting them.
2. **The proposal rules live in `Strategy` objects, not hardcoded** (June's call) — a calibration input that shapes behavior (§2's definition; the spec already treats "next tangible item per project" as such a strategy). Visible to June and tunable.
3. **June's response is logged** — including a revisit interval ("not now, come back in X months") so the system does not re-ask before then. Reuses/extends the plan-corrections log; feeds the two-tier learning loop (§10).

**Initial strategies to write (June — already obvious):**
- If a **non-Backburner project hasn't been worked on in ~1 month** → propose moving it to Backburner.
- If a **Steady project hasn't been surfaced/worked in ~16 days** → propose foregrounding it (16 chosen so it doesn't overlap the 1-month rule). This is the upkeep side of the "foreground activates Steady / rotation" mechanism (Layer 2).
- Consider making these **one combined strategy** so the two thresholds don't drift apart.
- Both depend on tracking *elapsed time since last worked/surfaced* — the shared mechanism noted under Parked.

---

## What the code must do (targets for step B — not built in this pass)

1. Selector gates grain by `engagement`: **Backburner** hidden-unless-neglected, **Open** hidden-unless-foregrounded (available in the map, not nagged), unset→Backburner-equiv, **Steady**→one item, **Done** excluded, **Needs Clarifying** flagged. (No Sprint/Hyperfixation gate — Sprint via foreground; Hyperfixation via qualitative entrypoint.)
   - **Explicit request overrides the gate (real need — June 2026-07-12):** when June's `extra` says "put X in today," the named task/project MUST be surfaced as a *real move* — never hidden by the gate, never relegated to still_here. Treat it as a per-generation foreground; the match from her words to the task lives where the model can do it (it already treats her words as top priority), not a brittle Python name-match. The gate's only job re: this is to never *remove* a task she named before the model can surface it.
2. Focus Period applied as an override *on top of* engagement (foreground elevates, incl. "sprint"; paused suppresses); does not mutate stored engagement.
3. `Side` (three-way) applied orthogonally; **confirm Wellbeing handling** before wiring.
4. Within a project, pick the one surfaced item by deadline → least-recently-surfaced; label "N more."
5. **"Nothing lost" = still in Anytype, not shown daily (June 2026-07-12).** The plan shows only selected moves; held-back tasks simply aren't selected — they live in Anytype, accessible there. **AS BUILT: kept `_ensure_all_tasks_accounted`, did NOT delete it** — it only sees the selector's *returned* set, so returning the gated ~12 makes still_here empty on its own, AND it now correctly guards *just those 12 real moves* against a silent model drop (more protective than deleting). **No LLM-contract or renderer edit needed** — verified. (Silent-drop protection for *named* items lives in the selector's explicit-request override, item 1.)
6. The LLM reads the qualitative entrypoint (`engagement_notes` / `affective`) when planning.
7. Engagement-upkeep proposals read from `Strategy` objects; log June's response + revisit interval.
8. Migrate the one existing `Sprint` project off that value (→ foreground or Steady as appropriate).

---

## Adjacent — PARKED / notes (captured, not this pass)

- **Neglected-*task* surfacing is itself a Strategy** (June's catch) — same propose→respond→log-with-revisit-interval pattern as engagement upkeep. What it *and* the engagement-upkeep strategies actually depend on is a **shared mechanism: tracking elapsed time since a task/project was last worked or surfaced.** Partly built — `Task.last_surfaced` + `neglect.py` — needs verifying/extending (especially "last worked on a *project*"). So this is "strategies + one tracking mechanism," not a big separate build. Design once the selection fix is live.
- **The agentive-dialogue surface is a foundational build much of this assumes (June's catch).** The upkeep loop, affective input, and neglect prompts all assume the system *proactively surfaces a proposal* ("move this to Backburner?") and June responds, logged. That proactive propose→respond→log surface isn't built — partial pieces exist (the overlay's negotiate + ask field, the `/drift` chat), but not the loop. Named here as a dependency: the upkeep / affective / neglect mechanisms can't fully land without it. **The core selection fix (step B) does NOT depend on it** — it runs on engagement values that already exist, so the immediate win lands regardless.
- **Route-prioritization (§8d) / survival-plan-as-Goal-with-routes** — the spec's answer to "where does my multi-route survival plan live." Separate high-value thread; the open sub-question (explicit route-condition fields vs. free text, §10) is June's to decide when §8d is designed.
- **Merge into `AI_LAYER_SPEC.md` §2/§9 — APPROVED by June.** Do after this doc is final (fold in the retire-Sprint, three-way Side, qualitative-entrypoint, and foreground-activates-Steady/rotation points).
