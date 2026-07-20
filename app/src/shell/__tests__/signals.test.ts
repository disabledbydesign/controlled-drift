// @vitest-environment node
// Pure logic — no DOM (localStorage is stubbed wholesale below, and jsdom's own
// localStorage is non-functional here anyway). Opting out of jsdom keeps 53 environment
// setups from contending for 8 cores, which is what made the suite time out under load.

/**
 * The presentation policy and the failure log (Task 11).
 *
 * These pin the parts of June's 2026-07-18 direction that are easiest to reverse by accident:
 *   1. success is QUIET by default — nothing appears at the bottom of the screen
 *   2. failure is a bar, and it does NOT auto-dismiss
 *   3. the verbose textual bar still exists for dev, and is opt-in rather than on
 *   4. a failure reaches the log even if nobody ever looks at the screen
 *
 * `vite.config` sets `globals: false`, so nothing here relies on ambient test globals.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { present, verboseSignals } from '../signals.ts';
import type { Signal } from '../signals.ts';
import { logFailure, recent, setFailureSink, _resetFailureLog } from '../errorLog.ts';

const sig = (over: Partial<Signal> = {}): Signal => ({
  kind: 'success',
  msg: 'Saved',
  seq: 1,
  nodeId: null,
  ...over,
});

/**
 * This environment's `localStorage` is present but non-functional (the run logs
 * "`--localstorage-file` was provided without a valid path", and `removeItem` is not a
 * function). `verboseSignals()` already treats a throwing `localStorage` as "off", which is the
 * right production fallback — but a test that cannot SET the flag cannot check the on case at
 * all. A minimal in-memory stand-in makes both branches reachable.
 */
const store = new Map<string, string>();
const fakeStorage = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
};

beforeEach(() => {
  store.clear();
  vi.stubGlobal('localStorage', fakeStorage);
  _resetFailureLog();
  // `logFailure` writes to console.error by design; silence it so a passing run is quiet.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  store.clear();
  _resetFailureLog();
});

describe('present() — the one place presentation is decided', () => {
  it('shows NOTHING at the bottom of the screen for a success, by default', () => {
    // The whole point of June's direction: *"I tend to hate validation toasts that pop up at the
    // bottom and say 'done'."* If this ever returns `bar` without the verbose flag, that is the
    // regression.
    expect(present(sig()).mode).not.toBe('bar');
  });

  it('a success is an in-place settle, not text', () => {
    expect(present(sig()).mode).toBe('inline');
  });

  it('a failure IS a bar, and it persists until dismissed', () => {
    const p = present(sig({ kind: 'failure', msg: 'Not moved. …' }));
    expect(p.mode).toBe('bar');
    expect(p.persist).toBe(true);
  });

  it('dev-verbose is OFF unless explicitly turned on', () => {
    expect(verboseSignals()).toBe(false);
  });

  it('with dev-verbose on, a success becomes the textual bar and fades on its own', () => {
    localStorage.setItem('cd.verboseSignals', '1');
    const p = present(sig());
    expect(p.mode).toBe('bar');
    expect(p.persist).toBe(false);
    // v2/v3's 1.6s pill (review-reorganize-mobile-v3.html:321).
    expect(p.ms).toBe(1600);
  });

  it('dev-verbose does NOT make failures fade — a failure is never transient', () => {
    localStorage.setItem('cd.verboseSignals', '1');
    expect(present(sig({ kind: 'failure' })).persist).toBe(true);
  });
});

describe('the failure log', () => {
  it('records a failure whether or not anyone reads the message', () => {
    logFailure('Not moved. …', { objectId: 'abc', before: { move: 'abc' } });
    expect(recent()).toHaveLength(1);
    expect(recent()[0]!.objectId).toBe('abc');
  });

  it('defaults `kind` to the value `corrections_log` will be called with', () => {
    logFailure('boom');
    expect(recent()[0]!.kind).toBe('write_failed');
  });

  it('hands the record to the Track B sink once one is installed', () => {
    const sink = vi.fn();
    setFailureSink(sink);
    logFailure('boom', { kind: 'move_refused' });
    expect(sink).toHaveBeenCalledTimes(1);
    expect(sink.mock.calls[0]![0]).toMatchObject({ kind: 'move_refused', msg: 'boom' });
  });

  it('records even with no sink installed — the local trail does not depend on the network', () => {
    logFailure('boom');
    expect(recent()).toHaveLength(1);
  });
});