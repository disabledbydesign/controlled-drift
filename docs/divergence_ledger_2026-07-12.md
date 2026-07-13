# Divergence Ledger — spec vs. what got built (2026-07-12)

**What this is.** The built system has grown away from the founding spec in a bunch of places. Some of that growth is *good* — the build solved the real problem better than the spec's machinery would have. Some of it is a plain reason nobody wrote down. And some of it left a real need unsolved. This ledger sorts each one, on its own evidence. The spec is not treated as sacred; the build is not treated as ratified.

**How to read it.** Each entry has: what the design wanted (and the problem it was solving), what actually exists, whether the built thing solves that problem, whether anyone decided this on purpose, a verdict, and one concrete next step.

**Four verdicts:**
- **Question for you** — genuinely ambiguous; I need your call before anyone acts.
- **Costs you** — the original need is now unmet or the change hurts; fix toward what the design was reaching for.
- **Reason never written down** — a real, deliberate reason exists; just put it in the spec so it stops looking like a mistake.
- **Better than the plan** — the build is an improvement; update the spec to match the build.

The questions come first (you read those), then the costs, then the undocumented reasons, then the wins.

---

## QUESTIONS FOR YOU (four)

### Q1. Your daily plan is never saved into Anytype — it lives only in a local file the overlay reads

1. **What the design wanted.** The spec says the confirmed plan gets *written into Anytype*, which then displays it: "its output becomes display-ready data written to Anytype, which renders it. Chat negotiates; Anytype holds and renders." (`AI_LAYER_SPEC.md:67`, also `:412`). The daily-plan prompt still says it out loud: "On confirm, Python writes the plan to Anytype, where June checks back on it visually." (`prompts/daily_list.md:8`). The problem this solved: for survival-critical tasks (legal, health, job), you must keep a usable, readable system *even when the AI layer is down* — "the human-readable layer must never depend on the AI to be legible." (`AI_LAYER_SPEC.md:456`, §10 graceful degradation).
2. **What is built.** The plan is written to a local cache file, `~/.controlled-drift/current_plan.json`, and rendered by the overlay (`scripts/plan_store.py:6`, `:103-107`). Nothing writes the plan into Anytype — the only Anytype writes anywhere are for task/project objects (`gsdo_objects.py`, `cd_mcp_server.py`), never the plan. So `prompts/daily_list.md:8` is now a false statement.
3. **Does it solve the original problem?** Partially. The *overlay* is a better everyday surface than an Anytype-rendered plan would be (instant, ambient, comes to you). But the §10 safety net is weakened: your ordered, framed daily plan now exists only in one local JSON file plus the overlay. Your underlying tasks/projects are still in Anytype and still legible — but the *plan itself* is not.
4. **Was this decided on purpose?** The overlay build was deliberate and documented (`docs/morning_build_vision.md`, the phase-6 plan docs). But **no record** reconciles it with the spec's "Anytype renders the plan" claim or the §10 degradation guarantee. The write-to-Anytype line was never built and never explicitly dropped.
5. **Verdict: Question for you.** The overlay-renders choice is good and should be written into the spec either way. The open part is the safety net.
6. **The question / action.** If the overlay or the generation pipeline is down some morning, is yesterday's cached plan enough — or do you want the confirmed plan mirrored into Anytype too, so a readable version always survives the AI layer going down? Either way: ratify "overlay renders the plan" into §1, and fix the stale `daily_list.md:8` line.

### Q2. Your morning phone notification sends your actual task text through a public relay

