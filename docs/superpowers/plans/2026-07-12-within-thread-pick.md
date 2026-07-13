# Within-thread pick signal — daily plan (2026-07-12)

**Scope:** bounded. The selection gate now collapses each surfacing Steady thread to ONE item,
but *which* item is still whatever Anytype storage order happened to be (a stable-sort accident
of the old date-hash era). This replaces that accident with a real, honest signal.

**Design source of truth:** `docs/spec_reconciliation_selection_2026-07-11.md` — Output section
("Picked-within-project by a real signal we already have — nearest deadline, else
least-recently-surfaced — labeled honestly 'next in X · N more', never a hash") and "what the
code must do" item 4 ("Within a project, pick the one surfaced item by deadline →
least-recently-surfaced; label 'N more'").

## What already exists (verified fresh, 2026-07-12)

- **Task `Due date`** = the built-in `due_date` property (`build_task.py`; the *deadline*
  field, distinct from `Scheduled` = "start considering on/after"). The task loader in
  `daily_plan.load_active_items` reads duration/affect/access/blocked/context/linked_projects
  but **never reads `due_date`** — the gap this closes.
- **Project `Deadline`** = `gsdo_deadline`, already loaded at `daily_plan.py:95` as `deadline`,
  then **dropped** — nothing downstream reads it (the audit's deadline-drop finding).
- **Per-task surface history** = `surface_log.surfaced_dates()` (id → most-recent surfaced
  datetime) and `effective_last_surfaced(...)` — the shared staleness resolver (landed today).
- **The collapse** = `plan_generate._gate_and_collapse`: hide gate (Backburner/Open/unset)
  then "first task seen per thread wins." No test locks its representative choice (checked).

**Live reality (read-only probe, honest):** 0 tasks have `due_date`, 0 projects have
`deadline`, 0 have `Scheduled` populated today; the surface log holds 102 tasks with history
(2026-06-18 → today). So the **deadline tier is wired-but-dormant** and **least-recently-surfaced
is the active differentiator** right now. Wiring the deadline tier is correct + future-proof;
it simply degrades to the surface tier until June authors deadlines. Report this honestly.

> NB the parent brief said "`Due date` is written at capture" — capture actually writes
> `Scheduled` (start-considering), not `Due date` (deadline). `Due date` is authored by June, not
> capture. This doesn't change the build (load + rank the deadline field), only the honesty of the
> live report. Noted, not silently absorbed.

## The pick signal (deterministic, pure-testable)

Per thread, among the tasks that survive the hide gate, pick ONE by:

1. **Nearest deadline first** — effective deadline = task `due_date`, else the project's
   `Deadline` (the reconciliation's "task due, then project deadline as tiebreak"). Since every
   task in a thread shares one project, the project deadline can't differentiate *between* a
   thread's tasks — it acts as the thread's urgency *floor* when no task has its own due date.
   Tasks with any deadline rank ahead of tasks with none.
2. **Else least-recently-surfaced** — oldest `surfaced_dates` entry first; a never-surfaced task
   is maximally stale, so it sorts first.
3. **Else the current stable order** — `min()` over candidates-in-given-order is stable, so ties
   fall back to exactly today's ordering. No hash.

## Tasks (per-task commits)

1. **Plan doc** (this file) — commit.
2. **Load `due_date`** in `daily_plan.load_active_items` task dict + a small date parse helper is
   in plan_generate (below), so loader just stores the raw Anytype date value. Test: a task with a
   `due_date` prop loads it.
3. **Pure pick helpers** in `plan_generate.py`: `_parse_date(raw)` (tolerant Anytype date →
   `date`), `_pick_within_thread(candidates, proj_deadline_raw, surface_dates)` → chosen task.
   Tests: deadline beats surface; earlier deadline wins; project deadline as floor; oldest-surface
   wins when no deadline; never-surfaced wins; stable fallback on total ties.
4. **Restructure `_gate_and_collapse`** to two passes: (a) hide gate → survivors (unchanged
   logic); (b) per-thread pick the winner via `_pick_within_thread`, emit the winner as the
   thread's one move; forced (`extra`-named) tasks and no-project tasks pass through exactly as
   now. Accept `surface_dates` param (injectable, defaults to the live log) for pure testing.
   Set `held_back` (int, count of same-thread survivors not shown) on each surfaced task, named
   clearly, on the returned list. Wire `surface_dates` in `build_context`. Tests: winner-by-signal;
   forced still through; no-project not collapsed; held_back count correct.
5. **"N more" reaches the LLM context** — in `_build_task_refs`, append `· N more in this thread`
   to a task's reference line when `held_back > 0` (one edit, reaches BOTH clock + priority
   shapes' prompts; the queued renderer thread consumes `held_back` from the payload). Optionally
   one honest clause in the ref-table intro that each day's item is its thread's next-due /
   longest-quiet move. Do NOT build the renderer. Test: line carries the count.

## Explicitly NOT touched (per brief)

Hide/shown gate logic (fresh, June-approved), force-append accounting
(`_ensure_all_tasks_accounted`), the overlay (another agent is in it now), scheduler,
capture files, `select_and_order_tasks` (cross-thread ordering stays; this is within-thread only).

## Verify

Full suite green (baseline 467). Live verify READ-ONLY: call the pick functions directly against
live data for 3–4 real threads, report which item is now picked + WHY (deadline vs
least-recently-surfaced vs fallback) vs. which the old first-in-storage-order would have picked.
Do NOT generate a plan (June's authored tomorrow plan must stay untouched). Cross-family review
chunked, triage, fix real findings. Update the Anytype task "Within-thread pick signal and
per-thread rendering" Context (do NOT mark done — rendering remains).
