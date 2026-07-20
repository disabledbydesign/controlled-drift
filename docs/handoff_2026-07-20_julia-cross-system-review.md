# A review brief for Julia — comparing Controlled Drift against your system

*From June, July 2026. Send with the repo URL.*

---

## Julia — the short version

After we talked about the organizational system you built with Codex, I built my own version – Controlled Drift. Would you please pass this document to an agent to have them compare your system and mine? 

I imagine there might be places where your agent says there are things I built that you can clone (copy to your computer) and adapt for your system (perhaps parts of the UI). And for myself, I want to know how your system works under the hood, so I can gauge how I might want to design and build to make my system work better. I want to compare the **logic underneath**: what your system *does*, how it *operates*, and where its underlying assumptions differ from mine. I suspect you solved some things in simpler ways than I have. 

Everything below is a brief for your agent. You don't need to read it.

---

## For Julia's agent — your task

You're reviewing a repository (Controlled Drift, also called "GSDO" / "get-shit-done-o-tron"
in the code) built by Julia's sister, June, a neurodivergent scholar-builder, and comparing it against **Julia's own task/organizer system** — which you have access to and June does not. Julia's system was the design inspiration for June's, so the interesting question is not "are they similar" but **where they diverge, and what each does that the other doesn't.**

### The frame — read this before you start

I want you to compare Controlled Drift and Julia's system from two angles - one is to surface info for Julia, the other is to surface info for June. Ask Julia if there's anything she wants you to pay attention to. Make sure you clearly organize Julia-facing and June-facing sections in your report. You may also conduct multiple passes, e.g., focusing on the Julia-facing content and the June-facing context separately, so you can focus more deeply on each. You should also review the scale of the comparison docs and assess whether breaking the task into multiple passes even further produces a higher quality report. 

- **Do not produce a balanced "both are strong systems" review.** That's the failure mode
  here. Produce divergences, gaps, and critique. If you find June's system does something
  well that Julia's lacks, note it and move on.
- **June wants to know how Julia's system works.** She expects Julia and herself solved similar problems in the different ways – and that Julia's solutions likely include things she hasn't designed or built yet for her system, or simplifications where her system does the same thing just as well (or better) without as much complex backend. There may also be places where June's system does things better than Julia's, or things Julia's systems doesn't do – that may be loadbearing for Julia, but that's her call.  June also wants to know what Julia's system generates and how. What objects exist in her data structure, and how do they interact?
- **Complexity is a cost unless proven load-bearing.** When June's system has machinery
  (a type, a field, a selection layer, a scheduler) and Julia's accomplishes the same end more
  simply — or doesn't need that end at all — that is valuable information. Name it plainly. More complexity may be useful if it produces better results, but that should not be assumed — complexity is a cost unless proven load-bearing.
- **The two systems also diverge in their architecture and assumptions.** This is the most important information for June. She wants to know how Julia's system works, and what it does that hers cannot. 
- **June does not need you to evaluate the frontend for her – and the frontend may or not be load-bearing for Julia if she wants to port or adapt any of it, but that's her call.** Ignore the web server (`scripts/server.py`), the app
  templates/HTML, the desktop app, and the test suite. Differences that come from "June built a
  UI" are explicitly out of scope. Stay in the logic layer – unless it is important to understand the UX (e.g., how a Focus Period actually gets set)

### What to read — start focused, then go wide

The repo is public: https://github.com/disabledbydesign/controlled-drift/

It's large, and much of it is UI and tests. **The code and the live data structure are the
ground truth** — the design docs explain intent, but where a doc and the code disagree, the
code wins. So don't stop at the design docs: read the actual `scripts/` and inspect the real
objects in the store. A reading order that keeps you from drowning:

**A warning about the older docs.** The repo has a lot of planning/design docs, and most of
them are from the design and early-build phase (mid-June 2026). The system has been built out
rapidly since, so those early docs — `ROADMAP.md`, `Parameters.md` / `Parameters_v2.md`,
`docs/map_and_arc.md`, `DESIGN_v1_emerging.md` — now *understate* what exists (`ROADMAP.md`
still says "no pipelines yet," which is no longer true). Don't use them for build state.
**`AI_LAYER_SPEC.md` is the one current design doc** (updated through mid-July), and the live
scripts + the code are ground truth. If you read an early doc for origin/flavor, treat it as
history, not as a description of the running system.

**Start here — the design and the live state:**

1. **`AI_LAYER_SPEC.md`** — the primary and only current design doc. **Read §0 first** — it's
   the telos: June thinks associatively; alignment lives in her head and her head can't hold it,
   so the system holds it *for* her (distributed cognition). §0 also states the master principle
   — *the output format is what triggers the bias*, so generative/relational description over
   any scalar score. Then §2 (data model), §3 (the six guards), §4 (design lineage), §5 (design
   principles). This is where the assumptions you're comparing against live. If Julia's system
   is built around a *different* core need than "hold the alignment June can't," that divergence
   is the single most important thing you can find.
