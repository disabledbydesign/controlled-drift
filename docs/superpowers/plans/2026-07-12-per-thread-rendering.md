# Per-thread stream rendering for the daily plan (2026-07-12)

Final item (5) of the reconciled selection model (`docs/spec_reconciliation_selection_2026-07-11.md`,
Output). The pick half landed earlier today (`_gate_and_collapse` collapses each thread to ONE
item by an honest signal, and records `held_back` = count of same-thread items not shown). This
half renders those collapsed threads as **named streams with an honest "· N more"**, and retires
the flat global "still here (N)" pile in favor of per-thread N-more.

Accessibility parameter (AI_LAYER_SPEC ~L375): named streams ARE the accessibility mechanism; a
flat all-tasks list is cognitively inaccessible. All June-facing copy stays in plain words (no
metaphors).

## What's already true (verified, don't rebuild)
- Gate collapses to one item/thread; each surfaced task carries `held_back` (int count). Reaches
  the LLM task-ref table as "· N more in this thread" text.
- `_ensure_all_tasks_accounted` sees only the *kept* (gated) set — so held-back items never enter
  still_here as a pile. It guards just the real moves against a silent model drop. RATIFIED — adapt,
  never delete.
- Overlay groups by project (`groupByProject`/`renderGroup`), has summary rows + a task drill-down,
  when-chips, move affordance, plan-age line. After collapse each thread = 1 item → `renderFlatItem`.

## The build

**1. Payload (plan_generate.py).**
- `_gate_and_collapse`: alongside the `held_back` count, record `held_back_names` = the names of that
  thread's not-shown survivors (so the drill-down can list them). Count unchanged (tests depend on int).
- `_resolve_ids`: thread `held_back` (count) + `held_back_names` onto each plan item by task id — same
  mechanism as `description` (Python owns the id→data map; the LLM only echoes a ref token). Held-back
  data reaches the cached plan JSON this way, not via the LLM body.
- `_ensure_all_tasks_accounted`: unchanged behavior (only sees kept set → no pile). Held-back items are
  accounted for by their thread's N-more entry on the surfaced item, not as a global still_here row.

**2. Prompt (prompts/daily_list.md).** Minimal edits: each scheduled item is its thread's one next
move rendered inside its named stream; the LLM must NOT enumerate a thread's other (held-back) tasks
in the body or in still_here — the surface shows "· N more" automatically from data. still_here is only
for genuinely thread-less / blocked-waiting items. Keep the honest framing already there.

**3. Overlay (docs/overlay_daily.html).**
- `renderFlatItem` + `renderPriorityItem`: when `item.held_back > 0`, show "· N more" after the project
  name; the row (already toggles `.open`) reveals the held-back task names on expand — reuse the existing
  expand pattern/CSS, don't duplicate the checkboxed drill-down (held-back items are not today's moves,
  so no checkbox).
- still-here section: drop the global `(n)` count from the label; render only the rows the payload
  carries (now genuinely thread-less items).

**4. Goal › Project grouping.** Projects in the payload carry `parent_project_id` but NO goal link — a
project's goal name does not drop out of current data. FOLLOW-UP, not this pass: to render "Goal ›
Project" the loader must resolve each project's parent goal name. Noted here; out of scope.

## Verify
- Suite green (baseline 489); new tests for held_back_names + resolve threading; per-task commits.
- Cross-family review chunked, triage, fix real.
- LIVE: restart server, POST /api/refresh (today's plan is past its hours; tomorrow's 9am push untouched),
  verify in the served overlay — streams render with N-more, no flat global pile, every gated-in task
  appears once and every held-back item sits inside exactly one N-more. If structurally wrong, revert
  the renderer and report BLOCKED rather than ship a mess for tomorrow.
- Close out the Anytype task "Within-thread pick signal and per-thread rendering" (this half completes it).
