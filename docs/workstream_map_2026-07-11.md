# Controlled Drift — workstream map (reconstructed 2026-07-11)

*Built from a three-way sweep (design docs, session memory + logs, code) + the live Anytype tree.
This is a **point-in-time reconstruction** — June's own conclusion this session is that the map
should become **a live function of the Anytype system** (agent-facing), not a doc rebuilt from
stale sources. Until that's built, this is the current snapshot. Grouped by status; the cracks
first, because those are what "fell through."*

## Fell through the cracks (named, so they stop being invisible)
- **Wins mirror** (daily + project) — reflect June's actual accomplishments back, capacity-relative
  ("went on a walk, couldn't a week ago"). The most cleanly *lost* thread: named early
  (`AI_LAYER_SPEC.md §8g`, `map_and_arc.md`), then in **zero** session trails. Sits in Anytype as
  "Time visualizations and wins display" — **Backburner**.
- **Learning loops (the interpretation layer)** — scattered across a "Pattern-learning loop"
  (Backburner), a "Learning loops design" filed under *GRA* (Backburner), and a written but
  un-handed-off plan (`docs/superpowers/plans/2026-07-02-learning-loops-v1.md`). Capture/logging is
  built; the loops that *read* the logs to adapt are deferred. That split is how it went invisible.
- **Balanced prioritization across streams over time** — "the deep methodology question"; a
  selection engine that rotates through projects over days→weeks, not just today's subset. In Design
  since session 17, untouched. May be the same need as nonlinear routing.
- **Nonlinear→linear map routing** — "the one true machinery gap"; nonlinear work should route to
  the map, not have the planner guess a next item. Marked Active in Anytype, never started.
- **Stuck-support mode** — genuinely undesigned; two case-data points (sessions 15, 22), parked-by-
  design ("don't force it"), untouched since.
- **Spoon-accounting parameters** — the multi-axis, learned-from-data spoon model
  (`docs/open_thread_spoon_accounting.md`). Backburner; its own design session owed. *Note: today's
  capacity→strategy work is a lighter path toward the same need — see [[flow-model-design-thread]].*
- **Calendar integration** — real Apple-Calendar read, to plan around appointments. Flagged "move
  up" at session 15, never moved. (The Focus Period "calendar module" is a different thing.)
- Others surfaced: project-level abstraction in the overlay; park-system migration; "plan silently
  drops unnamed tasks"; the Claude-facing protocol index; system-wide plain-language enforcement.

## Active (moving)
- **Focus-configuration → Phase 6** (overlay authoring + "see my week"). Phases 1–5 built; Phase 6
  Task 1 decided (Option B — fold into Today); Task 2 (`GET /api/period` / `period_view`) in progress
  right now (parallel work).
- **Orientation map / arc** — built (Steady) and served in the Map tab; but the plain-language
  renderer rebuild is still owed (the current one uses superseded encoded glyphs).
- **Log Day** — designed, folded into Phase 6, not yet built.

## Built + shipped
Data model (5 types); Anytype write layer; folder binding + Orient + Sweep; clock scheduling;
weeding/capture pipeline; daily-plan pipeline; ambient overlay + morning push + phone access;
mark-done + undo; async generate-and-poll; pluggable backends (Mistral default); break logic;
open-hobby-block; **hobby-out-of-plan + Settings toggle (2026-07-11)**; **capacity→strategy
(2026-07-11)**; monthly recurrence; access tags (read-bug fixed 2026-07-11); daily memory pass
(core); focus-config Phases 1–5; learning-loop *logging* (not the interpretation loops).

## Outlined, downstream (not lost, just later)
Phase 7 (obligation check-in + under-rest by 7-types-of-rest, cross-day); Phase 8 (staleness
rollover + day-off-vs-deadline conflicts); 7-types-of-rest cross-day tracking; open-hobby-block
refinements.

---
*How to use this: ask a fresh agent "walk me through the workstream map, one group at a time." The
durable fix is to make this a live Anytype query — see the "Agent-facing protocol surface" project.*
