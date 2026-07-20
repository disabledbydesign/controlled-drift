/**
 * Where the wire shapes and the app's shapes disagree, and exactly how much.
 *
 * Kept apart from `client.ts` (which only moves bytes) and from `model/` (which is pure) so
 * that every place the two tracks did not converge is visible in ONE file. Each function below
 * names the divergence it closes and cites where the contract records it.
 */

import type { Node, Period, Plan, PlanBlock, PlanItem, Schema } from '../fixtures/index.ts';
import type { Graph, ModelNode, OrphanBucket } from '../model/index.ts';

// ── GET /api/tree ────────────────────────────────────────────────────────────

/** What `scripts/api_tree.build_tree()` returns (read from the live endpoint, 2026-07-18). */
export interface TreeResponse {
  nodes: Node[];
  strategies: Node[];
  /**
   * ⚠ A KEYED OBJECT, not an array. `fixtures/orphans.ts` models it as `{key,label,nodes}[]`
   * and the endpoint answers `{[key]: {label, nodes}}` — verified live. The fixture's own header
   * says the four keys and labels were copied from the endpoint, and they match; only the
   * container differs.
   */
  orphans: Record<string, { label: string; nodes: Node[] }>;
  counts?: Record<string, unknown>;
}

/**
 * The endpoint's payload as the app's `Graph`.
 *
 * Bucket ORDER matters and an object has none worth relying on, so the four keys are listed
 * explicitly, in `review_surface.py`'s order (the surface being retired) — goal-less projects,
 * orphan tasks, orphan recurrings, parentless workstreams. Any key the server adds later still
 * comes through, appended after the four.
 */
const BUCKET_ORDER = [
  'projects_without_goal',
  'orphan_tasks',
  'orphan_recurring',
  'parentless_workstreams',
] as const;

export function graphFromTree(res: TreeResponse): Graph {
  const buckets: OrphanBucket[] = [];
  const seen = new Set<string>();
  const push = (key: string) => {
    const b = res.orphans?.[key];
    if (!b || seen.has(key)) return;
    seen.add(key);
    buckets.push({ key, label: b.label, nodes: (b.nodes ?? []) as ModelNode[] });
  };
  for (const k of BUCKET_ORDER) push(k);
  for (const k of Object.keys(res.orphans ?? {})) push(k);

  return {
    roots: (res.nodes ?? []) as ModelNode[],
    strategies: (res.strategies ?? []) as ModelNode[],
    orphans: buckets,
  };
}

// ── GET /api/schema ──────────────────────────────────────────────────────────

/**
 * The live schema, narrowed to what `applySchema` consumes.
 *
 * The endpoint returns TWO keys the fixture does not have — `fields` (per-field semantics from
 * `scripts/field_semantics.py`) and `levelTypes` — plus a `property` name on each relation. All
 * three are additive and ignored here; `controls` and `notes` were compared against the fixture
 * and are byte-identical, so nothing needs translating.
 *
 * ⚠ TWO VOCABULARIES GENUINELY DIFFER, and the LIVE one wins:
 *   · `proj` (Project engagement) — fixture 7 options, live 5. `Sprint` and `Hyperfixation` were
 *     RETIRED from the data structure (auto-memory `engagement-proposal-shipped`); the tags no
 *     longer exist, so offering them would produce a failed write.
 *   · `strategyState` (Applies when) — fixture 5, live 2. `Overwhelmed` / `Sprint` / `Stuck`
 *     were never built (`scripts/build_strategy.py`; contract §2.1 flags it).
 * That is why the schema is FETCHED rather than shipped: the fixture is a stale snapshot of a
 * vocabulary that is now wrong in a way the user could not see until the write failed.
 */
export function schemaFromResponse(res: unknown): Schema {
  return res as Schema;
}

// ── GET /api/plan ────────────────────────────────────────────────────────────