2. **`python3 scripts/describe_model.py`** — prints the *live* data model straight from the
   store, with per-field notes on what actually reads each field (`[live]` / `[planned]` /
   `[undesigned]`). This is the real schema, not the specced one.
3. **`python3 scripts/whats_open.py`** — the live map of what work is currently open. It queries
   the store at run time, so it's current whenever you run it (a live query, not a cached
   snapshot).

**Then go wide — the actual mechanics and data:**

4. **The code.** Especially `scripts/daily_plan.py` and `scripts/plan_generate.py` (selection +
   daily-plan generation, where most of the interesting logic lives), and the object-builder
   scripts (`scripts/build_*.py`) for how each type is constructed. Read the code, not just the
   summary below.
5. **The live data structure** — inspect the real objects in the store, not only the schema.
   What's actually stored, and on how many objects, tells you what's load-bearing versus
   aspirational.
6. **Current design-detail docs**, when a specific mechanic needs its reasoning:
   `docs/map_design.md` (rendering / grain), `docs/spec_reconciliation_selection_2026-07-11.md`
   (the three-layer selection model), `docs/focus_configuration_addendum.md` (Focus Periods).
   Deep detail — pull them only as needed, don't read them front to back.
7. **`skills/drift/SKILL.md`** — June operates the system through **two** doors: the **app**
   (the UI) and this **`drift` skill** — an agent she talks to through Claude Code that does
   capture / weed / plan / think. This file is how the agent door works. Both are real operating
   surfaces, so *how* Julia's system is operated — one door or several, app versus conversation —
   is itself a fair comparison point.

**A note on honesty about build state:** `AI_LAYER_SPEC.md` is design *intent*. Some of it is
wired and running on real data, some is built-but-not-wired, some is specced-only. The two live
scripts above (`describe_model.py`, `whats_open.py`) plus the code are the source of truth for
what's actually running. When you compare, compare Julia's *working* system against June's
*actual* wired behavior, not against the spec's aspiration — and flag anywhere the spec claims a
mechanism that the live model shows nothing reads.

---

## How June's system works (so you can go straight to comparison)

A compressed map of the mechanics, so you're not reconstructing it from source:

1. **Store.** Everything is objects in a single **Anytype** space — a local-first,
   end-to-end-encrypted graph database. Chosen specifically because June's tasks include legal,
   health, and job-search material and she wanted it on-device with no server to run. Objects
   link to objects (graph edges), so cross-cutting relationships are native.

2. **Five object types + one config type.** Goal, Project (nestable — a nested Project can be a
   "work stream"), Task, Recurring, Strategy, plus a Focus Period config object. Governing rule:
   **a formal field exists only for what the AI must query or filter on; everything else lives in
   a free-text `context` field the AI always reads.** June never fills a form — the AI proposes
   field values in conversation and she confirms. Most fields are empty on most tasks.
	1. Task and recurring are discrete to-do items. Recurring repeats, task is a one-off
	2. Projects (and nested subprojects/workstreams)
	3. Goals are high level medium-to-long term
	4. Focus Periods are short-term prioritization frameworks. 
	5. Strategies are natural language instructions for how the LLM should produce output in different contexts (e.g., how to organize the daily plan for June, what a "low capacity" day means in terms of what should be moved around or adjusted in the daily plan)

3. **Alignment hierarchy.** Goal → Project → Task, stored as a graph (many-to-many; a Task can
   serve several Projects; Projects nest), viewed as both a tree and a graph. The "why"
   (`reaching_for`) persists at the Goal level so June doesn't have to re-derive her own reasons.
   **Drift detection** is an LLM reading a new change against that free-text "why" and asking, in
   natural language, "does this still serve what she said this is for?" — offered as a question,
   never blocking.