1. **What the design wanted.** The whole reason the store is Anytype is privacy: "tasks include legal, health, and job-search material," so the system uses a local, end-to-end-encrypted store (`AI_LAYER_SPEC.md:47`). The privacy ladder is explicit (`memory/backend-model-comparison.md:37,71`).
2. **What is built.** The morning push POSTs the plan body — the woven frame plus the first block's task names — to `https://ntfy.sh/{topic}`, a public notification relay (`scripts/morning_push.py:191-199`). The topic is a secret only your phone subscribes to.
3. **Does it solve the original problem?** For *delivery*, yes — it's free, needs no Apple developer account, and is reliable from a background job. For *privacy of content*, it opens a gap: the real task names (which can be the exact legal/health/job material the encrypted store exists to protect) travel through a third-party public server, protected only by an unguessable topic name, not end-to-end encryption.
4. **Was this decided on purpose?** The *choice of ntfy* was deliberate and documented — billing-proof, no Apple account, reliable where macOS notifications weren't (`docs/morning_build_vision.md:14`, `memory/project_gsdo.md:480`). But **no record** shows anyone weighing the privacy cost of pushing plan *content* through the public relay specifically.
5. **Verdict: Question for you.** This is a risk judgment only you can make.
6. **The question / action.** Is it OK that real task names go to your phone this way — or should the push be content-free ("your plan is ready, tap to open") with the actual content only behind the overlay? Cheap to switch to content-free if you want it.

### Q3. A set of fields are written or read by nothing — decide, per field, wire it or drop it

1. **What the design wanted.** Each of these fields was given a real job in the spec: **AI-autonomous** = "can the AI do this with minimal oversight? Lets the system offload work you don't need to touch" (`:148`); **Access notes** (the open-text access/EF note) = where unnamed executive-function barriers accrete and get promoted to real tags — "this is where the dropped cognitive-load axis lives" (`:147`); **Task due date** = the deadline that's supposed to be the *first* signal for picking the next item (`:144`, and §5 "nearest deadline"); **Relevant docs** = "the AI reads these before working on project tasks" (`:126,:149`); **Project description / reaching-for** = the "what" and the "why" of the alignment chain (`:118-120`).
2. **What is built.** All of them are dead on at least one end. Due date isn't even loaded in the plan path; description/reaching-for/relevant-docs/access-notes have readers that are unwired, wrong-keyed, or starved because no capture path writes them (`docs/structural_diagnosis_2026-07-11.md:48-49`; `docs/orchestrator_flags_2026-07-11.md:35`, the capture-writes findings).
3. **Does it solve the original problem?** No — these needs are unmet. But they are **not** speculative schema: the spec assigns each a concrete role. The exception is *AI-autonomous* — the "offload work" subsystem it feeds was never designed, so it's the closest to speculative.
4. **Was this decided on purpose?** No decision either way. The capture-writes audit (`docs/orchestrator_flags_2026-07-11.md:35`, item 5) names exactly this set and says the move is to "decide build-reader-or-drop before writing to them."
5. **Verdict: Question for you.** This is genuinely per-field, and it's your call.
6. **The question / action.** For each — AI-autonomous, Access notes, Task due date, Relevant docs, Project description/reaching-for — do you want it *wired* (build the missing reader or writer) or *dropped* (remove from the schema so it stops implying it works)? Due date and reaching-for look highest-value to wire (they drive selection and drift). AI-autonomous looks likeliest to drop.

---

## COSTS YOU (four)

### H1. The plan promises you that deferred things "come back and get their turn" — but the machinery that would make that true is broken

