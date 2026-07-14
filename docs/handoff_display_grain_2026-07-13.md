# Open build: display-grain rule for the daily plan

**Status:** designed-in-spec, NOT built. June wants to build this with a fresh agent from a clean slate. This doc is the factual description + pointers — not a plan. Write the plan with June.

## The concept (read these first)
- **`AI_LAYER_SPEC.md` §2** — the selection-model note at the top of the data-model section (the `Side` field now has four values, added 2026-07-13). The display-grain rule is written there as intended behavior.
- **The originating note is June's own**, in `docs/controlled_drift_changes.json` — search the item with `"id": "5h5p3u"` (project "Profile memory formation"), field `noteForClaude`. That paragraph is where June first articulated the display-grain problem in her own words. Read it verbatim; it carries the concept.

## The factual issue
The daily plan surfaces work at a single grain — individual **tasks** — for every project. June's data shows that's wrong for some work and right for others. The rule she specified:

- **`Side = Fun / hobby`** → not rendered in the daily plan at all. **(already built** — `daily_plan.partition_by_side`.)
- **`Side = Daily life`** → render at **task** grain (the specific chore: "clean the kitchen"). Marks the Sustainable-daily-life subprojects (medical / household / self-care / social), which now carry `Side = "Daily life"`. **(the Side value exists; the grain behavior is the default task-grain, so nominally already true — but see the open question below.)**
- **Everything else (Obligation / Wellbeing)** → render at **smallest-subproject** grain: a "work on [subproject]" block, NOT individual tasks — with **workstreams filtered out** of that grain calculation. June does the within-subproject prioritization manually. **(NOT built — this is the real work.)**

## Where it lives
`scripts/plan_generate.py`, `_gate_and_collapse` / `select_and_order_tasks` — the code that gates by engagement and collapses each project to one next move. The grain rule changes what UNIT that collapse emits (a task vs. a "work on X" project block).

## Open design questions (answer WITH June before building — she flagged this as "a real design session" in the 5h5p3u note)
1. **Duration**: a "work on [subproject]" block needs a time length for the scheduler (which places clock-time blocks). Where does it come from?
2. **Persistence/completion**: a "work on X" block is checkable-but-returned-to across days — the current done/not-done task model doesn't represent that. June's note calls this a "larger than a time estimate can really account for" unit; she suspects it's what `Steady`/`Open` engagement really mean.
3. **Who picks the subproject**: the LLM (needs a prioritize-between-subprojects subsystem "we haven't built yet" — June's words) or June manually (she says "'work on scholarly writing' would also work, and I do the prioritization manually")?
4. **Engagement-gate interaction**: the new `Daily life` subprojects have unset Engagement, so under the current gate they're hidden-unless-neglected. "Daily life renders tasks" and "the engagement gate hides unset-engagement projects" currently fight; which wins is undecided.

## Downstream ripple (scope awareness)
Changing the emitted unit touches: the selection engine, the LLM prompt contract (`prompts/daily_list.md`), the scheduler (needs a duration for a block), the held-back/"N more" logic, and completion tracking. This is why it's a plan-first build, not an inline edit.
