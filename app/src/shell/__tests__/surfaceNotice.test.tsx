/**
 * THE WIRING BETWEEN THE ROW AND THE SIGNAL SEAM.
 *
 * Every refusal in the Today tab is raised by a component calling `ctx.notice(...)`. The
 * component tests use a spy for that, which proves the component CALLS it and proves nothing
 * about where the call goes — and "built but unreachable" is this repo's most expensive
 * recurring defect. A `notice` wired back to `flash` would pass every component test in the
 * suite while rendering nothing at all on screen, which is precisely the bug being fixed.
 *
 * So this drives the real `useSurface` and asserts on the signal that actually reaches `toast`,
 * because that is the object `present()` and `SignalBar` dispatch on.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { themes } from '@tokens';

vi.mock('../../api/client.ts', () => ({
  apiGet: async () => ({ ok: false, error: 'not part of this test' }),
  apiSend: async () => ({ ok: false, error: 'not part of this test' }),
}));

import { useSurface } from '../useSurface.ts';
import { present } from '../signals.ts';

afterEach(cleanup);

function mount() {
  return renderHook(() =>
    useSurface({ T: themes.celestial, name: 'celestial', setTheme: vi.fn(), wide: false, source: 'fixtures' }),
  );
}

describe('useSurface — a row’s refusal reaches the seam that can show it', () => {
  it('raises what a row refuses as a notice, carrying the row it is about', async () => {
    const { result } = mount();

    await act(async () => {
      result.current.todayCtx.notice('There is nowhere else to put this today.', 'l3pdzq');
    });

    expect(result.current.st.toast?.kind).toBe('notice');
    expect(result.current.st.toast?.msg).toBe('There is nowhere else to put this today.');
    expect(result.current.st.toast?.nodeId).toBe('l3pdzq');
  });

  /**
   * And the seam presents it where she can read it. Asserted end to end rather than on
   * `present()` alone: the failure being guarded against is a correct `present()` reached by a
   * signal of the wrong kind, which no unit test of either half can see.
   */
  it('presents that refusal in the bar, and lets it fade on its own', async () => {
    const { result } = mount();

    await act(async () => {
      result.current.todayCtx.notice('That needs to be a number of minutes above zero.', 't1');
    });

    const p = present(result.current.st.toast!);
    expect(p.mode).toBe('bar');
    expect(p.persist).toBe(false);
    expect(p.ms).toBeGreaterThanOrEqual(4000);
  });

  /**
   * An instruction with no object behind it takes the same route — `nodeId` is genuinely absent
   * rather than a made-up id. `Object.keys` because `toHaveBeenCalledWith`-style deep equality
   * treats an explicit `undefined` as an absent key, and here the difference matters: `nodeId`
   * must be present and null, which is what the `Signal` shape promises every consumer.
   */
  it('carries an instruction with no row behind it, without inventing one', async () => {
    const { result } = mount();

    await act(async () => {
      result.current.todayCtx.notice('Pick an item to move');
    });

    expect(result.current.st.toast?.msg).toBe('Pick an item to move');
    expect(result.current.st.toast?.nodeId).toBe(null);
    expect(Object.keys(result.current.st.toast!)).toContain('nodeId');
  });

  /**
   * The receipt side, unchanged and asserted so it stays that way: June asked for successes to
   * stay quiet, and `flash` must keep raising a success. This fix makes refusals loud; it must
   * not make the app noisy.
   */
  it('leaves an ordinary flash a quiet success', async () => {
    const { result } = mount();

    await act(async () => {
      result.current.todayCtx.flash('Saved');
    });

    expect(result.current.st.toast?.kind).toBe('success');
    expect(present(result.current.st.toast!).mode).not.toBe('bar');
  });
});