4. **Selection / the daily plan.** No stored priority number anywhere. What surfaces today is
   composed at read time from three layers: a per-project **engagement** grain (Steady / Open /
   Backburner / Done), a temporary **Focus Period** lens (what's in front *this stretch*), and an
   orthogonal **Side** tag (obligation / wellbeing / daily-life / fun). The LLM proposes ordering
   and selection; **deterministic Python** places items at real clock times around fixed
   appointments (LLMs can't be trusted with the current time or duration arithmetic). Chat is the
   negotiation surface; the confirmed plan is *written* to Anytype as the artifact June lives in.

5. **Weeding gate.** An unstructured brain-dump (voice or text) goes in; the system sorts it into
   typed objects and flags what's unclear. June doesn't pre-organize — that's the point.

6. **Affect and capacity are never a scalar.** No 1–5 readiness score. Affective weight and
   capacity are modeled as a *constellation* of labeled signals, each tagged by source (June
   stated it vs. AI inferred it) and confidence. This is enforced by two of six **non-negotiable
   guards**: nothing punitive (no streaks, no "overdue"); offer-don't-impose; no scalar
   flattening; alignment-check-is-not-surveillance; don't-flatten-situated-specifics; and
   June-must-see-*why* (any recommendation carries its full reasoning, because reconstructing
   implicit reasoning is exactly the cognitive load the system exists to remove).

7. **The labor split.** The LLM does judgment (ordering, alignment, drift, register, weeding);
   Python does everything deterministic (clock time, calendar facts, is-today-in-window). Results
   are stored once a decision is settled and recomputed only where fresh judgment is needed.

---

## The questions — what June wants to know

Organize your findings around these. The first three are the spine; the numbered probes feed
them.

**A. What does Julia's system do that June's has no answer for?** (Gaps in June's system.)

**B. Where did June build machinery that Julia's system accomplishes more simply — or doesn't
need at all?** (Over-engineering June expects and wants named.)

**C. Where do the two systems assume *different things at the root?*** Not feature presence —
underlying model. Does Julia's system even assume a goal-alignment hierarchy? Does it try to
generate a daily plan at all? Does it model affect? Does it externalize strategies? The most
useful divergences are the ones where June's system takes as given something Julia's doesn't
(or vice versa).

**D. What does Julia's system *produce*, and how does she interact with it?** Not just the
architecture — the *output* and the *use*. What does it give her (a daily plan? a list? a map?
nudges?), how does she interact with it day to day, what gets *stored* versus computed fresh,
and how does it *weight* or prioritize what surfaces? June wants to compare the lived surface
of Julia's system against her own, not only the backend.

Probes, each mapped to a mechanic above — answer them *of Julia's system* and contrast:

1. **Design values / guards.** Does Julia's system carry explicit commitments (accessibility-first, anti-punitive,
   offer-don't-impose, show-your-reasoning)? Which ones, and are they enforced in code or just
   in how the agent is prompted?
2. **Reverse-Engineered Spec**. What components exist in Julia's system, and how do they interact end to end? What goes in where, and what comes out?
3. **Store.** What does Julia use, and what does that choice buy and cost versus a local
   encrypted graph? Does her store shape her logic the way Anytype's graph shapes June's?
4. **Schema richness.** What Julia's typed objects does Julia store, and how are they structured? What do the types and fields do – how do they interact with the larger system? 
5. **Alignment / the "why."** Does Julia's system track goals, reasons, or drift — or do tasks
   stand on their own? How does she do that?
6. **Goals / strategies / routines / mindsets.** How do Julia's goals, strategies, routines, mindsets, or other non-task objects feed into the live system?
7. **Recurring**. How does Julia's system handle tasks that recur regularly?
8. **Selection.** How does Julia's system decide what to show *today*? Is there anything like
   engagement states, focus periods, and sides — or a single simpler rule?
9. **Daily plan + scheduling.** Does Julia generate a daily plan? Does she place things in real
   clock time deterministically, or avoid clock-time entirely? 
10. **Affect and capacity.** Does Julia model emotional weight, capacity, or spoons? If so, how? June refuses any single readiness score on principle; does Julia
   share that, or does she find a scalar actually works fine?
11. **The agent boundary.** In Julia's system, what does the *agent* do versus what's
    deterministic code? June drew a hard line (LLM = judgment, Python = time/facts). Where's
    Julia's line?
12. **Proactivity.** Does Julia's system initiate — a morning plan, a nudge when something's gone
    quiet — or is it pull-only (June has to open it)? June's proactive layer isn't built yet;
    seeing Julia's would be useful.

## Also worth asking — things June didn't think to ask, that a comparison like this can uniquely surface

13. **What broke, and why.** What in Julia's system failed, got abandoned, or had to be redesigned
    — and what was the cause? Failure modes in a sibling system are the best available predictor of
    June's. (One is already known: practices-as-tasks. What else?)
14. **Built vs. actually used.** What did Julia build and *stop* using, versus what she reaches for
    daily? June's system has a lot of built-but-unused surface; real stickiness data from a similar
    user, with similar needs, is rare and valuable.
15. **Operating cost.** How much effort does Julia's system take to *keep alive* — daily upkeep,
    maintenance, the tax of running it? June's has many moving parts; a lighter system that gets
    used beats a richer one that doesn't.
16. **The verdict summary** Having seen both: **what are the key things you'd tell June to cut, add, or change?** Direct, opinionated, from a system that's actually been
    lived in.

---

*If anything here is ambiguous, err toward saying what you actually see rather than smoothing it.
June would rather have a sharp, possibly-wrong observation she can react to than a safe summary.*
