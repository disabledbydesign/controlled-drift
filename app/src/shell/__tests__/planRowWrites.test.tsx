import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * THE THREE PER-ROW PLAN WRITES, AT THE SEAM WHERE THEY WERE UNTESTED.
 *
 * Review finding B3: `RowActions`'s own tests stop at a mocked `ctx`, and `planRow`'s stop at
 * `fetch`. Ninety lines sat between the two — the guards, the toast wording, the
 * `setPlan(planFromLive(...))` that is the ONLY reason anything moves on screen, and the
 * panel-close-on-success. Deleting `setPlan(planFromLive(res.plan))` from `moveRow` broke no
 * test at all: the write succeeded, the toast said "Moved", and the row did not move.
 *
 * So these tests assert what the SURFACE ends up holding, not merely what was sent. Each one is
 * positive: it names the plan the hook must be showing, the ui state it must have returned to,
 * or the words she must have been given.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

/** The durable failure log, so a partial success can be asserted to have left a record (B4). */
const logged = vi.fn();
vi.mock('../errorLog.ts', () => ({
  logFailure: (...a: unknown[]) => logged(...a),
}));

import { useAppState } from '../useAppState.ts';

const TASK_ID = 'bafytask';
const OTHER_ID = 'bafyother';

const TREE = { nodes: [], strategies: [], orphans: {} };

/** A priority-shaped plan, in the shape `/api/plan` really answers. `order` picks the order. */
function livePlan(order: string[] = [TASK_ID, OTHER_ID]) {
  return {
    shape: 'priority',
    header: '',
    woven_frame: 'Today.',
    generated_at: '2026-07-18T09:00:00',
    items: order.map((id) => ({
      id,
      task: id === TASK_ID ? 'Call the clinic' : 'Email Sam',
      time: '',
      duration_min: 30,
    })),
  };
}

function hydrate(plan: unknown = livePlan()) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: plan };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings')
      return { ok: true, data: { backend: 'mistral', options: [], include_hobby_block: false } };
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  send.mockReset();
  get.mockReset();
  logged.mockReset();
});

afterEach(cleanup);

async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  return h;
}

/** The ids of the rendered plan, in order — what she is actually looking at. */
function shownOrder(plan: { blocks: { items: { id?: string }[] }[] }): (string | undefined)[] {
  return plan.blocks.flatMap((b) => b.items.map((it) => it.id));
}

describe('moving a row — the screen must follow the write', () => {
  it('renders the REORDERED plan the server sent back, not the one it had before', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, plan: livePlan([OTHER_ID, TASK_ID]) } });
    const { result } = await mount();
    // Positively: before the move, she is looking at the original order.
    await waitFor(() => expect(shownOrder(result.current.plan)).toEqual([TASK_ID, OTHER_ID]));

    await act(async () => {
      await result.current.moveRow(TASK_ID, { block: null, position: 1 });
    });

    expect(shownOrder(result.current.plan)).toEqual([OTHER_ID, TASK_ID]);
    expect(result.current.toast?.msg).toBe('Moved');
  });

  it('closes the panel and the placement mode once the move has landed', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, plan: livePlan([OTHER_ID, TASK_ID]) } });
    const { result } = await mount();
    act(() => {
      result.current.up({ editOpen: { [TASK_ID]: true }, movePick: TASK_ID });
    });
    expect(result.current.ui.editOpen[TASK_ID]).toBe(true);

    await act(async () => {
      await result.current.moveRow(TASK_ID, { block: null, position: 1 });
    });

    expect(result.current.ui.editOpen[TASK_ID]).toBeUndefined();
    expect(result.current.ui.movePick).toBeNull();
  });

  it('leaves the panel open and says the row did not move when the server refuses', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: "no scheduled item with id 'bafytask' to move." });
    const { result } = await mount();
    act(() => {
      result.current.up({ editOpen: { [TASK_ID]: true }, movePick: TASK_ID });
    });

    await act(async () => {
      await result.current.moveRow(TASK_ID, { block: null, position: 1 });
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('That did not move');
    // Still open, because she may well want to try a different spot.
    expect(result.current.ui.editOpen[TASK_ID]).toBe(true);
    // And the plan on screen is untouched.
    expect(shownOrder(result.current.plan)).toEqual([TASK_ID, OTHER_ID]);
  });
});

