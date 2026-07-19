import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT THE ACTION ROW IS ALLOWED TO CLAIM, AND WHEN.
 *
 * The six generation buttons used to call `flash()` and nothing else — "Regenerating plan…",
 * "Trimmed to one small win", "Showing quick wins" all described a plan change that never
 * happened. They now call `/api/refresh` and `/api/negotiate`.
 *
 * ⚠ THE HAZARD THAT MOTIVATES EVERY TEST BELOW: both endpoints answer **202** and generate in a
 * background thread (`server.py:910`, `:921`, `_start_generation` at `:269`). A 202 means the
 * work STARTED. Treating it as a finished write would put "Your plan is updated" on screen
 * while generation had not yet produced a line — which is the exact bug class this thread
 * exists to close, dressed as a fix for it.
 *
 * Every assertion is POSITIVE: it names the request that must go out, or the signal that must
 * be raised. Asserting only that success did NOT appear would pass just as well against a
 * button wired to nothing, which is how a dead control gets certified as fixed.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit or renders
 * accumulate.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';

/**
 * A plan payload in the shape `/api/plan` really answers — `woven_frame`, not `woven`. The
 * adapter (`api/adapt.ts:planFromLive`) is what renames it, so a fixture-shaped payload here
 * would test the test rather than the wire-in.
 */
const NEW_PLAN = {
  shape: 'schedule',
  header: '',
  woven_frame: 'A newly generated day.',
  generated_at: '2026-07-18T09:00:00',
  blocks: [{ time: '09:00', label: 'Morning', framing: '', items: [] }],
};

/** What a read answers: a fixed result, or a function for a sequence of them. */
type Answer = unknown | (() => Promise<unknown>);

/**
 * The four mount reads, all succeeding.
 *
 * ⚠ These are set BEFORE mounting and replaced AFTER it (`answering`), never merged. An earlier
 * version passed the per-test `/api/plan` override into hydration too, so the "could not read
 * the new plan" test was actually asserting on the failure the MOUNT raised — it passed while
 * `regenerate` did nothing at all.
 */
function hydrate() {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
    // The real vocabulary is irrelevant here and an EMPTY one keeps the mount silent: a failed
    // schema read raises its own failure signal, which would sit in `toast` and be mistaken for
    // this feature's.
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { empty: true } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    return { ok: false, error: 'not part of this test' };
  });
}

/** What the reads answer once the app is mounted — the polling and plan-reread traffic. */
function answering(map: Record<string, Answer>) {
  get.mockImplementation(async (path: string) => {
    const a = map[path];
    if (a === undefined) return { ok: false, error: `${path} is not part of this test` };
    return typeof a === 'function' ? await (a as () => Promise<unknown>)() : a;
  });
}

/**
 * `/api/status` answering `running` `runs` times before it settles to `state`.
 *
 * This is what makes the poll observable: with one 'idle' answer a test cannot tell polling
 * from a lucky first read, so every timing test below uses at least one 'running' answer.
 */
function statusSequence(runs: number, settled: Record<string, unknown> = { state: 'idle' }) {
  let n = 0;
  return async () => {
    n += 1;
    return n <= runs ? { ok: true, data: { state: 'running' } } : { ok: true, data: settled };
  };
}

beforeEach(() => {
  send.mockReset();
  get.mockReset();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

/** Mount live and wait for hydration to settle, so the mount reads cannot be confused for polls. */
async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  get.mockClear();
  return h;
}

/** Let the poll loop run: each turn is one `sleep(POLL_MS)` plus its status read. */
async function tick(turns = 1) {
  for (let i = 0; i < turns; i += 1) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_200);
    });
  }
}

