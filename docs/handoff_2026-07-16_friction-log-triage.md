# Handoff — friction log location + first triage (2026-07-16)

*For the next agent picking this up. Read this before touching anything called "friction log" —
there are two different things with that name in this repo and confusing them wastes a round.*

## STATUS — session 4 (2026-07-17): entire backend list CLOSED except infra

Continued the backend triage with June, one item at a time, her OK before each build (same
discipline as session 2/3). All landed on `feat/overlay-actionable`, 714 tests green.

1. **NEW entry, not in the original triage — "created two tasks I'd already finished as
   uncheckoffable items" (2026-07-17T09:17) — ✅ FIXED.** Traced via completion_log +
   plan_snapshots: not a duplicate-creation bug — `undone_yesterday()`'s rollover-candidate check
   only recognized a completion dated exactly the prior calendar day, so a task finished the
   NEXT morning (after its original plan_date) still read as "not marked done" and kept getting
   offered as a rollover candidate on every regeneration that day — the model would name it, but
   it couldn't resolve to an id (correctly excluded from the active pool by then), producing a
   same-day ghost row with no checkbox. `plan_generate._filter_rollover_to_active` checks the
   CURRENT active pool instead of trusting a date window. `scripts/plan_generate.py`, commit
   `6ca7ce6`.
2. **A calendar event isn't loading for today (2026-07-16T09:31) — ✅ FIXED.** Traced to the real
   incident: "Therapy" (a real timed Recurring anchor, due that Wednesday 11:00) was entirely
   absent from a fragmented/priority-shape plan — not scheduled, not in still_here, nowhere. Root
   cause: `format_priority_list` never looks at timed anchors at all, and the anchor-accounting
   guard (`_ensure_all_anchors_accounted`, added session 3) no-ops for priority shape. Fix: a new
   top-level `plan["appointments"]` field, Python-owned, built from today's timed recurrings
   independent of shape — a real appointment always lands somewhere real and checkoffable
   regardless of clock vs. priority day. `scripts/daily_plan.py` + `scripts/plan_generate.py`,
   commit `33f81ce`. **Frontend companion still open** — logged as an Anytype task under Build
   Controlled Drift ("Build the overlay's pinned Appointments section"), not built this session
   (backend only).
3. **Leatherworking scheduled twice — ✅ CONFIRMED already fixed, no code change needed.**
   Checked all three of 07-17's real plan regenerations (09:00 morning, 09:02 and 10:36
   refreshes) — leatherworking/cuff-order appears exactly once each time, correctly deferred with
   a single still_here note. The 07-16 15:28 block-dedup commit (`25607f2`) has held on every real
   regeneration since.
4. **Plan text claims "low-EF first" while scheduling a high-EF task first (2026-07-16T09:32) —
   ✅ FIXED.** Traced to the real incident: the 07-16 09:00 woven frame said "starts gently—low-EF
   tasks first" while the first scheduled task carried the real `Involves-leaving-house` tag,
   already visible to the model in its own prompt context. `prompts/daily_list.md` now tells the
   model to check the real access tag before writing that kind of ordering claim. Commit
   `5d01f4c`.
5. **Leaving-the-house tasks aren't clustered (2026-07-16T12:25) — ✅ FIXED.** Builds
   `AI_LAYER_SPEC.md`'s documented-but-never-shipped "errand-batching" (line 210) — the
   `Involves-leaving-house` tag was only ever read at capture time. Two independent bugs, both
   confirmed against the real 07-16T12:20:03 incident: (a) `_compute_break_anchors` is
   duration-blind and wedged a break between two already-adjacent mail errands purely on
   crossing `BREAK_WORK_MIN`; (b) nothing clustered same-tagged tasks adjacent in the first
   place. Fixed both, scoped to exactly the one tag AI_LAYER_SPEC names — the deeper multi-tag
   spoon-cost batching stays parked in `docs/open_thread_spoon_accounting.md` for its own
   design session, per June's explicit call. Commit `5d01f4c`.
6. **Server reachable only on WiFi — NOT addressed, infra not app logic.** Out of scope for a
   backend code session; still open if June wants to pursue it.

