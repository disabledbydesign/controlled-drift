// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * Tests for the FOCUS write seam.
 *
 * The shapes below are the server's real ones, read off `scripts/server.py` (`/api/focus/author`
 * :1344, `reflect` :1362, `commit` :1371, `edit` :1427, `update` :1451) and
 * `focus_period_adapter.missing_required` — not inferred from the app side. The plan's line
 * numbers for commit/update were stale; these are the read ones.
 *
 * THE HAZARD THIS FILE EXISTS FOR. `commit` and `update` answer a REFUSED write with **HTTP 200**
 * and a body of `{"blocked":[...]}`. `client.ts`'s generic `request()` treats any 200 without
 * `ok:false` as success, so a refusal would raise a success toast over a period that was never
 * written. Three outcomes must stay distinguishable: saved / needs-a-field / failed. Collapsing
 * any two of them is the defect this seam exists to prevent.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { commitFocus, updateFocus, startAuthor, startFocusEdit, reflectFields } from '../focus.ts';

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

const FIELDS = { name: 'Jobs week', start_date: '2026-07-20', end_date: '2026-07-26' };

describe('commitFocus — the 200 that is not a success', () => {
  it('reports a written period as SAVED, carrying the id the server wrote', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, id: 'fp123', name: 'Jobs week' }));
    expect(await commitFocus(FIELDS, 'jobs first this week')).toEqual({
      kind: 'saved',
      id: 'fp123',
      name: 'Jobs week',
      unresolved: [],
      notReactivated: [],
    });
  });

  /**
   * THE CORE CASE. A 200 carrying `blocked` is a refusal — she has not filled the dates in.
   * It must arrive as its own outcome, naming the fields, so the shell can tell her which one
   * to fill without addressing her as if something broke.
   */
  it('reports a blocked write as NEEDS, naming the missing fields', async () => {
    vi.stubGlobal('fetch', respond(200, { blocked: ['start date', 'end date'] }));
    expect(await commitFocus(FIELDS, 'jobs first')).toEqual({
      kind: 'needs',
      missing: ['start date', 'end date'],
    });
  });

  it('keeps needs and saved as different answers', async () => {
    vi.stubGlobal('fetch', respond(200, { blocked: ['end date'] }));
    const res = await commitFocus(FIELDS, 'x');
    expect(res.kind).toBe('needs');
    expect(res.kind).not.toBe('saved');
  });

  /** A real breakage stays a breakage — the server's own sentence, which says what did not save. */
  it('reports a server failure as FAILED, carrying the server sentence', async () => {
    vi.stubGlobal('fetch', respond(500, { error: 'period did not persist correctly on read-back' }));
    expect(await commitFocus(FIELDS, 'x')).toEqual({
      kind: 'failed',
      error: 'period did not persist correctly on read-back',
    });
  });

  it('keeps needs and failed as different answers', async () => {
    vi.stubGlobal('fetch', respond(500, { error: 'boom' }));
    const res = await commitFocus(FIELDS, 'x');
    expect(res.kind).toBe('failed');
    expect(res.kind).not.toBe('needs');
  });

  /** An unknown project name comes back 400 with a real sentence — a failure, not a refusal. */
  it('reports an unknown project name as FAILED, not as a missing field', async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'no project named "Jorbs"' }));
    const res = await commitFocus(FIELDS, 'x');
    expect(res).toEqual({ kind: 'failed', error: 'no project named "Jorbs"' });
  });

  it('sends the fields and the raw text the server reads', async () => {
    const f = respond(200, { ok: true, id: 'fp1', name: 'n' });
    vi.stubGlobal('fetch', f);
    await commitFocus(FIELDS, 'jobs first this week');
    const [path, init] = f.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/focus/commit');
    expect(JSON.parse(init.body as string)).toEqual({
      fields: FIELDS,
      raw_text: 'jobs first this week',
    });
  });
});

