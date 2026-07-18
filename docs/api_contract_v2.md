# API contract v2 — the frontend/backend seam for the unified surface

> **Purpose.** The new *Review & reorganize* UI (`design/mockups/review-reorganize-mobile-v4.html`)
> replaces **both** `docs/overlay_daily.html` (served by `scripts/server.py`) **and**
> `scripts/surface_template.html` + `scripts/surface_serve.py` + `scripts/review_surface.py`.
> Frontend and backend are being built **in parallel by separate agents**. This document is the
> only thing making that safe: it is the agreed seam. The frontend builds against the fixtures;
> the backend must return these shapes.
>
> **Why this can be written up front rather than guessed:** the mockup ships **complete fixture
> data** (`seed()`, `seedStrategies()`, `seedPlan()`, `seedPeriods()`, `defaultSchema()`). Every
> response shape below is **read off those fixtures**, not invented. Where the fixture and the
> live backend disagree, both are shown so the backend track knows the exact delta.
>
> Companion documents: `docs/review_reorganize_backend_spec.md` (the authority on intended
> data-model changes — cited below as **spec §N**), `docs/spec_deltas_2026-07-16.md`.
>
> **Conventions in this doc.** Shapes are TypeScript-ish. `?` = optional. Anything I inferred
> rather than read directly is marked **[INFERRED]**. Anything genuinely undetermined is in §6,
> not silently resolved.

---

## 0. Orientation: what the mockup actually declares

Three facts about the mockup shape this whole contract, and the frontend agent should know them:

1. **There is exactly one declared network seam in the entire 1179-line mockup.**
   `loadSchema()` (line 131) contains a commented-out `fetch('/api/schema')`. A grep for `fetch(`
   returns that single hit. Everything else — tree, plan, periods, strategies — is an in-memory
   fixture with a synchronous mutation method. **The frontend track's first structural job is
   therefore to introduce the data layer the mockup does not have**, using the fixtures as the
   contract for what that layer must return. The mutation methods (`setVal`, `move`, `del`, …)
   are all local-state-only today and each one becomes a network call (see §4).

2. **The only persisted client state is the theme.** `localStorage` is used for exactly one key,
   `cd_theme` (`celestial` | `hardware`). Matches spec §18 — presentational, no backend needed.

3. **The plan fixture is one revision ahead of itself in one place and one behind in another.**
   `seedPlan()` still carries `why:` on its items, but a grep for `.why` in the render code returns
   **0 uses** — the render layer already complies with spec §14's "drop the per-item why". Treat
   `why` as **dead**: the generator should stop producing it, and the frontend must not render it.
   Conversely the fixture omits `held_back` counts that the backend already produces.

---

## 1. Endpoint inventory

**Status legend:** `EXISTS` = current endpoint already returns what the UI needs ·
`CHANGE` = exists, shape/behavior must change · `NEW` = must be built.

