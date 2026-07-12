# Flow-model design thread — the interaction model June actually needs

*Opened 2026-07-11. **This is the design conversation June started the session with**, then
deliberately parked so it wouldn't get done badly inside a sprawling session. It is the thing she
most wants solved. This doc exists so a new agent can pick it up **cold** — June should not have to
reconstruct it from memory. Read this whole doc before proposing anything.*

## Do not start by building or by drawing mockups
The earlier overlay mockups "didn't land," and this session clarified **why**: they designed the
*look of a screen*, but June's friction is in the **interaction model** — *how she tells the system
anything at all*. Starting from view-layout will miss the target again. This is a design
conversation (use the `workshop` skill, grounded in her real use), not a build task.

## The problem, in June's words (this session, 2026-07-11)
- "The tool is not really giving me what I need for me to use it. The LLM may not be able to plan
  without more context for what I need and what I want to focus on that day. Sometimes I want to be
  able to add todos and then reorganize my daily plan around that."
- "I often want to put all this info in one thing… *Here's what I want to focus on today or over
  these next few days, here's what needs to be added to the todo list so I do it today, and then,
  let's make sure those added items end up on the plan for today.* So I wonder if the problem is
  actually that the overall model of our flow is too clunky."
- "I know what I want to do in my head. The LLM doesn't. We need to figure out how to create less
  friction to get to a happy medium — **not me having to schedule everything by hand, but not an LLM
  trying to mind-read, either.**"
- Focus-period entry needs to be **easier** (the current authoring is too much friction).

## The target
**One natural input** that carries, together, what are currently three separate operations she has
to run in sequence (set focus → capture todos → regenerate plan):
1. **Focus** — "here's what I want in front today / the next few days"
2. **Capture** — "here's what to add to my todos so I do it today"
3. **Re-plan** — "make sure those added things land on today's plan"

The **happy medium**: between hand-scheduling everything herself (too much friction) and the LLM
guessing her intent (mind-reading, gets it wrong). Something in between, low-friction, that she
directs.

## The key lead from this session: strategies are the missing integration piece
On 2026-07-11 we built **capacity → strategy** (see `scripts/daily_plan.py` `capacity_level` +
the "Applies when" field on Strategy, commit `34f992a`). That pattern is a **working template for
the happy medium**: June authors her knowledge **once**, in her own words (a Strategy), and the
system **applies** it — not hand-scheduling, not mind-reading. June's own realization: *"strategies
are really a missing piece that will make this system run more smoothly once we integrate it more."*
The flow-model design should treat this as a live clue — much of what feels like missing machinery
may be **strategies waiting to be wired**, activated by context, rather than new UI.

## Open questions for the conversation
- What is the **one-input** shape? How does a single utterance decompose into focus + capture +
  re-plan without June having to name which is which (she should never name a function)?
- How does **easier focus-period entry** fold into this — is authoring a focus period just another
  thing the one input handles?
- Where do **strategies** sit in it — does the input also let her drop self-knowledge that the
  system holds and applies later?
- Is the right surface the overlay, the chat (`/drift`), or both — and does the *interaction model*
  even depend on the surface, or is it prior to it?

## Design constraints (June's access needs — non-negotiable)
- Plain language, **no metaphors** in anything June-facing (hard guard).
- **One thing at a time.** Do not stack options or sprawl.
- **AI proposes with its reasoning surfaced; June reacts.** Never cold-generate. Never a closed
  multiple-choice menu that forecloses "that's the wrong frame."
- **React-to-real-output / build-and-fix** is the method here — design against her real data and
  real use, not in the abstract.
- Parallel exploration is her natural mode; she directs, reviews, approves — she does not generate
  or manage.

## How to restart this (say this to a new agent)
> "Let's do the flow-model design conversation. Read `docs/flow_model_design_thread.md` first, then
> let's talk it through — don't jump to building or mockups."

The agent reconstructs the whole thread from this doc. June does not have to hold it.

---

# DECIDED — 2026-07-11 workshop session (the design is now settled enough to plan)

> **Status (2026-07-12): the build scope is FINALIZED in the plan, not here.** Authoritative: `docs/superpowers/plans/2026-07-11-capture-when-regenerate-flow.md` (rev. 3, critic-swarm-reviewed) + `docs/handoff_2026-07-12_capture-when-thread.md`. **Key change since this section was written:** the future-date "held off today" behavior is NOT built by this thread — it's handed to the selection thread (which owns `daily_plan.py`/`plan_generate.py`); this thread ships the `Scheduled` field + a pure eligibility predicate. See the plan's "HANDOFF TO THE SELECTION THREAD" section.

*Reached via the `workshop` skill, grounded in the real tool (overlay `docs/overlay_daily.html` +
`scripts/server.py` routes + `scripts/daily_plan.py`). This section is the outcome; read it and the
thread above together.*

