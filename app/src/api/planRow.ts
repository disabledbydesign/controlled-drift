/**
 * The PER-ROW plan write path — "not today", duration, and move.
 *
 * ── why this file exists ─────────────────────────────────────────────────────
 * Three endpoints were live and unreachable. The old overlay carried all three per row
 * (`docs/overlay_daily.html`, `editPanelHtml` ~2135); the v4 rebuild's row has only an edit chip,
 * which opens the object editor instead. Every one of these backends predates the rebuild — the
 * new surface simply never called them. This is the wire-in, not a new feature.
 *
 * ── WHAT THESE ROUTES ANSWER WITH, AND WHY IT IS THE POINT ───────────────────
 * All three return the REWRITTEN PLAN. That plan is the only proof the write landed, and taking
 * it is what makes the change survive a reload — the same reasoning `chunkBlock` records in
 * `shell/useAppState.ts` for the block check. A seam that answered `boolean` would force the
 * caller to re-fetch, or to leave an unchanged screen standing as if it were the new truth.
 *
 * ── TWO OUTCOMES, NOT THREE — AND WHY THE WARNING RIDES ON `saved` ───────────
 * Every one of these is `saved | failed`. There is deliberately no third variant, because unlike the
 * focus family (`api/focus.ts`) these routes have no refusal-on-200 convention: a 4xx is a real
 * not-written, and `client.ts` has already turned it into `{ok:false,error}` carrying the
 * server's own sentence.
 *
 * `not-today` DOES have a partial failure: the row comes off today's list, and then one of the
 * two logs (the 8h deferral window, the corrections record) may fail to write. The server sends
 * `{ok:true, plan, warning}` — the removal is NOT undone. So the warning is DETAIL ON THE SAVE,
 * exactly as `api/focus.ts` argues for its reactivation failures: the question this union answers
 * is "did it come off today's list?", and the answer is plainly yes. A separate `kind` would let
 * a caller that forgot the variant tell her a removal that happened did not — a lie about her
 * data, traded for a message she should merely have seen. `warning` is therefore always present
 * (`null` when clean), never optional, so it cannot be read as clean by forgetting a key.
 *
 * ── `not-today` IS CACHE-ONLY BY DESIGN. DO NOT MAKE IT DURABLE. ─────────────
 * No Anytype write, no status change, no reschedule. The 8h session window makes a SAME-DAY
 * regenerate honour it, and then it expires. June asked for exactly that: it holds for the day
 * and does not leak into future days. Its deferral record goes to `corrections_log`, not
 * `signal_log` — `signal_log` is her own typed words, and a machine-recorded deferral is not her
 * voice (June's correction, 2026-07-18; commit 1522ad5).
 */

import { apiGet, apiSend } from './client.ts';
import type { ApiResult } from './client.ts';
import type { LivePlan } from './adapt.ts';

/**
 * The failure half, shared by all three.
 *
 * Across every `saved` below, `plan` is `null` when the server had nothing cached to rewrite
 * (`/api/duration` answers `{empty:true}` in that case). The write itself still happened — the
 * field write and the plan rewrite are separate effects — so that is a `saved` with no plan,
 * never a failure.
 */
export type Failed = { kind: 'failed'; error: string };

/** `not-today` alone can half-succeed — see the warning note in the header. */
export type NotTodayWrite = { kind: 'saved'; plan: LivePlan | null; warning: string | null } | Failed;

/** Duration echoes back the minutes the SERVER confirmed, which is what should be displayed. */
export type DurationWrite = { kind: 'saved'; plan: LivePlan | null; minutes: number } | Failed;

/** A move has nothing to report beyond the rewritten plan. */
export type MoveWrite = { kind: 'saved'; plan: LivePlan | null } | Failed;

interface RowBody {
  plan?: unknown;
  warning?: unknown;
}

/** `{empty:true}` is "no cached plan", not a plan. Anything else usable is handed straight on. */
function planOf(raw: unknown): LivePlan | null {
  if (!raw || typeof raw !== 'object') return null;
  if ((raw as { empty?: unknown }).empty) return null;
  return raw as LivePlan;
}

/** The one shared translation: a real 4xx/5xx is a failure, anything else carries a plan. */
function rowOutcome(res: ApiResult<RowBody>): { kind: 'saved'; plan: LivePlan | null } | Failed {
  if (!res.ok) return { kind: 'failed', error: res.error };
  return { kind: 'saved', plan: planOf(res.data?.plan) };
}

/**
 * `POST /api/task/not-today` — take this off TODAY'S list only.
 *
 * `kind` is what the server dispatches on: `'task'` drops one row, `'block'` takes the id as a
 * PROJECT id and drops every row of that block.
 */
