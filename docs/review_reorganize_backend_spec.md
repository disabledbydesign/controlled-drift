# Review & Reorganize — backend spec (living)

> **Vendored 2026-07-17** from the Claude Design project *"HTML overlay mobile adaptation"*
> (`Review-Reorganize-Backend-Spec.md`). That project is the authoring surface; this file is
> the in-repo copy the build works from. If the two diverge, re-vendor rather than hand-editing.
> Companion: `docs/spec_deltas_2026-07-16.md`. Mockup: `design/mockups/review-reorganize-mobile-v4.html`.

Status legend: **DECIDED** (agreed, ready to build) · **PROPOSED** (surfaced in the UI, needs June's ok + a schema/logic change) · **OPEN** (needs a design pass).

This spec is derived from the mobile *Review & reorganize* surface and June's live edits. It captures the **data-model and backend changes** the UI now assumes. It is intentionally incremental — revise it as the surface evolves; do not try to land it all at once.

Source of truth for current schema: `scripts/build_*.py`, `scripts/review_surface.py`, `scripts/daily_plan.py`, `scripts/plan_generate.py`. Orient from the live system first (`describe_model.py`, `whats_open.py`) before building.

---

## 1. Apply-live model (replaces the export diff) — DECIDED
Today the surface stages edits client-side and exports a `controlled_drift_changes.json` diff that Claude applies separately. Target end-state: **the surface writes to Anytype directly**, with the same discipline as the `drift` skill — idempotent write → **read-back to confirm persistence** → then confirm + `notify.ding()`. Every applied change is **logged for the learning loop** (see §11) in the appropriate place (session/surface log).
- Keep the **export diff as a fallback** for when no backend/server is running.
- New surface actions map to deterministic writes: rename, field set, move (re-parent link), delete, create, **type-convert** (§5), **toggle recurring active** (§3).
- Files: a write endpoint alongside `surface_serve.py`; reuse `gsdo_objects.py` create/update + read-back.

## 2. Recurring mirrors Task — PROPOSED (schema extension)
> **Clarification (June):** Practices/Routines are **not** Strategies. A **Recurring** object is a recurring *action you do* on a schedule (water the plants, pay bills). A **Strategy** (§9) is a behavioral *rule for how the AI plans* ("when low energy, pick one small win"). Different types, different jobs — don't merge them.

Decision (June): **Recurring should carry the same fields as Task, except deadline/scheduling fields are replaced by recurrence logic.** Today `build_recurring.py` only has: Frequency, Has target/Target, Project link, Context, Day of week (multi), Day of month, Time of day, Duration min, Interval unit/count.

Add to the Recurring type (mirror Task, reuse the existing property keys so they're shared, not duplicated):
- `AI autonomous` (checkbox) — reuse Task's `gsdo_ai_autonomous`
- `Needs clarifying` (checkbox)
- `Access conditions` (multi_select) — reuse Task's, incl. the new options in §6
- `Access notes` (text)
- `Relevant docs` (text)
- `Blocked on` (text)
- `Affective` (text) — capacity signal, **never scalar-flatten** (guard #3)
- (`Duration min`, `Context` already present)

Explicitly **NOT** on Recurring: `Due date`, `Scheduled` (recurrence logic replaces them).

> ❌ **CUT (June, 2026-07-17) — reaffirms `spec_deltas_2026-07-16.md` §1.** The Practice/Routine distinction is dropped. It was briefly reinstated when reframed in plain language, but on reflection it gives the user nothing actionable: the recurrence **interval already encodes frequency**, and **nothing reads `target`** (no adherence/streak tracking exists or is planned). A recurring item is defined by its interval (`{unit, count}`) alone. Removed from the UI. Backend: run the delta §1 removal TODOs. If per-target adherence tracking is ever wanted, that is a *new* feature to spec, not a revival of this flag.

> **The one axis that stays: Scheduled vs. `as_needed`** (interval unit) — does it auto-populate on a cadence, or only when invoked? A *scheduling* choice, unrelated to the now-cut practice/routine idea. A recurring can be scheduled (trash every Tuesday) *or* as-needed (grocery run when low). Model it as the interval unit. See §3.
- File: `scripts/build_recurring.py` (idempotent add), then `verify_model.py` + `review_surface.py` PRIORITY/PRIMARY lists.

## 3. Recurring active/paused + `as_needed` + focus-period override — DECIDED
> **Primary use (June):** be able to **convert a one-time Task ↔ a Recurring** to correct the weeder LLM when it filed something as the wrong kind. That conversion lives in §5 (type conversion, data preserved). The active-toggle / as_needed / focus-period behavior below is the recurring-side model once an object *is* a Recurring.

The surface reframes recurring completion: **it is not "done" (that's per-occurrence); it is an on/off "in my daily plan" toggle.**
- Add `active` (or `paused`) boolean to Recurring. Default active. UI toggle = this flag. `daily_plan`/scheduler skip recurring anchors that are not active.
- **`as_needed` interval unit** (already in the schema enum) = a recurring with **no schedule at all**. It never auto-populates. It enters the plan only when:
  1. June toggles it **active** in this surface, OR
  2. the LLM adds it via the **Add tab** (capture), OR
  3. a **focus period overrides** it in — *even if it is not marked active.* → new capability: focus-period authoring can name recurrings to force-include for the period regardless of `active`.
- Scheduler logic: `active` gate is the default; focus-period force-include list bypasses it. Log toggles + focus-period overrides for the learning loop.
- Files: `build_recurring.py` (active prop), `daily_plan.py`/`scheduler.py` (active gate + as_needed handling), `focus_period*.py` (force-include list), `plan_generate.py`.

## 4. Block-level schedulable attributes + inheritance resolver — DECIDED
The daily plan is often generated at the grain of a **project/workstream block** ("work on GRA for 90 min"), not a discrete task. So embodiment/access + duration must live at that grain too.

> **June's framing — this is exactly the need:** a workstream usually has a **shared** accessibility profile that all its tasks follow, and a project may have a **predictable** access condition — *but* individual tasks (or subprojects/workstreams) sometimes **diverge** from that norm. So the model is **inherit-the-shared-default, override-when-it-differs.** That is precisely the resolver + tri-state below.

- Add to Project (and thus Subproject/Workstream): `Access conditions` (reuse), a **typical block duration** (`blockMin`/reuse Duration min semantics), and `Affective`.
- **Shared `effective(node, field)` resolver**: own value → else nearest ancestor's value (walk the Parent-project chain). This mirrors the **existing Side and `is_workstream` walk-ups** in `daily_plan.py`/`orient_map.py` — build one shared helper and point Side, is_workstream, access, block-duration, affective at it.
- **Tri-state per inheritable field** (needed): distinguish
  - **unset** = defer to parent (inherit), from
  - **custom** = own value, *including an explicit empty* ("intentionally none").

  Represent as: property **absent** = inherit; property **present** (even if empty) = custom. The resolver stops at the first ancestor where the key is present.
- Files: `build_project.py` (props), a shared `resolve.py`/helper for `effective()`, wire into `daily_plan.py` selection + `capture_generate.py`.

## 5. Type conversion (Task ↔ Recurring ↔ Subproject ↔ Workstream) — DECIDED
Miscategorised objects (often from the weeding gate) must be reclassifiable **without losing entered data.**
- Conversions: Task↔Recurring↔Subproject↔Workstream; top-level Project↔Workstream.
- Mapping: Task = `Task` type; Subproject/Workstream/Project = `Project` type (Workstream = `is_workstream` true; Subproject vs Project = nesting depth). Recurring = `Recurring` type.
- **Preserve all field values** on convert (fields not applicable to the new type stay stored, just unshown — reappear if converted back). Cross-type moves that change the Anytype object *type* need a create-new-of-type + copy-props + relink + delete-old, or an in-place type change if the API allows — decide per Anytype capability.
- Guard: an object with children cannot become a Task/Recurring (leaf types) — block until children are moved.
- Files: `gsdo_objects.py` (convert op with prop-carry + relink), guard in the shared write layer.

## 6. Access-condition option additions — DECIDED
Add to the `Access conditions` multi_select options:
- `Requires-deep-thinking`
- `Involves-bureaucracy`
- `Induces-pain` — physical-pain cost of the task; a capacity/access signal the scheduler and LLM should weigh (e.g. deprioritise on low-capacity days, pair with rest). Keep as an access-condition tag, not a scalar.

(Existing: Requires-talking-to-a-person, Can-be-done-lying-down, Involves-leaving-house.)
- File: wherever the Access conditions property tags are defined (`build_task.py`) + shared with Recurring/Project per §2/§4.

## 7. Goal status gates planning — CONFIRMED (already true)
`daily_plan.py` reads `gsdo_goal_status`; Parked/Achieved goals drop out of planning. Engagement governs *how* a goal is worked; status is the lifecycle gate. The surface shows **status + horizon** on goals and can **hide Parked/Achieved**. No change needed — documented so the UI and backend stay aligned.

## 8. Task: Due date vs. Scheduled are distinct fields — DECIDED
The surface exposes both, with distinct hints, because they answer different questions:
- **Due date** = the deadline. Drives urgency/ordering in the plan (same signal `plan_generate.py` uses today).
- **Scheduled** = the day the plan has actually placed the task (set by the scheduler or by June moving it). Not a deadline.

Backend must keep these as two separate date properties (do not collapse into one "date" field) and continue to read Due date for urgency while Scheduled is the placement record.

## 9. Strategy is a first-class type — DECIDED
Global, non-hierarchical behavioral directives (no parent, no children, not part of the Goal tree). Fields: **Applies when** (`Always | Low energy | Overwhelmed | Sprint | Stuck`), **Strategy status** (`Active | Retired`), **Directive** (the actual instruction text), **Notes**. The seeded examples in the UI (e.g. "when low energy, pick one small win and stop") are the shape — June's real strategies replace them. The daily-plan/context-assembly layer should pull **Active** strategies whose `when` matches the current state (or `Always`) into the prompt/context, the same way it reads Goal/Project fields today. Retired strategies drop out, same pattern as Parked goals.

## 10. Field audit — wired vs. not-yet-wired — OPEN
Per `structural_diagnosis_2026-07-11.md`, several stored fields drive no selection today: `barriers`, `arc_position_rationale`, `ai_autonomous`, `relevant_docs`, `access_notes`, Project `deadline` (loaded, unordered), and `affective` (in LLM context, no filter). Task `due_date` now feeds within-thread pick (2026-07-12).
- **Excitement**: **CUT (June)** — removed from the UI and to be **removed from the data structure** (`excitement_level`). It was never wired into selection and June opted to drop it rather than carry a dead field. Backend: delete the property (or stop building it) in the relevant `build_*.py`; scrub references in `review_surface.py`/verify lists.
- Action: decide per remaining field — wire it, or mark it "optional/not-yet-wired" in the UI (collapse/hide) so the detail page leads with load-bearing fields.

## 11. Learning-loop logging hooks — OPEN
Every applied edit (and every recurring toggle / focus-period override / type-convert / dedup decision) should emit a signal for the two-tier loop (`AI_LAYER_SPEC.md` §10). **Do not invent a new log** — route these through the **existing learning-loop logging framework** (the same session/surface logs the Add-tab capture already writes to); match its shape and location so surface writes land in the loop we already have.

## 12. Controlled vocabularies the surface assumes — DECIDED (reconcile with Anytype select options)
The write-back layer must map these to the existing Anytype select properties (create missing options idempotently; do not silently coin new ones). Note that **Engagement and Status are type-specific** — they are *not* one shared enum:
- **Goal engagement**: Backburner · Open · Steady · Sprint
- **Project/Subproject/Workstream engagement**: Backburner · Open · Steady · Sprint · Hyperfixation · Needs Clarifying · Done
- **Goal status**: Active · Parked · Achieved
- **Project status**: Active · Parked · Inactive
- **Task status**: Ready · Active · Blocked · In Design · Parked · Needs Clarifying · Done
- **Strategy status**: Active · Retired
- **Horizon** (Goal): Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing
- **Side** (Project/Subproject): Work · Daily life · Fun / hobby · Wellbeing  *(renamed from "Obligation" → "Work"; migrate the existing option value)*
- **Recurrence unit**: day · week · month · as_needed
- **Strategy "Applies when"**: Always · Low energy · Overwhelmed · Sprint · Stuck
- **Access conditions**: see §6.

These are the *display* vocabularies; confirm each against the live schema before writing (some may already exist under slightly different labels).

## 13. "Needs Clarifying" — reconsider whether it earns its place — OPEN
June's read: not convinced "Needs Clarifying" is useful **except when it flags something an agent could automate the clarification of** — otherwise it may just be premature scaffolding we haven't found the right use for. It currently exists three ways (Task `Needs clarifying` flag, `Needs Clarifying` Task-status option, `Needs Clarifying` Project-engagement option).
- Don't over-build. Leave it as-is for now; **revisit when a concrete "agent auto-clarifies this" use appears**, and at that point collapse to one canonical representation (most likely the boolean flag as the machine signal). Until then, treat the triplication as low-priority cleanup, not a blocker.

---

## 14. Today / plan surface — display deltas — DECIDED
- **Drop the per-item "why" rationale.** The plan no longer renders a per-task/per-block "why today" line, and the generator should **stop producing it** (was `item.why` / `block.why`). Remove it from the plan-generation prompt/output contract in `plan_generate.py` / `daily_plan.py`; do not spend tokens composing it. The *woven frame* (whole-day framing) stays — that's the one narrative the surface keeps, shown always-expanded.
- **Plan age line removed** from the surface (the "built this morning at HH:MM" timestamp). Keep `generated_at` in the plan payload for staleness logic/logging, just don't surface it here.
- **Held-back items** (`held_back_names`): the "· N more" affordance now expands to list them inline. Keep populating `held_back_names` per surfaced item (the names of same-thread items held for another day). If it's empty, the affordance is hidden.
- **Priority (fragmented-day) ordering.** The Priority view is a flat, ranked, no-clock list. ⚠ **Backend question to resolve:** what sets the order? Options: (a) the same generator ranking used to pick today's items (rank by focus-period front + engagement + neglect), surfaced as an explicit ordered `items[]`; (b) a stored user reorder that overrides generation for the day. Decide the source-of-truth and expose it as an ordered list on the plan payload (`shape:"priority"`, `items:[…]`), with any user reorder logged for the learning loop (§11).
- **Arc "here" advance.** When a plan block is an arc and its current (`state:"here"`) step is checked done, the next `ahead` step becomes `here`. This is a client rendering convenience today; if arc position is persisted server-side, mirror the advance on write.
- **"Life admin & household" regeneration preset.** Today's action row gains a preset that regenerates the plan prioritizing life-admin + household chores (the `Household` project + `Recurring` chores, side `Daily life`). Add it to the plan-regeneration presets alongside "Low energy" / "Quick wins" in `plan_generate.py`.
- **Block chunk-check is a completion, not a chunk-note.** The work-block's did-a-chunk check now reads as completion (strikes through the block title like a task), and the "did a chunk today — comes back tomorrow" caption is removed from the UI. The returns-tomorrow semantics still live in the backend (a chunked block reopens next day); the surface just doesn't narrate it.

## 15. Calendar-sourced recurring items are read-only reflections — DECIDED
A recurring item synced from a calendar object carries `source = "calendar"`. Its calendar-owned fields (title, `day_of_week`, `time_of_day`, interval) are a **one-way, read-only reflection** — edited only upstream in the calendar. App-native relations (`engagement`, `access_conditions`, `duration_estimate`/`blockMin`, `context`, notes) stay fully editable in GSDO and **never sync out**. No write-back to the provider (reaffirms the `AI_LAYER_SPEC.md` §454 privacy stance).
- Add `source` to Recurring (`select`: `manual` default | `calendar`).
- Every write path (this surface, MCP, drift skill) must **reject edits to calendar-owned fields when `source = calendar`**, allow the app-native ones. The surface renders the synced time as a locked "from Calendar" value with an "edit in your calendar" affordance.
- Scheduler treats set `day_of_week` + `time_of_day` as a fixed anchor already — no scheduler change; just ensure synced items land there.

## 16. Field options are schema-driven — CONFIRMED (UI contract)
The surface derives every field's option set (statuses, engagement, access conditions, frequencies, day-of-week, strategy triggers) from a single schema object with a `loadSchema()` seam for a live pull, rather than hardcoded lists. The write-back layer should treat the **relation schema as the source of truth for option sets** (consistent with `AI_LAYER_SPEC.md` §446); §12's vocabularies are the current snapshot of that schema, not a parallel hardcode to maintain.

> ⚠ **Implementation note (2026-07-17):** this implies a `GET /api/schema` endpoint that does not exist yet. The mockup's `defaultSchema()` (v4 lines 90–125) is the exact shape the UI expects; `loadSchema()` (v4 line 131) is the seam. The whole form/picker/chip/dropdown layer is generated from it — this endpoint is load-bearing, not optional.

## 17. Focus Period object — editor fields — DECIDED
The focus-period authoring/editor was rebuilt to reflect the real Focus Period object (per `scripts/build_focus_period.py`), surfaced as a directly-editable detail form. Fields the surface now reads/writes:
- **Name, Period (start / end), Intent** — existing; intent is the user's own words, never reworded by the generator.
- **Availability window** (`avail_start` / `avail_end` + note) — a *narrower* free window inside the period (e.g. caregiving days, mornings only). Empty = the whole period is available. Scheduler should treat this as the bound for placing work, distinct from the period's own start/end.
- **Plan shape override** (`plan_output`: Auto | Clock schedule | Priority list) — per-period override of the plan's rendered shape. Ties directly to §14's `shape` field: a period can force `shape:"schedule"` or `shape:"priority"`, else Auto lets the generator decide. Persist on the period and let `plan_generate.py` honor it.
- **Workday start + end** (`workday_start` / `workday_end`) — ⚠ **`workday_start` is NEW** (the object previously had only an end). Add it to the Focus Period type and to the scheduler's day-bounds logic (was end-only). Empty = system default.
- **Days off** (`days_off`: list of dates) — a per-period **override of the system's weekly days-off**, not a new global setting. Backend: store as period-scoped date list; scheduler uses period `days_off` when present, else falls back to the system weekly setting. (`days_on` / override-off-days is stubbed in the UI but not yet a committed field — leave OPEN.)
- **Foreground projects** (`front`) and **Paused projects** (`paused`) — two project lists. **Paused is filtered to "pausable" projects** in the picker: only those that would normally populate the plan (not Backburner/Done engagement, not Parked/Inactive status). Backend: while a period is active, `paused` projects are held out of plan generation; `front` projects are worked first. Both are project references, grouped by goal in the picker.

## 18. Theme / appearance — whole-surface look — DECIDED (client-side; optional server persist)
The surface ships **two complete visual themes** (one token set per look, every color/radius/font/glow/checkbox derived from it): **Celestial** ("space-girl future femme" — soft starfield, rose glow, round checks, pill chips) and **Hardware** ("cyberdeck hacker future femme" — instrument surface, beveled framed modules, LED status, mono-uppercase chrome, square checks). A toggle in **Settings › Theme** switches the whole app at once.
- **Purely presentational.** Theme changes no data, no schema, no option sets, no plan/scheduler behavior. It does not touch the §16 schema-driven option contract — vocabularies and field options are identical across themes; only their rendering differs.
- **Persistence is client-local by default.** Stored in `localStorage` (`cd_theme` = `celestial` | `hardware`, default `celestial`) and restored on load. No backend needed for v1.
- **Optional server persist (only if cross-device sync is wanted).** Store it the same way the **backend model choice** is stored — as a **user/app preference**, not on any Anytype domain object. This is a display preference, so it must **never** be written to Anytype objects or included in plan-generation context.

---

## Build order

**DECIDED and ready to build:** §1 (apply-live writes), §3 (recurring active/as_needed/focus-override), §4 (block-level attrs + `effective()` resolver + tri-state), §5 (type conversion, data-preserving), §6 (access options + `Induces-pain`), §8 (due vs. scheduled), §9 (Strategy type), §12 (vocabularies), §14 (Today-surface deltas), §15 (calendar `source`), §16 (schema-driven options), §17 (Focus Period fields — incl. NEW `workday_start`).

**DECIDED-but-schema-touching, sequence first:** §2 (Recurring mirrors Task — the property additions in §1/§3/§4/§6 all assume these keys exist).

**Remaining OPEN (not blockers, decide in-build):** §10 (field audit + Excitement removal), §11 (route logging through existing loop), §13 (Needs-Clarifying triplication — defer).

**Suggested order:** §2 schema → §1 write layer + read-back → §5 conversion → §3/§4 scheduler wiring → §17 focus-period fields (`workday_start` + per-period `days_off` touch the scheduler) → §11 logging → §14 Today-surface → §15 calendar sync.

---

### Parking lot (not backend, tracked elsewhere)
- Data reorg from June's export notes (job-search subproject structure, household/self-care/medical/social subprojects, crafts/leatherworking split, recurring-ize bills/chores) — content edits, done through the surface, not schema.

### Superseded by the 2026-07-17 planning session
- ~~"Desktop two-pane layout of this surface (UI, separate track)."~~ The desktop layout **is already designed** in v4 (`deskApp()`, resizable multi-column browser with breadcrumb bar). Not a separate track.
- The new surface replaces **both** `docs/overlay_daily.html` **and** `scripts/surface_template.html` + `scripts/surface_serve.py` (confirmed by June, 2026-07-17). Two servers and two token sets consolidate into one app.