describe('the generation controls issue the request the server implements', () => {
  it('sends POST /api/refresh for a fresh plan', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': { ok: true, data: { state: 'idle' } } });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/refresh', {});
  });

  it('passes a capacity through to /api/refresh when one is given', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': { ok: true, data: { state: 'idle' } } });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh', capacity: 'low-energy' }, '↻ Fresh plan');
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/refresh', { capacity: 'low-energy' });
  });

  /**
   * The ids are the server's, read from `plan_store._DEFAULT_ACTIONS['presets']` and confirmed
   * against her live `~/.controlled-drift/actions.json`. `find_preset` answers an unknown one
   * with 400 (`server.py:927`), so a typo here is a button that fails on contact.
   */
  it.each([
    ['low-energy', 'Low energy today'],
    ['quick-wins', 'Quick wins only'],
    ['stuck', 'I’m stuck'],
  ])('sends POST /api/negotiate {preset_id:%s} for "%s"', async (presetId, label) => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': { ok: true, data: { state: 'idle' } } });

    await act(async () => {
      void result.current.regenerate({ kind: 'preset', presetId }, label);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/negotiate', { preset_id: presetId });
  });
});

describe('a 202 is not a finished write', () => {
  it('raises no signal at all while the generation is still running', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': statusSequence(3) });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    await tick(2);

    // POSITIVE: the poll is what is happening right now, and the control says so.
    expect(get).toHaveBeenCalledWith('/api/status');
    expect(result.current.generating).toBe('↻ Fresh plan');
    expect(result.current.toast).toBeNull();
  });

  it('raises success and shows the new plan only once the generation has settled', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': statusSequence(2), '/api/plan': { ok: true, data: NEW_PLAN } });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    await tick(4);

    await waitFor(() => expect(result.current.toast?.kind).toBe('success'));
    expect(result.current.toast?.msg).toBe('Your plan is updated');
    // The plan she is looking at is the one the server just made — the point of the whole wire-in.
    expect(result.current.plan.woven).toBe('A newly generated day.');
    expect(result.current.generating).toBeNull();
  });

  it('re-reads the plan only after the poll settles, never off the 202', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({ '/api/status': statusSequence(2), '/api/plan': { ok: true, data: NEW_PLAN } });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    // One turn in, the generation is still running: the plan read must not have happened yet.
    await tick(1);
    expect(get.mock.calls.map((c) => c[0])).toEqual(['/api/status']);

    await tick(3);
    await waitFor(() => expect(get).toHaveBeenCalledWith('/api/plan'));
  });
});

describe('a failure is readable, and never reads as a success', () => {
  it('names the server error when the request cannot start', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'unknown preset' });
    const { result } = await mount();

    await act(async () => {
      await result.current.regenerate({ kind: 'preset', presetId: 'low-energy' }, 'Low energy today');
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('unknown preset');
    expect(result.current.toast?.msg).toContain('has not changed');
    expect(result.current.generating).toBeNull();
  });

  it('reports a generation that failed on the server, with what it said', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({
      '/api/status': statusSequence(1, { state: 'error', error: 'the model timed out' }),
    });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    await tick(3);

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(result.current.toast?.msg).toContain('the model timed out');
  });

  it('says so when another generation already holds the server lock', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: false } });
    const { result } = await mount();

    await act(async () => {
      await result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('did not start');
  });

  it('reports a new plan it could not read, rather than claiming the old one is new', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({
      '/api/status': statusSequence(1),
      '/api/plan': { ok: false, error: 'could not reach the server' },
    });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    await tick(3);

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(result.current.toast?.msg).toContain('could not be read');
  });

  /**
   * A dropped status read is NOT a failed generation, and saying it was would be its own false
   * claim. The loop keeps polling and recovers when the server answers again.
   */
  it('keeps polling through a status read that failed, and still confirms when it settles', async () => {
    let n = 0;
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();
    answering({
      '/api/status': async () => {
        n += 1;
        if (n === 1) return { ok: false, error: 'could not reach the server' };
        if (n === 2) return { ok: true, data: { state: 'running' } };
        return { ok: true, data: { state: 'idle' } };
      },
      '/api/plan': { ok: true, data: NEW_PLAN },
    });

    await act(async () => {
      void result.current.regenerate({ kind: 'refresh' }, '↻ Fresh plan');
    });
    await tick(4);

    await waitFor(() => expect(result.current.toast?.kind).toBe('success'));
    expect(result.current.plan.woven).toBe('A newly generated day.');
  });
});
