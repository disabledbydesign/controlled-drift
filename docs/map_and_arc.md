# The map, and the arc — what Controlled Drift is actually for

*Captured 2026-06-19 (session 10), from June, during the first live test of binding + Orient. This is framing, not a feature spec. It governs how Orient, the daily plan, the rendering, and eventually the UI should behave — and it reframes pieces already built.*

## The reframe

**June does not primarily need tasks. She needs the arc — so she knows she is still somewhere in it.**

The thing that usually happens, and that the system exists to prevent: the pieces get lost. Not "the tasks don't get done" — the *whole shape* dissolves. A thread she was inside of stops being legible, and with it goes the sense that there was ever a logic holding it together.

So the load-bearing deliverable is **the map**: the work streams, persisted, that she can open and look inside. The pieces are held *at whatever grain they are at right now* — a fully-formed task, a vague direction, a single sentence, a "this exists and matters but isn't ready." The grain is allowed to be rough. What matters is that the piece is *there* and findable, inside a named stream with a logic, rather than carried in her head or lost.

When she is working inside a stream, she wants two things from the system: **where am I** in this arc, and **is there a logic here** (yes, here it is). That is the reassurance. The map being present *is* the reassurance — more than any individual task.

> "It's not that I need a ton of tasks. It's that I need the arc, so that I know I'm still in the arc somewhere." — June, session 10

## "Task" is too noisy as the primary unit

Task-as-the-main-thing is the wrong frame for June's cognition. Tasks are fine as a *grain* a piece can be at, but they are not what she navigates by, and leading with them creates noise that buries the arc. The primary unit is the **work stream** (the arc); tasks are one possible grain of a piece inside it.

This also means: the system should not push her toward producing tasks, or treat "no tasks here yet" as incompleteness. A work stream with rich context and zero tasks is a *complete, valuable* object — it is the map doing its job.

## "Work stream" over "project / sub-project"

The Goal / Project / sub-project vocabulary blurs for June — and she is right that it does: a sub-project is literally a Project with a parent link, identical fields. The underlying type stays Project (no migration, nothing breaks), but **"work stream" is the word the system uses with her**. Whether the three-level Goal/Project/Task ontology should simplify is a real open question — parked, its own conversation, not churned on here.

## This applies to everything, including what's already built

This is not only about future work. The same shape governs the pieces already shipped — Orient, the daily plan, the weeding gate, the rendering. They were tuned toward this instinct ("never a flat list; group into named routes") but not as cleanly as this names it. The arc/map framing is the more elegant statement of what those pieces were reaching for, and propagating it back through them is high-leverage. That propagation is its own focused pass (do it against the friction the live retest surfaces — see methodology note).

## What "the map" becomes in the UI

The UI need is a **map** — some structured surface where June can see the streams, see inside each, and locate where she is. The exact form is open (a structured view, a spatial layout, something else). What's fixed is the function: *show the arc and the position-within-it, so nothing gets lost and there is always a visible logic.* This belongs to the "Seeing your time, and seeing what you actually did" work stream.

## The brain-dump lesson (a behavioral correction)

The weeding / brain-dump pipeline **works** — it was tested and validated. Treating it as the blocking next step, and surfacing "you need to do a brain-dump" repeatedly, *became a stressor that made the system harder to use*. That is the system manufacturing urgency on something already done — exactly what it must not do. The brain-dump is not owed. The actual missing piece was the map. Future instances: do not re-surface the brain-dump as a gate.

## Methodology note (for reassurance against "did we design wrong")

This framing arrived by *building first to have a surface to raise friction off of*, then raising the friction in live use. That is the intended process working, not a failure of upfront design. The build was the instrument that made this insight visible. Redesigning some things in light of it is the method succeeding.

## What the map is — settled with June, 2026-06-20

The map exists so June can **see the whole picture at once** — all the work streams, readable together — so she can hold the shape of the work without carrying it in her head. That seeing-the-whole is the point. It is not a prompt to act on one thing.

What we settled:

- **It describes; it does not encode.** No symbols that stand for hidden meanings (no filled-vs-empty marks), and no one-word codes she has to translate ("held," "active," and the like). Each work stream says, in plain words, what it is and where it stands. June reads it directly — she never decodes it. **This holds everywhere the system communicates with her, and in the concepts we build into the system — not only the map.** (This is her standing preference; a drift into label-jargon is what surfaced the problem.)

- **For the stream being worked on now, the map shows what is actually being worked on in it** — the current piece — in words. A description, not a marker.

- **It is built on open, flexible structure — not a fixed, closed list of states.** A rigid menu (for example, a five-value field mapped onto two marks) is a brittle bet that will fight the system once it is actually running and meets distinctions we cannot predict now.

- **It reads the same way every time** — written once, stored, shown back — so it does not get re-improvised or drift from session to session. But that steadiness comes from showing a *stored, plain-language description*, not from locking into a rigid set of categories. Steady to read **and** open to grow.

**Superseded by the above:** the first renderer (`scripts/orient_map.py`) was an early cut that used filled/empty marks driven by a fixed five-value field — exactly the encode-and-lock approach this replaces. When picking this up fresh, rebuild it to read and show stored plain-language descriptions, on open structure.
