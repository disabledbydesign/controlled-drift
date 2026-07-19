import { afterEach, describe, expect, it, vi } from 'vitest';
import { isNative, nativeWidthFor, NATIVE_HEIGHT } from './native.ts';

const setSearch = (search: string) => {
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search },
    writable: true,
    configurable: true,
  });
};

/**
 * The per-tab widths are the load-bearing port from v4 `deskApp()` (mockup line 733). If these
 * numbers drift, the desktop window resizes to the wrong size on tab change — pin them.
 */
describe('nativeWidthFor — v4:733 per-tab window width', () => {
  it('narrow tabs are 392 with no editor open', () => {
    expect(nativeWidthFor('today', false)).toBe(392);
    expect(nativeWidthFor('add', false)).toBe(392);
    expect(nativeWidthFor('settings', false)).toBe(392);
  });

  it('an open detail widens Today/Add to 872 — but NOT settings', () => {
    expect(nativeWidthFor('today', true)).toBe(872);
    expect(nativeWidthFor('add', true)).toBe(872);
    // settings never docks an editor pane, so a stray detail flag must not widen it
    expect(nativeWidthFor('settings', true)).toBe(392);
  });

  it('map is the 1024 Finder-width; routines/strategies are 832 (DETAIL+COL+12)', () => {
    expect(nativeWidthFor('map', false)).toBe(1024);
    expect(nativeWidthFor('routines', false)).toBe(832);
    expect(nativeWidthFor('strategies', false)).toBe(832);
    // the wide tabs don't grow for a detail — the pane is already in their layout
    expect(nativeWidthFor('map', true)).toBe(1024);
    expect(nativeWidthFor('routines', true)).toBe(832);
  });

  it('height is fixed across tabs', () => {
    expect(NATIVE_HEIGHT).toBe(860);
  });
});

describe('isNative — only true under ?native=1', () => {
  const original = window.location.search;
  afterEach(() => {
    // restore whatever the harness set, so one test can't leak native-mode into the next
    Object.defineProperty(window, 'location', {
      value: { ...window.location, search: original },
      writable: true,
      configurable: true,
    });
  });

  it('is false in a plain browser (no query)', () => {
    setSearch('');
    expect(isNative()).toBe(false);
  });

  it('is true with ?native=1', () => {
    setSearch('?native=1');
    expect(isNative()).toBe(true);
  });

  it('is true with ?native present among other params', () => {
    setSearch('?foo=bar&native=1');
    expect(isNative()).toBe(true);
  });
});

describe('nativeResize — the pywebview bridge', () => {
  afterEach(() => {
    delete (window as unknown as { pywebview?: unknown }).pywebview;
    setSearch('');
  });

  /**
   * The module seeds `ready` and registers its `pywebviewready` listener at import time, so each
   * case must import FRESH after stubbing the globals. `addEventListener` is mocked across the
   * import so the listener is captured here rather than left attached to `window` — otherwise
   * listeners from earlier imports leak and fire on a later dispatch. `fireReady` invokes only
   * THIS import's handler.
   */
  const load = async () => {
    vi.resetModules();
    const handlers: Array<(e: Event) => void> = [];
    const spy = vi
      .spyOn(window, 'addEventListener')
      .mockImplementation((type, h) => {
        if (type === 'pywebviewready') handlers.push(h as (e: Event) => void);
      });
    const mod = await import('./native.ts');
    spy.mockRestore();
    return {
      nativeResize: mod.nativeResize,
      fireReady: () => handlers.forEach((h) => h(new Event('pywebviewready'))),
    };
  };

  it('drives the bridge with the tab width + fixed height when native + injected', async () => {
    const resize = vi.fn();
    setSearch('?native=1');
    (window as unknown as { pywebview: unknown }).pywebview = { api: { resize } };
    const { nativeResize } = await load();

    nativeResize('map', false);
    expect(resize).toHaveBeenCalledWith(1024, 860);
    nativeResize('today', false);
    expect(resize).toHaveBeenLastCalledWith(392, 860);
    nativeResize('today', true); // an open editor widens Today
    expect(resize).toHaveBeenLastCalledWith(872, 860);
  });

  it('is a no-op in a plain browser even if a bridge somehow exists', async () => {
    const resize = vi.fn();
    setSearch(''); // no ?native=1
    (window as unknown as { pywebview: unknown }).pywebview = { api: { resize } };
    const { nativeResize } = await load();

    nativeResize('map', false);
    expect(resize).not.toHaveBeenCalled();
  });

  it('holds the latest size until the bridge is injected, then replays only that one', async () => {
    setSearch('?native=1'); // native, but NO window.pywebview yet → not ready
    const { nativeResize, fireReady } = await load();

    nativeResize('map', false); // 1024 — queued
    nativeResize('routines', false); // 832 — overwrites the queued 1024 (last-wins)

    const resize = vi.fn();
    (window as unknown as { pywebview: unknown }).pywebview = { api: { resize } };
    fireReady();

    expect(resize).toHaveBeenCalledTimes(1);
    expect(resize).toHaveBeenCalledWith(832, 860); // only the final size, not the stale 1024
  });
});
