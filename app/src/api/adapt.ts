/**
 * Where the wire shapes and the app's shapes disagree, and exactly how much.
 *
 * Kept apart from `client.ts` (which only moves bytes) and from `model/` (which is pure) so
 * that every place the two tracks did not converge is visible in ONE file. Each function below
 * names the divergence it closes and cites where the contract records it.
 */

import type { Node, Plan, PlanBlock, PlanItem, Schema } from '../fixtures/index.ts';
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
 * ⚠ FOCUS PERIODS ARE NOT WIRED, and this note is the record of why.
 *
 * `GET /api/periods` DOES NOT EXIST — verified live 2026-07-18 (`{"error":"no route
 * /api/periods"}`). Contract §2.5 marks it CHANGE: the singular `/api/period` returns only the
 * ACTIVE period, already rendered for display, which the Focus editor cannot edit. So the Focus
 * tab still runs on `seedPeriods`. Building the endpoint is Track B; inventing a client-side
 * shim over the display-rendered singular endpoint would be guessing at the field mapping
 * (`period_to_fields` is flat snake_case with different names — §2.6 says to agree ONE
 * convention rather than maintain a translation on both sides).
 */