/**
 * FINDING 2 — the write that saved AND partly did not.
 *
 * Both write routes reactivate the as-needed tasks she named ("keep the dishes going") AFTER the
 * period itself is written and read back. A task whose name cannot be resolved, or that fails to
 * turn back on, does not roll the period back — so the server answers `{"ok":true, …}` and adds
 * `reactivate_unresolved` / `reactivate_failed` beside it, with a comment saying these are
 * "surfaced alongside the success, never silently dropped".
 *
 * The client must not undo that. Dropping them means she is told her period saved while a task
 * she asked for stays off, with nothing anywhere saying so — the same success-over-a-partial-write
 * defect this seam exists to prevent, arriving from the other direction.
 */
describe('commitFocus — a period that saved while part of it did not', () => {
  it('carries the names the server could not resolve alongside the save', async () => {
    vi.stubGlobal(
      'fetch',
      respond(200, {
        ok: true,
        id: 'fp1',
        name: 'Jobs week',
        reactivate_unresolved: ['Dishes'],
      }),
    );
    expect(await commitFocus(FIELDS, 'keep the dishes going')).toEqual({
      kind: 'saved',
      id: 'fp1',
      name: 'Jobs week',
      unresolved: ['Dishes'],
      notReactivated: [],
    });
  });

  /**
   * The failed entries keep their `error` rather than being reduced to ids: the id is a
   * gsdo object id, which means nothing to June, while the error is what has to reach the log
   * for anyone to find out why a task she asked for did not come back.
   */
  it('carries the tasks that failed to turn back on, with the reason, alongside the save', async () => {
    vi.stubGlobal(
      'fetch',
      respond(200, {
        ok: true,
        id: 'fp1',
        name: 'Jobs week',
        reactivate_failed: [{ id: 'task-9', error: 'connection refused' }],
      }),
    );
    expect(await commitFocus(FIELDS, 'x')).toEqual({
      kind: 'saved',
      id: 'fp1',
      name: 'Jobs week',
      unresolved: [],
      notReactivated: [{ id: 'task-9', error: 'connection refused' }],
    });
  });

  /**
   * `_reactivate_named_tasks` returns `[{"id": null, "error": …}]` when RESOLUTION itself threw —
   * a real partial failure with no id to name. It must still register as one, or the whole
   * resolution step failing would read as a clean save.
   */
  it('still reports a partial failure when the failed entry has no id on it', async () => {
    vi.stubGlobal(
      'fetch',
      respond(200, {
        ok: true,
        id: 'fp1',
        name: 'Jobs week',
        reactivate_failed: [{ id: null, error: 'space unreachable' }],
      }),
    );
    expect(await commitFocus(FIELDS, 'x')).toEqual({
      kind: 'saved',
      id: 'fp1',
      name: 'Jobs week',
      unresolved: [],
      notReactivated: [{ id: null, error: 'space unreachable' }],
    });
  });

  /** A clean save must stay legible as clean — both lists empty, so a caller can just check them. */
  it('reports a clean save with both partial-failure lists empty', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, id: 'fp1', name: 'Jobs week' }));
    expect(await commitFocus(FIELDS, 'x')).toEqual({
      kind: 'saved',
      id: 'fp1',
      name: 'Jobs week',
      unresolved: [],
      notReactivated: [],
    });
  });
});

