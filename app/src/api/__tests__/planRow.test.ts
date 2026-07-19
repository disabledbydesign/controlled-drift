/**
 * Tests for the PER-ROW plan write seam — "not today", duration, and move.
 *
 * The shapes below were read off the running handlers in `scripts/server.py`, not inferred from
 * the app side or from the build plan (whose line numbers were stale three separate times):
 *
 *   POST /api/task/not-today  {id, kind:'task'|'block', name?}
 *       200 {ok:true, plan, warning?}   — `warning` means the row IS off today's list but a log
 *                                         write failed. The removal still happened.
 *       404 {error:"that item isn't on today's list"} / {error:'no cached plan to remove from'}
 *   POST /api/duration        {id, minutes}
 *       200 {ok:true, id, duration_min, plan}   — plan may be {empty:true}
 *       400 {error:'duration needs id and positive integer minutes'}
 *   POST /api/task/move       {id, target_block?, position?}
 *       200 {ok:true, plan}
 *       400 out of range / already there   404 no cache / id not found
 *
 * THE HAZARD THIS FILE EXISTS FOR. All three answer with the REWRITTEN PLAN, and that plan is the
 * only proof the write landed. A seam that returned a boolean would leave the caller re-fetching
 * or, worse, trusting an unchanged screen. So `saved` carries the plan, and a `warning` rides on
 * `saved` rather than becoming a third outcome — the removal is not undone by a failed log write,
 * so answering "did it come off today's list?" with anything but yes would be a lie about her data.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { moveItem, notToday, setDuration } from '../planRow.ts';

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

const PLAN = { shape: 'priority', items: [{ task: 'still here', id: 'b2' }] };

describe('notToday', () => {
  it('reports the removal as SAVED and hands back the rewritten plan', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, plan: PLAN }));
    expect(await notToday('t1', 'task')).toEqual({ kind: 'saved', plan: PLAN, warning: null });
  });

  it('sends the id and the kind the server dispatches on', async () => {
    const f = respond(200, { ok: true, plan: PLAN });
    vi.stubGlobal('fetch', f);
    await notToday('p9', 'block');
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ id: 'p9', kind: 'block' });
    expect(f.mock.calls[0]![0]).toBe('/api/task/not-today');
  });

  /**
   * The partial-failure case, and the reason `warning` is not a third outcome: the row is OFF
   * today's list. Reporting anything other than `saved` here would tell her a removal that
   * happened did not.
   */
  it('still reports SAVED when only the log write failed, carrying the warning', async () => {
    vi.stubGlobal(
      'fetch',
      respond(200, { ok: true, plan: PLAN, warning: "removed, but the learning note didn't save" }),
    );
    expect(await notToday('t1', 'task')).toEqual({
      kind: 'saved',
      plan: PLAN,
      warning: "removed, but the learning note didn't save",
    });
  });

  it("reports the server's own sentence when the row was not on today's list", async () => {
    vi.stubGlobal('fetch', respond(404, { error: "that item isn't on today's list" }));
    expect(await notToday('t1', 'task')).toEqual({
      kind: 'failed',
      error: "that item isn't on today's list",
    });
  });
});

describe('setDuration', () => {
  it('reports SAVED with the rewritten plan and the minutes the server confirmed', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, id: 't1', duration_min: 45, plan: PLAN }));
    expect(await setDuration('t1', 45)).toEqual({ kind: 'saved', plan: PLAN, minutes: 45 });
  });

  /**
   * `{empty:true}` is the server's "nothing cached to rewrite" answer. The DURATION still wrote —
   * the write and the plan rewrite are separate effects — so this stays `saved` with a null plan.
   */
  it('reports SAVED with a null plan when the server had no cached plan to rewrite', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, id: 't1', duration_min: 45, plan: { empty: true } }));
    expect(await setDuration('t1', 45)).toEqual({ kind: 'saved', plan: null, minutes: 45 });
  });

  it('sends the id and integer minutes', async () => {
    const f = respond(200, { ok: true, id: 't1', duration_min: 30, plan: PLAN });
    vi.stubGlobal('fetch', f);
    await setDuration('t1', 30);
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ id: 't1', minutes: 30 });
    expect(f.mock.calls[0]![0]).toBe('/api/duration');
  });

  it("reports the server's refusal of a non-positive duration", async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'duration needs id and positive integer minutes' }));
    expect(await setDuration('t1', 0)).toEqual({
      kind: 'failed',
      error: 'duration needs id and positive integer minutes',
    });
  });
});

describe('moveItem', () => {
  it('sends target_block AND position on a clock day, and reports SAVED with the plan', async () => {
    const f = respond(200, { ok: true, plan: PLAN });
    vi.stubGlobal('fetch', f);
    expect(await moveItem('t1', { block: 2, position: 0 })).toEqual({ kind: 'saved', plan: PLAN });
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ id: 't1', target_block: 2, position: 0 });
    expect(f.mock.calls[0]![0]).toBe('/api/task/move');
  });

  /**
   * On a fragmented (priority) day the whole plan is one ordered list and there is no block. The
   * server reads "position only" as the priority-shape reorder, so `target_block` must be ABSENT,
   * not null — `move needs a task id and integer target_block/position` rejects a null.
   */
  it('sends position ONLY on a priority day, with no target_block key at all', async () => {
    const f = respond(200, { ok: true, plan: PLAN });
    vi.stubGlobal('fetch', f);
    await moveItem('t1', { block: null, position: 3 });
    const sent = JSON.parse(f.mock.calls[0]![1].body);
    expect(sent).toEqual({ id: 't1', position: 3 });
    expect('target_block' in sent).toBe(false);
  });

  /** Moving EARLIER is a supported destination, not only later (server: `plan_store.move_item`). */
  it('accepts an earlier destination and reports it SAVED', async () => {
    const f = respond(200, { ok: true, plan: PLAN });
    vi.stubGlobal('fetch', f);
    expect(await moveItem('t1', { block: 0, position: 0 })).toEqual({ kind: 'saved', plan: PLAN });
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ id: 't1', target_block: 0, position: 0 });
  });

  it("reports the server's own sentence when the destination was out of range", async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'position 9 is out of range' }));
    expect(await moveItem('t1', { block: 1, position: 9 })).toEqual({
      kind: 'failed',
      error: 'position 9 is out of range',
    });
  });
});