1. **What the design wanted.** The "still here, not today" list is supposed to reassure you concretely: each parked item shows its rhythm and reason, "and the system actually re-surfaces it. The relief depends on the re-surfacing being real, not just stated." (`AI_LAYER_SPEC.md:413,416`). The prompt tells the model to say so (`prompts/daily_list.md:50`).
2. **What is built.** The model improvises to keep that promise — one real saved plan says of your job-search threads: *"these are steady threads—each will get its turn in the rotation."* (`scripts/data/plan_snapshots.jsonl:6`). That sentence is the "rotation" phrase you half-remember. **It is not a design concept** — it's the LLM's own gloss on the "reassure them, they resurface" instruction. And the resurfacing behind it is broken three separate ways: the "last surfaced" field is written only by a path you don't use; the neglect query has no done/parked filter; and the display filter checks a key that's never returned — dead code (`docs/orchestrator_flags_2026-07-11.md:14`).
3. **Does it solve the original problem?** No. The plan tells you things will come back, and nothing reliably brings them back. That's the exact "you won't forget" lie the spec warned breaks trust in the system.
4. **Was this decided on purpose?** No — this is accreted breakage, verified live (5 of 137 tasks have the field, none newer than mid-June).
5. **Verdict: Costs you.** A stated promise with no working mechanism is worse than silence here.
6. **The action.** Make resurfacing real before the prompt keeps promising it: point the neglect check at `scripts/data/surface_log.jsonl` (which is current), add the done/parked filter, and fix the dead display filter. (Note: the Focus Period layer is good but does **not** deliver this — see B2. Different problem.)

### H2. "Just the next step" — the core thing that lets you not hold everything at once — isn't built as a structure; it's fragile text-matching

1. **What the design wanted.** The next-step trajectory is the anti-overwhelm heart of the system. Your own margin note says it plainly: *"the beauty of the next step is that it allows me to not have to hold everything in my head at once — I just focus on the one thing I'm working on."* (`DESIGN_v1_emerging.md:99`; the mechanism is §8c, AI-assisted breakdown). The spec deliberately said steps should be *generated on demand*, not stored as objects (`AI_LAYER_SPEC.md:135`).
2. **What is built.** No breakdown feature (§8c is unbuilt). In its place, the "arc / next step" is pulled out of a project's free-text Context by splitting on the first em-dash — it only works if the text happens to be formatted `next step — …`, and silently returns nothing otherwise (`scripts/orient_map.py:140-163`).
3. **Does it solve the original problem?** Not really. On-demand breakdown was the plan; a fragile string convention that vanishes on a formatting miss is a stopgap that fails quietly — the worst failure mode for a trust-the-system tool.
4. **Was this decided on purpose?** No record ratifies the em-dash convention as the mechanism. `ROADMAP.md:17` already calls `orient_map.py` a "superseded first cut." §8c was deferred in the build order (deliberate), but nothing chose the em-dash parse as its replacement — it accreted.
5. **Verdict: Costs you.** The mechanism you named as the point of the whole system is standing on string-matching.
6. **The action.** Either make next-step a real field the AI proposes and writes (robust, no formatting dependency), or build §8c properly. At minimum, stop depending on em-dash formatting for something load-bearing.

### H3. Your multi-route survival plan still lives nowhere durable

1. **What the design wanted.** Your conditional, evolving job/survival plan (grants vs. academic vs. industry vs. income, gated by savings, recovery, a possible move) is explicitly **not** a Strategy object — it's meant to live in a Goal with route-Projects plus route-prioritization, §8d, where the AI reads the situation and proposes which route gets this week's energy (`AI_LAYER_SPEC.md:196`, §8d at `:320`). "I keep forgetting and reinventing this whole plan" is the core reason the system exists.
2. **What is built.** The Strategy type is deliberately narrow — status, what-for, learning-notes, applies-when (`scripts/build_strategy.py:8-16`) — correctly, per spec. But §8d was never built, and it's been deferred every pass as "needs real Project data" (`AI_LAYER_SPEC.md:419,433`).
3. **Does it solve the original problem?** No. "June's survival strategy lives nowhere durable; the plan re-derives it from scattered free text every run. This is the exact failure the whole system exists to fix." (`docs/structural_diagnosis_2026-07-11.md:45`).
4. **Was this decided on purpose?** The narrow Strategy type: yes, deliberate and documented. The §8d gap: a deliberate *deferral*, not a wrong turn — but the cost is now active.
5. **Verdict: Costs you.** Deferred-by-design, but the thing being deferred is the system's founding promise.
6. **The action.** Prioritize a durable home for the multi-route survival plan (§8d, or the Goal-with-routes structure it needs). This is the highest-telos gap in the ledger.