/** The plan as `scripts/plan_store.py` still stores it — contract §2.4 "CURRENT". */
interface LivePlanItem {
  id?: string;
  time?: string;
  task?: string;
  project?: string | null;
  description?: string;
  duration_min?: number;
  interstitial?: boolean;
  block?: boolean;
  block_project?: boolean;
  /** A block's real id lives here. See the ⚠ in `planFromLive`. */
  project_id?: string;
  chunk_min?: number;
  arc?: { text: string; state: 'done' | 'here' | 'ahead'; id?: string }[];
  did_chunk_today?: boolean;
  held_back_names?: string[];
  done?: boolean;
  recurring?: boolean;
  as_needed?: boolean;
}

export interface LivePlan {
  woven_frame?: string;
  shape?: string;
  /** One line naming what today's shape is and why (`plan_generate.py:361`). */
  header?: string;
  blocks?: { label: string; time: string; framing: string; items: LivePlanItem[] }[];
  items?: LivePlanItem[];
  appointments?: LivePlanItem[];
  generated_at?: string;
  empty?: boolean;
}

/**
 * The live plan in the shape the Today tab renders.
 *
 * ── this is a TRANSITIONAL adapter and should be deleted ─────────────────────
 * Contract §2.4 assigns this conversion to the BACKEND ("Delta list for the backend track") and
 * it is unbuilt — verified live 2026-07-18: `/api/plan` still answers `woven_frame`, flag-bag
 * items and no `date`. The alternative to adapting here was leaving Today on the fixture, and
 * that is the worse failure: the fixture would render a plausible fake day as though it were
 * June's, which is exactly the class of thing this surface exists to stop. So the mapping is
 * applied client-side, entirely from §2.4's own table, and nothing is invented:
 *
 *   woven_frame → woven · chunk_min → chunkMin · held_back_names → heldBack ·
 *   duration_min → durationMin · interstitial AND no id → kind:'break' · block → kind:'block' ·
 *   everything else → kind:'task' · `why` DROPPED (spec §14, already unrendered).
 *
 * ⚠ TWO FIELDS ARE STILL OPEN QUESTIONS and are NOT invented into a shape here:
 *   · `still_here` — contract §6 Q5, needs June's read. Carried through untouched, unrendered.
 *   · `appointments[]` — contract §6 Q9. **Prepended as ordinary rows**, because dropping them
 *     is the documented check-off-doesn't-stick bug (`plan_store.py:125-133` walks them
 *     specifically); a fixed-time anchor that renders nowhere cannot be checked off at all.
 *     Whether they should instead be a distinct band is Q9 and stays open.
 *
 * ⚠ A PRIORITY-shape plan has flat `items` and no blocks. The Priority view flattens blocks
 * anyway, so the flat list is carried in ONE unlabelled block. That is a container, not a
 * label the user reads — an empty `label`/`time`/`framing` renders no band header.
 */
/**
 * The id this row can actually be addressed by on the server, or `''` when it has none.
 *
 * ⚠ A BLOCK CARRIES ITS ID IN `project_id`, NOT `id` — see the long note in `planFromLive`'s
 * block branch — so both are read here, and "does this row have an id" answers the same question
 * everywhere in this file. An empty string counts as NO id, which is why this is not `??`:
 * `'' ?? x` is `''`, and a blank id addresses nothing.
 *
 * ⚠ `project_id` IS ONLY THIS ROW'S OWN ID WHEN THE ROW IS A BLOCK — so the fallback is gated on
 * `it.block` ALONE, which is the one flag that makes `project_id` the row's own identity.
 * `plan_generate.py:734` sets `project_id` on ORDINARY task rows as well, where it names the
 * task's PARENT PROJECT. Falling back to it unconditionally would hand a project's id to a task
 * row and address the wrong object.
 *
 * ⚠ `block_project` IS NOT A BLOCK FLAG, and reading it as one was this exact defect arriving by
 * the back door. `plan_generate.py:726-735` sets `block_project` on ORDINARY TASK rows, and
 * explicitly `continue`s past any row where `block` is true — so `block_project: true` implies
 * `block` is falsy, and the row's `project_id` is its PARENT's. Gating on it made a task row
 * addressable as its own parent project: checking it off, setting its duration or moving it would
 * each have written to the wrong Anytype object. A `block_project` row with no `id` therefore
 * answers `''` here, which is the truth — it is not addressable by an id of its own.
 *
 * The gate also matches `planFromLive`'s render branch, which tests `if (it.block)` and nothing
 * else. Two different tests for "is this a block" is how the two answers drift apart.
 */
