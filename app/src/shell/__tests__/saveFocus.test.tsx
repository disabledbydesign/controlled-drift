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
  // She asked for this as-needed task to come back on this period — the write must carry it.
  reactivate: ['Dishes'],
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
    // Not this test's concern (the honest-values thread added the read) — answered so it
    // doesn't raise a spurious failure toast that these tests' own assertions would trip over.
    if (path === '/api/actions') return { ok: true, data: { presets: [] } };
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
        reactivate_tasks: ['Dishes'],
      },
      // She never typed anything on THIS action — the form came from the fixture, not from the
      // author box — so there is no raw text to attribute to her. See the raw-text group below.
      raw_text: '',
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
    /**
     * AND IT STAYS UP UNTIL SHE DISMISSES IT. `hold` is what pins it, and this one has to be
     * pinned: nothing on screen changed when the server declined, so a sentence that faded would
     * leave her believing the period saved.
     *
     * Asserted here because the notice kind now has two presentations. Refusals fade after five
     * seconds — correctly, because the control they come from reverts to the stored value in the
     * same breath. This one has no such control behind it, so sharing their fade would be a
     * silent regression that nothing else in the suite could see.
     */
    expect(result.current.toast?.hold).toBe(true);
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

/**
 * FINDING 3 — what lands in `signal_log.jsonl` as June's own typed words.
 *
 * `raw_text` is not metadata. On both routes it is passed to
 * `signal_log.log_signal(raw_text, source="config_authoring" | "config_correction")`, and that
 * file is documented and read as HER OWN TYPED WORDS. A commit landing the same day
 * (`1522ad5`) removed a machine-written record from that same log for exactly this reason.
 *
 * The defect: `saveFocusPeriod` sent `form.intent` as `raw_text`. Open the per-field editor on an
 * existing period, change only the workday end time, save — and a correction signal is written
 * whose text is the period's PRE-EXISTING intent sentence, which she did not say, at that moment,
 * about that change. The words are attributed to her; she never typed them on this action.
 */
describe('only words she actually typed are recorded as her words', () => {
  it('sends no raw text when she edited fields directly and typed nothing', async () => {
    hydrate([SAVED_PERIOD]);
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('edit', 'fp-saved', { ...FORM, workdayEnd: '19:00' });
    });

    const call = send.mock.calls.find((c) => c[1] === '/api/focus/update');
    expect((call![2] as { raw_text: string }).raw_text).toBe('');
  });

  /**
   * The other half, and why this is not solved by sending '' everywhere: on the AUTHOR path she
   * really did type a sentence, into the "say it in your own words" box. That sentence is hers
   * and belongs in the log — dropping it would lose a real record.
   */
  it('sends the sentence she typed into the author box when committing that period', async () => {
    hydrate();
    send.mockImplementation(async (_m: string, path: string) => {
      if (path === '/api/focus/author') return { ok: true, data: { state: 'running', started: true } };
      return { ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } };
    });
    get.mockImplementation(async (path: string) => {
      if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
      if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
      if (path === '/api/plan') return { ok: true, data: { empty: true } };
      if (path === '/api/periods') return { ok: true, data: { periods: [] } };
      if (path === '/api/focus/status') return { ok: true, data: { state: 'done', result_ready: true } };
      if (path === '/api/focus/result') {
        return { ok: true, data: { raw_text: 'jobs first, dishes back on', fields: { name: 'Jobs week' } } };
      }
      return { ok: false, error: 'not part of this test' };
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.authorFocus('jobs first, dishes back on');
    });
    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    const call = send.mock.calls.find((c) => c[1] === '/api/focus/commit');
    expect((call![2] as { raw_text: string }).raw_text).toBe('jobs first, dishes back on');
  });

  /**
   * Her intent sentence must never be the thing attributed to her by default. This is the
   * regression itself, asserted on the value: the period's intent text does NOT become a
   * correction signal just because she touched an unrelated field.
   */
  it('does not attribute the period’s existing intent to her as something she just said', async () => {
    hydrate([SAVED_PERIOD]);
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('edit', 'fp-saved', FORM);
    });

    const call = send.mock.calls.find((c) => c[1] === '/api/focus/update');
    expect((call![2] as { raw_text: string }).raw_text).not.toBe(FORM.intent);
  });
});

/**
 * FINDING 2 at the shell — a period that saved while a task she asked for did not come back.
 *
 * The server goes out of its way not to drop this (`_reactivate_named_tasks`, `server.py:238`);
 * the surface must not drop it either. Both truths have to be in the one sentence she reads: the
 * period DID save, and the named task did NOT come back on.
 */
describe('a save that partly did not happen says both things', () => {
  it('names the task that did not come back, and still says the period saved', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, id: 'fp-saved', name: 'Jobs week', reactivate_unresolved: ['Dishes'] },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(result.current.toast?.msg).toContain('Dishes');
    expect(result.current.toast?.msg).toContain('saved');
  });

  /**
   * It travels the FAILURE channel, not the success one: `fail` is what reaches `errorLog`, and
   * a task that silently stayed off is exactly the kind of thing that has to leave a trace. It
   * is also the register June needs — a quiet success signal would let her walk away believing
   * the whole instruction landed.
   */
  it('reports the partial failure loudly enough to reach the error log', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, id: 'fp-saved', name: 'Jobs week', reactivate_unresolved: ['Dishes'] },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(result.current.toast?.kind).toBe('failure');
  });

  /**
   * ⚠ It still LANDED. The period is written and proved; returning false would close nothing and
   * leave her editor open over a period that is already saved, inviting a duplicate write.
   */
  it('still reports the period as landed, because the period itself was written', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, id: 'fp-saved', name: 'Jobs week', reactivate_unresolved: ['Dishes'] },
    });
    const { result } = await mount();

    let landed: boolean | undefined;
    await act(async () => {
      landed = await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(landed).toBe(true);
  });

  it('says a task did not come back when the reactivation itself failed', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: {
        ok: true,
        id: 'fp-saved',
        name: 'Jobs week',
        reactivate_failed: [{ id: 'task-9', error: 'connection refused' }],
      },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('connection refused');
  });

  /** A clean save must stay a plain quiet success — the caveat wording appears only when earned. */
  it('keeps a clean save a quiet success with no caveat attached', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-saved', name: 'Jobs week' } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, FORM);
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Focus period saved');
  });
});

/** MINOR 6 — a step that cannot be carried out must say so, not quietly do something else. */
describe('an edit with no period id refuses rather than creating a second period', () => {
  it('reports a failure and issues no write at all', async () => {
    hydrate([SAVED_PERIOD]);
    send.mockResolvedValue({ ok: true, data: { ok: true, id: 'fp-new', name: 'Jobs week' } });
    const { result } = await mount();

    let landed: boolean | undefined;
    await act(async () => {
      landed = await result.current.saveFocusPeriod('edit', null, FORM);
    });

    expect(landed).toBe(false);
    expect(result.current.toast?.kind).toBe('failure');
    expect(send.mock.calls.map((c) => c[1])).toEqual([]);
  });
});

/** MINOR 9 — the sentence she reads at the moment a save is refused must be grammatical. */
describe('the missing-field sentence reads as a person telling her what is left', () => {
  it('puts an article in front of the field it names', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { blocked: ['end date'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, { ...FORM, end: '' });
    });

    expect(result.current.toast?.msg).toContain('needs an end date');
  });

  it('reads grammatically when it names both fields', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { blocked: ['start date', 'end date'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.saveFocusPeriod('author', null, { ...FORM, start: '', end: '' });
    });

    expect(result.current.toast?.msg).toContain('needs a start date and an end date');
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