### H4. The shrinking countdown you said you need "desperately" was never built — and neither was the completion sound

1. **What the design wanted.** Time shown as space — a shrinking-disc countdown — flagged as near-non-negotiable: *"I need that desperately."* (`Parameters_v2.md:31`; scoped into v1 at `AI_LAYER_SPEC.md:326-327`, §8f). Plus one small dopamine affordance in v1: "a small positive sound on task completion via afplay" (`AI_LAYER_SPEC.md:421`, §9).
2. **What is built.** Neither. No countdown/disc/SVG exists anywhere in the code. A completion sound helper exists (`scripts/notify.py`, "Tink") but it fires on *capture confirmation*, not task completion — marking a task done (`scripts/task_actions.py`, `POST /api/complete`) plays nothing.
3. **Does it solve the original problem?** No — the time-blindness affordance you named as a deep personal need is absent, and the one v1 dopamine hit isn't wired to completion.
4. **Was this decided on purpose?** **No record found** of a decision to drop either. The disc is ~30 lines of SVG by the spec's own estimate; the sound is ~1 line.
5. **Verdict: Costs you.** A "desperately"-flagged need dropped silently is exactly the kind of thing that falls between the cracks.
6. **The action.** Build the shrinking-disc countdown (cheap, and you flagged it as load-bearing); wire the existing sound helper into the task-completion path.

---

## REASON NEVER WRITTEN DOWN (one)

### U1. There are two ways in (chat and overlay) with different guards — on purpose, for a real reason, just not in the spec

