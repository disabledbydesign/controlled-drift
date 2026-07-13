# Orchestrator flags — 2026-07-11 (verified findings each in-flight thread needs)

**What this is:** a 5-agent survey (open discovery, wiring audit, adversarial verification of today's diagnosis docs, capture audit, docs inventory) ran on 2026-07-11, checking every claim against the live working tree and the live Anytype space. These are the findings that change what each in-flight thread should build. Every claim below was code- or live-data-verified; file:line anchors included. **If you are an agent working one of these threads, read your section before writing code.**

Reliability grades on today's diagnosis docs (from the adversarial verification):
- `docs/spec_reconciliation_selection_2026-07-11.md` — **fully verified** (every factual premise confirmed against live counts). Safe baseline.
- `docs/cram_selection_diagnosis.md` — verified, holds.
- `docs/structural_diagnosis_2026-07-11.md` — good field inventory; WRONG on: the two "read bug" claims (Goal `reaching_for` reads fine under `gsdo_reaching_for_(text)`; "Goal engagement" exists live, it's just unpopulated on 7/8 goals), the Side/Wellbeing section (describes pre-rework two-category code), and the "one cause" frame (at least nine verified independent causes exist).

---

## Thread: selection/engagement rewiring (step B of the spec reconciliation)

1. **Neglect-resurfacing is non-functional end to end — do not build "hidden unless neglected" on it as-is.** Three independent breaks: (a) `Last surfaced` is written only by the interactive CLI confirm path (`daily_plan.py:718-723,819`) which June doesn't use — live: 5 of 137 tasks have the field, none newer than 2026-06-18; (b) `neglect.py:21,47-57` has no Done/Parked status filter; (c) the display filter at `daily_plan.py:385-390` checks a key `query_neglected` never returns — unreachable code. If the gate ships against this, "put away" silently becomes "gone." Fix candidates: write `Last surfaced` on the overlay/morning path where `log_surfaced_batch` is already called (`plan_generate.py:770`), or point neglect at `scripts/data/surface_log.jsonl` (1,617 records, current through today).
2. **Capture pre-loads the flooding the gate closes:** every captured Project gets hardcoded `Engagement="Steady"` (`capture_generate.py:260`; also `gsdt_bind.py`). Unless the default moves to Open/unset in the same change, the day re-crowds one captured project at a time and the fix will look like it regressed.
3. **Rendering is a co-equal cause, not a follow-up.** `_ensure_all_tasks_accounted` (`plan_generate.py:666-691`) force-appends everything the LLM omits, so all 82 items reach June's screen regardless of selection. The per-thread "next item · N more" rendering (reconciliation Output section) must land WITH the gate or the visible volume barely changes.
4. **"Unset → Backburner-equivalent" hides 16 more obligation tasks** (verified live count). Confirm with June that's intended before shipping.
5. **No focus period is active today** — the entire current order is the date-hash. Whatever you build, define lapse behavior (the keystone signal currently degrades silently).
6. **15 of today's 39 schedulable tasks link to no project** — project-level engagement gating can't reach them. Decide their handling explicitly (they are why "unlinked" ordering exists in `select_and_order_tasks`).
7. **Adjacent one-line key bugs in files you own** (fix while there, or explicitly decline): `daily_plan.py:137` reads `gsdo_status`, live key is `gsdo_strategy_status` → status filter is a no-op, all 12 Strategies fire every day including retired ones; `daily_plan.py:92` reads `gsdo_reaching_for`, live key is `gsdo_reaching_for_(text)` → always None; Project `Deadline` is loaded (`daily_plan.py:95`) then dropped — `_project_line()` never includes it.
8. Line-number staleness: `select_and_order_tasks` is now at `plan_generate.py:370-393` (diagnosis docs say 318-341).
9. **(added 2026-07-12, June's decision)** Task `Due date` should be LOADED and used as the within-project pick signal — the reconciled model's "nearest deadline, else least-recently-surfaced" needs it, and today the plan path never even loads it (`daily_plan.py` loader). Project `Deadline` is loaded then dropped by `_project_line` — same fix family. June decided wire-don't-drop for these fields.

## Thread: capture-when → regenerate-today flow

1. Sequencing confirmed by verification: no payoff until the selection fix lands (regenerate rebuilds a crammed day). No code collision found — different files.
2. **If you touch the weeding-gate JSON contract to add `when`, coordinate with the pending capture-writes thread** (see below) so the contract changes once, not twice. The highest-leverage co-rider: a per-item `duration` read (fixes the flat-30-minute default that currently shapes nearly every scheduled block — live: 2 of 82 candidate tasks have a duration).
3. `memory_pass.py:394-435` is a third, independent copy of the capture write-pattern. Any contract/field change must land there too or the paths diverge further.

## Thread: status-checker (plan at docs/superpowers/plans/2026-07-11-status-checker.md)

1. Correction to the handoff: `neglect.py` is NOT never-run scaffolding — it is on the live plan path (`plan_generate.py:408`). What's dead is its INPUT (`Last surfaced`, see selection flag #1). The checker's staleness evidence must not trust `Last surfaced` as-is; `surface_log.jsonl` is the current data.

## Proposed thread (not yet launched): capture-writes fix

The capture audit confirmed June's hypothesis: both capture paths (plus memory_pass) write at most 3 of a Task's 14 fields / 3 of a Project's 16 — one hardcoded, one a repurposed reasoning string. Ranked fixes: (1) ask+write `Duration min`; (2) persist the already-inferred `capacity_read` to `Affective` instead of dropping it (`capture_generate.py:239,387` — inference exists, persistence doesn't); (3) prompt-notice `Blocked on` / `Access conditions` (readers already wired, starved at 1%/29%); (4) the update-vs-create gap (nothing recognizes "new information about an existing thing" — design conversation, not a patch); (5) dead-on-both-ends fields (AI autonomous, Access notes, Task Due date, Relevant docs, Project Description/Reaching for) — decide build-reader-or-drop before writing to them.

## General

- Nobody has touched `plan_generate.py` / `daily_plan.py` in the uncommitted work — the selection thread has a clean tree.
- Uncommitted work is accumulating (memory_pass.py +205, AI_LAYER_SPEC.md banner, flow_model_design_thread.md, several untracked docs) — commit at your thread's next logical checkpoint.
- The in-repo `skills/drift/SKILL.md` mirror (Jun 22) is behind the live global `~/.claude/skills/drift/SKILL.md` (Jul 11).