function usableId(it: LivePlanItem): string {
  if (it.id) return it.id;
  if (it.block) return it.project_id || '';
  return '';
}

export function planFromLive(live: LivePlan): Plan {
  const shape = live.shape === 'priority' ? 'priority' : 'schedule';
  const conv = (it: LivePlanItem): PlanItem => {
    /*
     * WHAT MAKES A ROW A BREAK: it has no addressable id, so there is nothing to check off. That
     * is the whole test — `!usableId(it)` — and it is deliberately NOT gated on `interstitial`.
     *
     * ⚠ Two ways this was wrong before, both live 2026-07-20:
     *   · `interstitial` ALONE is not "a break" — it means "short", and the LLM prompt (JSON rule
     *     3) flags real ≤15-min TASKS interstitial too. Reading the flag by itself deleted a real
     *     chore ("Do the dishes", with a real id) from the Priority list. A row with an id is a
     *     task whatever the flag says — `usableId` (which reads `project_id` for a block) is the
     *     authority, so an id-carrying short task keeps `kind:'task'`.
     *   · `interstitial AND no id` was too NARROW the other way: meals and model-authored fillers
     *     ("Lunch", "Rest — stand up, stretch, move") arrive with NO id and `interstitial:false`,
     *     so they fell through to `kind:'task'` with id '' and hit `TaskRow`'s `node(idx,'')===null`
     *     guard — rendering nothing, a silent gap in the schedule. With no id they are not tasks;
     *     they are breaks, and now render as such (a block keeps its id in `project_id`, so
     *     `usableId` keeps a real work block out of this branch).
     */
    if (!usableId(it) && !it.block) {
      return { kind: 'break', time: it.time ?? '', task: it.task ?? '' };
    }
    if (it.block) {
      return {
        kind: 'block',
        // ⚠ A BLOCK CARRIES ITS ID IN `project_id`, NOT `id` — verified against the live plan
        // 2026-07-18, where the block row "Work on IOP and recovery" has `id` ABSENT and
        // `project_id` set. `server.py`'s own comment on the complete route says so ("the
        // overlay sends the block's project_id in `id`"), and `plan_store.is_block_item`
        // matches on that id. Reading `it.id` alone produced an unchecked-offable block — the
        // "uncheckoffable ghost row" this repo already paid a rebuild for, arriving by a
        // different route. The fixture hid it: `seedPlan`'s blocks carry a plain `id`.
        id: usableId(it),
        task: it.task ?? '',
        time: it.time ?? '',
        chunkMin: it.chunk_min ?? 0,
        why: '',
        // The server's own record of today's chunk (`plan_store.mark_block_chunked`). Carried
        // through so a reload renders the check from the plan rather than from UI state, which
        // does not survive one.
        didChunkToday: Boolean(it.did_chunk_today),
        ...(it.arc ? { arc: it.arc } : null),
      };
    }
    return {
      kind: 'task',
      id: it.id ?? '',
      time: it.time ?? '',
      durationMin: it.duration_min ?? 0,
      why: '',
      ...(it.task ? { task: it.task } : null),
      ...(it.description ? { description: it.description } : null),
      ...(it.held_back_names?.length ? { heldBack: it.held_back_names } : null),
      ...(it.done ? { done: true } : null),
      // A row whose id is a real appointment is FIXED, wherever it renders. The flag is the only
      // trace of that once the backend has scheduled it into a block as an ordinary-looking row;
      // it is what holds the move controls off it. See `PlanTaskItem.appointment`.
      ...(it.id && apptIds.has(it.id) ? { appointment: true } : null),
    } as PlanItem;
  };

  // The ids the backend calls fixed-time appointments. Used both to FLAG appointment rows and to
  // avoid rendering one twice: on a clock day the backend both schedules the appointment into a
  // block (at its real time) AND lists it in appointments[], so prepending the second copy put
  // the same object on screen twice — once out of temporal place at the top of band 0. We prepend
  // an appointment ONLY when the model did not already place it in a block.
  const apptIds = new Set((live.appointments ?? []).map((a) => a.id).filter(Boolean));

  const blocks: PlanBlock[] =
    shape === 'schedule'
      ? (live.blocks ?? []).map((b) => ({
          label: b.label,
          time: b.time,
          framing: b.framing,
          items: b.items.map(conv),
        }))
      : [{ label: '', time: '', framing: '', items: (live.items ?? []).map(conv) }];

  const idsInBlocks = new Set(
    blocks.flatMap((b) => b.items.map((i) => ('id' in i ? i.id : null))).filter(Boolean),
  );
  // Only the appointments NOT already standing in a block. On a clock day that is usually none —
  // the appointment renders at its real time in its block, and the client's bands then match the
  // server's list exactly, so the move offset (apptCount) is zero. On a priority day, or when the
  // model dropped an appointment, the ones left over are prepended so a fixed commitment never
  // vanishes.
  const appts = (live.appointments ?? [])
    .filter((a) => !(a.id && idsInBlocks.has(a.id)))
    .map(conv);

  // Appointments are fixed-time anchors, so any that must be prepended lead. See the ⚠ above.
  if (appts.length) {
    const first = blocks[0];
    if (first) first.items = [...appts, ...first.items];
    else blocks.push({ label: '', time: '', framing: '', items: appts });
  }

  return {
    // Display-formatted server-side in the fixture (contract §6 Q8, unresolved). Formatted here
    // from the real generation timestamp rather than left blank.
    date: live.generated_at ? fmtDay(live.generated_at) : '',
    /*
     * The server's real generation timestamp, carried through RAW and unformatted.
     *
     * ⚠ This was `''`, on the reasoning that "spec §14 removed the plan-age line and nothing
     * renders this." Blanking it removed the ONLY signal that separates today's plan from
     * yesterday's: with the age line gone she saw `date` — which she reads as today's — on a
     * plan that may have been built before a failed morning generation. The spec line does not
     * outrank the function; the display is back (`model/plan.ts` `planAgeText`, restored from
     * the old overlay), and this is what feeds it.
     *
     * NOT formatted here, deliberately. The words depend on when they are READ, not on when
     * the payload arrived — a surface left open across midnight must stop saying "this
     * morning". `planAgeText` composes them at render time.
     *
     * Absent stays `''` — the renderer then shows no age line at all. An invented build time
     * would be the same defect one field over.
     */
    generated: live.generated_at ?? '',
    shape,
    // How many appointments were PREPENDED into `blocks[0]` above — the ones the model did not
    // already place in a block. Those extra front rows are not in the server's own list, so
    // `/api/task/move`'s `position` on band 0 is offset by exactly this many. When every
    // appointment already stands in its real block (the common clock day) this is zero and the
    // rendered order matches the server's. See `Plan.apptCount` and `moveTargets.offsetOf`.
    apptCount: appts.length,
    // The server's own reason for that shape, carried verbatim. NOT composed here: the client
    // cannot know which branch of `resolve_output_shape` produced the shape, so a locally
    // written sentence would sometimes assert a cause that is not the cause. Absent becomes
    // `''` — never the string "undefined" on a surface she reads.
    header: String(live.header ?? ''),
    woven: live.woven_frame ?? '',
    blocks,
  };
}

