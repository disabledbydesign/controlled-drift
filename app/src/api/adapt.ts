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
 *   duration_min → durationMin · interstitial → kind:'break' · block → kind:'block' ·
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
export function planFromLive(live: LivePlan): Plan {
  const shape = live.shape === 'priority' ? 'priority' : 'schedule';
  const conv = (it: LivePlanItem): PlanItem => {
    if (it.interstitial) {
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
        id: it.id ?? it.project_id ?? '',
        task: it.task ?? '',
        time: it.time ?? '',
        chunkMin: it.chunk_min ?? 0,
        why: '',
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
    } as PlanItem;
  };

  const appts = (live.appointments ?? []).map(conv);
  const blocks: PlanBlock[] =
    shape === 'schedule'
      ? (live.blocks ?? []).map((b) => ({
          label: b.label,
          time: b.time,
          framing: b.framing,
          items: b.items.map(conv),
        }))
      : [{ label: '', time: '', framing: '', items: (live.items ?? []).map(conv) }];

  // Appointments are fixed-time anchors, so they lead. See the ⚠ above.
  if (appts.length) {
    const first = blocks[0];
    if (first) first.items = [...appts, ...first.items];
    else blocks.push({ label: '', time: '', framing: '', items: appts });
  }

  return {
    // Display-formatted server-side in the fixture (contract §6 Q8, unresolved). Formatted here
    // from the real generation timestamp rather than left blank.
    date: live.generated_at ? fmtDay(live.generated_at) : '',
    // Spec §14 removed the plan-age line and nothing renders this. Kept empty rather than
    // fabricating "Built this morning at 9:02."
    generated: '',
    shape,
    woven: live.woven_frame ?? '',
    blocks,
  };
}

function fmtDay(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
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

