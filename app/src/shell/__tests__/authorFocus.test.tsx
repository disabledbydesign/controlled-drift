import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * "HERE'S WHAT I HEARD" HAS TO BE TRUE.
 *
 * The author flow's "Structure this →" ran `formFromDraft`, a client-side stand-in that
 * hardcoded `start:'2026-07-21'`, `end:'2026-07-27'` and derived the period's name by cutting
 * her sentence at the first comma. The screen it fed is headed "Here's what I heard" and tells
 * her "It reads back what it heard for you to check — it won't reword your intent." No model had
 * run. The surface was claiming a comprehension that never happened, and showing her two
 * constants as the dates it had understood.
 *
 * `POST /api/focus/author` is what actually structures her words. It is asynchronous: the POST
 * answers 202, the work happens on a thread, and the client polls `/api/focus/status` then reads
 * `/api/focus/result`.
 *
 * Assertions are POSITIVE — they name the fields that must come from the SERVER's answer.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';

/** What the structure step really produces — the server's flat, snake_case field dict. */
const STRUCTURED = {
  name: 'Job search, caregiving from Saturday',
  start_date: '2026-08-03',
  end_date: '2026-08-09',
  intent: 'jobs first this week, caregiving from Saturday, Sunday off',
  foreground_projects: ['Job search'],
  days_off: ['2026-08-09'],
  output_format: 'Priority list',
  workday_start: '09:00',
};

function hydrate(opts: { status?: unknown; result?: unknown } = {}) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { empty: true } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/focus/status') {
      return { ok: true, data: opts.status ?? { state: 'idle', result_ready: true } };
    }
    if (path === '/api/focus/result') {
      return { ok: true, data: opts.result ?? { raw_text: 'x', fields: STRUCTURED } };
    }
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  send.mockReset();
  get.mockReset();
});

afterEach(cleanup);

async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  return h;
}

const WORDS = 'jobs first this week, caregiving from Saturday, Sunday off';

describe('structuring her words goes to the model, not to a stand-in', () => {
  it('posts her words to /api/focus/author', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    await act(async () => {
      await result.current.authorFocus(WORDS);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/focus/author', { text: WORDS });
  });

  /**
   * THE FABRICATION TEST. The dates on the returned form must be the ones the server sent.
   * `formFromDraft`'s constants were '2026-07-21'/'2026-07-27'; these are neither, so a form
   * still built by a client-side stand-in fails here.
   */
  it('returns the dates the model produced, not client-side constants', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    let form: unknown;
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect((form as { start: string }).start).toBe('2026-08-03');
    expect((form as { end: string }).end).toBe('2026-08-09');
  });

  it('carries every structured field the model produced onto the form she checks', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    let form: any;
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect(form.name).toBe('Job search, caregiving from Saturday');
    expect(form.front).toEqual(['Job search']);
    expect(form.daysOff).toEqual(['2026-08-09']);
    expect(form.output).toBe('Priority list');
    expect(form.workdayStart).toBe('09:00');
  });

  /** Spec §14/§17: intent is her own words and is never reworded. */
  it('carries her intent through unchanged', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    let form: any;
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect(form.intent).toBe(WORDS);
  });

  it('reads the structured answer from /api/focus/result', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    await act(async () => {
      await result.current.authorFocus(WORDS);
    });

    expect(get).toHaveBeenCalledWith('/api/focus/result');
  });
});

describe('when the structure step cannot run', () => {
  /**
   * The single generation lock is shared with plan generation. `started:false` arrives on a 202
   * — an ordinary outcome, said plainly, and NOT a form built anyway from a stand-in.
   */
  it('returns no form when the server was busy, and says so without claiming breakage', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: false } });
    const { result } = await mount();

    let form: unknown = 'untouched';
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect(form).toBeNull();
    expect(result.current.toast?.kind).toBe('notice');
  });

  it('reports a failed structure step as a failure, and returns no form', async () => {
    hydrate({ status: { state: 'error', error: 'the model did not answer' } });
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    let form: unknown = 'untouched';
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect(form).toBeNull();
    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('the model did not answer');
  });

  /**
   * An empty result is not a form full of blanks presented as "what I heard" — that is the same
   * fabrication in a quieter form. Nothing is returned and she is told.
   */
  it('returns no form when the result came back empty', async () => {
    hydrate({ result: { empty: true } });
    send.mockResolvedValue({ ok: true, data: { state: 'running', started: true } });
    const { result } = await mount();

    let form: unknown = 'untouched';
    await act(async () => {
      form = await result.current.authorFocus(WORDS);
    });

    expect(form).toBeNull();
  });
});
