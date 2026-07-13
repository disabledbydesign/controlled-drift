# Handoff — daily-plan engagement-gate fix + open threads (2026-07-12)

Audience: the orchestration agent wiring/integrating the system. This covers one shipped fix and the threads it opened or touched. Branch: `feat/overlay-actionable` (shared/hot — commit only your own files).

## What just shipped (do NOT redo or re-edit without coordinating)

**The daily-plan selector now gates by `engagement`** — the core fix for "June stopped using the plan; too overwhelming on open." The build had drifted from `AI_LAYER_SPEC.md` §2/§9 (spec always said "Steady → one move; next item per thread, never the pile"); the selector was surfacing *every* task, ordered by a date-hash, with `engagement` only hinted to the LLM, never deterministically gating.

- Commits: `e944e9f` (diagnosis + reconciliation + spec merge), `6b25581` (code).
- Files: `scripts/plan_generate.py` (new `_gate_and_collapse` + `_match_extra`; called in `build_context` right after `partition_by_side`; `extra` threaded from `generate_plan` + `reorder`), `scripts/build_project.py` ("Open" added to Engagement select — **applied to live space**), `tests/test_plan_generate.py` (mock signature fix).
- Behavior: default plan = one next-move per thread; Backburner/Open/unset hidden unless foregrounded or (Backburner/unset) neglected; Steady → one move. A task named in `extra` ("put X in today") is force-included as a real move (never relegated to still_here). Held-back tasks are NOT dropped — they live in Anytype, just not in today's plan.
- Verified live (read-only): 82 active → **12 next-moves**; explicit requests pull the named task in even when collapsed. **387 tests pass.**

## Source of truth — read before touching selection / engagement / plan output

- `docs/spec_reconciliation_selection_2026-07-11.md` — **canonical** for the selection design: the three-layer model (engagement grain gate / Focus Period phase-lens / three-way Side), the explicit-request override, "what the code must do," and the parked items. Reflects June's decisions.
- `docs/structural_diagnosis_2026-07-11.md` — root-cause with file:line evidence.
- `AI_LAYER_SPEC.md` §2 (see the "⟳ Selection model reconciled 2026-07-11" callout) + §9 pointer — spec is accurate again.

## Definition-of-done for the fix to *fully* land (not code)

1. **A current Focus Period must be authored** (the last one expired Jul 6). Without an active period there's no foreground, so the 12 moves are in un-prioritized order. Authoring UI = the focus-slot / Phase-6 thread.
2. **Server restart** — `launchctl kickstart -k gui/$(id -u)/com.june.controlled-drift.server`. Needs June's go (kills a running process). Until then nothing reaches her phone.

## Open threads (state + dependencies, for sequencing)

| Thread | State / where | Depends on |
|---|---|---|
| **Agentive-dialogue surface** (proactive propose→respond→log) | NOT built. Partial: overlay negotiate + ask field + `/drift` chat. Foundational — the next three assume it. | — |
| **Engagement/affective upkeep loop** | Design done (reconciliation doc): Strategy-driven proposals + response-logging + elapsed-time tracking (partly built: `Task.last_surfaced`, `neglect.py`). Strategy rules named in the doc. | agentive-dialogue surface |
| **Affective input via `/drift`** | Storage exists (`affective`/`engagement_notes` on Project, read by the plan). Needs update-vs-create in the capture path (the weeding-dedup shape). **Overlaps the capture-writes work** — coordinate. | capture path |
| **Neglected-*task* surfacing** | = a Strategy + the shared elapsed-time mechanism. | upkeep loop |
| **Route-prioritization (§8d) / survival-plan-as-Goal-with-routes** | Unbuilt. Spec's answer to where June's multi-route survival plan lives. Open sub-question (§10): explicit route-condition fields vs. free text. High value. | multiple Projects existing |
| **Wellbeing Side handling** | Third Side value; meaning settled (health/body/care: exercise, medical, self-care — first-class rest, distinct from Fun-hobby). Plan behavior NOT wired. Lives near `daily_plan.partition_by_side` + plan output. | — |
| **Sprint→foreground migration + option cleanup** | Sprint retired by design (→ foreground); Hyperfixation retired (→ qualitative). 1 project still tagged `Sprint`; migrate. Eventually remove both options from the Engagement select. | — |

## v1 refinements of the shipped code (safe as-is; tighten later)

- `_match_extra` is a lenient token match — can over-surface (naming "cuff order" pulled in all cuff tasks). Errs toward inclusion (safe direction June chose).
- Foreground currently yields one move per thread; Sprint/foreground getting more real-estate + "rotation over Steady threads each phase" is a later build (mechanism noted: foreground *activates* a Steady project).
- No-project discrete-task handling (surface each, never collapse) is untested at volume — 0 in June's data now.

## Hazards / coordination

- **Pre-existing test failure** `tests/test_capture_when.py::test_capture_writes_scheduled_and_marks_today` — fails on a clean checkout (verified via stash), in the capture-writes area (commit `1edbfe1`). NOT from the selection fix. The capture-writes agent should own it.
- `build_context` / `select_and_order_tasks` are now the reconciled version — coordinate before re-editing.
- Do not touch the LLM plan contract / `format_priority_list` for this fix — it deliberately does NOT need those (the gate is pure-Python; still_here empties on its own because `_ensure_all_tasks_accounted` only sees the gated set — kept, not deleted, so it still guards the 12 real moves).
