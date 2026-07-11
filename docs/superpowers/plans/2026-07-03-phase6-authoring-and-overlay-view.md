# Phase 6 Build Plan — Authoring + Seeing the Focus Period in the Overlay

*Phase 6 of `2026-07-02-focus-configuration-layer.md`. Design source-of-truth: `docs/focus_configuration_addendum.md`. Written session 26 (2026-07-03). **Revised the same day after a 5-lens critic-swarm** (cold build agent, skeptical architect, neurodivergent-UX practitioner, cold reader, author-informed) — the swarm ledger at the end records how each finding was resolved. Status: **revised draft for June's intent-skim, then build.** June approves before code.*

---

## Read this first (plain summary)

Phases 1–5 built the backend: the system holds June's Focus Period, uses it to plan her day, and logs raw learning signal. What it can't do yet is let her **see and author that configuration herself** — the thing she has named as what makes the system real for her. Phase 6 builds that surface.

**This is the UI layer, and it is accessibility-critical.** June is autistic; the visual dimension has to be genuinely solid for her to parse information. That is a load-bearing functional requirement, not polish — and it is distinct from the colors-displacement pattern (`tractable-vs-goal-displacement` memory): that was aesthetic tuning standing in for use; this is legible structure that is a *prerequisite* for use.

**Two decided facts that shape everything below (June, 2026-07-03):**
- **Authoring lives in the overlay** (primary surface); the `/drift` chat path stays as a secondary way in. The backend already serves both.
- **The overlay is June's primary access point, on her phone, opened often.** Small screen, real data, daily use — the access frame is not hypothetical.

---

## The build method — mockups and real-wiring, each for its own job

