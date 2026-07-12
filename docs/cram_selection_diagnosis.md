# Root-cause diagnosis — the daily plan crams every task into every day

*Written 2026-07-11 for the SEPARATE thread June is running to fix this (with another agent). A cold
agent can pick it up from here. This is diagnosis + evidence, not a repair design — the repair needs
its own design pass because the spec is stale (see bottom).*

## The symptom
Today's daily plan tries to fit **every active task** in, every day. June has asked for this to be
fixed before; it wasn't. It is the root problem underneath a lot of the system's friction.

## Where the cram comes from (evidence)
Task selection for the daily plan lives in two places, and **neither trims the list**:

1. **`scripts/daily_plan.py :: load_active_items`** — selects tasks by **status only**: every non-done
   task with `gsdo_task_status` ∈ {None, Active, Ready, Needs Clarifying} is a candidate *every day*
   (`daily_plan.py:101-134`). No date filter, no engagement filter, no cap. (Projects are excluded
   only if Engagement == "Done", `:78`.)
2. **`scripts/plan_generate.py :: select_and_order_tasks`** (`:318-341`) — only **orders**
   foreground-first and **drops paused-project** tasks. It keeps everything else and passes the whole
   list on. No per-project limit, no engagement sizing, no capacity cap.

So the full active list reaches the plan. **The prompt asks for restraint but nothing enforces it:**
`prompts/daily_list.md:16-17,46` tells the model to use Engagement to size "how much plan real estate
each project gets" and to surface "the next tangible item per project, not the whole pile" — but it's
a soft instruction to the LLM over a fully-crammed input, so the day overstuffs.

## The intended model (already written, never implemented)
`AI_LAYER_SPEC.md` specifies the anti-cram selection:
- **Engagement drives real estate** (Project `engagement`, spec §2): Sprint / Hyperfixation → priority
  (more); **Steady → one daily move**; Backburner → invisible unless neglected; Done → excluded.
- **"Active tasks" are derived** (Task `status`, spec §2): task is Ready **AND** its project's
  Engagement ∈ {Steady, Sprint, Hyperfixation} — not "any task that isn't done."
- The **"next tangible item per project, not the whole list"** strategy was meant to be "baked into
  the architecture" (spec Strategy section).

## Why this can't just be "implement the spec" (June, 2026-07-11)
**The spec is stale.** It was written *before* the build, *before* the `Side` field, and the `Side`
binary (Obligation/Wellbeing) is itself being reworked into multiple tiers in another session. Since
the spec, the system also grew focus periods (foreground/paused projects) and the capacity→strategy
wiring — **several overlapping "what shows up today" signals that were never reconciled**:
- Engagement (spec's intended sizer — not implemented)
- Focus-period foreground/paused (implemented, in `select_and_order_tasks`)
- Side partition (`partition_by_side`, and Side itself in flux)
- Capacity → triggered strategies (`daily_plan.py:183-241`)

So the repair is a **design job**: define one current-truth selection model that composes these
signals (how many items per project by engagement; how focus-period foreground interacts with
engagement sizing; how capacity shrinks the set; where Side sits), then implement it deterministically
so the day is *the next item(s) per engaged project, sized by engagement, capped by capacity* — not
every task. Reusable idempotent field/type machinery: `gsdo_anytype.ensure_property` /
`link_properties_to_type`, verified via `verify_model.py`.

## Downstream dependency
The UI-flow work (`docs/flow_model_design_thread.md`) — Add-tab regenerates today's plan for
today-marked captures — **assumes this fix has landed**. Until it does, "regenerate" just rebuilds a
crammed day. This fix goes first.