## The break, made concrete
The current overlay splits the work across **two disconnected places**: the **Add** tab
(`/api/capture` → weeds a task into Anytype, does **not** touch today's plan) and the **Today** tab
(the Ask field → `/api/negotiate` reorder/generate, plus "Fresh plan" → `/api/refresh`). To do
June's real move — *add these, then fit them into today* — she has to add on one tab, switch tabs,
and **re-state her intention by hand** in the Ask box. That re-statement is both the friction AND
the exact place the system can guess wrong. Her intention was clear when she added the task; the
tool just doesn't carry it across the gap.

## The reframe (this is the actual design move)
**The fix is not a "put it on today" button. It's that the *when* is captured together with the
task.** June already says the when in her head ("email the registrar *today*", "syllabus *for
Thursday*", "*someday* clean up Zotero"). The capture step is already an LLM structuring her words —
so it also reads the *when*, and routing follows:
- **said "today"** → the item goes onto today's plan, and *that* is what triggers the rebuild
- **said another day** → set for that day; **today is left untouched**
- **said no when** → captured and parked; **no date, no rebuild**; surfaced later *(June's chosen default)*

So "add these and put them on today" stops being a special mode. It's just what happens when the
thing added *is for today*. A mixed dump (three for today, one Thursday, one someday) routes item by
item — the today ones rebuild today, the rest don't.

## Why this is reliable, not mind-reading (June's load-bearing constraint)
The risky part — *should I regenerate the plan?* — stays **mechanical**: plain code fires the replan
when an added item's date == today. The LLM is used **only where it is already reliable**: structure
the task, notice the word "today." We do **not** build a bundled free-text intent-classifier that has
to decide what she's asking. This is the same proven pattern as (a) focus-period authoring (LLM reads
"Saturday", Python anchors the real date) and (b) capacity→strategy (`daily_plan.py:183–241` — author
in your words, system applies). Not hand-scheduling (she never picks a slot), not mind-reading (she
literally said the when).

## Two-act split (organizes everything, including where future pieces go)
- **Telling the system what you want** = forward-facing, one act, one input: capture, re-plan, and
  **focus** all live here. focus = *criteria that keep applying over coming days*; re-plan = *criteria
  for today only*. **Same act, one difference: how long what she said keeps applying.** ("criteria the
  system keeps applying" is literally what a Strategy already is — this is the integration the thread
  was reaching for.)
- **Telling the system what happened** = the **log** (not yet built) = backward-facing, a *different*
  kind of act. Open question that decides its placement: *does a log entry ever need to change the
  plan right then?* If purely reflective → its own tab is fine. If "today wiped me out" should make
  tomorrow lighter → it must feed the same planning path, not a separate tab.

## Root cause found (2026-07-11) — the build drifted from the spec; THAT is the real problem
Three read-only inventories + the daily-plan prompt confirmed the deeper issue June has flagged
before: **the daily plan crams every active task into every day.** The selector
(`daily_plan.load_active_items` + `plan_generate.select_and_order_tasks:318`) filters by task *status*,
orders foreground-first, drops paused/Done-project tasks — then hands the WHOLE remaining list to
today. It never limits to the next item per project, never sizes real estate by Engagement, never caps
by capacity. The prompt (`prompts/daily_list.md:16-17,46`) *does* tell the model to give each project
the right real estate and surface "the next tangible item per project, not the whole pile" — but
nothing deterministic enforces it, so the day overstuffs. The intended model IS written in
`AI_LAYER_SPEC.md` (Engagement drives real estate: Sprint/Hyperfixation → more, Steady → one move,
Backburner → invisible-unless-neglected, Done → excluded; "active tasks" = Ready AND project engaged).
Specified, never implemented.

**BUT the spec is STALE** (June): written pre-build, pre-`Side`, and the `Side` binary is itself being
reworked. So the repair is NOT "restore the spec verbatim" — it's reconcile the spec's intent with
everything built since (Side, focus periods, capacity→strategy) into one current-truth selection
model. **This repair is a SEPARATE thread — June works it with another agent.** Root-cause note for
that thread: `docs/cram_selection_diagnosis.md`.

## What THIS thread builds (the UI flow) — assumes the cram fix has landed
June's deliberate minimal cut (low-spoons; solves the pressing problem without overcomplicating):
- **The Add tab gains the power to regenerate today's plan.** When captured item(s) are marked
  *today*, the plan regenerates to include them — June never crosses to a second box to say "put these
  on today." This removes the two-place split that was the original friction.
- **A verification step before regenerating** (June's add): the add proposes, June okays, *then* it
  regenerates. Never a surprise rebuild.
- **Regenerate fires ONLY when added task(s) are marked today.** Not-today (a day / someday / no when)
  → captured and routed, plan untouched.
- **The Ask field and everything else stay exactly as they are.** Ask = pure reshaping ("reorder, I'm
  low") — a different act, no new task. Not the cleanest architecture; it's the true minimal fix.

Core mechanics (from the inventories): `capture_generate.capture` (already an LLM) also reads a
`when`; anchor it to a real date in Python (reuse `datetime_seam` weekday→date); write it to a NEW
"when/scheduled" Task field (**not** `due_date` — that means *deadline*). The replan must be **chained
inside the single capture job** (one global `_gen_lock`; a second `_start_generation` would no-op). A
today-marked task is already plan-eligible once the selector is fixed.

## No-delete parameter — corrected scope
Protects the *good* features (weeding, flexible replan, receipts, the whole focus-editing sub-app). It
does **not** protect the cram-everything selection — that's a bug, fixed in the separate thread, not
functionality to preserve. *(Claude first misapplied no-delete to the cram behavior and recommended
preserving it; June corrected it. Recorded so it isn't repeated.)*

## Sequencing (matters)
This flow's payoff depends on the cram fix landing FIRST — otherwise "regenerate" just rebuilds a
crammed day. Order: (1) cram/selection fix (June's separate thread) → (2) this UI flow on top.

## Build protocol (when June has spoons — NOT started)
`writing-plans` → plan in `docs/superpowers/plans/` → `critic-swarm` → build on June's explicit go.
Nothing built yet.
