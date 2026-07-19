import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * "SAVED" MUST FOLLOW THE WRITE, AND A PENDING WRITE MUST NOT BE DROPPED.
 *
 * Two defects, one mechanism, both about the object editor's title field.
 *
 * 1. `Detail.tsx`'s title textarea said `onBlur={() => flash('Saved')}`. The title write is on a
 *    600ms debounce, so the claim could precede the REQUEST entirely — not merely the response.
 *    `DetailCtx.flash`'s own doc-comment asserted the opposite ("there is nothing left to write
 *    — the flash is the only effect"), which is how it survived.
 *
 * 2. The unmount cleanup called `clearTimeout(t)` on every pending title timer WITHOUT firing
 *    it. Closing the app within 600ms of the last keystroke silently discarded a write she had
 *    already been told had saved.
 *
 * The fix is one seam: `finishedEditing(id)` flushes any pending debounce for that object NOW,
 * waits for the write, and raises "Saved" only if the server confirmed it. Unmount fires the
 * same pending writes instead of discarding them.
 *
 * ⚠ WHY THE CONFIRMATION IS NOT SIMPLY RAISED BY EVERY SUCCESSFUL WRITE. `succeed` sets a
 * TOAST, and `patchVals` (the note fields) fires per keystroke — so confirming on each write
 * would flicker "Saved" on every character she typed. Blur is the right moment to speak; the
 * bug was that blur was not waiting for anything.
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
import { setTitle, setVal } from '../../model/index.ts';

const ID = 'bafytask';

const TREE = {
  nodes: [
    {
      id: ID,
      title: 'Cancel food stamps',
      level: 'task',
      vals: { done: false, description: '' },
      children: [],
    },
  ],
  strategies: [],
  orphans: {},
};

function hydrate() {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { empty: true } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings')
      return { ok: true, data: { backend: 'mistral', options: [], include_hobby_block: false } };
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  send.mockReset();
  get.mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(h.result.current.idx.byId.get(ID)).toBeTruthy());
  return h;
}

/** The server's answer to a title PATCH — the read-back `api_write` performs. */
function saved(title: string) {
  return {
    ok: true,
    data: { object: { id: ID, title, level: 'task', vals: { done: false }, children: [] } },
  };
}