### Reads

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/api/schema` | Relation vocabularies + per-level control tuples + per-level note fields. The entire form/picker/chip/dropdown layer is generated from this. | **NEW** |
| GET | `/api/tree` | The whole object graph (Goal → Project → Subproject → Workstream → Task/Recurring) as nested nodes with typed `vals`. Backs the Review tab. | **NEW** |
| GET | `/api/strategies` | Flat list of Strategy objects. Separate from the tree — Strategy is global and non-hierarchical (spec §9). | **NEW** |
| GET | `/api/map` | Structured nested map data for the Map tab. | **CHANGE** — returns 66-col monospace **text** today; must return JSON. See §3.2. |
| GET | `/api/plan` | Today's plan. | **CHANGE** — key renames + `kind` discriminator + `shape` always present. See §2.4. |
| GET | `/api/periods` | **All** focus periods (current + upcoming) with the full spec §17 field set. | **CHANGE** — `/api/period` today returns only the *active* period, pre-rendered for display. See §2.5. |
| GET | `/api/actions` | Regeneration preset buttons for the Today action row. | **CHANGE** — add the "Life admin & household" preset (spec §14). |
| GET | `/api/status` | Generation state `{idle\|running\|error}` + plan timestamp, for polling after a regenerate. | EXISTS |
| GET | `/api/projects` | Flat project list w/ side + engagement + parent — the Focus-period `front`/`paused` pickers. | EXISTS |
| GET | `/api/project-summaries` | Per-project "what it is / next step" parsed from Context. | EXISTS |
| GET | `/api/session?stream=capture` | The Add-tab receipt (every capture this session, undoable). | EXISTS |
| GET | `/api/settings` | Which LLM backend is live + option descriptors + health. | EXISTS |
| GET | `/api/focus/status` | Poll the async focus-period authoring run. | EXISTS |
| GET | `/api/focus/result` | Structured fields + reflect-back for the authoring confirm surface. | EXISTS |
| GET | `/api/focus/edit-fields` | The active period as editable fields (direct edit, no LLM). | **CHANGE** — must include `workday_start` (spec §17). |
| GET | `/` , `/assets/*` | Serve the built app bundle. | **CHANGE/NEW** — see §3.3. |

### Writes

| Method | Path | Purpose | Status |
|---|---|---|---|
| POST | `/api/object` | Create an object (`addChild`, `capture`). | **NEW** |
| PATCH | `/api/object/{id}` | Set title and/or one-or-more field values (`setTitle`, `setVal`, `toggleMulti`). | **NEW** |
| POST | `/api/object/{id}/clear-field` | Remove a property so it inherits again — the tri-state "unset ≠ empty" of spec §4. | **NEW** |
| POST | `/api/object/{id}/move` | Re-parent (`move`). | **NEW** |
| POST | `/api/object/{id}/type` | Type conversion, data-preserving (`setType`, spec §5). | **NEW** |
| DELETE | `/api/object/{id}` | Archive (`del` / `askDelete`). | **CHANGE** — `task_actions.archive_object()` exists but is only reachable via `/api/capture/undo`; needs a general route. |
| POST | `/api/complete` | Check off a task / arc step / block chunk. | **CHANGE** — must return the re-fetched object, not `{ok, …}`. See §4. |
| POST | `/api/uncomplete` | Undo a check-off. | **CHANGE** — same read-back requirement. |
| POST | `/api/recurring/active` | The Recurring in-my-plan on/off toggle (`toggleActive`, spec §3). | **CHANGE** — same read-back requirement. |
| POST | `/api/task/reschedule` | Anchor a when-token to a real date. | **CHANGE** — same read-back requirement. |
| POST | `/api/task/move` | Reorder/defer a row **within today's plan** (cache-only). | EXISTS |
| POST | `/api/task/not-today` | Drop a row from today only (cache-only, no Anytype write). | EXISTS |
| POST | `/api/duration` | Correct a task's duration estimate. | EXISTS |
| POST | `/api/plan/priority-order` | Persist the user's drag-reorder of the Priority view (`priOrder`). | **NEW** — *and gated on open question Q1, §6.* |
| POST | `/api/refresh` | Regenerate the plan (async 202 → poll `/api/status`). | EXISTS |
| POST | `/api/negotiate` | Regenerate with a preset or freetext instruction. | EXISTS |
| POST | `/api/capture` | Weed freetext into typed/linked objects (async 202). | EXISTS |
| POST | `/api/capture/undo` | Archive a just-captured object. | EXISTS |
| POST | `/api/logday` | Log-mode entry, tagged `day` / `issue`. | **CHANGE** — UI tag labels are `The day` / `Friction`; server accepts `day` / `issue`. Agree a mapping. |
| POST | `/api/settings` | Set the LLM backend / hobby-block flag. | EXISTS |
| POST | `/api/focus/author` · `/reflect` · `/commit` · `/edit` · `/update` | Focus-period authoring + editing flow. | **CHANGE** — must carry the spec §17 fields incl. new `workday_start`. |
| OPTIONS | `*` | CORS preflight. | **NEW** — see §3.4. |

**Counts: 15 EXISTS · 13 CHANGE · 10 NEW** (38 rows; the `/api/focus/*` write row bundles five
endpoints — `author`, `reflect`, `commit`, `edit`, `update` — that all change identically, so the
true endpoint count is higher than the row count).

---

## 2. Payload schemas

### 2.1 `GET /api/schema` — NEW

Read verbatim off `defaultSchema()` (mockup lines 90–125). `applySchema()` derives `OPTS`/`CTRL`/`TEXT`
from it, so **this exact nesting is load-bearing** — do not flatten it.

```ts
interface Schema {
  relations: Record<RelKey, { label: string; options: string[] }>;
  controls:  Record<Level, Control[]>;
  notes:     Record<Level, [label: string, valKey: string][]>;
}

type Level  = 'GOAL'|'PROJECT'|'SUBPROJECT'|'WORKSTREAM'|'TASK'|'RECURRING'|'STRATEGY';
type RelKey = 'goalEng'|'goalStatus'|'horizon'|'proj'|'projStatus'|'side'|'taskStatus'
            | 'access'|'unit'|'dow'|'strategyState'|'strategyStatus';

// Positional tuple — the UI destructures by index, so arity and order matter.
type Control =
  | [kind: 'select', label: string, valKey: string, relKey: RelKey, hint?: string]
  | [kind: 'multi',  label: string, valKey: string, relKey: RelKey, hint?: string]
  | [kind: 'date',   label: string, valKey: string, relKey: null,   hint?: string]
  | [kind: 'number', label: string, valKey: string, relKey?: null,  hint?: null]
  | [kind: 'time',   label: string, valKey: string]
  | [kind: 'toggle', label: string, valKey: string]
  | [kind: 'recur',  label: string, countKey: string, unitKey: string];
```

The current option sets (spec §12 is the snapshot; the live relation schema is the source of truth
per spec §16):

| relKey | label | options |
|---|---|---|
| `goalEng` | Engagement | Backburner · Open · Steady · Sprint |
| `goalStatus` | Status | Active · Parked · Achieved |
| `horizon` | Horizon | Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing |
| `proj` | Engagement | Backburner · Open · Steady · Sprint · Hyperfixation · Needs Clarifying · Done |
| `projStatus` | Status | Active · Parked · Inactive |
| `side` | Side | Work · Daily life · Fun / hobby · Wellbeing |
| `taskStatus` | Status | Ready · Active · Blocked · In Design · Parked · Needs Clarifying · Done |
| `access` | Access conditions | Requires-talking-to-a-person · Can-be-done-lying-down · Involves-leaving-house · Requires-deep-thinking · Involves-bureaucracy · Induces-pain |
| `unit` | Frequency | day · week · month · as_needed |
| `dow` | Day of week | Mon · Tue · Wed · Thu · Fri · Sat · Sun |
| `strategyState` | Applies when | Always · Low energy · Overwhelmed · Sprint · Stuck |
| `strategyStatus` | Status | Active · Retired |

**Implementation note.** The live data needed to build this already exists behind
`scripts/gsdo_anytype.py` (`find_type`, `find_property`, and the type-detail call
`GET /spaces/{sid}/types/{id}` that `scripts/describe_model.py:52` already makes to read each
type's properties and formats). `describe_model.describe()` renders that to text; the schema
endpoint is the same read rendered to JSON. **The `controls`/`notes` ordering and the `hint`
strings are UI-authored, not derivable from Anytype** — they should live server-side as a
declarative table that is *merged with* the live option sets, so option vocabularies stay
schema-driven (spec §16) while field order stays intentional.

**Known live-schema divergences the backend must reconcile before this endpoint is honest:**
- `Applies when` is built with only `["Active"…]`/`["Always","Low energy"]` in
  `scripts/build_strategy.py:15` — **missing Overwhelmed / Sprint / Stuck**.
- The Strategy type has `What for` / `Learning notes` / `Context`, but the UI's notes list is
  `Directive` + `Notes`. **`Directive` has no live property.** [INFERRED] the intent is that
  `Directive` is a new field (spec §9 names it explicitly as a field), *not* a rename of
  `What for` — but that mapping is unconfirmed. Flagged in §6 (Q4).
- `Side` needs the `Obligation` → `Work` option migration (spec §12).
- `Excitement` is to be deleted from the data structure (spec §10).

### 2.2 `GET /api/tree` — NEW

Read off `seed()` (mockup lines 197–266). Note `vals` is an **open string-keyed bag**, not a fixed
struct — that is deliberate, because `controls`/`notes` in the schema name the keys.

```ts
interface TreeResponse { nodes: Node[]; }   // top level = Goals

interface Node {
  id: string;                 // real Anytype object id
  level: Level;               // GOAL|PROJECT|SUBPROJECT|WORKSTREAM|TASK|RECURRING
  type: 'Goal'|'Project'|'Task'|'Recurring';   // the Anytype type
  title: string;
  vals: Record<string, string|number|boolean>;  // ONLY keys actually set — see tri-state below
  children: Node[];
}
```

**`level` vs `type` is a real distinction, not redundancy.** Per spec §5: Subproject, Workstream
and Project are all the Anytype type `Project`; Workstream is `is_workstream = true`; Subproject vs
Project is nesting depth. The UI needs the finer `level` to pick the right control set. The backend
must compute `level` from (type, `is_workstream`, depth).

**Tri-state is expressed by key presence, and this is load-bearing (spec §4).** `effective()`
(line 486) and `clearVal()` (line 487) both use `hasOwnProperty`:
- key **absent** → inherit from nearest ancestor that has it
- key **present**, even as `''` → an explicit own value ("intentionally none")

So the serializer **must not** emit `null`/`''` placeholders for unset fields. Emitting a
default-filled `vals` object silently destroys inheritance across the whole tree.

Observed `vals` keys in the fixture, by level:

| Level | keys seen |
|---|---|
| GOAL | `engagement`, `status`, `horizon`, `reaching`, `resolution`, `context`, `barriers` |
| PROJECT | `engagement`, `status`, `side`, `deadline`, `blockMin`, `access`, `reaching`, `description`, `context`, `affective`, `barriers` |
| SUBPROJECT | as PROJECT minus `deadline` |
| WORKSTREAM | `engagement`, `status`, `blockMin`, `access`, `reaching`, `context` |
| TASK | `status`, `due`, `scheduled`, `duration`, `ai`, `needs`, `access`, `context`, `accessNotes`, `affective`, `blocked`, `docs`, `done` |
| RECURRING | `count`, `unit`, `dow`, `dom`, `tod`, `duration`, `ai`, `needs`, `access`, `context`, `accessNotes`, `affective`, `blocked`, `docs`, `source`, `paused` |
| STRATEGY | `when`, `status`, `directive`, `context` |

Two `vals` keys are **not** in any `controls`/`notes` list and are therefore driven by dedicated UI,
not the generic form — the backend must still round-trip them:
- `done` (TASK) — the checkbox; `toggleDone` also flips `status` to `Done`/`Ready`.
- `source` (RECURRING) — `'calendar'` marks calendar-owned fields read-only (spec §15). The fixture
  sets it on `r-therapy`. Default `'manual'`.
- `paused` (RECURRING) — `toggleActive` flips it. **Naming conflict:** spec §3 specifies an
  `active` boolean (default active); the UI stores the inverse, `paused`. One side must adapt —
  see §6 (Q3).

`multi` fields are **comma-joined strings**, not arrays: `toggleMulti` (line 283) does
`.split(',').map(trim)` … `.join(', ')`. The fixture confirms it (`access:'Involves-leaving-house'`).
The backend stores these as Anytype multi-selects, so the serializer must join and the parser must
split. [INFERRED] a cleaner contract would be `string[]`, but the mockup's read *and* write paths
both assume the joined string, so the contract keeps the string and the backend does the conversion.

### 2.3 `GET /api/strategies` — NEW

Read off `seedStrategies()` (lines 267–276).

```ts
interface StrategiesResponse { strategies: StrategyNode[]; }
interface StrategyNode {
  id: string;
  level: 'STRATEGY';
  type: 'Strategy';
  title: string;                                  // the rule, in June's words
  vals: { when?: string; status?: string; directive?: string; context?: string };
  children: [];                                   // always empty — global, non-hierarchical
}
```

### 2.4 `GET /api/plan` — CHANGE

This is the largest delta. **Current** shape (`scripts/plan_store.py:8`, built in
`scripts/daily_plan.py:895–960` and `scripts/plan_generate.py:318–336, 380–392`):

```ts
// CURRENT
{
  woven_frame: string;
  shape?: 'priority';                 // present ONLY on fragmented days; absent means schedule
  header?: string;                    // priority shape only
  blocks?: { label, time, framing, items: Item[] }[];   // clock shape
  items?: Item[];                                       // priority shape (flat)
  appointments?: Item[];
  still_here: { label: string; note: string }[];
  generated_at: string;               // ISO
  source: string;                     // "generate" | "refresh" | "negotiate"
}
// CURRENT Item — a flag-bag, not a discriminated union
{
  time: string; task: string; project: string|null; why: string|null;
  interstitial: boolean;              // true => a break
  id?: string;
  block?: true; block_project?: true; // the two block flavours
  project_id?: string; arc?: Step[]; chunk_min?: number;
  absorbed_ids?: string[]; did_chunk_today?: boolean;
  held_back?: number; held_back_names?: string[];
  description?: string; recurring?: true; as_needed?: boolean; done?: boolean;
}
```

**Required** shape, read off `seedPlan()` (lines 786–804):

```ts
// REQUIRED
interface Plan {
  date: string;            // "Wed Jul 16" — display-formatted [INFERRED: the UI renders it raw]
  generated: string;       // human sentence; NOT surfaced (spec §14 removed the plan-age line)
  shape: 'schedule' | 'priority';   // ALWAYS present, both shapes
  woven: string;           // was `woven_frame`
  blocks: Block[];         // schedule shape
  items?: PlanItem[];      // priority shape (flat, ordered)
  stillHere?: { label: string; note: string }[];   // [INFERRED] — see below
}

interface Block { label: string; time: string; framing: string; items: PlanItem[]; }

type PlanItem = TaskItem | BlockItem | BreakItem;   // discriminated on `kind`

interface TaskItem {
  kind: 'task';
  id: string;              // real Anytype task id — the checkbox writes against this
  time: string;
  durationMin?: number;
  description?: string;
  heldBack?: string[];     // names of same-thread items held for another day
  done?: boolean;
  recurring?: boolean; asNeeded?: boolean;   // routing flags, carried through
}

interface BlockItem {
  kind: 'block';
  id: string;              // project id
  task: string;            // "Work on the reviewer response"
  time: string;
  chunkMin: number;
  arc?: Step[];
  didChunkToday?: boolean;
}

interface BreakItem { kind: 'break'; time: string; task: string; }   // no id, not checkable

interface Step { text: string; state: 'done'|'here'|'ahead'; id?: string; }
```

**Delta list for the backend track:**

| Current | Required | Note |
|---|---|---|
| `woven_frame` | `woven` | rename |
| — | `date` | new; display-formatted day string |
| `shape` present only on priority days | `shape` always `'schedule'\|'priority'` | the UI branches on it unconditionally |
| `interstitial: true` / `block: true` / `block_project: true` flags | `kind: 'task'\|'block'\|'break'` | **collapse the flag-bag into one discriminator.** `interstitial → 'break'`; `block → 'block'`; `block_project` → a `'task'` that the client groups under a block header |
| `chunk_min` | `chunkMin` | rename (snake → camel throughout) |
| `held_back` (count) + `held_back_names` | `heldBack: string[]` | the count is derivable from `.length`; spec §14 says the "· N more" affordance expands to the names inline |
| — | `durationMin` | not currently on the row; must be emitted |
| `why` on every item | **removed** | spec §14; render layer already ignores it (0 uses) |
| `generated_at` | `generated` + keep `generated_at` | spec §14: keep the timestamp in the payload for staleness logic, just don't surface it |
| `still_here` | `stillHere` | **[INFERRED]** — `seedPlan()` has **no** still-here field at all. Either the new UI drops the still-here list, or it is rendered somewhere I did not locate. Flagged in §6 (Q5). |
| `appointments[]` | *(unmapped)* | **[INFERRED]** — the current payload carries `appointments: [{id, task, time:"HH:MM", duration_min, recurring:true, as_needed}]` on **both** shapes: today's fixed-time Recurring anchors. `seedPlan()` has no equivalent; the fixture's only timed non-task row is a `break`. Either appointments become `kind:'task'` rows inline, or the field is dropped. Flagged in §6 (Q9). |

**Already matching — do not change:** the `arc` step shape. `scripts/grain.py:91` `project_arc()`
already returns exactly `{text, state: 'done'|'here'|'ahead', id}` with `id` being the real Anytype
task id, which is precisely the mockup's `arc:[{text,state,id}]`. This is the one place the two
sides already agree; preserve it.

### 2.5 `GET /api/periods` — CHANGE

**Current:** `/api/period` calls `period_view.render_period()` and returns the *active* period only,
pre-rendered for display, with `{"active": false}` as the empty state. The new Focus tab needs the
**list** (it filters `when === 'now'` and `when === 'upcoming'`) with raw editable fields.

Read off `seedPeriods()` (lines 805–812) and `saveFocus()` (line 920):

```ts
interface PeriodsResponse { periods: Period[]; }
interface Period {
  id: string;
  when: 'now' | 'upcoming';   // derived server-side from start/end vs today [INFERRED]
  name: string;
  start: string; end: string;             // ISO "2026-07-14"
  intent: string;                         // June's own words — never reworded (spec §17)
  front: string[];                        // foreground projects
  paused: string[];                       // paused projects
  note: string;                           // availability note
  availStart: string; availEnd: string;   // '' = whole period available
  daysOff: string[];                      // ISO dates
  daysOn: string;                         // stubbed in UI, NOT a committed field (spec §17)
  output: 'Auto' | 'Clock schedule' | 'Priority list';
  workdayStart: string; workdayEnd: string;  // "HH:MM", '' = system default
}
```

**Live-schema check** (`scripts/build_focus_period.py:15–32`): `Period start`, `Period end`,
`Intent`, `Availability start/end/note`, `Days off`, `Days on`, `Output format`, `Workday end`,
`Foreground projects`, `Paused projects` all exist. **`Workday start` does not exist** — confirms
spec §17's ⚠, and it must be added to the type *and* to the scheduler's day-bounds logic, which is
end-only today.

`front`/`paused` are **project name strings** in the fixture but `objects` (id references) in
Anytype. [INFERRED] the backend should send ids and the UI resolve names via `/api/projects` —
but the fixture unambiguously uses names, so **either the contract sends `{id, name}` pairs or the
frontend must be told to expect ids**. Recommend `{id, name}[]`; flagged in §6 (Q6).

### 2.6 Endpoints kept as-is

`/api/status`, `/api/projects`, `/api/project-summaries`, `/api/session`, `/api/settings` (GET+POST),
`/api/focus/status`, `/api/focus/result`, `/api/refresh`, `/api/negotiate`, `/api/capture`,
`/api/capture/undo`, `/api/task/move`, `/api/task/not-today`, `/api/duration`. Their current shapes
are adequate; the frontend can code against them directly.

Notes the frontend track needs:
- `/api/settings` returns `{backend, options: [{id, label, mechanism, model}], include_hobby_block,
  health}`. `options` is computed live by `plan_generate.backend_descriptor` over
  `("mistral", "openrouter", "claude", "local")` — **four**, while the mockup's Settings panel
  hardcodes three (`claude` / `local` / `api`, lines 1153–1162) and the server's default is
  `mistral`, which the mockup does not offer at all. The UI must render `options[]` from the
  response; the server computes real routing descriptors precisely so the UI cannot drift.
- `/api/actions` returns `{version, presets: [{id, label, operation, capacity_flag?, payload}]}`,
  merged by id from defaults on read so new fields propagate without deleting the file. Current
  preset ids: `low-energy`, `quick-wins`, `stuck`, `add` (UI-only, no payload). Spec §14 adds the
  "Life admin & household" preset here.
- `/api/project-summaries` is keyed by project **name, not id**, and only includes projects whose
  Context text actually parses. [INFERRED] joining by name is fragile if two projects share one —
  consider re-keying by id as part of this work.
- `/api/focus/edit-fields` returns `fields` as a **flat snake_case dict** from
  `focus_period_adapter.period_to_fields`: `name, start_date, end_date, intent, availability_start,
  availability_end, availability_note, days_off[], days_on[], output_format, workday_end,
  foreground_projects[], paused_projects[]`. The mockup's `Period` (§2.5) is camelCase with
  different names (`start`, `end`, `availStart`, `daysOff`, `output`, `workdayEnd`, `front`,
  `paused`). **Agree one naming convention across the seam and apply it in one place** — a per-field
  translation layer maintained on both sides is exactly how these two tracks would diverge.
- `/api/logday` accepts tags `day` | `issue`; the UI's buttons read `The day` | `Friction`
  (line 1130). Map in the client, or widen the server's allow-list. Pick one and write it down.
- `/api/capture` polls **`/api/status`** — the *shared* plan-generation status, not a capture-specific
  one — then reads `/api/session?stream=capture` for the result. `/api/focus/author` and
  `/api/focus/edit` poll a *different* endpoint, `/api/focus/status`. Easy to wire wrong.
- Async writes return **202 `{state, started}`**, and `started: false` means a run was already in
  flight — **not an error**. The UI must not surface it as a failure.
- `/api/focus/commit` returns **200 `{"blocked": [labels]}`** when required fields are missing — a
  200, not a 4xx. The client must check the body, not just the status code. [INFERRED] this is worth
  changing to a 4xx under the new contract, but it is a behavior change that would break the current
  overlay if both run during the transition.

---

## 3. Known gaps — what must be built

### 3.1 `GET /api/schema` does not exist, and the whole form layer depends on it

**Status: load-bearing, build first.** Confirmed by reading `do_GET` (`scripts/server.py:330–472`):
there is no schema route. `defaultSchema()` is the exact required shape (§2.1).

Why it blocks everything: `applySchema()` derives `this.OPTS` / `this.CTRL` / `this.TEXT`, and every
select, multi-select chip, toggle, date picker, number field, recurrence editor and notes textarea
in the detail pane is generated by iterating those. There is no hardcoded form anywhere in the
mockup. A stubbed or wrong schema does not degrade the UI — it produces an empty one.

**Build guidance.** Serve a merge of two sources:
1. **Option sets from live Anytype** — the read `describe_model.py:52` already performs
   (`GET /spaces/{sid}/types/{id}` → `properties[]` with `name` + `format`), plus the select tags
   per property. Spec §16 makes the relation schema the source of truth for option sets.
2. **Field order, labels and hints from a server-side declarative table** — `controls`/`notes` carry
   UI intent (ordering, the "Block-level default — tasks inherit unless they set their own." hint,
   the due-vs-scheduled hints of spec §8) that Anytype cannot supply.

Because `loadSchema()` is `async` and the UI calls `applySchema() + bump()` after it, a slow live
read is tolerable — but ship `defaultSchema()` as the client-side fallback so a schema fetch failure
degrades to the last-known vocabulary rather than a blank form.

### 3.2 `/api/map` returns text, not data

**Current:** `scripts/server.py:361–368` calls `orient_map.render_map(PROJECT_NAME)` and sends the
result as `text/plain`; on failure it returns a 500 whose body is also plain text
(`"(map render failed: …)"`), so a client expecting JSON gets a parse error rather than a readable
error. `PROJECT_NAME` is **hardcoded to `"Build Controlled Drift"`** at line 303 — the new Map tab
presumably needs to map any project, so the endpoint should take `?project=` (or an id) rather than
inherit that constant. `scripts/orient_map.py` (858 lines) fuses tree-walking with ASCII formatting
against constants `_BASE="   "`, `_LABEL_W=11`, `_VALUE_COL=16`, `_WIDTH=66` (lines 64–67).

**Recommended refactor: extract `map_tree()` returning nested dicts; keep `render_map()` as a text
view over it.** The fusion points, from a full read of the module:

| Function | Line | What's fused |
|---|---|---|
| `_arc_lines` | 251–272 | Lines 258, 262–269 derive real state (ordered steps; first not-done = "here", rest = "todo"); 260, 271 turn it into `"   The arc:"` and `f"      {icon} …"`. |
| `_detail_lines` | 232–243 | Parses context then **discards two of three parsed values**, wraps, splices arc lines. |
| `_append_flat_streams` | 400–437 | 402–424 segment topo-sorted streams into **parallel groups** by consecutive equal `(depth, stream_order)` — a genuine structural concept that **exists nowhere except the string `"  — running alongside —"`**. |
| `_append_grouped_streams` | 440–490 | Encodes **nesting depth as a hardcoded 2-space prefix** (461, 465, 472, 477). Depth exists only as literal indent. Also descends **only one level**, though the data is arbitrarily deep. |
| `render_map` | 493–578 | 500–527 is pure selection/derivation; 529–578 builds lines; the `_finish()` closure (546–554) is both formatter and return path, so empty-state control flow is entangled with rendering. |

Recommended target shape:

```ts
map_tree(project_name): {
  project: { id, name };
  goal: { id, name, horizon, reaching_for } | null;
  workstreams: { id, name }[];
  done: Node[];
  groups: Group[];
  empty_reason: 'no_streams' | 'no_project_level_streams' | null;
} | null   // null = project not found; replaces the "(no project …)" string at line 503

Group = { depth: number; stream_order: number|null; parallel: boolean; streams: Node[] }

Node = {
  id; name;
  engagement: 'active'|'later'|'done';   // semantic, NOT the glyph
  is_workstream: boolean; is_grouping: boolean;
  depth: number; stream_order: number|null; depends_on: string[];
  what_it_is: string|null; next_step: string|null;
  arc_note: string|null; arc_rationale: string|null;
  is_structured: boolean;
  steps: Step[]; children: Node[]; children_done: Node[];
}
Step = { id; name; status: string|null; done: boolean; state: 'done'|'here'|'todo'; order: number|null }
```

**Keep unchanged** (already pure): `_load` (322), the field accessors `_props`/`_sel`/`_txt`/`_objs`,
the `_is_*` predicates, `_topo_sort_streams` (279), `_steps_for` (360), `_children_of` (376),
`_workstream_descendants` (388), `_parse_context` (193), `_wrap` (70), `missing_descriptions`,
`gap_streams`. **Rewrite as thin views** over `map_tree`: `render_map`, `render_stream`, `_header`,
`_detail_lines`, `_arc_lines`, and both `_append_*`. **Leave alone:** `render_map_agent` (698–777) —
it is a second independent walk with different rules and would drag `_AGENT_FIELDS` into the node
shape; folding it in is a worthwhile follow-up, not a prerequisite.

Three things this refactor forces into the open, which the contract should decide rather than
inherit by accident:
1. `render_map` descends **one** level under a grouping. A nested-JSON consumer wants full
   recursion — that is a **behavior change**, not just a refactor.
2. "Later" (Backburner) streams currently suppress their arc entirely (429–431, 481–484). In a
   structured tree, prefer emitting `steps` and letting the client decide — but that changes the
   payload's meaning.
3. `next_step`, `arc_note` and `arc_rationale` are already computed and then discarded on the map
   path. Exposing them is free and is probably what a drill-in UI wants — note it as an intentional
   widening rather than letting it look accidental.

### 3.3 No static-asset route

**Confirmed** by reading `do_GET`. `scripts/server.py` serves exactly two files:
`/` → `OVERLAY_HTML` (lines 331–343, `Cache-Control: no-store`) and `/manifest.webmanifest`
(345–352). Every other path falls through to `{"error": "no route …"}` (line 472). There is no
directory handler, no MIME-type mapping, no path-traversal guard.
`scripts/surface_serve.py` similarly serves only `/`, `/favicon.ico` and `POST /rebuild`.

**Must build:** a static route serving a build directory (`/assets/*` or a catch-all fallback),
with (a) a MIME map covering at minimum `.js`, `.css`, `.map`, `.woff2`, `.svg`, `.png`;
(b) a path-traversal guard — `os.path.realpath` containment check, since `http.server`'s stdlib
translate_path is not in use here; (c) an SPA fallback returning `index.html` for unknown non-`/api`
paths **[INFERRED]** — the mockup is a single class component with internal tab state, so it likely
needs no routing, but a fallback costs nothing and prevents a class of dev-server confusion.

### 3.4 No CORS headers

**Confirmed definitively:** `_send` (line 309) sets only `Content-Type` and `Content-Length`; the
two static branches add `Cache-Control`. `grep` for `Access-Control` across `scripts/server.py`
returns nothing, and there is **no `do_OPTIONS` method** on either server — so a preflight gets a
501 from `BaseHTTPRequestHandler`.

**Must build:** on every response, `Access-Control-Allow-Origin` (echo the dev origin, or `*` —
this binds to localhost and holds health/financial data, so **do not** add
`Allow-Credentials: true` alongside `*`), plus `Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS`
and `Allow-Headers: Content-Type`. Add a `do_OPTIONS` returning 204 with those headers. Without
this, the frontend agent cannot run a Vite/dev server on a second port against the real backend at
all — this blocks parallel work from day one, so it should land early.

---

## 4. Write-path contract

Spec §1: the surface writes to Anytype **directly**, with the `drift` skill's discipline —
idempotent write → **read-back to confirm persistence** → then confirm. The repo's CLAUDE.md states
it plainly: *a good answer is not a saved object.*

**The current server is inconsistent at the response boundary — this is the delta to close.**
The underlying helpers genuinely read back (see below), but the HTTP layer discards most of the
result. Three tiers exist today:

- **Returns a partial object + the mutated plan.** `/api/complete` and `/api/uncomplete` return
  `{"completed"|"uncompleted": {id, name?, status?, done, …flags}, "plan": {…}}`. Closest to the
  target; still not the full object.
- **Returns the mutated plan only.** `/api/task/not-today`, `/api/task/move`, `/api/duration`.
- **Returns a bare scalar.** `/api/task/reschedule` → `{"ok", "when_label"}` (server.py:586);
  `/api/project/engagement` → `{"ok", "engagement"}` (604); `/api/recurring/active` →
  `{"ok", "active"}` (622); `/api/logday` → `{"ok", "tags"}`. The client cannot verify what
  persisted — only that the server *claims* success.

A frontend therefore cannot uniformly "apply the returned object" after a write, which is exactly
what the new UI needs to do on every one of its ~14 mutations. **Every mutation endpoint must
return the re-fetched persisted object under one envelope.**

**Read-back correctness gaps to fix while the envelope changes** (found by reading the helpers, not
the routes — all four are real, none are cosmetic):

1. `/api/capture/undo` → `task_actions.archive_object` (line 182) confirms only the **HTTP status
   code** (`if st not in (200, 204): raise`) and never re-fetches to confirm the object is gone.
   This is the one write path where "ok" rests on the API's acknowledgment rather than on observed
   state — precisely the failure mode the read-back discipline exists to prevent.
2. `reschedule_task`'s date read-back compares parsed dates to tolerate Anytype's timezone
   normalization, but guards with `if persisted is not None and persisted != intended`. A date that
   comes back **entirely absent** passes silently.
3. `/api/focus/commit` and `/api/focus/update` re-fetch and then validate **only** that `start` and
   `end` landed — every other written field is unverified.
4. `_reactivate_named_tasks` (server.py:220) calls a function that does read back, but **never
   raises**: failures are collected into `reactivate_failed` and returned alongside `{"ok": true}`.
   A caller checking only `ok` misses them. Under the new envelope, partial failure must not
   present as success.

### Required response envelope — all mutations

```ts
interface WriteResult {
  ok: true;
  object: Node;        // THE RE-FETCHED OBJECT, read back from Anytype after the write.
                       // Same shape as a GET /api/tree node (id, level, type, title, vals).
                       // Not the request echo. Not a constructed dict. A real read.
  plan?: Plan;         // present when the write invalidates today's cached plan
}
// errors
interface WriteError { ok: false; error: string; }   // 4xx/5xx; never a silent success
```

The client renders `flash('Saved')` **from `object`**, not from `ok` — the mockup already flashes on
every mutation (lines 282–299), so the only change is making the flash truthful.

### Mutation inventory

| UI method | line | Endpoint | Request | Response |
|---|---|---|---|---|
| `setVal(id,k,v)` | 282 | `PATCH /api/object/{id}` | `{vals:{[k]:v}}` | `WriteResult` |
| `toggleMulti(id,k,opt)` | 283 | `PATCH /api/object/{id}` | `{vals:{[k]: joinedString}}` | `WriteResult` |
| `setTitle(id,t)` | 284 | `PATCH /api/object/{id}` | `{title}` | `WriteResult` — debounce client-side; this fires per keystroke today |
| `clearVal(id,k)` | 487 | `POST /api/object/{id}/clear-field` | `{key:k}` | `WriteResult` — **must remove the property, not set it empty** (tri-state, spec §4) |
| `del(id)` / `askDelete` | 285 / 476 | `DELETE /api/object/{id}` | — | `{ok, id, archived:true}` — archive, not hard delete (`task_actions.archive_object`, line 182) |
| `move(id,toId)` | 286 | `POST /api/object/{id}/move` | `{parent_id: toId}` | `WriteResult` — re-parent link; response `level` may change with depth |
| `setType(id,target)` | 287 | `POST /api/object/{id}/type` | `{target:'Task'\|'Recurring'\|'Subproject'\|'Workstream'\|'Project'}` | `WriteResult` — spec §5, preserve all field values |
| `toggleDone(n)` | 297 | `POST /api/complete` / `POST /api/uncomplete` | `{id}` | **CHANGE to `WriteResult`** — also flips `status` Done↔Ready for TASK |
| `toggleActive(n)` | 298 | `POST /api/recurring/active` | `{id, active:boolean}` | **CHANGE to `WriteResult`** — note UI stores `paused`, inverse of `active` (Q3) |
| `addChild(parentId,type)` | 299 | `POST /api/object` | `{parent_id, type, level, title:''}` | `WriteResult` — UI creates a local `_new` node and opens the editor immediately; **the real id must replace the temp id on response** |
| `capture()` | 1136 | `POST /api/capture` | `{text}` | `202 {state:'running'}` → poll `/api/status`, then `GET /api/session?stream=capture` for the receipt |
| `saveFocus(view)` | 920 | `POST /api/focus/commit` (new) / `POST /api/focus/update` (edit) | the `Period` shape of §2.5 | `{ok, period: Period}` — re-fetched |
| arc-step check | (in plan) | `POST /api/complete` | `{id: step.id}` | `WriteResult` — arc step ids are **real task ids** (`grain.project_arc`) |
| block chunk check | (in plan) | `POST /api/complete` | `{id: block.id, kind:'block'}` | cache-only chunk log; spec §14 renders it as a completion |
| `setTheme(name)` | 167 | *(none)* | — | `localStorage` only (spec §18). **Must never be written to an Anytype object or enter plan context.** |
| `toggleCollapse(id)` | 676 | *(none)* | — | pure view state |
| priority reorder | 1025–1027 | `POST /api/plan/priority-order` | `{order: string[]}` | gated on Q1 |

### Write guards the backend must enforce

These exist in the mockup as client-side checks; the server must enforce them independently, since
a client check is a UX affordance and not a constraint.

1. **Leaf-type guard.** `setType` (line 288) refuses `Task`/`Recurring` when `children.length > 0`
   ("Can't convert — has sub-items, move them first"). Spec §5 requires the same guard in the shared
   write layer.
2. **Type-option gating.** `typeOptions` (line 291) offers `['Task','Recurring','Subproject','Workstream']`
   only when the node has a schedulable ancestor, else `['Project','Workstream']`.
3. **Calendar-owned fields are read-only.** Spec §15: when `source === 'calendar'`, reject writes to
   `title`, `dow`, `tod` and the interval; allow the app-native relations. **Every** write path
   (this surface, MCP, drift skill) must enforce it, not just this one.
4. **Vocabulary discipline.** Spec §12: map values to existing Anytype select options, creating
   missing options idempotently — never silently coin new ones.
5. **Learning-loop logging.** Spec §11: every applied edit, recurring toggle, focus-period override
   and type-convert emits a signal through the **existing** loop (the same session/surface logs the
   Add-tab capture writes to: `scripts/data/signal_log.jsonl`, `surface_log.jsonl`). Do not invent a
   new log. **See §7 — corrections to LLM-authored values must be distinguishable from ordinary
   edits, which spec §11 as written does not do.**

---

## 5. Absorbed capabilities — what must not drop when the old surfaces retire

`scripts/review_surface.py` + `scripts/surface_template.html` and `scripts/surface_serve.py` are
being retired. Everything below works today and must have a home in the new UI.

### From `review_surface.py` / `surface_template.html`

| Capability | Where it lives today | Absorbed as |
|---|---|---|
| Render the live Anytype space as a collapsible Goal → Project → Subproject → Task tree | `review_surface.build()` | `GET /api/tree` + Review tab |
| Every field as a **correctly-typed** control (select → dropdown, bool → checkbox, date → picker) | `fieldControl()` | schema-driven `controls` (§2.1) |
| **Field display ordering** — `PRIORITY` list (lines 36–44); unlisted fields sort last | `fieldPrio()` | must move into the schema endpoint's `controls`/`notes` ordering. The list verbatim: Task status, Project status, Goal status, Engagement, Goal engagement, Side, Done, Due date, Scheduled, Deadline, Horizon, Interval unit, Interval count, Day of week, Time of day, Day of month, Frequency, Context, Description, Affective, Reaching for, Resolution condition, Barriers, Blocked on, Needs clarifying, Duration min, Duration source, Access conditions, Access notes, AI autonomous, Depends on, Relevant docs, Arc position rationale, Engagement notes, Last surfaced |
| **Primary inline field** on the collapsed row — the field she changes most, editable without opening the node | `PRIMARY` (line 46): `Goal→Goal engagement`, `Project→Engagement`, `Task→Task status`, `Recurring→Interval unit` | **not visibly present in the mockup's collapsed rows** — flag to June before dropping (Q7) |
| **System-field hiding** — `SKIP_NAMES` (lines 31–34) keeps Anytype plumbing out of the surface | `review_surface` | schema endpoint must apply the same exclusion; `describe_model.INERT` is a near-duplicate list — unify them |
| Hierarchical **move picker** with subtree filtering | `buildMoveTree` / `filterMoveTree` / `openMovePanel` | `move()` + `pickerFilter` state (present in mockup) |
| **Add-from-page** — create a child node inline at the right level | `createChildNode` / `childLevelFor` / `buildNewNodeFields` | `addChild()` (present) |
| **Hide done** toggle — honors **both** the primary select being `"Done"` **and** the separate `Done` checkbox (the field redundancy June flagged), and re-applies after every edit so marking something done while filtered hides it immediately | `applyHideDone` | ⚠ **not found in the mockup** — flag (Q7). Note the dual-condition logic is a real bug fix, not incidental; whatever replaces it must keep both conditions |
| **Workstreams as a distinct visual layer**, grouped rather than interleaved | `wsGroupEl` | mockup has the `WORKSTREAM` level with its own control set; grouping behavior needs confirming |
| **Change tracking + diff view + export** to `controlled_drift_changes.json` | `changedItems` / `renderDiff` / `buildExport` / `doExport` | **spec §1 keeps this as the fallback for when no backend is running.** With live writes it is no longer the primary path, but it must not vanish — the offline fallback is explicitly retained |
| **Rebuild from Anytype** (discard unexported edits, re-pull live) | `rebuildBtn` → `POST /rebuild` | a refresh of `/api/tree`; the "discards unexported edits" warning becomes moot under live writes |
| **Live select-option enumeration per property** — `fieldmeta`: per type, `{fieldName: {format, options[]}}`, options fetched live from each property's tags endpoint. This is what makes every control correctly typed. | `review_surface.build()` | **becomes `GET /api/schema`** (§2.1) — this is the existing implementation of the schema endpoint's core read, and should be lifted rather than rewritten |
| **Workstream inheritance rule** — a project is a workstream if `is_workstream` is checked **or it inherits it** by walking up the parent chain (with a cycle guard) | `review_surface` | must drive the `level` computation in `GET /api/tree` (§2.2). Also duplicated in `orient_map._is_workstream` (150–167) and `daily_plan` — spec §4 asks for **one** shared `effective()` resolver; this is one of its three named callers |
| **Four honest-empty orphan buckets** so nothing vanishes: `⚠ NO GOAL YET`, `⚠ NO PROJECT — orphan tasks`, `⚠ NO PROJECT — orphan recurring items`, `⚙ Workstreams with no parent project` | `review_surface` (`GROUP` level) | ⚠ **no equivalent in the mockup's `seed()`** — every fixture node has a parent. Orphans exist in the real data and this is a deliberate anti-vanishing affordance; dropping it silently loses objects from view. Flag (Q7) |
| **Expand all / Collapse all** | template | not located in mockup — flag (Q7) |
| **Title search filter** — reveals matches and walks up through both node and workstream ancestors, opening them | `filterMoveTree` + tree search | mockup has `pickerFilter` for the *move picker*; a whole-tree search was not located — flag (Q7) |
| **Per-item notes to Claude** (`noteForClaude`) + one free-text **`patternNotes`** box for cross-cutting observations ("all the 'cuff order' tasks are really one restart") | template | ⚠ no equivalent found in the mockup. This is a **dialogic** affordance — June annotating the data for Claude rather than editing it — and is not replaceable by field editing. Flag (Q7) |
| Build-time **object count line** (goals / projects / tasks / recurring / orphan-tasks / orphan-recurring / goalless-top-projects / workstream-projects) | `review_surface.build()` | diagnostic; low priority but currently the only at-a-glance data-health readout |
| Local-file-only posture — the generated HTML and June's export are **gitignored** (health/financial data) | module docstring, line 13 | the new surface must keep the same posture: no publishing, no remote hosting. ⚠ Note `server.py` binds `127.0.0.1` by default but accepts `CD_BIND=0.0.0.0` for phone access **with no authentication of any kind** (acknowledged in-code at 296–299). Consolidating onto one server does not change that; it does mean one more surface is exposed when that flag is used |

### From `surface_serve.py`

Serves `/` (the generated tree HTML), `/favicon.ico`, and `POST /rebuild` (regenerate from live
Anytype). Its whole job — a second server on a second port with a second token set — is what the
consolidation removes. The only capability to carry over is **rebuild-from-live**, which becomes an
ordinary re-fetch.

---

## 6. Open questions

Ordered roughly by how much they block. Q1 and Q2 were known going in; Q3–Q9 surfaced from reading
the sources; Q10 and Q11 come out of §7 (correction logging), which is written below this section —
read it first if those two don't make sense in isolation.

**Q1 — What sets Priority-view ordering?** *(spec §14, explicitly unresolved there.)*
Options named in the spec: (a) the generator ranking used to pick today's items (focus-period front
+ engagement + neglect), surfaced as an explicit ordered `items[]`; (b) a stored user reorder that
overrides generation for the day.
**New evidence from the mockup:** it implements *both, layered* — `priOrder` starts `null` and falls
back to the generator's order (`let order = (st.priOrder && …) || items.map(it=>it.id)`, line 1025),
with up/down `move()` at 1027. So the answer is likely "generator ranks; user reorder overrides for
the day." **What remains genuinely undecided is persistence**: `priOrder` is ephemeral component
state, so a reload loses it. Does the reorder survive a reload, and is it logged for the learning
loop (spec §11 says any user reorder should be)? Until that is decided,
`POST /api/plan/priority-order` cannot be specified.

**Q2 — Does Anytype support in-place object type change?** Determines whether spec §5 conversion is
an in-place type write or create-new-of-type → copy-props → relink → delete-old. I did not find any
type-change call in `scripts/gsdo_objects.py` (which exposes only `create_object`, `create`,
`update`, `find_existing`) or elsewhere in `scripts/`. This is a **capability probe against the live
Anytype API**, not a code question, and it should be run before the conversion endpoint is built —
the two implementations differ enough that guessing wrong is a rewrite. Note the create-copy-delete
path also has to preserve the object **id**, or every inbound reference (plan cache rows, arc step
ids, focus-period `front`/`paused` links, logs) breaks.

**Q3 — `active` or `paused` on Recurring?** Spec §3 specifies an `active` boolean defaulting to
active. The mockup's `toggleActive` (line 298) stores the **inverse**, `paused`, and the existing
endpoint `POST /api/recurring/active` takes `{active: boolean}`. Two of three agree on `active`;
the UI fixture uses `paused`. Recommend the backend stays `active` and the frontend inverts at the
seam — but it must be written down, because a silent polarity flip is the kind of bug that survives
integration testing.

**Q4 — Strategy `Directive`: new field, or rename of `What for`?** `scripts/build_strategy.py`
builds `Strategy status`, `What for`, `Learning notes`, `Context`, `Applies when`. The UI's notes
list is `Directive` + `Notes`. Spec §9 names `Directive` as a field, which reads as new — but
`What for` is semantically close and may be the same thing under an older name. If it is a rename,
existing values need migrating; if it is new, `What for` and `Learning notes` are now unsurfaced
fields with no home in the UI. Also: `Applies when` is built with only `Always` / `Low energy` and
is missing `Overwhelmed` / `Sprint` / `Stuck`.

**Q5 — Does the new surface keep `still_here`?** The current plan payload carries
`still_here: [{label, note}]` and `plan_generate.py` treats it as load-bearing — there is an
explicit completeness check (line 1103) forcing every active task to appear *either* scheduled *or*
in `still_here`, precisely because silent omission was a bug. `seedPlan()` has **no** still-here
field. Either the new UI drops the reassurance list (a real product change, since its whole job is
"your other work is not lost"), or it renders it somewhere I did not locate. Needs June's read.

**Q6 — `front` / `paused` as names or ids?** `seedPeriods()` uses project **name strings**
(`front:['Academic positions','Publishing papers']`); Anytype stores them as `objects` (id
references, `build_focus_period.py:30–31`). Recommend the payload carry `{id, name}[]` so the UI can
display without a second lookup and write without ambiguity — but names are not stable identifiers
and two projects can share a name, so this needs an explicit decision rather than a convenient
default.

**Q7 — Seven `review_surface` capabilities I could not locate in the mockup.** (a) **hide-done**;
(b) the **primary inline field** on collapsed rows (the `PRIMARY` map — the one field June changes
most, editable without opening the node); (c) **expand all / collapse all**; (d) **whole-tree title
search**; (e) the **four orphan buckets** that keep parentless objects visible; (f) **per-item notes
to Claude** and the free-text **`patternNotes`** box; (g) the **object count / data-health line**.
All are real affordances in the surface being retired. (e) and (f) are the ones I would push hardest
on: orphan buckets prevent objects vanishing from view entirely, and notes-to-Claude is a *dialogic*
affordance — annotating the data for Claude rather than editing it — with no field-editing
equivalent. I searched v4 by keyword across 1179 lines of dense `createElement`, so **absence of
evidence is weak here** — worth a direct check with whoever authored v4 before concluding these were
dropped rather than moved or deliberately cut.

**Q9 — What happens to `appointments[]`?** The current plan payload carries a separate
`appointments` array on **both** shapes — today's fixed-time Recurring anchors, each with a real id
and a `recurring: true` completion route. `seedPlan()` has no equivalent and its only timed non-task
row is a `break` (which has no id and is not checkable). Do appointments become ordinary
`kind:'task'` rows placed inline by time, or does the new surface render them as a distinct band?
This is not cosmetic: `plan_store._iter_items` walks `appointments` specifically because omitting it
was a real check-off-doesn't-stick bug (documented at `plan_store.py:125–133`).

**Q10 — Does the UI ever need to *display* which fields are LLM-authored?** §7.3 recommends carrying
provenance in the write log rather than on the object, which is right for the learning loop but
cannot cheaply answer "mark the LLM-authored fields in this form." The mockup has no such affordance
and `defaultSchema()` has no control kind that would carry it, so I have assumed no. If June would
actually want to *see* which values the model guessed — which seems plausible for a system whose
whole premise is that alignment lives outside her head — that changes the recommendation, and it
should change it deliberately rather than being patched on later.

**Q11 — Should the LLM write paths be modified to stamp authorship?** §7.4 needs `authored_by` to be
resolvable, which requires `capture_generate.py` / `plan_generate.py` / `daily_plan.py` /
`focus_period_author.py` to emit an authorship record at creation time. That widens backend scope
well beyond this surface. The alternative — accept `authored_by: 'unknown'` for everything until the
stamps land — is honest and ships sooner but produces no usable correction signal in the meantime.
Worth an explicit sequencing decision rather than assuming the wider scope.

**Q8 — `date` and `generated` formatting.** `seedPlan()` carries `date:'Wed Jul 16'` and
`generated:'Built this morning at 9:02.'` — both pre-formatted display strings. Spec §14 removes
the plan-age line from the surface, so `generated` appears to be vestigial. Should the backend send
an ISO date and let the client format (better for i18n/testing), or keep server-side formatting to
match the fixture exactly? The fixture says server-formats; general practice says otherwise. Low
stakes, but it is a real fork the two tracks would resolve differently on their own.

---

## 7. Correction-of-the-model as a distinct signal (sharpens spec §11)

> **The requirement, in the owner's words:** *"a major win would be logging the changes I make to
> LLM created input for our learning loops."*

### 7.1 Why spec §11 does not already cover this

Spec §11 says every applied edit "should emit a signal for the two-tier loop." That treats all edits
alike, and the distinction being drawn here cuts across it:

- June edits a value **she** entered → an ordinary edit. Low signal. She changed her mind.
- June edits a value **the LLM generated** → a **correction of the model**. This is the highest-value
  training signal the system can produce, because it is a labelled instance of the model being wrong
  in a way she cared enough to fix.

Conflating them dilutes the loop: the corrections are a minority of edits, and averaged in with
"changed her mind," their signal disappears. Telling them apart requires knowing **who authored the
value being overwritten** — and today, with one exception, nothing records that.

**This is a spec gap, not just a build detail.** §11 should be amended to carry the distinction;
this section is the proposed sharpening.

### 7.2 What exists today (verified, not assumed)

- **`scripts/plan_corrections_log.py`** — `log_correction(kind, before, after, path=None)` appends
  `{ts, kind, before, after}` to `plan_corrections.jsonl`. Its docstring is explicit that this is
  "v1 logs only; no learning loop yet." Live data confirms it: entries with
  `kind: "freetext"` carrying a whole `before.woven_frame`.
- **Six logs already record old→new deltas:** `completion_log.py`, `engagement_log.py`
  (`engagement_corrections_log.jsonl` — `log_change(project_id, name, old, new)`),
  `plan_corrections_log.py`, `reactivation_log.py` (same `log_change` signature),
  `rollover_log.py`, `surface_log.py`.
- **`signal_log.SOURCES`** already includes a `config_correction` tag alongside `config_authoring` —
  so the *vocabulary* of "this was a correction" exists at the signal level, just not at field level.
- **No general provenance mechanism exists.** A grep for `llm_authored|ai_authored|authored_by|
  provenance` across `scripts/` returns exactly one hit.

**That one hit is the important finding, and it is a working precedent, not a stray comment.**
`scripts/capture_fields.py:88–102` (`build_optional_props`) already implements field-level
authorship for duration:

> *"Duration carries provenance: June's stated duration (`duration_min`) is truth and always wins;
> an LLM estimate (`duration_estimate_min`) fills silence only. Whichever is written, a companion
> `'Duration source'` label (`'stated'|'estimated'`) is written alongside it so the reader — and the
> future duration-bias loop — can tell them apart. A June-stated 90 and an estimated 90 must never
> be indistinguishable."*

That last sentence **is** the general principle the owner is asking for, already reasoned through
and shipped for exactly one field. `Duration source` is a real Anytype property and appears in
`review_surface.PRIORITY`, so it is surfaced too. The task here is to generalize the principle
without generalizing the mechanism.

### 7.3 Recommendation — provenance lives in the write log, not on the object

The three options, weighed against the hard constraint that **this must not add per-field properties
to the Anytype schema** (spec §2/§4 treat schema additions as expensive and human-gated; the repo
carries a standing guard against field bloat and scalar-flattening):

| Option | Verdict |
|---|---|
| **(a) Per-object sidecar** listing which field keys the LLM populated at write time | **Rejected.** A sidecar keyed by object id is a second source of truth about objects that must stay in sync with Anytype across every write path (this surface, MCP, the drift skill) and every type conversion, move and archive. It buys object-level queryability the loop does not need and costs a consistency problem the repo does not have today. |
| **(b) Parallel `*_provenance` property per object/field** | **Rejected as the general mechanism** — this is precisely the schema bloat the constraint forbids. Roughly 35 fields appear in `review_surface.PRIORITY`; doubling that is not a tractable schema. **But keep the one instance that already exists:** `Duration source` stays, because the *scheduler* reads it, not only the loop — it is load-bearing at runtime, which is what earns a field its place on the object. That is the test for any future exception: does something other than the learning loop read it? |
| **(c) Provenance carried in the write log only** | **Recommended.** |

**Why (c) is right rather than merely cheapest.** The provenance of a value is a fact about *how the
value came to be*, which is history — and history is what a log is for. Putting it on the object
implies it is part of the domain model, which it is not: nothing in planning, selection or rendering
needs to know who authored a field, only the loop does. Storing it on the object would also make it
mutable by every write path and would need migrating on type conversion (spec §5 already has to
carry field values across a possible create-copy-relink-delete; carrying a parallel provenance set
through that is a second chance to lose data). The log is append-only, already exists, is already
where the loop reads from, and cannot corrupt the domain objects. Keeping the objects clean is the
point, not a side effect.

**The cost, stated honestly:** with (c) you cannot answer "which fields on this object are currently
LLM-authored?" by reading the object — you have to fold the log forward. For the learning loop that
is fine (it reads the log anyway, and the correction event is self-contained: it carries `before`,
`after`, and who authored `before`). It would **not** be fine if the UI wanted to visually mark
LLM-authored fields in the form. **[INFERRED]** that the UI does not want this — the mockup has no
such affordance and `defaultSchema()` has no provenance-bearing control kind — but if that
requirement appears later, option (c) does not serve it and this decision should be revisited rather
than patched. Flagged as Q10.

### 7.4 The correction record shape

Every mutation endpoint in §4 emits one record per changed field:

```ts
interface CorrectionRecord {
  ts: string;                 // ISO, timespec="seconds" — matches signal_log's existing format
  object_id: string;
  object_type: string;        // Goal | Project | Task | Recurring | Strategy | Focus Period
  field: string;              // the property key, or "__title__" / "__parent__" / "__type__"
                              // for rename / move / type-convert
  before: unknown;
  after: unknown;
  authored_by: 'llm' | 'user' | 'unknown';   // WHO AUTHORED `before` — the load-bearing field
  generation_id?: string;     // which generation produced `before`, when known
  surface: string;            // "review_reorganize" — which UI produced the correction
}
```

`authored_by` is the whole point of the record, and **`'unknown'` must be a real, honest value.**
Every object written before this ships has no provenance, and guessing `'user'` for those would
quietly poison the loop with false negatives ("she rarely corrects the model") — which is worse than
having no data, because it looks like data. The loop must filter to `authored_by === 'llm'` and
treat `'unknown'` as unusable, not as `'user'`.

**Where `authored_by` comes from.** At write time the server does not inherently know. Two sources,
in precedence order:

1. **The generating surface stamps it at creation.** When `capture_generate.py`,
   `plan_generate.py`, `daily_plan.py` or `focus_period_author.py` writes an object or field, it
   emits an *authorship* record (same log, `before: null`, `after: <value>`, `authored_by: 'llm'`,
   with `generation_id`). A later correction resolves `authored_by` by finding the most recent
   authorship or correction record for that `(object_id, field)`.
2. **Fall back to `'unknown'`** when no such record exists.

**[INFERRED]** — the authorship-stamp-at-creation half is a design proposal, not something the
sources specify. It is the minimum needed to make `authored_by` resolvable, but it does mean the LLM
write paths must be touched, which widens the backend scope beyond the surface itself. Worth naming
explicitly before it is committed to.

### 7.5 Which existing log each correction lands in

Per spec §11, **do not invent a new log.** Routing:

| Correction kind | Existing log | Note |
|---|---|---|
| Plan content — woven frame, block framing, item ordering, item text | `plan_corrections_log.log_correction(kind, before, after)` | Already exactly this job. Needs `authored_by` + `object_id`/`field` added to the record; plan content is **always** LLM-authored, so `authored_by: 'llm'` is a constant here, not a lookup. |
| Project engagement | `engagement_log.log_change(project_id, name, old, new)` | Already old→new. Add `authored_by`. |
| Recurring active/paused | `reactivation_log.log_change(recurring_id, name, old, new)` | Same. |
| Completion / uncompletion | `completion_log` | Unchanged — not a correction of a value. |
| **Every other field edit, rename, move, type-convert** | `signal_log.log_signal(raw, source, reference)` | Use a **new `source` tag**, `"field_correction"`, added to `signal_log.SOURCES` alongside the existing `config_correction`. The `CorrectionRecord` of §7.4 goes in `reference`; `raw` carries any free-text note. |

**A new `SOURCES` entry is not a new log** — `signal_log.jsonl` is the existing surface log the
Add-tab capture already writes to, and `SOURCES` is explicitly an extensible tag list (it already
carries six values added incrementally, each with a comment naming its origin). This satisfies §11's
"route these through the existing framework; match its shape and location."

**One genuinely new thing is needed, and here is the justification:** the *authorship* stamp of
§7.4(1) has no existing home. It is not a correction and not a signal from June — it is the system
recording what it itself generated. **[INFERRED]** the least-invasive placement is the same
`signal_log.jsonl` under a second source tag `"llm_authorship"`, so authorship and correction records
are co-located and a single forward-fold resolves `authored_by`. Splitting them into two files would
mean the loop reads two logs to answer one question. If that placement is wrong, the alternative is a
dedicated `provenance.jsonl` — but that should be a deliberate choice, not a default.

### 7.6 Surfaces that produce LLM-authored values

These are the write paths whose output, when June edits it, is a correction of the model. They are
the ones that must emit authorship stamps:

| Surface | File | What it authors |
|---|---|---|
| Capture / weeding | `scripts/capture_generate.py` | The whole shape of a captured object: title, type, parent link, status, engagement, and the optional fields via `capture_fields.build_optional_props` |
| Plan generation | `scripts/plan_generate.py`, `scripts/daily_plan.py` | `woven_frame`, block labels/framings, item ordering, item text rewrites, block/task grain choice |
| Focus-period authoring | `scripts/focus_period_author.py`, `focus_period_generate.py` | Every structured field **except `intent`** — spec §17 is explicit that intent is June's own words, never reworded. Intent is therefore `authored_by: 'user'` even on an LLM-authored period, and stamping it `'llm'` would be wrong. |
| Inferred fields | `scripts/capture_fields.py`, `scripts/block_duration.py`, `scripts/duration_backfill.py`, `scripts/neglect.py` | Duration estimates (**already** provenance-tracked via `Duration source`), block chunk minutes, engagement proposals, access conditions |

The focus-period row is the clearest illustration of why field-level rather than object-level
provenance is the right grain: a single object legitimately carries both LLM-authored and
user-authored fields at the same time.

---

## Appendix — files this contract touches

**Backend, to change:** `scripts/server.py` (routes, CORS, static, write envelope) ·
`scripts/orient_map.py` (extract `map_tree()`) · `scripts/plan_generate.py` + `scripts/daily_plan.py`
(plan payload shape, drop `why`, add `shape` always) · `scripts/plan_store.py` (cache shape) ·
`scripts/gsdo_objects.py` (convert op, clear-field, generic create/update route) ·
`scripts/build_recurring.py` (`active`, `source`, mirrored Task fields — spec §2) ·
`scripts/build_focus_period.py` (`Workday start`) · `scripts/build_strategy.py` (`Directive`,
missing `Applies when` options) · `scripts/build_task.py` / `scripts/build_project.py` (access
options, `blockMin`, `Affective`) · a new shared `effective()` resolver (spec §4).

**Backend, for §7 (correction logging):** `scripts/signal_log.py` (add `"field_correction"` and
`"llm_authorship"` to `SOURCES`) · `scripts/plan_corrections_log.py` (add `authored_by`,
`object_id`, `field` to the record) · `scripts/engagement_log.py` + `scripts/reactivation_log.py`
(add `authored_by`) · and, if Q11 resolves toward stamping at creation,
`scripts/capture_generate.py`, `scripts/plan_generate.py`, `scripts/daily_plan.py`,
`scripts/focus_period_author.py`. `scripts/capture_fields.py`'s `Duration source` mechanism stays
as-is — it is the working precedent, and it is load-bearing at runtime, not only for the loop.

**Backend, to retire:** `scripts/surface_serve.py` · `scripts/review_surface.py` ·
`scripts/surface_template.html` · `docs/overlay_daily.html`. Retire only once §5's absorbed
capabilities are confirmed present in the new surface — including the export-diff fallback, which
spec §1 explicitly keeps.
