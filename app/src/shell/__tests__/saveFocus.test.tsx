import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT SAVING A FOCUS PERIOD MUST ACTUALLY DO.
 *
 * `saveFocus` was a pure local state change. Every field June edited — name, dates, intent,
 * availability window, note, plan shape, workday hours, days off, foreground and paused projects
 * — was gone on reload, under a toast reading "Focus period updated". Two live endpoints already
 * did this correctly and nothing called them: `POST /api/focus/commit` (new) and
 * `POST /api/focus/update` (edit in place).
 *
 * Four things every test below holds:
 *
 * 1. **The request goes out, carrying the fields under the SERVER's key names.** A key the
 *    server does not recognise is not an error — it is a field that quietly does not save.
 * 2. **The success signal comes only after the server confirms.** Both routes re-fetch and
 *    prove the write before answering, so their `ok` is worth something. `logDay` is the model.
 * 3. **A REFUSAL IS NOT A FAILURE, AND NEITHER IS IT A SUCCESS.** Both routes answer a declined
 *    write with HTTP 200 `{"blocked":[...]}`. It must name the missing field, in her register,
 *    without claiming a save and without claiming breakage.
 * 4. **The saved period is re-read from the server**, so the list shows what persisted rather
 *    than what the client hoped it sent.
 *
 * Assertions are POSITIVE — they name the request that must go out and the value that must be
 * true afterwards. "A wrong write did not happen" also passes against a control wired to
 * nothing at all.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';
import type { FocusForm } from '../../model/index.ts';

const FORM: FocusForm = {
  name: 'Jobs week',
  start: '2026-07-20',
  end: '2026-07-26',
  intent: 'jobs first this week, caregiving Saturday',
  front: ['Job search'],
  note: 'free after 3',
  availStart: '2026-07-21',
  availEnd: '2026-07-24',
  daysOff: ['2026-07-25'],
  daysOn: 'Mon, Tue',
  output: 'Priority list',
  workdayStart: '09:00',
  workdayEnd: '17:00',
  paused: ['Reading group'],
};

/** A period as `GET /api/periods` really sends it. */
const SAVED_PERIOD = {
  id: 'fp-saved',
  name: 'Jobs week',
  start_date: '2026-07-20',
  end_date: '2026-07-26',
  intent: 'jobs first this week, caregiving Saturday',
  foreground_projects: ['Job search'],
  paused_projects: ['Reading group'],
  days_off: ['2026-07-25'],
  days_on: ['Mon', 'Tue'],
  output_format: 'Priority list',
  workday_start: '09:00',
  workday_end: '17:00',
  availability_start: '2026-07-21',
  availability_end: '2026-07-24',
  availability_note: 'free after 3',
};

function hydrate(periods: unknown[] = []) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { empty: true } };
    if (path === '/api/periods') return { ok: true, data: { periods } };
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

describe('saving a NEW focus period writes it to the server', () => {
  it('issues POST /api/focus/commit carrying every field under the server’s key names', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/focus/commit', {
      fields: {
        name: 'Jobs week',
        start_date: '2026-07-20',
        end_date: '2026-07-26',
        intent: 'jobs first this week, caregiving Saturday',
        foreground_projects: ['Job search'],
        availability_note: 'free after 3',
        availability_start: '2026-07-21',
        availability_end: '2026-07-24',
        days_off: ['2026-07-25'],
        days_on: ['Mon', 'Tue'],
        output_format: 'Priority list',
        workday_start: '09:00',
        workday_end: '17:00',
        paused_projects: ['Reading group'],
      },
      raw_text: 'jobs first this week, caregiving Saturday',
    });
  });

  it('reports the save as landed', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    let landed: boolean | undefined;
    await act(async () => {
      landed = await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(landed).toBe(true);
    expect(result.current.toast?.kind).toBe('success');
  });

  /**
   * The period the Focus tab lists must come from the server, not from the form. This is the
   * read-back rule: what she sees is what persisted.
   */
  it('re-reads the periods so the list shows what actually persisted', async () => {
    hydrate();
    let periodsRead = 0;
    get.mockImplementation(async (path: string) => {
      if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
      if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
      if (path === '/api/plan') return { ok: true, data: { empty: true } };
      if (path === '/api/periods') {
        periodsRead += 1;
        return { ok: true, data: { periods: periodsRead > 1 ? [SAVED_PERIOD] : [] } };
      }
      return { ok: false, error: 'not part of this test' };
    });
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(result.current.periods.map((p) => p.id)).toContain('fp-saved');
    expect(result.current.periods.find((p) => p.id === 'fp-saved')!.name).toBe('Jobs week');
  });
});

describe('editing an existing period updates it in place', () => {
  it('issues POST /api/focus/update carrying the period id', async () => {
    hydrate([SAVED_PERIOD]);
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('edit', 'fp-saved', FORM);
    });

    const call = send.mock.calls.find((c) => c[1] === '/api/focus/update');
    expect(call).toBeTruthy();
    expect((call![2] as { id: string }).id).toBe('fp-saved');
  });

  it('does not create a second period when she is editing one', async () => {
    hydrate([SAVED_PERIOD]);
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('edit', 'fp-saved', FORM);
    });

    // Positive form: the ONE route that ran is the in-place update.
    expect(send.mock.calls.map((c) => c[1])).toEqual(['/api/focus/update']);
  });
});

describe('a refused write names the field and does not claim a save', () => {
  /**
   * THE CASE THIS TASK EXISTS FOR. `{"blocked":["end date"]}` arrives on a 200. Before this
   * wire-in it would have raised "Focus period saved" over a period the server declined.
   */
  it('tells her which field to fill in, as a notice rather than a breakage', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { blocked: ['end date'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, { ...FORM, end: '' });
    });

    expect(result.current.toast?.kind).toBe('notice');
    expect(result.current.toast?.msg).toContain('end date');
  });

  it('reports a refused save as NOT landed, so the editor stays open on her work', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { blocked: ['end date'] } });
    const { result } = await mount();

    let landed: boolean | undefined;
    await act(async () => {
      landed = await result.current.saveFocusPeriod('author', null, { ...FORM, end: '' });
    });

    expect(landed).toBe(false);
  });

  it('names both fields when both are empty', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { blocked: ['start date', 'end date'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, { ...FORM, start: '', end: '' });
    });

    expect(result.current.toast?.msg).toContain('start date');
    expect(result.current.toast?.msg).toContain('end date');
  });
});

describe('a real failure is reported as a failure', () => {
  it('says the period was not saved and carries the server’s sentence', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'period did not persist correctly on read-back' });
    const { result } = await mount();

    let landed: boolean | undefined;
    await act(async () => {
      landed = await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(landed).toBe(false);
    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('period did not persist correctly on read-back');
  });

  /** The three outcomes stay three. A breakage must not arrive wearing the notice's clothes. */
  it('keeps a failure distinct from a refusal', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'boom' });
    const { result } = await mount();
    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });
    expect(result.current.toast?.kind).toBe('failure');
  });
});
