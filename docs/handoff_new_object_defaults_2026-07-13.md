# Open design + bug: newly-created projects are born invisible

**Status:** design session + bug fix, NOT started. June wants to do this clean-slate with a fresh agent: explain what she wants new projects to look like, then generalize so the system stops producing this bug on every project creation. This doc is the factual description + pointers — not a plan.

## The bug (concrete)
A project created without an `Engagement` value is **silently hidden from the daily plan**. Two causes compound:

1. **Creation sets no default.** `gsdo_objects.create()`, the surface's add-from-page, and the drift skill's capture/weeding all create a Project without setting `Engagement` (or `Side`). So new projects are born with those unset.
2. **The gate treats unset as dormant.** `scripts/plan_generate.py`, `_gate_and_collapse` — `eng = proj_eng.get(proj, "unset")` (~line 534), then a project with `eng in ("Backburner", "unset")` is hidden unless it's foregrounded (Focus Period) or already neglected ~16 days. So "unset" == "Backburner" == invisible.

Net effect: **create a project → its tasks don't surface in the daily plan for ~16 days** (until the neglect threshold trips). June experiences this as "I made the thing and the system acts like it doesn't exist." It violates the telos (alignment lives outside June's head — she shouldn't have to remember to configure a field to make a project real).

## What June wants (in her words, 2026-07-13)
- Not to fill engagement in by hand on every new project (that's the manual-labor failure).
- Not to have Claude guess it (engagement is a situated "how am I engaging" judgment).
- A **general default policy** so a newly-created project is well-formed and visible by default — and the same for whatever other fields a new object needs to not be broken (`Side`, maybe `Project status`). "Figure out how to generalize this into a system where we don't hit this bug every time we create a new project."

## The design questions (answer WITH June)
1. **What should a new project default to?** e.g. `Engagement = Open` (available, self-paced, visible-but-not-pushed) vs `Steady` vs a "Needs Clarifying" state that prompts her. And `Side` — inherit from parent? default to something? (Top-level job-search projects have no Side ancestor since Goals don't carry Side.)
2. **Where does the default live?** Set at creation time (one place: `gsdo_objects.create`, so every writer inherits it) vs interpreted at gate time (`_gate_and_collapse` treats unset as visible, not dormant). Creation-time is more explicit; gate-time is a smaller change but leaves the stored data blank. Probably creation-time + a sensible gate reading of unset as a backstop.
3. **Is unset ever legitimately "dormant"?** If some flow intentionally leaves engagement blank to mean "parked," changing the default breaks it — check before generalizing.
4. **Generalize to all creation paths:** whatever the default policy is, wire it into every place a Project (or other type) is created — `gsdo_objects.create`, add-from-page (surface export→apply), drift-skill capture/weeding — so no new object is born broken.

## Currently-affected projects (backfill once policy is decided)
Active, non-workstream projects with unset `Engagement` as of 2026-07-13 (most are the containers created this session's reorg):
`Job search`, `Job applications`, `Headhunters`, `Grants / fellowships`, `Networking and relationships`, `Learning to code`, `Reframe`, `Leatherworking`, `Sell phone case`, `Writing projects`, and the daily-life subprojects `medical` / `household` / `self-care` / `social`. (Several GRA workstreams too, but those are lower-priority.) Several of these ALSO have unset `Side`.

## Pointers
- `AI_LAYER_SPEC.md` §2 — the engagement/Side selection model (the top-of-section reconciled-selection note).
- `docs/spec_reconciliation_selection_2026-07-11.md` — the fuller selection-model reconciliation.
- Related open build: `docs/handoff_display_grain_2026-07-13.md` (the daily-life subprojects' unset engagement interacts with the display-grain rule — the two design sessions touch the same gate).
