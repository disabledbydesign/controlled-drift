/**
 * The shared Today-tab test context factory.
 *
 * Extracted VERBATIM from `today.test.tsx` (2026-07-18) so a second test file can build the
 * same context. Nothing about the behaviour changed in the move: `BASE_UI`, `freshGraph`,
 * `freshPlan` and `ctxWith` are the same code, in the same order, with the same defaults.
 * They moved together because `ctxWith` reads all three, and `today.test.tsx` also calls
 * `freshGraph` and `freshPlan` directly.
 */

import { vi } from 'vitest';
import { themes } from '@tokens';
import { seed, seedPeriods, seedPlan, seedStrategies } from '../../../fixtures/index.ts';
import type { Plan } from '../../../fixtures/index.ts';
import { index } from '../../../model/index.ts';
import type { Graph, ModelNode } from '../../../model/index.ts';
import type { TodayCtx, TodayUi } from '../types.ts';
import { focusCtxWith } from '../../focus/__tests__/harness.ts';

export const BASE_UI: TodayUi = {
  todayShape: 'schedule',
  focusExpanded: false,
  heldOpen: {},
  chunked: {},
  blocksOpen: {},
  priOrder: null,
  ask: '',
};

export function freshGraph(): Graph {
  return {
    roots: structuredClone(seed) as ModelNode[],
    strategies: structuredClone(seedStrategies) as ModelNode[],
  };
}

export function freshPlan(): Plan {
  return structuredClone(seedPlan) as Plan;
}

/** A context whose `up` / `apply` / `applyPlan` are spies, so writes are observable. */
export function ctxWith(ui: Partial<TodayUi> = {}, plan: Plan = freshPlan()) {
  const graph = freshGraph();
  const up = vi.fn();
  const apply = vi.fn();
  const applyPlan = vi.fn();
  const flash = vi.fn();
  const openDetail = vi.fn();
  const goTab = vi.fn();
  const ctx: TodayCtx = {
    T: themes.celestial,
    graph,
    idx: index(graph),
    plan,
    periods: seedPeriods,
    // Task 9: FocusSlot's expanded body is FocusPanel, which reads this.
    focus: focusCtxWith().ctx,
    ui: { ...BASE_UI, ...ui },
    up,
    apply,
    applyPlan,
    flash,
    openDetail,
    goTab,
  };
  return { ctx, up, apply, applyPlan, flash, openDetail, goTab };
}
