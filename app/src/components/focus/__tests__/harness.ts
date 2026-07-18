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

export function focusCtxWith(ui: Partial<FocusUi> = {}, periods: Period[] = freshPeriods()) {
  const up = vi.fn();
  const applyPeriods = vi.fn();
  const openEditor = vi.fn();
  const closeEditor = vi.fn();
  const ctx: FocusCtx = {
    T: themes.celestial,
    graph: freshFocusGraph(),
    periods,
    ui: { ...BASE_FOCUS_UI, ...ui },
    up,
    applyPeriods,
    openEditor,
    closeEditor,
  };
  return { ctx, up, applyPeriods, openEditor, closeEditor };
}
