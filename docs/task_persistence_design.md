# Task persistence (unfinished items stay until done) — design

**Status:** design SETTLED with June 2026-07-17, approved to build. Not yet built.
Sits alongside `docs/as_needed_reactivation_design.md` — both use the same "surface every day until
done" rail. Replaces the current LLM-narrated "carried over from yesterday" rollover behavior.

## The core behavior (June's words)
Unfinished things should **just keep showing up on the todo list until done** — silently, without the
system announcing "here's what you didn't finish yesterday." June doesn't want to keep re-telling the
system to bring a task back; an unfinished item persists on its own.

> **surfaced + not completed → stays on the list every day until completed → done → stops.**

This is already how one-off tasks behave (an unfinished one returns the next day). The decision extends
the same rule to scheduled recurring chores, so the whole system is consistent: **unfinished = still on
the list.**

## Persist by default, with two exceptions
Persistence is the **default for every task.** Two kinds of task do NOT persist:

1. **Tasks that recur every 1 day (daily cadence).** A daily task is re-surfaced every day by its
   cadence anyway, so persistence is redundant for it — exempt it from the carryover mechanism, so a
   missed daily chore is simply due again tomorrow, not double-handled as "carried over."
2. **Tasks with the opt-out flag set** — a per-task "let this go if I miss it" boolean. The clear case
   is weekly therapy: miss this Tuesday and it should NOT sit on Wednesday's list; it waits for its next
   cadence. Most tasks should persist, so the flag is an **opt-out** (default = persist), not an opt-in —
   June doesn't have to tick a box on everything to get the behavior she wants.

## No LLM narration of carryover
Today the planner is handed a labeled "## Carried over from yesterday (not marked done)" list and asked
to decide what carries forward (`plan_generate.py:759-766`). That framing is **removed.** Persistence
becomes a plain, deterministic rule — an unfinished item stays in the active set and surfaces like any
other item, with no "you didn't finish this" narration. Two benefits: (a) more predictable (no LLM
adjudication of what carries), and (b) it removes the false "you didn't finish this" signal on a chore
that was actually done (see the completion-recording fix below).

## The enabling change: record recurring completions
Today a recurring task's "done" is a **local cache day-flip that is never written to the durable
completion record** (`server.py:446-450` returns without calling `completion_log.log_completion`). So
the rollover cannot tell a done recurring from an undone one, and falls back on a cadence-shaped proxy
("is it in today's active pool?") — which mislabels a completed daily chore as unfinished carryover.
**Fix:** record a recurring completion for its day, so the planner's picture of "what was actually done"
is honest and persistence reads real done-state instead of guessing from cadence.

## Mechanism note — shared rail with as-needed reactivation
"Keep surfacing every day until done" is the *same* surfacing behavior the as-needed reactivation
feature builds (an active as-needed task surfaces daily until completed). Persistence is a new **control
over that rail, not a new mechanism.** The entry trigger differs (as-needed: June asks for it;
scheduled-persist: a due instance goes uncompleted), but "surface daily until done" is one shared
behavior, and "done stops it" is one shared rule.

## Explicitly out of scope (for now)
- The as-needed on/off feature itself — its own design doc (`as_needed_reactivation_design.md`) + plan.
- Any change to one-off rollover beyond dropping the LLM-narration framing (the `6ca7ce6` active-state
  filter stays; this design layers real recurring completion state onto it).

## Grounding note for the builder (reason from function, not doc-text)
The rollover candidate set is assembled in `plan_generate.build_context` (~:632-634) via
`plan_snapshot_log.undone_yesterday()` + `_filter_rollover_to_active` (the cadence-shaped active-pool
proxy this design replaces with real completion state). Recurring completion routing is
`server.py:436-469`. Verify by driving the REAL plan, not tests alone: complete a daily recurring and
confirm it is NOT relabeled "carried over"; miss a weekly persist-task and confirm it keeps surfacing
each day until done; miss a therapy-type opt-out task and confirm it waits for its next cadence. (Repo
build-frame guard.)
