/**
 * A REFUSAL COMING BACK FROM THE MODEL LAYER IS NOT A RECEIPT.
 *
 * `apply()` raised every `toast` a mutation returned as a SUCCESS. Most of them are receipts
 * ('Saved', 'Moved · synced') and that is right — the control has already re-rendered with the
 * new value, so `present()` keeps them quiet on purpose.
 *
 * One of them is not a receipt. `setType`'s leaf guard returns
 * 'Can’t convert — has sub-items, move them first' with the graph UNCHANGED and `node: null`.
 * Raised as a success that is presented `inline`, and with no node to settle on, it rendered
 * NOWHERE: she pressed a type button, nothing happened, and nothing said why.
 *
 * These assert POSITIVELY on the kind of signal that reaches `toast` — the thing `present()`
 * and `SignalBar` then dispatch on — rather than on some wrong thing not happening.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';

vi.mock('../../api/client.ts', () => ({
  apiGet: async () => ({ ok: false, error: 'not part of this test' }),
  apiSend: async () => ({ ok: false, error: 'not part of this test' }),
}));

import { useAppState } from '../useAppState.ts';
import type { MutationResult } from '../../model/index.ts';

afterEach(cleanup);

describe('apply — a refused mutation is said out loud, not filed as a success', () => {
  it('raises a refusal as a notice, which is the kind that reaches the bar', async () => {
    const { result } = renderHook(() => useAppState('fixtures'));
    const refused: MutationResult = {
      graph: result.current.graph,
      toast: 'Can’t convert — has sub-items, move them first',
      refusal: true,
      ui: null,
      node: null,
    };

    await act(async () => {
      result.current.apply(refused);
    });

    expect(result.current.toast?.kind).toBe('notice');
    expect(result.current.toast?.msg).toBe('Can’t convert — has sub-items, move them first');
  });

  /**
   * And it FADES — `hold` is what would pin it up, and a refusal must not be pinned: the type
   * badge still shows the type the object really has, so the screen is truthful on its own.
   */
  it('does not pin the refusal to the screen', async () => {
    const { result } = renderHook(() => useAppState('fixtures'));

    await act(async () => {
      result.current.apply({
        graph: result.current.graph,
        toast: 'Can’t convert — has sub-items, move them first',
        refusal: true,
        ui: null,
        node: null,
      });
    });

    expect(result.current.toast?.hold).toBeFalsy();
  });

  /**
   * The other side of the distinction, so the flag has to actually distinguish. An ordinary
   * receipt stays a success and therefore stays quiet — June asked for that and it is preserved.
   */
  it('still raises an ordinary receipt as a quiet success', async () => {
    const { result } = renderHook(() => useAppState('fixtures'));

    await act(async () => {
      result.current.apply({
        graph: result.current.graph,
        toast: 'Saved',
        ui: null,
        node: null,
      });
    });

    expect(result.current.toast?.kind).toBe('success');
  });
});