function fmtDay(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

// ── plan-action presets ──────────────────────────────────────────────────────

/** One plan-action button, as stored in her own `~/.controlled-drift/actions.json`. */
export interface Preset {
  /** ⚠ CONTRACT. `POST /api/negotiate {preset_id}` dispatches on this and 400s on an unknown one. */
  id: string;
  /** ⚠ DISPLAY. Hers to change; nothing may depend on its text. */
  label: string;
}

/** The `GET /api/actions` payload — the VARIABLE button schema (`plan_store.py`). */
export interface ActionsResponse {
  version?: number;
  presets?: { id?: string; label?: string }[];
}

/**
 * Her plan-action buttons, read from her file instead of hardcoded in the app.
 *
 * WHY THIS EXISTS. The four buttons on Today carried hardcoded labels, and they had already
 * drifted from what she stores: her `quick-wins` preset reads "Quick wins first" while the
 * button said "Quick wins only". Asked which was right, the question was withdrawn — it is the
 * wrong question. Correcting the string would leave the same drift free to happen again on the
 * next edit to her file. Reading the label from the file is what removes the class.
 *
 * ⚠ LABELS ARE DISPLAY, IDS ARE CONTRACT — do not conflate them. The id is passed to
 * `/api/negotiate` untouched and an unknown one answers 400 (`server.py:1017`); the label is
 * hers and may change any time. Nothing here normalises, title-cases or otherwise "tidies" a
 * label: the whole point is that what she typed is what she sees.
 *
 * The `add` entry is excluded. It is a UI-only marker with a null payload, and June removed
 * "Add something" from this row on 2026-07-18 (navigation among plan actions; the Add tab is
 * one tap away). Honouring her file must not quietly undo her decision.
 *
 * Entries missing an id or a label are DROPPED, not repaired — an id-less preset could never
 * dispatch and a label-less one renders a blank button. Supplying a stand-in for either is the
 * same defect this function exists to remove.
 */
export function presetsFromLive(live: ActionsResponse): Preset[] {
  return (live.presets ?? [])
    .filter((p) => p && typeof p.id === 'string' && p.id !== '' && p.id !== 'add')
    .filter((p) => typeof p.label === 'string' && p.label !== '')
    .map((p) => ({ id: p.id as string, label: p.label as string }));
}

// ── periods ──────────────────────────────────────────────────────────────────

/*
 * FOCUS PERIODS ARE WIRED, as of `GET /api/periods` (server.py, built 2026-07-18).
 *
 * The endpoint answers `{periods: [...]}` — EVERY focus period, each one in the flat
 * snake_case EDIT shape `focus_period_adapter.period_to_fields` produces, plus `id` and
 * `active`. It is deliberately not the singular `/api/period`, which is display-rendered
 * (pre-formatted date strings) and carries only the active period, so it cannot seed an editor.
 *
 * The two sides never agreed one naming convention (contract §2.6 wanted that and it did not
 * happen), so the translation lives HERE, in the one file that exists to hold exactly this kind
 * of disagreement — not spread across the Focus screen. `periodsFromLive` below is the whole of
 * it; nothing else in `app/src` may read a snake_case period field.
 */

/** One period as `GET /api/periods` sends it. Every field may be absent or null on the wire. */
export interface LivePeriod {
  id?: string | null;
  active?: boolean | null;
  name?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  intent?: string | null;
  availability_start?: string | null;
  availability_end?: string | null;
  availability_note?: string | null;
  days_off?: string[] | null;
  days_on?: string[] | null;
  output_format?: string | null;
  workday_start?: string | null;
  workday_end?: string | null;
  foreground_projects?: string[] | null;
  paused_projects?: string[] | null;
}

export interface PeriodsResponse {
  periods: LivePeriod[];
}

/** A wire string as the app's always-present string. null/undefined become `''`, never absent. */
function str(v: string | null | undefined): string {
  return v ?? '';
}

/** A wire list as the app's always-present array, with empty entries dropped. */
function list(v: string[] | null | undefined): string[] {
  return Array.isArray(v) ? v.filter((s) => typeof s === 'string' && s !== '') : [];
}

/**
 * One wire period as the app's `Period`.
 *
 * Three shape differences the server cannot close on its own:
 *
 *  1. NAMES. `start_date`→`start`, `end_date`→`end`, `availability_start`→`availStart`,
 *     `availability_end`→`availEnd`, `availability_note`→`note`, `days_off`→`daysOff`,
 *     `output_format`→`output`, `workday_start`→`workdayStart`, `workday_end`→`workdayEnd`,
 *     `foreground_projects`→`front`, `paused_projects`→`paused`.
 *  2. `daysOn` IS A STRING in `Period`, while every sibling day list is an array and the server
 *     sends an array. The v4 fixture typed it that way and the form editor binds it to a text
 *     input; joined here rather than changing the type under the editor.
 *  3. `when` IS NOT A SERVER FIELD. The server says which single period contains today
 *     (`active`); the past/future split is derived HERE, from `end_date` against today.
 *
 *     ⚠ Six of her seven real periods have already ended. Mapping every non-active period to
 *     `'upcoming'` put all six under a heading reading "coming up" with a "Next" chip — a
 *     period from three weeks ago announced as the next one. `PeriodWhen` gained `'past'` for
 *     exactly this; see the type's own note.
 *
 * `output` falls back to `'Auto'`, matching `formFromPeriod` and the server's own default, so
 * the select never renders blank. No other field invents a value: a missing string is `''` and a
 * missing list is `[]` — never `undefined`, so no consumer has to guard.
 *
 * `today` is a parameter rather than a `new Date()` inside, so the mapping stays pure and the
 * boundary cases (a period ending exactly today; a period with no end date) are testable.
 */
/** Local calendar date as `YYYY-MM-DD`. NOT `toISOString()`, which converts to UTC first and so
 *  reports tomorrow's date all evening in her timezone. */
function todayIso(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/**
 * `active` is the server's word and wins outright — it owns the window logic
 * (`focus_period.load_active_focus_period`), and second-guessing it here would put the same
 * rule in two places.
 *
 * Otherwise the split is `end_date` against today. ISO dates compare correctly as strings, so
 * no parsing is needed. A period ending exactly today is NOT past. A period with no end date
 * cannot be shown to have ended, so it stays `'upcoming'` rather than being guessed into the
 * past — the direction that keeps it visible instead of quietly filing it away.
 */
function periodWhen(p: LivePeriod, today: string): Period['when'] {
  if (p.active === true) return 'now';
  const end = str(p.end_date);
  return end && end < today ? 'past' : 'upcoming';
}

export function periodFromLive(p: LivePeriod, today: string = todayIso()): Period {
  return {
    id: str(p.id),
    when: periodWhen(p, today),
    name: str(p.name),
    start: str(p.start_date),
    end: str(p.end_date),
    intent: str(p.intent),
    front: list(p.foreground_projects),
    note: str(p.availability_note),
    availStart: str(p.availability_start),
    availEnd: str(p.availability_end),
    daysOff: list(p.days_off),
    daysOn: list(p.days_on).join(', '),
    output: str(p.output_format) || 'Auto',
    workdayStart: str(p.workday_start),
    workdayEnd: str(p.workday_end),
    paused: list(p.paused_projects),
  };
}

/**
 * The endpoint's payload as the app's period list.
 *
 * The server already sorts earliest-start-first and that order is kept. A payload with no
 * `periods` array reads as NO periods rather than throwing — the Focus tab's empty state is a
 * real state June can be in (she has not authored one), and it is the honest thing to show.
 */
export function periodsFromLive(res: PeriodsResponse, today: string = todayIso()): Period[] {
  // `today` is resolved ONCE and passed down, not defaulted per period: a list mapped across
  // midnight would otherwise date its first entries yesterday and its last ones today.
  // The explicit arrow also stops `.map` handing the array INDEX to the `today` parameter.
  return Array.isArray(res?.periods) ? res.periods.map((p) => periodFromLive(p, today)) : [];
}

