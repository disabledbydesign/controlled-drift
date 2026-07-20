// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * Tests for the PRIORITY-ORDER seam — `savePriorityOrder` and `readPriorityOrder`.
 *
 * The shapes below were read off the running handler in `scripts/server.py`, not inferred:
 *
 *   POST /api/plan/priority-order  {order:[task ids]}
 *       200 {ok:true, plan}                    — plan carries `priority_order`
 *       400 {error:'…must be a task id'} / '…does not match the plan's list…'
 *       404 {error:'no cached plan to rank'} / '…no priority list to rank…'
 *
 * WHY THIS EXISTS AT ALL. Until now `PriorityList.tsx` wrote her reordering to `ctx.up({priOrder})`
 * and stopped there — client state, gone on reload. June's decision, 2026-07-19: "Yes, should
 * persist." This is the wire.
 *
 * ⚠ THE ORDER IS A LIST OF OBJECT IDS, NEVER SLOT POSITIONS. A regenerated plan reassigns slots,
 * so an index-keyed ranking reattaches to whatever now sits at that index. Commit b721103 moved
 * block state off slot keys for this reason and `chunked` carried the same bug before it. The
 * first test below asserts the ids go on the wire, which is what makes that concrete.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { readPriorityOrder, savePriorityOrder } from '../planRow.ts';

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as unknown as Response);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

const PLAN = {
  shape: 'priority',
  items: [{ id: 'a' }, { id: 'b' }, { id: 'c' }],
  priority_order: ['c', 'a', 'b'],
};

describe('savePriorityOrder', () => {
  it('reports SAVED and hands back the rewritten plan', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, plan: PLAN }));
    expect(await savePriorityOrder(['c', 'a', 'b'])).toEqual({ kind: 'saved', plan: PLAN });
  });

  it('puts the OBJECT IDS on the wire, in her order, under `order`', async () => {
    const f = respond(200, { ok: true, plan: PLAN });
    vi.stubGlobal('fetch', f);
    await savePriorityOrder(['c', 'a', 'b']);
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ order: ['c', 'a', 'b'] });
    expect(f.mock.calls[0]![0]).toBe('/api/plan/priority-order');
  });

  it("reports the server's own sentence when the order names a row the plan does not have", async () => {
    vi.stubGlobal(
      'fetch',
      respond(400, { error: "that order does not match the plan's list; not in the plan: ['z']" }),
    );
    expect(await savePriorityOrder(['a', 'z'])).toEqual({
      kind: 'failed',
      error: "that order does not match the plan's list; not in the plan: ['z']",
    });
  });

  it('reports a failure when there is no cached plan to rank', async () => {
    vi.stubGlobal('fetch', respond(404, { error: 'no cached plan to rank' }));
    expect(await savePriorityOrder(['a'])).toEqual({
      kind: 'failed',
      error: 'no cached plan to rank',
    });
  });
});

describe('readPriorityOrder', () => {
  /**
   * There is deliberately NO dedicated read route. The saved ranking rides back inside
   * `GET /api/plan` with the rest of the plan, so this reads that payload and picks the field
   * out. See the note on the function itself for why the component reads it rather than the
   * shell.
   */
  it('reads the saved order off GET /api/plan', async () => {
    const f = respond(200, PLAN);
    vi.stubGlobal('fetch', f);
    expect(await readPriorityOrder()).toEqual(['c', 'a', 'b']);
    expect(f.mock.calls[0]![0]).toBe('/api/plan');
  });

  it('answers null when the plan carries no saved order', async () => {
    vi.stubGlobal('fetch', respond(200, { shape: 'priority', items: [{ id: 'a' }] }));
    expect(await readPriorityOrder()).toBeNull();
  });

  it('answers null when there is no cached plan at all', async () => {
    vi.stubGlobal('fetch', respond(200, { empty: true }));
    expect(await readPriorityOrder()).toBeNull();
  });

  /**
   * A failed read is not an empty ranking. Both answer `null` — there is nothing to apply
   * either way — but this must never be reported to her as "you have no ordering saved", and
   * nothing downstream may write `null` back to the server on the strength of it.
   */
  it('answers null when the plan could not be read', async () => {
    vi.stubGlobal('fetch', respond(500, { error: 'boom' }));
    expect(await readPriorityOrder()).toBeNull();
  });

  it('ignores an order that is not a list at all', async () => {
    vi.stubGlobal('fetch', respond(200, { shape: 'priority', priority_order: 'c,a,b' }));
    expect(await readPriorityOrder()).toBeNull();
  });

  /**
   * ⚠ A LIST WITH A NON-ID IN IT — the case the `Array.isArray` check above does NOT cover.
   * An earlier version of this file tested only the string `'c,a,b'`, which is rejected by
   * `Array.isArray` before the per-entry check is ever consulted, so the per-entry guard could
   * be deleted with every test still green. Found by mutation, not by reading.
   *
   * Dropping the whole thing is the point: applying it partly would rank some rows and lose
   * the others, which is worse than showing the generator's order.
   */
  it('drops the whole order when any entry is not an id, rather than applying it partly', async () => {
    vi.stubGlobal('fetch', respond(200, { shape: 'priority', priority_order: ['c', 7, 'b'] }));
    expect(await readPriorityOrder()).toBeNull();
  });
});