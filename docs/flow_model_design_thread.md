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