The only backend item from the original 07-16 triage left genuinely open is #6 (infra). Every
other backend entry — including the pre-session-2 ones — is now closed. Frontend items remain
untouched (June scoped every session in this triage to backend only); the Appointments-field
render is the one new frontend follow-up this session generated.

## STATUS — session 2 (2026-07-16 evening): 4 backend items CLOSED, live-verified, tested

Went through the backend list below with June, one item at a time, her OK before each build.
All landed on `feat/overlay-actionable`, 682 tests green, non-Claude cross-family review run per
file (see per-item notes for what was applied vs. skipped as noise). Frontend items untouched —
June scoped this pass to backend only. Details on each fix are in the commit(s); this section is
the map-status update so the next session doesn't re-diagnose what's already closed.

1. **Focus-authoring overrides stated input (the 5-entry cluster) — ✅ FIXED.**
   `scripts/focus_period_generate.py`: removed the literal "survival-first" priming phrase (it was
   in the prompt TWICE — the model was echoing it regardless of what June actually said); replaced
   with an instruction to ground `intent` in her own words. Also gave the authoring prompt real
   visibility into her Goals and a filtered discrete-Tasks list (reusing `daily_plan.load_active_items`
   + `grain.classify` — the SAME filter the real daily plan uses — so it's grounded in her actual
   structure instead of inventing generic framing, and doesn't leak dev-backlog task names). This
   also covers the "packing got dropped" entry — it's now visible to the model as a real task.
   `scripts/daily_plan.py`: a second, independent priming source (a hardcoded "low-spoon means
   fewer items" rule that competed with June's literal words) was found and removed **by a
   different concurrent session** (commit `095aba1`) — same diagnosis, already landed, nothing
   further to do here.
2. **Walk duration doesn't include drive time — ✅ FIXED.**
   `scripts/capture_fields.py` (`DURATION_PRIORS`, the single shared duration-estimation text used
   by both capture and duration-backfill): added a floor (a walk is 60+ min on its own, never 30)
   and travel-time guidance for any leaving-the-house task.
3. **"Insurance" task appears multiple times in one plan — ✅ FIXED.**
   Root cause: `plan_generate._resolve_ids` resolves each plan row independently with no
   cross-item check; the existing block-level dedup (`b52c4a3`) is project-id-keyed and explicitly
   skips plain tasks. Added `_dedup_resolved_items`, wired into both `generate_plan` and `reorder`
   right after `_resolve_ids`.
4. **Duplicate task creation ("bleed") — ✅ FIXED, and reframed.**
   Traced to a real incident in `session_log.json`: 2026-07-14 16:59 captured "Pay bills to Sutter
   and LabQuest"; 2026-07-15 01:01 (same day) captured a near-duplicate ("Follow up on outstanding
   medical bills...") because the dedup list the LLM checks against (`capture_generate.
   _format_dedup_list`) only showed bare task names — June had to undo it by hand. June's framing,
   which should shape any future work in this area: **this is not user error — forgetting you
   already captured something is a real, expected use case, and the dedup check exists exactly for
   that.** Fix: each dedup-list line now also carries the item's linked project + Context snippet
   (`_dedup_extra`), reusing data already fetched — no schema change, no new write path.

**Corrected, not just re-confirmed:** the "Control drift showing up in daily plan" entry (Both
cluster, below) — live-checked its actual `Side` value and it's **already correctly set to "Fun /
hobby"** (`grain.classify` would already exclude it). So the original triage guess ("likely a
data/classification mismatch") is wrong — if this is still happening, the bug is in the render
path, not the data. Check the real commit timestamp against this entry before touching anything.

**Explicitly deferred, not forgotten:** the leatherworking live-verify (below) — June chose not to
trigger a live regeneration tonight (it would've overwritten her actual cached today-plan); she'll
check it next time she regenerates normally. Don't re-build dedup code for this without checking
first, per the note in this doc.

## The two things named "friction log" — do not conflate them

1. **The real one — `scripts/data/signal_log.jsonl`.** This is what June means when she says
   "the friction log." It's fed by a button labeled **"Friction"** in the overlay's Log tab
   (`docs/overlay_daily.html:1324`, `data-tag="issue"`). Submitting posts to `POST /api/logday`
   (`scripts/server.py:643`), which calls `signal_log.log_signal(text, source="log_day",
   reference={"kind": "log_day", "tags": tags})`. Entries are stored **verbatim, append-only, no
   interpretation** (`scripts/signal_log.py` docstring is explicit: "CAPTURE ONLY"). Filter for
   `reference.tags` containing `"issue"` to get the friction-tagged subset — as of this handoff,
   **40 of 69 total entries**, spanning 2026-07-14 through 2026-07-16. **No reader has ever
   consumed this file** — this triage is the first pass over it.
2. **NOT the friction log — two markdown docs that happen to have "friction" in the filename:**
   `docs/friction_2026-07-16_reorder_pipeline.md` (a debugging writeup from today's
   `reorder()` session — already resolved/tracked, not live signal) and
   `docs/friction-audit-binding-sweep.md` (a 2026-06-20 audit of a *different repo's* bind+sweep
   flow — mostly already fixed, see below). Both are historical documents, not the input stream.
   An earlier pass in this session initially triaged *those* by mistake before June corrected it —
   if you're asked to "check the friction log," go to `signal_log.jsonl` first.

## How to pull the friction-tagged entries

```python
import json
rows = [json.loads(l) for l in open('scripts/data/signal_log.jsonl') if l.strip()]
issues = [r for r in rows
          if isinstance(r.get('reference'), dict) and 'issue' in (r['reference'].get('tags') or [])]
```
(`reference` is sometimes a bare string on older/other-source rows — guard with `isinstance`.)

## First triage — backend / frontend / both (40 entries, 2026-07-16)

Full text of each entry is in `signal_log.jsonl`; numbering below is just this triage's own index
(chronological), not a stored id.

**Backend**
- ✅ **FIXED (session 2, see STATUS above)** — Focus-authoring overrides stated input —
  recurring theme, 5 separate entries: reverses self-care framing; inverts a low-spoons request
  and injects unrequested "survival first" wording (twice); drops a stated priority ("packing");
  frames around "immediate survival" unprompted. All point at the same root: the LLM
  structuring/authoring step for Focus Periods is overwriting intent instead of transcribing it.
  Highest-value fix in the whole list — it's the most-repeated complaint.
- ✅ **FIXED (session 2)** — Walk duration doesn't include drive time.
- ✅ **FIXED (session 2)** — Duplicate task creation ("bleed") — earlier chat-turn tasks get
  recreated.
- ✅ **FIXED (session 3, 2026-07-16 night)** — Duration change on a task doesn't propagate
  to the schedule. Root cause was two bugs stacked: `plan_store.set_item_duration` updated
  the cached `duration_min` number but never touched the displayed clock-time ranges, and
  `_reflow_block` (the existing time-recompute helper used by tap-to-move) derived slot
  length only from the OLD time range, never from `duration_min` (backend, `524fff5`).
  Separately, the overlay's duration-chip commit handler discarded the `plan` the server
  already returned and only patched its own chip's label — every other mutating handler in
  the file re-renders from `data.plan`, this was the one exception (frontend, `923e869`).
  Live-verified end-to-end via agent-browser against an isolated server instance (not June's
  real data): changing a task's duration now visibly re-times it and cascades every later
  item in the same block.
- ✅ **FIXED (session 3, 2026-07-17)** — Recurring "dishes" task won't toggle back on via
  focus period or regen instructions. Real root cause, corrected from an earlier wrong
  diagnosis in this same session (initially misdiagnosed as fixed by `acdd54a`'s never-drop
  guard — that guard only stops the data from vanishing; `still_here` isn't rendered in the
  UI at all, June turned it off 2026-07-13, so that "fix" left the actual symptom untouched).
  The real bug: every recurring item due today (dishes, kitchen, toilet, laundry, recycling,
  a walk) with no `time_of_day` set was defaulting to a fabricated 9am, which made it
  "overdue" on every generation (plans rarely start before 10am), demoted it to a flexible
  item, and shoved it behind every real task the model had already placed — losing the
  scheduling race by construction, every day. Not something June asked for: traced to an
  unreviewed default from the original 2026-06-18 pipeline build. Fix: `datetime_seam.py`
  now separates "due today" from "has a real clock time" — a due-but-timeless item no longer
  gets an invented time; `daily_plan.load_active_items` folds it into the same task pool the
  LLM composes and orders (real ref token, real id, `_resolve_ids`/`_ensure_all_tasks_accounted`
  cover it for free — no parallel guard needed); only a genuinely time-bound recurring item
  (a real `time_of_day`) stays a true clock anchor. Prompt text updated to match. 13 tests in
  `test_datetime_seam.py` rewritten for the new `(due, clock)` contract; 2 new regression
  tests (`test_mark_done.py`, `test_retime_clock_plan.py`) cover the completion-routing flag
  and composed-order placement. Live-verified read-only against June's real Anytype data (no
  writes): all 6 of her real untimed recurring chores now appear correctly in the live prompt
  as normal composable tasks instead of fake 9am anchors. Also answered in the same pass:
  "as needed" recurring items never enter the daily-plan pipeline at all (browsable on the Map
  instead, by design); a scheduled chore's "done" state is cache-only, never written to
  Anytype, so it reenters the next day's plan unconditionally regardless of whether it was
  completed — there's no adherence/streak tracking today, worth knowing on its own.
- ✅ **FIXED (session 2)** — "Insurance" task appears multiple times in one plan.
- A calendar event isn't loading for today. *(still open)*
- Plan text claims "low-EF first" while actually scheduling a high-EF (leave-the-house) task first. *(still open)*
- Leaving-the-house tasks aren't clustered despite that being a stated design intent. *(still open)*
- Leatherworking scheduled twice — **see live-verify note below, likely already fixed — June
  deferred the live check to her own next regeneration (session 2); do not re-build.**
- Server reachable only on WiFi; June wants remote/authenticated phone access — infra, not app logic.

**Frontend**
- The "(was 9:00)" demoted-anchor label is unclear/unneeded (this is display text from the
  same overdue-anchor mechanic fixed in `e3070e1`/`b206dfd` — the *fix* landed, this is a
  follow-up UX complaint about the label it produces).
- Priority-list spacing/indentation is overwhelming to parse.
- Remove the "pink text" significance explainer from the UI (paired backend ask below).
- Day-log vs. Friction buttons should toggle, not allow multi-select.
- Stale "undefined" chip left over from old clock-time rendering.
- Marking therapy done is too subtle to confirm it registered.
- Today/tomorrow mixup made worse by confusing separate "save changes"/"done" buttons on Focus
  Period editing.
- In a block's arc, the next item doesn't visually highlight after completing the previous one.
- Wants a separate log tab so a task doesn't get logged as a friction by mistake (ties to the two
  mistagged entries below).

**Both**
- Disability task + walk not checkoffable; can't edit block length (resolution/backend + missing
  controls/frontend).
- Can't reassign a project on an item in the review UI (missing control + needs backend support
  for the nested-structure write).
- A Focus Period for tomorrow/a future date doesn't render, and there's no way to see/edit future
  Focus Periods at all (no data path exposed + no UI for it — two entries, same root).
- Medical block renders differently from normal blocks and is missing its arc.
- "Pick up meds from pharmacy" not checkoffable despite being added the night before.
- Adding "dishes" via the Add tab gives no completion feedback AND doesn't actually reactivate the
  recurring task.
- Retire the "reorder" button/function now that deterministic reordering exists (a removal —
  touches the button and the code path it calls).
- Can only move tasks later in the day, not earlier.
- "Control drift" (the app's own dev project!) is showing up in June's daily plan with no actions
  (can't say not-today/edit/checkoff) and shouldn't be there at all — she says it should be
  excluded as Fun/hobby. **Live-checked (session 2): the data is already correct** — both
  "Build Controlled Drift" and its subproject have `Side` = "Fun / hobby", so `grain.classify`
  already excludes them. The original "likely a data/classification mismatch" guess was WRONG.
  If this is still happening, it's a render-path bug, not a data problem — check the real
  friction-entry timestamp against relevant commits before assuming it's still live.
- Can't resize the medical block or move the "sorting through mail" task to a different time.
- Changing a task's duration or marking "not today" should trigger an LLM replan call that adds
  new items as needed — the UI action already exists, the backend wiring to actually regenerate
  doesn't.

**Not actually frictions — mistagged, June flagged this herself**
- "Cancel food stamps / disenroll Costco / decide re: union card" — a task dump, not a friction.
- "Schedule facilities visit for IOPs" — a task; the very next entry says "please delete, this was
  a task not a friction."
- `signal_log.py` is **append-only with no delete/edit function**. These two entries currently
  can't be removed without adding that capability. June was given the choice (leave them and just
  exclude from triage, vs. add a small delete capability) — **unresolved, ask her** before adding
  write/delete surface to what's meant to be a faithful raw-capture log.

## Live-verify note — do not re-fix, check first

`git log` shows the plan-input-seam's project-dedup commit landed **2026-07-16 15:28
(`b52c4a3`, "one 'Work on X' block per project... dedup by project_id")**. The three
"leatherworking scheduled twice" friction entries are timestamped **14:30–14:33**, i.e. *before*
that fix landed. This is very likely already resolved by the seam ship, not a live bug. **Confirm
with a real plan regeneration before writing any new dedup code** — per the repo's build-frame
guard, a green suite isn't sufficient here since this exact shape (block-project duplication) is
what that commit targeted.

Also note: entries #38 and #39 in the raw log are byte-identical duplicates at the same
timestamp — that's a double-submit in the Friction button itself (a UI bug in the logging
mechanism, separate from the leatherworking content).

## Open thread — June is considering a scheduled headless-agent triage of this log

June's own words: she suspects a lot of this is automatable and doesn't want to have to route
every entry through herself, but wasn't sure whether an agent could read the log *accurately*.
This session's manual triage is a working existence proof that it can, **provided the automated
version does the same verification discipline a human triage does**, not a keyword match. What
that means concretely for whoever builds it:

- **Cross-check "is this already fixed" against real commit timestamps**, not vibes — the
  leatherworking case above only resolved cleanly because the agent compared the friction entry's
  timestamp against `git log --format="%h %ci %s"` for the relevant fix commit. A shallow triage
  that just reads the friction text and current code without dating both would have either
  falsely closed still-open items or reproduced an already-shipped fix.
- **Distinguish mistagged entries** (task dumps under the Friction tag) from real frictions —
  those two in this pass were only catchable because June had explicitly self-corrected in the
  very next entry ("sorry, that was a task"). A model with no such signal needs a real heuristic
  (e.g., "does this read as a bug report/complaint about the system, or as a to-do item") — this
  is a judgment call worth giving a few worked examples in the prompt, not a keyword filter.
- **The backend/frontend/both split is not always obvious from the text alone** — several entries
  required opening the actual code path (`grain.classify`, `signal_log.py`, `overlay_daily.html`)
  to tell whether a described symptom was a rendering gap, a missing wire-up, or a data problem.
  An automated triage agent needs read access to the repo, not just the log file, to do this
  reliably.
- **No destructive action without a human gate.** The log has no delete function by design
  (append-only, faithful-capture); an automated pass should never be given delete/write access to
  it, even for mistagged entries — flag, don't remove.
- The `schedule` skill (cron-based recurring cloud agents) and `CronCreate`/`CronList` tools are
  the mechanism if June decides to build this — **not built yet**, this is scoping only. Suggested
  shape if she wants to proceed: a scheduled `claude -p` run that (1) pulls new `issue`-tagged
  entries since its last run, (2) triages each with repo read access using the discipline above,
  (3) writes a structured report (or an Anytype capture) for June to review — never auto-applies a
  fix. Whether the *output* goes to a markdown doc, a work-stream item, or something else is her
  call, not decided here.