describe('updateFocus — the same refusal convention on the edit route', () => {
  it('reports a written update as SAVED', async () => {
    vi.stubGlobal('fetch', respond(200, { ok: true, id: 'fp9', name: 'Care week' }));
    expect(await updateFocus('fp9', FIELDS, 'caregiving starts Saturday')).toEqual({
      kind: 'saved',
      id: 'fp9',
      name: 'Care week',
      unresolved: [],
      notReactivated: [],
    });
  });

  /** The edit route reactivates too, so it reports a partial failure the same way. */
  it('carries an unresolved name alongside a saved update', async () => {
    vi.stubGlobal(
      'fetch',
      respond(200, { ok: true, id: 'fp9', name: 'Care week', reactivate_unresolved: ['Fridge'] }),
    );
    expect(await updateFocus('fp9', FIELDS, 'x')).toEqual({
      kind: 'saved',
      id: 'fp9',
      name: 'Care week',
      unresolved: ['Fridge'],
      notReactivated: [],
    });
  });

  it('reports a blocked update as NEEDS, naming the missing field', async () => {
    vi.stubGlobal('fetch', respond(200, { blocked: ['end date'] }));
    expect(await updateFocus('fp9', FIELDS, 'x')).toEqual({ kind: 'needs', missing: ['end date'] });
  });

  /** The server refuses an update with no id at 400. That is a failure, not a missing field. */
  it('reports a missing period id as FAILED', async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'update needs the period id' }));
    expect(await updateFocus('', FIELDS, 'x')).toEqual({
      kind: 'failed',
      error: 'update needs the period id',
    });
  });

  it('sends the period id the server requires', async () => {
    const f = respond(200, { ok: true, id: 'fp9', name: 'n' });
    vi.stubGlobal('fetch', f);
    await updateFocus('fp9', FIELDS, 'text');
    const [path, init] = f.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/focus/update');
    expect(JSON.parse(init.body as string)).toEqual({
      id: 'fp9',
      fields: FIELDS,
      raw_text: 'text',
    });
  });
});

describe('startAuthor — the 202 that may not have started', () => {
  /**
   * `_start_focus_generation` shares ONE lock with plan generation. A busy server answers
   * `started:false` on a 202 — a 2xx. Reading that as "running" polls forever for a job that
   * does not exist, while her words sit there looking submitted.
   */
  it('reports a busy server as BUSY, not as started', async () => {
    vi.stubGlobal('fetch', respond(202, { state: 'running', started: false }));
    expect(await startAuthor('jobs first this week')).toEqual({ kind: 'busy' });
  });

  it('reports a real start as started', async () => {
    vi.stubGlobal('fetch', respond(202, { state: 'running', started: true }));
    expect(await startAuthor('jobs first this week')).toEqual({ kind: 'started' });
  });

  it('reports empty text refused by the server as FAILED', async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'authoring needs text' }));
    expect(await startAuthor('')).toEqual({ kind: 'failed', error: 'authoring needs text' });
  });

  it('posts her words to the authoring route', async () => {
    const f = respond(202, { state: 'running', started: true });
    vi.stubGlobal('fetch', f);
    await startAuthor('jobs first this week');
    const [path, init] = f.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/focus/author');
    expect(JSON.parse(init.body as string)).toEqual({ text: 'jobs first this week' });
  });
});

describe('startFocusEdit — the spoken-revision route', () => {
  it('reports a busy server as BUSY, not as started', async () => {
    vi.stubGlobal('fetch', respond(202, { state: 'running', started: false }));
    expect(await startFocusEdit('make Sunday off too')).toEqual({ kind: 'busy' });
  });

  it('posts her words to the edit route', async () => {
    const f = respond(202, { state: 'running', started: true });
    vi.stubGlobal('fetch', f);
    await startFocusEdit('make Sunday off too');
    const [path, init] = f.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/focus/edit');
    expect(JSON.parse(init.body as string)).toEqual({ text: 'make Sunday off too' });
  });
});

describe('reflectFields — the deterministic read-back', () => {
  /**
   * The reflect template lives in Python and is the single source of the wording June checks.
   * This call is what makes "Here's what I heard" true: it renders the fields the model actually
   * produced, rather than the client inventing a summary.
   */
  it('returns the server-rendered reflect payload', async () => {
    vi.stubGlobal('fetch', respond(200, { summary: 'Jobs week · Mon Jul 20 – Sun Jul 26', items: [] }));
    const res = await reflectFields(FIELDS);
    expect(res.ok).toBe(true);
    if (res.ok) expect(res.data.summary).toBe('Jobs week · Mon Jul 20 – Sun Jul 26');
  });

  it('sends the fields and the original, so the diff read-back can mark what changed', async () => {
    const f = respond(200, { summary: 's', items: [] });
    vi.stubGlobal('fetch', f);
    await reflectFields(FIELDS, { name: 'Old week' });
    const [path, init] = f.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/focus/reflect');
    expect(JSON.parse(init.body as string)).toEqual({
      fields: FIELDS,
      original: { name: 'Old week' },
    });
  });
});