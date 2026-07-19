/**
 * A `FocusCtx` whose writers are spies, shared by the focus tests and by the Today test
 * (whose `FocusSlot` now mounts `FocusPanel` and so needs one).
 */

import { vi } from 'vitest';
import { themes } from '@tokens';
import { seed, seedPeriods, seedStrategies } from '../../../fixtures/index.ts';
import type { Period } from '../../../fixtures/index.ts';
import type { Graph, ModelNode } from '../../../model/index.ts';
import type { FocusCtx, FocusUi } from '../types.ts';

export const BASE_FOCUS_UI: FocusUi = {
  focusView: 'list',
  focusEditId: null,
  focusReflect: null,
  focusDraft: '',
  focusNewOff: '',
  focusPickFront: '',
  focusPickPaused: '',
};

export function freshFocusGraph(): Graph {
  return {
    roots: structuredClone(seed) as ModelNode[],
    strategies: structuredClone(seedStrategies) as ModelNode[],
  };
}

export function freshPeriods(): Period[] {
  return structuredClone(seedPeriods) as Period[];
}

/**
 * What `authorFocus` resolves to by default in these tests — a stand-in for the SERVER's answer.
 *
 * ⚠ It is a test fixture, not a client-side form builder. The thing this replaced (`formFromDraft`)
 * built a form exactly like this in PRODUCTION and showed it under "Here's what I heard".
 */
export const BASE_AUTHORED_FORM = {
  name: 'Job search week',
  start: '2026-08-03',
  end: '2026-08-09',
  intent: 'jobs first this week',
  front: [] as string[],
  note: '',
  availStart: '',
  availEnd: '',
  daysOff: [] as string[],
  daysOn: '',
  output: 'Auto',
  workdayStart: '',
  workdayEnd: '',
  paused: [] as string[],
  /** Empty by default so a test that does not care about reactivation reads unchanged. */
  reactivate: [] as string[],
};

export function focusCtxWith(ui: Partial<FocusUi> = {}, periods: Period[] = freshPeriods()) {
  const up = vi.fn();
  const applyPeriods = vi.fn();
  const openEditor = vi.fn();
  const closeEditor = vi.fn();
  // The two server seams. Defaults are the happy path: the structure step returns a form, and
  // the write lands — so a test that does not care about the network reads as it did before.
  const saveFocusPeriod = vi.fn().mockResolvedValue(true);
  const authorFocus = vi.fn(async () => ({ ...BASE_AUTHORED_FORM }));
  const ctx: FocusCtx = {
    T: themes.celestial,
    graph: freshFocusGraph(),
    periods,
    ui: { ...BASE_FOCUS_UI, ...ui },
    up,
    applyPeriods,
    openEditor,
    closeEditor,
    authorFocus,
    saveFocusPeriod,
  };
  return { ctx, up, applyPeriods, openEditor, closeEditor, authorFocus, saveFocusPeriod };
}