1. **What the design wanted.** The spec describes capture as one gate (§8a) and assumes a shared write path.
2. **What is built.** Two capture front doors. In Claude Code, "capture" needs no separate LLM call because Claude Code *is* the model; the overlay is "a plain Python server with no intelligence of its own, so it has to call an LLM itself" (`scripts/capture_generate.py:2-8`). The link-safety guard (that a Task's link points at a Project, not a Goal) currently lives only in the overlay path, because it's built on overlay-only tokens — flagged in the code: the rule "belongs in the shared write layer so both paths inherit it and can't drift. Until that consolidation lands, this is the only enforcement." (`capture_generate.py:48-55`, flagged for you 2026-06-23).
3. **Does it solve the original problem?** Yes — both paths capture. The mechanical reason for two paths is sound (the overlay genuinely can't reuse Claude Code's intelligence).
4. **Was this decided on purpose?** Yes, and it's documented — in code comments and plan docs (`docs/superpowers/plans/2026-07-03-phase6-authoring-and-overlay-view.md:14`, `docs/session_layer_design.md:132`) — just not in `AI_LAYER_SPEC.md`.
5. **Verdict: Reason never written down.**
6. **The action.** Add a line to §1/§8a naming the two front doors and why; and move the link-kind guard into the shared write layer (`gsdo_objects.create`) so both paths inherit it and the flagged drift risk closes.

---

## BETTER THAN THE PLAN (two)

### B1. The plan force-shows every task somewhere — a deliberate honesty backstop worth keeping

1. **What the design wanted.** The spec's "still here, not today" list assumes the model reliably names every deferred item. Nothing enforced that.
2. **What is built.** A deterministic backstop, `_ensure_all_tasks_accounted` (`scripts/plan_generate.py:666-691`): after the plan is built, any active task the model didn't schedule *or* name gets force-appended to "still here" with a flag. Built directly after a real incident — a phone call, dinner, and a drive to SF all vanished from a generation with no error and no trace (commit `da98b5c`, "never silently drop an active task"; `memory/project_gsdo.md:214`).
3. **Does it solve the original problem?** Yes — it makes the plan honest about what's there. A duplicate mention costs nothing; a silent drop costs your trust that the plan is complete.
4. **Was this decided on purpose?** Very much so — commit message, memory record, and the function's own docstring all trace it to the 2026-07-02 incident.
5. **Verdict: Better than the plan.** Keep it. Note: the "wall of text" worry (all 82 items reaching the screen) is **not** this function's fault — it's the upstream selection gate being off, so everything counts as "active." The per-thread "next item · N more" rendering already planned fixes the volume; the honesty backstop should stay.
6. **The action.** Ratify it into the spec as the plan-honesty guarantee. Leave the volume fix to the selection-gate work.

### B2. The Focus Period layer is a better answer than the "rotation" it seems to replace — but it solves a different problem, so keep both in view

1. **What the design wanted.** The spec had no way to hold *which goals are in front right now*. The closest ideas were the temporal-lens "rotate the framing" move (`SYNTHESIS_design_time.md:101`) and a much later, still-unbuilt idea of rotating over Steady projects across days so they don't all compete (`docs/spec_reconciliation_selection_2026-07-11.md:37`). The "each will get its turn in the rotation" phrase you remember is neither — it's LLM flavor text (see H1).
2. **What is built.** The Focus Period object: a calendar plus a set of plain, Python-readable overrides for a stretch of time — which projects are foreground (elevated, planned first) or paused (dropped this stretch), workday bounds, days off, output shape, and a free-text note carrying what the stretch means. The period overrides a project's enduring engagement while active, then the default returns (`docs/focus_configuration_addendum.md`; `scripts/plan_generate.py:370-393`).
3. **Does it solve the original problem?** Yes, and better — it gives you an authored place to say "jobs are in front this week," which the spec genuinely lacked. Your instinct is right that this is better UX. **But** it is not the same thing as the deferred-items-come-back promise (that's H1, and it's broken), and it is not yet the "rotate over Steady threads across days" mechanism (that's still In Design — `docs/workstream_map_2026-07-11.md:25`). Focus Period is the *substrate* those would build on, not a replacement for them.
4. **Was this decided on purpose?** Yes — a full design session and addendum (session 23), already approved to fold into §2/§9.
5. **Verdict: Better than the plan.**
6. **The action.** Finish folding Focus Period into §2/§9 (already approved). Keep it clearly separate from H1 (make resurfacing real) and from the still-unbuilt Steady-rotation, so the good new layer doesn't get credited with solving problems it doesn't touch.

---

## Summary

| # | Divergence | Verdict | Next step |
|---|---|---|---|
| Q1 | Daily plan lives only in a local cache + overlay, never written to Anytype | Question for you | Mirror plan to Anytype, or accept cache-only? Ratify overlay-renders in §1; fix stale `daily_list.md:8` |
| Q2 | Morning push sends real task text through public ntfy.sh relay | Question for you | Keep content, or switch to content-free "tap to open"? |
| Q3 | AI-autonomous, Access notes, Due date, Relevant docs, Project desc/reaching-for are dead-ended | Question for you | Per field: wire the reader/writer, or drop from schema? |
| H1 | Plan promises deferred items "come back / get their turn"; resurfacing is broken 3 ways | Costs you | Make neglect-resurfacing real before promising it |
| H2 | Next-step mechanism is em-dash string-matching, fails silently; §8c unbuilt | Costs you | Make next-step a real field or build §8c |
| H3 | Multi-route survival plan lives nowhere durable; §8d never built | Costs you | Prioritize §8d / Goal-with-routes home |
| H4 | Countdown disc ("desperately" needed) + completion sound never built | Costs you | Build the disc (~30 lines); wire the sound to completion |
| U1 | Two capture front doors with a guard only on one; deliberate + mechanical | Reason never written down | Note it in §1/§8a; move link-guard to shared write layer |
| B1 | Force-append "everything is accounted for" honesty backstop | Better than the plan | Ratify as the plan-honesty guarantee; keep it |
| B2 | Focus Period layer (which goals are in front this stretch) | Better than the plan | Finish folding into §2/§9; keep separate from H1 + Steady-rotation |
