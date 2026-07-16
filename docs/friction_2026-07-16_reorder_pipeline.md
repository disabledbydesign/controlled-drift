# Friction log — reorder() pipeline, live-caught 2026-07-16

*Found while pushing a chat-negotiated daily plan (survival/prep day for the SF move) through
`plan_generate.reorder()` — the same function the overlay's negotiate buttons call. Two distinct
problems surfaced. One is fixed (with a live-verified regression test); one is still open and
needs a real design pass, not a quick patch.

## 1. FIXED — overdue Recurring anchors could vanish with no trace

**Symptom (live, reproduced):** a `reorder()` call correctly dropped the mailing/grocery items
into place, but three real Recurring chores — **Do the dishes**, **Clean the kitchen**, **Clean
the toilet** — disappeared from the output entirely. Not scheduled, not in `still_here`, no error,
no log line pointing at them. Identical shape to the 2026-07-02 task-drop incident
(`_ensure_all_tasks_accounted`'s regression) and the 2026-07-13 repeat — except this time the
dropped items were Recurring anchors, not Tasks, which turned out to be a blind spot that
guard never covered.

**Root cause** (`scripts/daily_plan.py :: build_schedule`, `scripts/scheduler.py :: schedule`):
- An anchor whose `fixed_time` has already passed relative to the plan's `start_time` (e.g. a
  "Do the dishes at 09:00" chore, planned at noon) is deliberately demoted to a **flexible** item
  by `build_schedule` so it can float into the current queue — labeled `"(was 09:00)"`. This is
  intentional and documented ("Past scheduled time ≠ done").
- But once demoted, that item is just another flexible item to `scheduler.schedule()`, which stops
  placing flexible items once its cursor reaches `end_time`. A full day (or a tight window) can
  push the cursor past `end_time` before the anchor's turn comes up — and `schedule()` just drops
  it from the output. No fallback.
- `plan_generate._ensure_all_tasks_accounted` — the existing deterministic backstop for exactly
  this class of bug — only ever iterated `tasks`. `all_anchors` (Recurring chores) was never in
  its scope, so there was no net under the *other* always-eligible item kind.

**Fix** (`scripts/plan_generate.py`): added `_ensure_all_anchors_accounted(plan, all_anchors)`,
the anchor counterpart to `_ensure_all_tasks_accounted`, wired into `_retime_clock_plan` right
after the existing task-accounting call. Same deterministic set-difference pattern, same
still_here fallback. Synthesized anchors with no real `id` (default meal placeholders) are
skipped — nothing real to lose track of.

**Verified, not just tested:**
- `tests/test_plan_generate.py` — 4 new tests (2 unit tests on the guard function, 1 unit test
  for the already-covered case, 1 regression test reproducing the exact end_time-overflow shape
  via `_retime_clock_plan` directly). Confirmed the regression test **fails without the fix**
  (reverted the wiring line, reran, watched it fail) and **passes with it restored** — so it's a
  real regression guard, not a tautology.
- Full suite: 621 passed, 0 broken.
- Live run against real Anytype data + the real Mistral backend (scratch `CD_CONFIG_DIR`, June's
  actual overlay cache untouched): re-ran a `reorder()` call shaped like the one that dropped the
  three chores. This time all three landed in `still_here` instead of vanishing. Confirmed the
  real overlay cache (`~/.controlled-drift/current_plan.json`, served live on `:5050`) was
  unaffected by the scratch run.

## 2. OPEN — freetext has no channel for a hard constraint

**Symptom (live, reproduced):** asked `reorder()`, in plain freetext, to (a) not schedule anything
before 12:00pm and (b) not schedule the full 120-minute recurring walk as a separate block. The
model's output ignored both — it scheduled outside-the-house errands at 11:00, and kept the full
walk as its own block.

**Why this isn't a quick fix:** everything June says in a `reorder()`/`generate_plan()` call —
"nothing before noon," "quick wins first," "I'm stuck, one small step" — goes into the prompt as
**freetext appended to `extra`** (`plan_generate._assemble_prompt`). The prompt has no way to
distinguish *"strong preference, please weight this heavily"* from *"literal constraint, do not
violate."* Both render as prose the model can (and sometimes does) deprioritize against its own
judgment about what the day needs. There's no structural equivalent of `start_time`/`end_time`
(which **are** hard, Python-enforced boundaries, computed before the model ever runs) for a
one-off request like "don't start before noon today."

**What a real fix would need** (not designed here — flagging for its own pass):
- A way for `reorder()`/`generate_plan()` to accept an **explicit start_time override** parsed
  from June's request (or a UI control), so "not before noon" becomes the same kind of
  Python-enforced boundary `start_time` already is — not a prompt suggestion.
- Some notion of a **hard constraint** distinct from a framing preference, in the JSON contract
  the model fills out (e.g. an explicit `honored_constraints` acknowledgment field, or a
  post-generation deterministic check that re-validates the output against a small set of
  structural asks and retries/corrects if violated — same shape as the zero-ref retry guard
  already in `generate_plan`).
- This connects to the already-logged **irregular-cadence / multi-phase task** gap (the
  `Multi-phase task support (e.g., laundry)` open thread) — "start the wash, deal with it later"
  is the same kind of thing: a single chore that's actually two time-separated steps, which the
  data model and the prompt contract don't represent today.

**What happened today instead:** the negotiated plan was hand-verified against the real overlay
cache rather than trusted from the automated pipeline's first pass — see the handoff in the
2026-07-16 session. That's a one-time workaround, not a systemic fix.