export async function notToday(id: string, kind: 'task' | 'block'): Promise<NotTodayWrite> {
  const res = await apiSend<RowBody>('POST', '/api/task/not-today', { id, kind });
  const out = rowOutcome(res);
  if (out.kind === 'failed') return out;
  const w = res.ok ? res.data?.warning : null;
  return { ...out, warning: typeof w === 'string' && w ? w : null };
}

/**
 * `POST /api/duration` — set how long this takes.
 *
 * ⚠ ONE endpoint, TWO meanings, dispatched SERVER-side on `plan_store.is_block_item`:
 *   - a BLOCK → the durable per-project CHUNK LENGTH ("how long I work on this in a sitting")
 *   - a TASK  → that task's own `Duration min` ("how long this specific thing takes")
 * The distinction is June's, and it is not cosmetic, so the caller must say which one she is
 * looking at in the label. This function does not need to know: it must not second-guess the
 * server's dispatch by trying to decide the kind itself.
 */
export async function setDuration(id: string, minutes: number): Promise<DurationWrite> {
  const res = await apiSend<RowBody & { duration_min?: unknown }>('POST', '/api/duration', {
    id,
    minutes,
  });
  const out = rowOutcome(res);
  if (out.kind === 'failed') return out;
  // Prefer the minutes the server CONFIRMED over the ones we asked for — showing the requested
  // value would display a number that was never written if the two ever diverge.
  const confirmed = res.ok ? Number(res.data?.duration_min) : NaN;
  return { ...out, minutes: Number.isFinite(confirmed) ? confirmed : minutes };
}

/** Where a move lands. `block` is `null` on a fragmented (priority) day, which has no blocks. */
export interface MoveTarget {
  block: number | null;
  /** The FINAL index the item lands at — the contract `/api/task/move` expects. */
  position: number;
}

/**
 * `POST /api/task/move` — relocate one item in today's cached plan.
 *
 * BIDIRECTIONAL (commit 3940fe7): earlier and later both work, and the server re-flows the clock
 * times in both affected blocks. The old overlay offered later-only; that limit was its own, not
 * the backend's, and it is not reproduced here.
 *
 * ⚠ `target_block` is OMITTED, not sent as null, on a priority day. The server reads
 * "position only" as the fragmented-day reorder (`plan_store.move_priority_item`) and rejects a
 * null outright — its `_bad_int` guard takes any non-int as a 400.
 *
 * The move lives ONLY in the cache. The next generation rebuilds from Anytype and it is gone;
 * nothing here should tell her otherwise.
 */
export async function moveItem(id: string, to: MoveTarget): Promise<MoveWrite> {
  const body: Record<string, unknown> = { id, position: to.position };
  if (to.block !== null) body['target_block'] = to.block;
  return rowOutcome(await apiSend<RowBody>('POST', '/api/task/move', body));
}

/**
 * `POST /api/plan/priority-order` — make June's OWN ranking of a fragmented-day list durable.
 *
 * Until 2026-07-19 the up/down controls wrote to `ctx.up({priOrder})` and nothing else: there was
 * no server reference anywhere, and every reordering she made was gone on the next load. Her
 * decision — "Yes, should persist" — closes `docs/api_contract_v2.md` §6 Q1.
 *
 * ⚠ `order` is a list of OBJECT IDS, in her order — never slot positions. A regenerated plan
 * reassigns slots, so an index-keyed ranking silently reattaches to whatever now sits at that
 * index. Commit b721103 moved block state off slot keys for exactly this reason and `chunked`
 * carried the same bug before it.
 *
 * Cache-only, like `moveItem`: a regeneration drops it and the generator's order stands. See
 * `plan_store.set_priority_order` for that decision and the alternative left open for June.
 */
export async function savePriorityOrder(order: readonly string[]): Promise<MoveWrite> {
  return rowOutcome(await apiSend<RowBody>('POST', '/api/plan/priority-order', {
    order: [...order],
  }));
}

/**
 * Her saved ranking, or `null` if there isn't one.
 *
 * ⚠ THERE IS NO DEDICATED READ ROUTE, deliberately: the order rides back inside `GET /api/plan`
 * with the rest of the plan. This reads that payload and picks the field out.
 *
 * ⚠ `null` MEANS "NOTHING TO APPLY", NOT "SHE HAS NO ORDERING". A failed read answers `null`
 * too, because in both cases there is nothing to render — but no caller may report this to her
 * as "no ordering saved", and nothing may write `null` back to the server on the strength of it.
 * That would turn one dropped request into the loss of the ordering this whole seam exists to
 * keep.
 */
export async function readPriorityOrder(): Promise<string[] | null> {
  const res = await apiGet<{ empty?: boolean; priority_order?: unknown }>('/api/plan');
  if (!res.ok || res.data?.empty) return null;
  const raw = res.data?.priority_order;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  // A malformed field is dropped rather than half-applied: a partly-string ranking would
  // reorder some rows and lose others, which is worse than showing the generator's order.
  if (!raw.every((i) => typeof i === 'string' && i)) return null;
  return raw as string[];
}
