# Handoff — surface rebuild (2026-07-17, end of session)

You are continuing a UI rebuild. **Read this before touching anything.** Branch: `feat/overlay-actionable`.

## What is being built

The whole Controlled Drift surface is being rebuilt from a design mockup. It replaces **two** live
surfaces at once: `docs/overlay_daily.html` (the daily overlay) **and** `scripts/surface_template.html`
+ `scripts/surface_serve.py` (the review/reorganize tree). Two servers and two token sets become one app.

**The owner's top requirement is extremely high fidelity.** She finetuned the design over a long
period and is — correctly — afraid of losing details. When in doubt, transcribe rather than improve.

## Three-way source of truth (memorise this)

| Question | Authority |
|---|---|
| How does it **look**? | `design/mockups/color-system.html` — the gallery. She tuned against it. |
| What **data** exists? | `docs/review_reorganize_backend_spec.md` + `docs/spec_deltas_2026-07-16.md` |
| How does it **behave / lay out**? | `design/mockups/review-reorganize-mobile-v4.html` |

Consequence: v4 still renders an excitement picker, but the spec cut that field — **do not port it.**

## State: done and committed

- `design/mockups/` — v4 (the single reference; v2 and v3 are byte-identical), the gallery, the DC runtime.
- `design/tokens/tokens.ts` — reconciled two-theme token module. Gallery-canonical: 63 corrections
  taken from it, ~40 tokens added for values v4 left inline. `RECONCILIATION.md` has the audit trail
  and 11 ambiguities (8 defaulted with reasoning, 3 resolved by the owner).
- `docs/api_contract_v2.md` — 38 endpoints (15 EXISTS / 13 CHANGE / 10 NEW), payload shapes, write-path
  contract, four known gaps. **Read the two appended sections at the end** — they correct earlier errors.
- `app/` — React 19 + Vite 8 + TypeScript. Verified running in both themes.
- `app/src/fixtures/` — v4's fixtures as typed TS, **verified byte-identical** (JSON.stringify, key
  order included). 5 goals / 46 nodes / 6 strategies / 3 plan blocks / 2 periods / 12 vocabularies.
- Read-back fixes: 790 tests passing.

## The load-bearing build decisions — do not quietly reverse these

1. **Styles stay INLINE STYLE OBJECTS reading from the token module.** Do NOT convert v4's 494 inline
   styles into CSS classes or CSS variables. That translation is exactly where finetuned detail leaks.
   The owner already gets one-file theme editing because the tokens are centralised. A class refactor
   is safe only AFTER fidelity is locked, and it is not this task.
2. **The new app mounts at `/app/`.** `overlay_daily.html` stays live and untouched at `/`. She uses it
   daily; it comes down only when she judges the new one better.
3. **Themes differ in SHAPE, not just colour.** v4 branches on `isHW()` at ~30 sites — checkbox
   geometry, radii, mono-vs-sans chrome, `//` vs `✦` glyph prefixes. Treat these as real forks.
4. **Object-type colour comes from the gallery legend** (`typeRamp` in tokens.ts), not v4's `TYPE` map.
   Goal→Project→Task get a continuous pale-cyan→cyan→blue ramp because that IS the containment
   hierarchy; Recurring and Strategy sit outside it. v4's map coloured TASK **green**, which collides
   with the completion green used for done/steady/saved. Do not reintroduce it.

## Do NOT port

- `renderApp()` (~697), `header()` (~344), `tab()` (~357) — dead legacy path, not called by `renderVals()`.
- The excitement picker — the field is cut.

## DO build

- **`toast()` is stubbed in v4** (`return null`; `flash()` sets the state and nothing renders it).
  It is not decoration — once writes go live it becomes the **read-back confirmation**, the UI half of
  this repo's "a good answer is not a saved object" discipline. Make it say what actually persisted.
- **Orphan buckets** (owner explicitly confirmed). Catch-all sections for unparented objects — tasks
  and recurrings with no project, workstreams with no parent, projects with no goal
  (`scripts/review_surface.py:234-247`). Capture and weeding produce unfiled objects, and in a pure
  Goal→Project→Task tree an unfiled task renders **nowhere**. Render only when non-empty.
- **Cross-tab search** spanning Map + Routines + Strategies, showing which tab each hit is in. v4 splits
  one tree into three tabs; the filter itself is unchanged (`Filter by title…`).

## Explicitly declined by the owner — do not add

- A **data-health count line**. Rejected as stressful, and genuinely redundant: the orphan buckets only
  render when non-empty, so their presence IS the signal. A count restates it as a standing score.
- Notes-to-Claude, expand/collapse-all, inline primary field (chips cover it).
- A **global hotkey** for quick capture. She hits hotkeys by accident and forgets bindings.

## Already in v4 — do not rebuild

`hideInactive` (level-aware, strictly better than the old Hide-done checkbox) and the per-tab title
filter. An earlier list wrongly claimed these were missing; three of its seven entries were wrong.

## Needs the owner / a live machine — DO NOT attempt unattended

1. **Schema writes against her live Anytype space are human-gated.** Edit `build_*.py`; never run it.
2. **The archive marker.** `archive_object` now requires a truthy archived marker on re-fetch. What the
   live API actually returns after DELETE could not be determined from code. If it returns an object
   with no marker of any name, **undo will now raise where it used to succeed.** Needs one live undo.
3. **A latent bug this surfaced:** `gsdo_objects.create` dedups by name and returns an existing id
   *without writing properties*. So committing a Focus Period whose name matches an existing one will
   now 500 with field mismatches. That is correct behaviour, but it is a live change on a path she uses.
   The honest fix is the create-vs-update seam (`docs/create_vs_update_design.md`), not a patch here.

## Parallel work

Another agent thread works this same branch (persistence / completion rail, `scripts/server.py`,
`scripts/daily_plan.py`). **Commit only your own files.** Do not revert or "clean up" theirs.

## Parked, not to be acted on

`docs/ux_consistency_review_2026-07-17.md` — a candidate list of UI inconsistencies. Every item is the
owner's call. Nothing there is decided. Do not implement from it.