describe('the title says "Saved" only once the server has it', () => {
  it('raises nothing at all while the debounce is still holding the write', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel the food stamps'));
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });

    // The write has NOT gone out yet — this is the 600ms window the old `flash('Saved')` lied in.
    expect(send).not.toHaveBeenCalled();
    expect(result.current.toast).toBeNull();
  });

  it('flushes the debounce on blur, so the write goes out immediately', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel the food stamps'));
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });
    await act(async () => {
      await result.current.finishedEditing(ID);
    });

    expect(send).toHaveBeenCalledWith('PATCH', `/api/object/${ID}`, {
      title: 'Cancel the food stamps',
    });
  });

  it('says "Saved" after the server confirms, not before', async () => {
    hydrate();
    let settle: (v: unknown) => void = () => {};
    send.mockReturnValue(
      new Promise((resolve) => {
        settle = resolve;
      }),
    );
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });

    let blurred: Promise<void> = Promise.resolve();
    await act(async () => {
      blurred = result.current.finishedEditing(ID);
    });

    // In flight: the request is out, and nothing has been claimed about it.
    expect(send).toHaveBeenCalledTimes(1);
    expect(result.current.toast).toBeNull();

    await act(async () => {
      settle(saved('Cancel the food stamps'));
      await blurred;
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Saved');
  });

  it('does NOT say "Saved" when the write failed', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'could not reach the server' });
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });
    await act(async () => {
      await result.current.finishedEditing(ID);
    });

    // The rollback's own report is what she gets, and it is the ONLY thing she gets.
    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    // ⚠ `seq` counts every toast ever raised. Asserting only the FINAL toast is not enough: a
    // "Saved" raised before the failure lands would be overwritten by it and leave this passing,
    // which is exactly what happened under mutation. Two messages about one event, the second
    // contradicting the first, is its own defect.
    expect(result.current.toast?.seq).toBe(1);
  });

  it('claims nothing when she leaves a field she never edited', async () => {
    hydrate();
    const { result } = await mount();

    await act(async () => {
      await result.current.finishedEditing(ID);
    });

    // Tabbing through an untouched field used to raise "Saved" for a write that never existed.
    expect(send).not.toHaveBeenCalled();
    expect(result.current.toast).toBeNull();
  });

  it('claims nothing on a second blur with no edit in between', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel the food stamps'));
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });
    await act(async () => {
      await result.current.finishedEditing(ID);
    });
    act(() => {
      result.current.dismissToast();
    });
    await act(async () => {
      await result.current.finishedEditing(ID);
    });

    // The write was consumed by the first blur. A second "Saved" would be describing nothing.
    expect(result.current.toast).toBeNull();
  });

  /**
   * ⚠ READ THIS BEFORE TRUSTING THIS TEST. `setVal` (`model/mutations.ts:44`) already returns
   * `toast: 'Saved'`, which `apply` raises OPTIMISTICALLY on every keystroke — so a note field
   * already shows a confirmation before its write lands. That is the SAME defect class, at a
   * third site, and it is NOT fixed here (see the report: a chip tap also goes through `setVal`
   * and has no blur to hang a confirmation on, so removing that toast would leave chips with no
   * feedback at all — an app-wide decision, not this task's).
   *
   * So asserting "the toast says Saved" would pass against the optimistic one and prove nothing.
   * What is asserted instead is that blur raises its OWN confirmation once the server answers —
   * `seq` counts toasts, so a second one means `finishedEditing` spoke for the confirmed write.
   */
  it('confirms a NOTE field the same way — those write per keystroke, with no debounce', async () => {
    hydrate();
    let settle: (v: unknown) => void = () => {};
    send.mockReturnValue(
      new Promise((resolve) => {
        settle = resolve;
      }),
    );
    const { result } = await mount();

    act(() => {
      result.current.apply(setVal(result.current.graph, ID, 'description', 'call them'));
    });
    expect(send).toHaveBeenCalledWith('PATCH', `/api/object/${ID}`, {
      vals: { description: 'call them' },
    });
    const optimistic = result.current.toast?.seq;

    let blurred: Promise<void> = Promise.resolve();
    await act(async () => {
      blurred = result.current.finishedEditing(ID);
    });
    // Still in flight: blur has NOT spoken yet.
    expect(result.current.toast?.seq).toBe(optimistic);

    await act(async () => {
      settle({
        ok: true,
        data: {
          object: { id: ID, title: 'Cancel food stamps', level: 'task', vals: { description: 'call them' }, children: [] },
        },
      });
      await blurred;
    });

    // A NEW confirmation, raised after the server answered.
    expect(result.current.toast?.seq).toBe((optimistic ?? 0) + 1);
    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Saved');
  });
});

describe('a pending title write is not thrown away when the editor goes', () => {
  it('sends the pending write on unmount instead of cancelling it', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel the food stamps'));
    const { result, unmount } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });
    expect(send).not.toHaveBeenCalled();

    // She closes the app inside the 600ms window. The write she was going to be told about
    // must still leave — the old cleanup called `clearTimeout` and dropped it on the floor.
    await act(async () => {
      unmount();
    });

    expect(send).toHaveBeenCalledWith('PATCH', `/api/object/${ID}`, {
      title: 'Cancel the food stamps',
    });
  });

  it('still lets the debounce fire normally when she just keeps working', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel the food stamps'));
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel the food stamps'));
    });
    await act(async () => {
      vi.advanceTimersByTime(700);
    });

    // The debounce is not replaced by the flush — it is the ordinary path and still works.
    expect(send).toHaveBeenCalledWith('PATCH', `/api/object/${ID}`, {
      title: 'Cancel the food stamps',
    });
  });

  it('sends only the LAST title of a burst, once', async () => {
    hydrate();
    send.mockResolvedValue(saved('Cancel it'));
    const { result } = await mount();

    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'C'));
    });
    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Ca'));
    });
    act(() => {
      result.current.apply(setTitle(result.current.graph, ID, 'Cancel it'));
    });
    await act(async () => {
      await result.current.finishedEditing(ID);
    });

    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith('PATCH', `/api/object/${ID}`, { title: 'Cancel it' });
  });
});