describe('taking a row off today', () => {
  it('renders the plan without the row and says so', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, plan: livePlan([OTHER_ID]) } });
    const { result } = await mount();

    await act(async () => {
      await result.current.notTodayRow(TASK_ID, 'task');
    });

    expect(shownOrder(result.current.plan)).toEqual([OTHER_ID]);
    expect(result.current.toast?.msg).toBe('Taken off today');
  });

  /**
   * B4. `setToast` is a single slot, so raising the outcome and then raising the caveat meant she
   * only ever saw the caveat — the exact inversion the code's own comment forbids ("say the true
   * thing first, then the caveat — never let the caveat stand in for the outcome"). ONE signal
   * now carries both, outcome first.
   */
  it('leads with the removal that happened, and still carries the caveat', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, plan: livePlan([OTHER_ID]), warning: 'The learning note was not written.' },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.notTodayRow(TASK_ID, 'task');
    });

    const msg = result.current.toast?.msg ?? '';
    expect(msg.startsWith('Taken off today')).toBe(true);
    expect(msg).toContain('The learning note was not written.');
  });

  /**
   * B4's second question, answered rather than assumed: the caveat still reaches the durable log.
   * The visible slot is a single slot and the outcome has to own it, but a half-completed write
   * that only ever existed in a toast she dismissed is not diagnosable afterwards — which is the
   * whole reason `errorLog` exists.
   */
  it('records the partial failure in the durable log even though the toast reads as a success', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, plan: livePlan([OTHER_ID]), warning: 'The learning note was not written.' },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.notTodayRow(TASK_ID, 'task');
    });

    expect(logged).toHaveBeenCalled();
    const [loggedMsg] = logged.mock.calls.at(-1)!;
    expect(String(loggedMsg)).toContain('The learning note was not written.');
  });

  it('says the row is still on today’s list when the removal fails', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'the server said no.' });
    const { result } = await mount();

    await act(async () => {
      await result.current.notTodayRow(TASK_ID, 'task');
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain("still on today's list");
    expect(shownOrder(result.current.plan)).toEqual([TASK_ID, OTHER_ID]);
  });
});

describe('setting a row’s length', () => {
  it('reports the minutes the SERVER confirmed, not the ones that were asked for', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { ok: true, duration_min: 45, plan: livePlan() },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.setRowDuration(TASK_ID, 40);
    });

    expect(result.current.toast?.msg).toBe('Set to 45 minutes');
  });

  it('closes the panel once the length has landed', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { ok: true, duration_min: 20, plan: livePlan() } });
    const { result } = await mount();
    act(() => {
      result.current.up({ editOpen: { [TASK_ID]: true } });
    });

    await act(async () => {
      await result.current.setRowDuration(TASK_ID, 20);
    });

    expect(result.current.ui.editOpen[TASK_ID]).toBeUndefined();
  });

  it('says the length was not saved when the server refuses, and keeps the panel open', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'minutes must be a positive integer.' });
    const { result } = await mount();
    act(() => {
      result.current.up({ editOpen: { [TASK_ID]: true } });
    });

    await act(async () => {
      await result.current.setRowDuration(TASK_ID, -1);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(result.current.ui.editOpen[TASK_ID]).toBe(true);
  });
});

describe('the guards in front of all three', () => {
  it('refuses a row with no id and names what was not saved', async () => {
    hydrate();
    const { result } = await mount();

    await act(async () => {
      await result.current.notTodayRow('', 'task');
    });

    expect(send).not.toHaveBeenCalled();
    // Positively: she is TOLD, rather than the tap doing nothing at all.
    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('no id on it');
  });
});