*(This section replaces the earlier "mockups-first for every screen" method. The swarm showed that a tune-the-mockup-then-look loop, on placeholder content, reproduces the displacement pattern and — worse — tests the wrong thing, because autistic parsing breaks on **real density** (39 real projects on a 360px screen), not the tidy sample rows a mockup shows. But mockups are genuinely the right tool for one job: **letting June decide a structure she can't yet picture.** So the method splits by job.)*

- **Mockups decide structure June can't visualize.** Where a layout choice is a real fork June can't picture in the abstract, build it as a **static mockup** (via `/ui-ux-pro-max:ui-ux-pro-max`, under the access frame + the existing CSS tokens) — and where the fork is genuine, build **both options** so she chooses by seeing, not by imagining. This is bounded and decision-oriented: mockups resolve a question, they are not the iteration loop. First and clearest instance: **is the composed "see my week" view a new tab, or folded into the Today screen?** (Task 1.)
- **Real-wiring builds and verifies.** Once a structure is chosen, wire it **thin and plain against June's real focus period and real projects** — deliberately unstyled first — and tune the visual **against real density**, in live use. This is the project's own proven method (`what-made-this-session-work`: react to real output, verify live). It is the only test that means anything for parsing.
- **Accessibility work is scoped, not scattered.** Visual/parsing treatment for the new surfaces uses **scoped classes** — it does **not** retune shared CSS tokens, because those reflow Today (June's daily-driver screen) as a side effect. A deliberate cross-surface accessibility pass on the *existing* tabs is a separate thing June opts into later, not a byproduct of Phase 6.

Build **one screen fully before the next** (decide structure → wire real → tune → verify live → ding). Small commits per screen.

---

## The access frame (governs every screen)

Hard constraints, not preferences.
1. **Autistic visual parsing is load-bearing.** Consistent hierarchy; one primary thing per screen; explicit visible section boundaries; generous whitespace; low per-screen load; predictable placement (same action, same place). Chunk; use progressive disclosure for genuinely long content — but note the tension in Task 2 (see-the-whole-picture vs. hide-behind-taps) and resolve it by *unit choice*, not by hiding.
2. **No metaphors in text the system generates fresh** (`accessibility-no-metaphors-june-facing`, HARD guard). *Note: existing enum values June already parses — "Sprint," "Backburner," "Steady" — are fine (June, 2026-07-03); she is the authority on her own parsing. The guard binds newly-generated prose, not her established vocabulary.*
3. **Describe in plain words, never encode** (`map_and_arc.md`). No status glyphs, no codes to decode. **This supersedes `orient_map.py`'s renderer** (filled/empty marks `●○✓☐` in a fixed-width `<pre>` that scrolls sideways on a phone) — do **not** model any new June-facing view on it.
4. **Meaning never carried by color alone.** Obligation vs. wellbeing must read from label + position + grouping.
5. **No motion that isn't functional.** Respect reduced-motion.
6. **Sensory-comfortable contrast.** Tune via scoped classes on new surfaces (see method), not shared tokens.

---

## What already exists (verified against the code, 2026-07-03)

- **`docs/overlay_daily.html`** (~1424 lines) — tab shell (`switchTab`), tabs **Today / Map / Add** + gear→**Settings**, shared CSS tokens, async generate→poll pattern. **The Today tab already has a compressed narrative context slot** (the "woven-frame," ~lines 716–720) — a real candidate home for the composed view (Task 1).
- **The Add-tab capture flow** — `POST /api/capture` → 202 → poll `GET /api/status` → `GET /api/session?stream=capture` → a receipt with **line-level undo**. Authoring reuses parts of this — but note the gap below: capture is **one-shot** (no confirm-then-commit second leg), so the hardest part of 6B has nothing to mirror.
- **The Map tab** — `GET /api/map` → `orient_map` text in a `<pre>`. Uses encoded glyphs + horizontal scroll — **the anti-pattern the access frame supersedes**, not a model to copy.
- **`scripts/focus_period_generate.py`** — `generate_focus_period(raw_text, today, names)` → structured fields via LLM. **Output keys are project NAMES** (`foreground_projects`/`paused_projects`), **ISO date strings** (`days_off`/`days_on`, `start_date`/`end_date`), and `output_format` (`"Auto"|"Clock schedule"|"Priority list"`).
- **`scripts/focus_period_author.py`** — `author_focus_period(raw_text, name, properties, source)` creates the object; wants `properties` keyed by **Anytype display names** (`"Period start"`, `"Foreground projects"`, `"Days off"`) with **project IDs** and days as **CSV/JSON text**. `resolve_project_names_to_ids(names)` exists.
- **⚠️ The adapter between those two does NOT exist.** Nothing maps `generate_focus_period`'s output (names, ISO strings, its key names) → `author_focus_period`'s `properties` (display-name keys, IDs, CSV dates). This is real, un-booked work (Task 3).
- **`scripts/signal_log.py`** — `log_signal(raw_text, source, reference, path)` writes `{ts, source, reference, raw}`, **deliberately flat and uninterpreted** (its docstring is emphatic: capture only, no classification). 6C honors this (Task 5).
- **⚠️ `build_context` does NOT compute the output `shape`.** (Corrects the earlier draft's false claim.) It returns `(full_context, schedulable, start_time)`; there is only a `# NOTE (Phase 6)` comment where `shape` should be. The real computation lives in `daily_plan.py` (`resolve_output_shape`, the terminal/`/drift` path the overlay never calls). Both inputs (`period`, `in_window`) are already in scope in `build_context`. **Computing + threading `shape` on the overlay path is real Phase 6 work (Task 6), not pre-existing.**
- **`session_store.STREAMS = ("capture", "negotiate")`** — no `focus`/`logday` stream. New authoring/log endpoints must extend it (or add a dedicated result route).
- **`server.py`** routes all async work through one `_gen_lock` + one global `GET /api/status`. New endpoints inherit that single-lane concurrency (Task 3/5 address what the UI shows when busy).

---

## Scope + sequencing (keystone-first)

- **Task 1 — Decide the shape of "see my week" (mockups of both).** Tab vs. folded-into-Today. June chooses by seeing both. *First, because it gates 6A's build and it's the choice she can't picture.*
- **Task 2 (6A) — The composed "see my week" view (read-only), wired to real data.** Her stated keystone. A rendering, not a stored copy.
- **Task 3 (6B) — Authoring in the overlay** (create a period): speak → **compressed-but-expandable reflect-back** → confirm/fix → create + read-back + ding.
- **Task 4 (6B-edit) — Edit an active period.** *New — the swarm caught its absence.* The addendum's own worked example (the Saturday caregiving shift) is an *edit*, not a new period; it had nowhere to land.
- **Task 5 (6C) — Log Day**, backend-only rest capture, dump kept faithful and uncategorized.
- **Task 6 (6D) — Fragmented-day priority list on the phone** — including the real `shape` computation the earlier draft wrongly booked as done.
- **Task 7 — Nonlinear → map routing** (folded-in).

---

## Task 1 — Decide the shape of "see my week" ✅ DECIDED 2026-07-11

**DECIDED (June): Option B — focus slot folded into Today. No new tabs.**

Mockups built twice (session 27): first with fake data (wrong — missed the authoring surface and duplicated Map content); second with real live data (40 real projects, real active focus period). Real data revealed: a flat project list is redundant with Map and not ADHD-scannable. The right content for the expanded slot is a **chronological period management surface** — not a project list.

**Settled design (docs/mockups/phase6-option-b-v2.html — authoritative mockup):**
- Focus slot lives at the top of Today, rose-bg, collapsed by default
- Collapsed shows: period name + dates (with day-of-week) + active availability note (if in window) + Edit button + "See this week ›" toggle
- Expanded shows: **period cards in chronological order** — current period card (intent clamped/expandable, "In front:" compact foreground list, availability note, Edit button scoped to that card) → "+ Set up next period — from [day date]" for the upcoming slot. No archived periods shown.
- Edit button scoped to each period card (not a global edit). Confirm-before-commit (reflect-back) is the write guard — no separate undo needed.
- Log Day lives in the Add tab as a second mode (Add task / Log day toggle) — NOT at the bottom of Today. Plan-change requests (actions + ask section) stay at the bottom of Today unchanged.
- Tab count stays 3: Today | Map | Add.

**Key design corrections found during mockup iteration (load-bearing for Task 2):**
- The "see my week" surface is a period management surface, not a project view — projects live in Map.
- Archaeology-before-generation is mandatory: read backend code + addendum before designing. The first mockup pass skipped this and produced wrong content.
- The authoring flow (Task 3) is shown in Frame 2 of the mockup: speak → reflect-back (deterministic template, compressed then expandable, per-item fix) → confirm → save. Frame 2 is sufficient design for the next builder; no further authoring-flow mockup work needed.
- One Jun 29–Jul 6 period in Anytype covers multiple phases (recovery, jobs, caregiving) in one object — that's fine; nuance lives in intent text + structured availability window.

## ⚠️ UPSTREAM DEPENDENCY — the category axes are being reworked (2026-07-11)

Reading the Task 1 selector against the **real 44 projects / 131 tasks** showed the `Obligation`/`Wellbeing`
`Side` binary **does not fit June's actual work** — "Wellbeing" as tagged is her build/creative/scholarly
work (zero rest in it); real rest, errands/chores, and social sit uncategorized; a spoons axis
(`Access conditions`: lying-down / leaving-house) already cuts across everything. **June is reworking the
categorization into multiple tiers in her own separate session.** Her direction: multi-tier not binary;
bills → life-admin; build and creative separated; survival/income further breakable; building/scholarly ≠ wellbeing.

**Build data-driven so categories plug in without a rewrite (the approach — not a blocker):**
- **The category filter/grouping reads whatever category values the projects carry — it does NOT hardcode `Obligation`/`Wellbeing`.** Today it reads the current `Side` field (the stub); when the real categories exist, the same code populates from the new field/values. What changes is the *data*, not the UI code. This is standard "don't hardcode the enum" — simple, and it means Phase 6 is **not blocked** on the categorization session.
- **The nested-tree selector structure** (mockup Frame 3) is category-independent (pure parent/child) and is **final now**. Only the *filter axis on top* is data-driven-and-pending.
- **Caveat — multi-tier:** a flat category swap is trivial (data-only). If the categories are tiered, the filter control itself gains a tier (a modest extension, not a rewrite). Build flat-data-driven now; extend to tiers when the shape is known.

## Task 2 (6A) — The composed "see my week" view (read-only), wired real
*⚠️ The "grouped by side" bit below is provisional — see the upstream-dependency note above. Build with the current Side as a stub; the real grouping axis is pending June's categorization session.*
- **Content:** the active Focus Period (name, dates, intent in plain words, days off, availability note) + projects grouped by **side**, structurally separated (never interleaved).
- **The density resolution (swarm — neurodiv-UX):** June has ~8 Obligation + ~31 Wellbeing projects. Showing 31 Wellbeing rows breaks glanceability; hiding them behind taps breaks see-it-together. Resolve by **unit choice**, mirroring the already-built `open_hobby_block` decision: **Obligation projects shown individually** (with engagement); **Wellbeing shown as the one protected block**, its projects available on expand. Engagement values render as-is (June parses them fine).
- **Backend:** `GET /api/period` returns a **structured JSON render payload** (not verbatim `<pre>` — that is the orient_map anti-pattern that scrolls sideways). The client renders accessible layout from the JSON, so color-alone and encode-and-lock are avoidable at the layout layer. A pure render/assembly function; deterministic (reads the same every time).
- **Project loader (build decision):** `load_active_items` excludes `Done`. "Every project's engagement + side" (addendum) means every **non-Done** project — Done work isn't part of *this week's* picture. Either lift the filter for this read or add a small all-active-projects loader; do **not** reuse `orient_map`'s glyph read.
- **Method:** wire thin against June's real week first, then tune visually against real density (scoped classes).
- **Verify:** live read-back; June confirms it's parseable with her real data on her phone.

## Task 3 (6B) — Authoring in the overlay (create a period)
- **The adapter (new module, real work):** map `generate_focus_period` output → `author_focus_period` `properties` — key renames, `resolve_project_names_to_ids`, ISO-date-lists → CSV, preserve `output_format` select exactly (`"Auto"|"Clock schedule"|"Priority list"`). Read-back asserts the select value survived.
- **The reflect-back — production specified (swarm, convergent: build agent + neurodiv-UX + author-informed):** the compressed confirmation is a **deterministic Python template over the already-structured fields** — *not* a second LLM call. Rationale: (1) it keeps a hard-guard'd, June-depended-on surface free of freshly-generated LLM prose (no-metaphors risk); (2) it's testable/verifiable; (3) the fields are already structured by the generate step. The template assembles a short line ("Jobs first, caregiving Sat–Wed, weekends off"). *If June wants more fluent phrasing later, an LLM version can be revisited with the guard enforced in-prompt — recommended default is the template.*
- **The reflect-back — shape (swarm, convergent — resolves compression-vs-verification + all-or-nothing-repair):** **compressed sentence by default → expandable to the exact saved fields** (start/end dates, the resolved days-off dates, availability window, foreground/paused lists) so June can verify the write is *right* (read-back-to-verify discipline) → **per-item "fix just this"** so a single wrong detail (heard Wednesday, meant Thursday) doesn't force re-speaking the whole week.
- **The "fix" per-field editor — DECIDED 2026-07-11 (June): deterministic direct-edit, NO LLM.** Tapping "fix" on a field opens a direct editor for that field only — a **date picker** for dates, a **project selector** for foreground, a plain text field for intent, a select for plan-shape. No re-speaking, no LLM round-trip. Rationale: reliability (no misinterpretation), speed (no ~30s model call to move one date), and it honors the date-determinism principle (dates set directly must never round-trip through a model). The LLM's job is turning the *initial spoken brain-dump* into structure; once structured, every field edit is direct manipulation. **The `focus_period_generate` LLM path is for speech→structure only; all field edits are deterministic.**
- **The foreground ("in front") project selector — DECIDED 2026-07-11 (June's concern: must not become chaotic with real data — she has ~40 projects).** Design (mockup Frame 3, `docs/mockups/phase6-option-b-v2.html`): (1) **current picks shown as removable chips** at top (the usual case is tweaking a few, not rebuilding); (2) a **search field** for the known-name fast path; (3) the pick list **grouped by Side, Obligation first** (~14 — foreground is almost always survival-side), with **Wellbeing collapsed** behind a tap (~26, rarely foregrounded but reachable). This keeps the default view scannable at any project count: your handful of chosen + search + the short obligation list; the long tail stays tucked away. A flat 40-item checklist is the anti-pattern to avoid.
- **Missing required field must BLOCK save — DECIDED 2026-07-11 (June).** Edge case she named: author a period but forget a date. Currently a **silent failure** — `focus_period.load_active_focus_period` requires both `start` and `end`, so a date-less period never becomes active and nothing tells her. Fix: the reflect-back must detect a missing required field (start/end date at minimum) and **surface it + block save until resolved** ("I don't have an end date for this period — when does it end?"), the same Needs-Clarifying pattern the capture flow uses. Never silently save a period that can never fire. (Malformed date-*lists* are already surfaced via `days_off_error`; this is about missing required scalars.)
- **Two-phase state (build gap):** generate → reflect-back → confirm → author. Server **stashes the structured fields keyed by session** between the generate call (202, poll `/api/status`) and the confirm call; extend `session_store.STREAMS` with `"focus"` (or a dedicated `/api/focus/result`). Confirm→author is a **synchronous** Anytype write (like `/api/capture/undo`), not another async gen — avoids colliding with the single `_gen_lock`.
- **Concurrency:** if a plan generation is already running, the authoring `202` returns busy — the UI shows a plain "one thing at a time, try again in a moment," never a silent hang.
- **Guard:** no auto-generation of content June must supply (Decision 4, addendum). The system structures her words; it never invents the week.
- **Verify:** author a real period by voice end-to-end; object persists (read-back); signal logged; the expand shows correct parsed dates.

## Task 4 (6B-edit) — Edit an active period
*New task — the addendum decided editing is in scope ("June edits it by voice when the time comes"); Phase 6 owns it because it owns authoring.*
- Same speak → reflect-back → confirm path, but **against the existing active period** (load it, apply the spoken change, reflect back the *changed* result, confirm, update-in-place with read-back). The mid-period caregiving shift is the target case.
- **Two edit routes — DECIDED 2026-07-11 (June):**
  - **Precise single-field edit → deterministic, no LLM** (the "fix"-editor path from Task 3): tap a period card's Edit, tap a field, change it directly (date picker / project selector / text). This is the safe, fast default for "move caregiving to Thursday" when she's already looking at the field.
  - **Broad spoken revision → LLM, guarded by a DIFF.** She *can* revise a period by voice ("push everything a day later," "drop the caregiving window, add a sprint Fri–Sun") and the `generate_focus_period` LLM interprets the change against the loaded period. **The safety is not protecting the period from the LLM — it's the confirm gate + a diff:** the reflect-back for an edit must show **what changed vs. what stayed** (not just the new state), so an LLM that clobbers an unrelated field is visible before anything writes. Nothing writes without June seeing the resulting state. (June weighed full-protection vs. allow-with-guard and chose allow-with-guard — the caregiving-shift example is itself a spoken edit.)
- **The edit reflect-back shows a diff, not just the new value** — this is the one real addition over Task 3's create reflect-back. Deterministic template over (old fields, new fields).
- **Build decision:** update-in-place vs. supersede-and-archive. Lean update-in-place for v1 (the period object is short-lived); archive-on-lapse is Phase 8's concern.

## Task 5 (6C) — Log Day (backend-only rest, uncategorized dump)
- **Framing:** June's own brain-dump of the day — never "report what you did." Home is Today's evening bookend or its own tab, per Task 1's outcome.
- **Storage — honors the addendum + `signal_log`'s design (swarm, convergent: architect + build agent):** append the dump **faithfully and uncategorized** via `log_signal(..., source="log_day")`. **Do NOT pre-carve a 7-types-of-rest schema into the record.** Phase 7 extracts rest-type from the raw text *when Phase 7 is built* — classifying now is the premature-operationalizing the addendum explicitly defers. (Data dependency is preserved: the raw text carries the type info; nothing is lost, nothing is prematurely fixed.)
- **Never narrate classification back (swarm — neurodiv-UX):** show June back only a plain acknowledgment of what she said, in her words. Being told what *kind* of rest she had is aversive. Any rest-type reading stays entirely backend.
- **Two-signal distinction preserved (swarm — author-informed; addendum lines 132–135):** "I did it differently" (a Log Day entry) is **not** the same as "the plan didn't fit me." The planned-vs-actual diff stays **backend-only** *and* does not treat a Log Day entry as a plan-failure signal. One sentence in the build note prevents a naive "deviation = plan wrong" wiring.
- **Creative hyperfocus ≠ rest** (addendum): the dump must not silently count hobby/dev time as rest.

## Task 6 (6D) — Fragmented-day priority list on the phone
- **First, the real `shape` computation (corrects the earlier draft):** extend `build_context` to call `resolve_output_shape(period, in_window)` (both already in scope) and thread `shape`; `generate_plan` branches on it. This is unbuilt work.
- **The JSON contract:** `_JSON_INSTRUCTION` hard-codes the clock-block schema — add a **second, no-clock list contract**; `parse_plan` handles it; the overlay gets a renderer branch (today it renders `.time-block` only). A text `format_priority_list` exists in the `/drift` path — decide reuse-as-JSON vs. fresh (lean: shared ordering helper, separate output shaping).
- **Python owns the order** (foreground-first, from the parent plan's foreground selection); the model narrates, never reorders.
- **Done-affordance (build gap):** priority-list items carry `id`/`ref` tokens so June can mark them done, same as clock items — decide explicitly (don't ship a read-only list by accident).
- **Predictable-placement (swarm — neurodiv-UX):** the same Today location now shows two different structures depending on invisible day-state. Add a **plain one-line header** stating which shape today is and why ("Today's fragmented — here's a short list to pull from, no fixed times"), so the switch is never silent.
- **Design it ADHD-friendly:** few items, plain language, no clock pressure, one clear "when a window opens, start here."

## Task 7 — Nonlinear → map routing (folded-in)
- **What already happens:** Wellbeing-side work already collapses to one open hobby block (`partition_by_side` + `open_hobby_block`, wired into `build_context`). So "don't invent a next item for nonlinear work" is *partly done* for the Wellbeing side.
- **What's genuinely new:** nonlinear **obligation** work (no single correct next step) and the actual "go look at the map and pick your thread" **surface on the phone**. Needs a linear/nonlinear signal per project — **Open question: inferred from side/engagement vs. an explicit Project field** (lean inferred, to avoid another field June must maintain; confirm reliability in build). Name the render location (route to the Map tab / the map surface) rather than leaving it unspecified.

---

## Owners for the addendum gaps this plan does NOT build (named, not dropped)
*(Swarm — author-informed: these were in the addendum's "gaps the plan must address"; naming their owner prevents fall-through.)*
- **Staleness re-author prompt** (period lapses → prompt to re-author): the v1 lapse-nudge already ships in Phase 3 (parent plan Decision 7); the richer rollover-and-react version is **Phase 8**. Phase 6 does not own it.
- **Conflict surfacing** (day-off vs. hard deadline same day): **Phase 8**. Phase 6 does not own it.

## Data dependency / hand-offs
- **6C → Phase 7:** rest-type is read from raw text by Phase 7's loop when built — *not* stored as a schema now. Dependency preserved without premature classification.
- **6A render function** is the reusable base for later composed views (Phase 8 conflict surfacing renders into it).
- **6D `shape`** is now computed in Phase 6 (not inherited) and threads to the renderer.

## Open questions (for June / for build)
1. ~~Overlay on her phone?~~ **RESOLVED: yes, primary access point.**
2. ~~Authoring surface?~~ **RESOLVED: overlay primary; `/drift` secondary.**
3. **Task 1 — tab vs. folded-into-Today** — decided by June from the two mockups.
4. **Nonlinear/linear signal** — inferred vs. explicit Project field (Task 7).

## Verification & discipline
- Idempotent Anytype writes; no silent failures (raise, don't `assert`); live read-back where it touches Anytype; tests never leave artifacts in June's real space.
- Pure render/parse/adapter/template functions get real pytest tests. The visual layer is verified by **live use on real data** (the wire-real-first method *is* the verification), not by mockups.
- Accessibility treatment on new surfaces via **scoped classes**; shared tokens untouched.
- One screen fully (decide → wire real → tune → verify) before the next; small commits.

## Process from here
1. **June intent-skims this revised plan** ("does this capture what I meant?").
2. **Build incrementally**, starting with Task 1's two mockups. Small commits, live read-back, self-cleaning tests.

---

## Swarm findings ledger (how each was resolved)
**Convergent (multiple lenses — load-bearing):**
- *Mock-first = displacement + tests fake density* (architect + neurodiv-UX) → method split by job: mockups decide un-picturable structure, real-wiring builds + verifies density. Task 1 mockups are bounded/decision-oriented, not a tuning loop.
- *Tab accretion / 6A is a second overview screen* (architect + neurodiv-UX) → Task 1 puts tab-vs-fold-into-Today to June as a seen choice; folding into Today's existing slot is a live option.
- *6C rest-by-type = premature schema, fights signal_log* (architect + build agent) + *don't narrate rest-type back* (neurodiv-UX) → Task 5: uncategorized faithful dump; Phase 7 extracts later; classification never shown to June.
- *Reflect-back: production unspecified + compression-vs-verification + all-or-nothing repair* (build agent + author-informed + neurodiv-UX; cold reader flagged the term) → Task 3: deterministic template, compressed-but-expandable-to-exact-fields, per-item fix.
- *author/see/EDIT gap + where authoring lives* (architect + author-informed + neurodiv-UX) → authoring = overlay (resolved); Task 4 adds the edit path.

**Single-lens (specialty):**
- *build_context doesn't compute shape (factual error)* (build agent) → corrected; real work in Task 6.
- *Missing adapter / two-phase state / STREAMS / concurrency* (build agent) → Task 3 specifies all four.
- *6A: all-projects vs active; payload text-vs-JSON* (build agent) → Task 2: non-Done projects, structured JSON.
- *Engagement enum = metaphors + codes* (neurodiv-UX) → **June overruled**: she parses Sprint/Backburner fine; guard binds generated prose only.
- *6A modeled on superseded orient_map renderer* (neurodiv-UX) → access frame item 3 + Task 2 forbid it.
- *No-metaphors guard not code-enforced on new generated surfaces* (neurodiv-UX) → template reflect-back avoids fresh prose; any LLM-generated June-facing text enforces the guard in-prompt.
- *Shared-token retune reflows Today* (neurodiv-UX) → scoped classes; shared tokens untouched.
- *Two-signal mush; unassigned staleness/conflict; "spatial-time guard" undefined label* (author-informed) → Task 5 preserves the distinction; owners named above; the undefined label is dropped (the constraint it pointed at is covered by access-frame items 1 + 3).
- *Inbound-citation stumbles* (cold reader) — agent-facing doc; the load-bearing ones (the false shape claim, the undefined "spatial-time guard," the forward-referenced "reflect-back") are fixed above.
