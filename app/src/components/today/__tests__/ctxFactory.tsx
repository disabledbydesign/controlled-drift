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
  editOpen: {},
  movePick: null,
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
export function ctxWith(
  ui: Partial<TodayUi> = {},
  plan: Plan = freshPlan(),
  /** Which control has a generation in flight — the action row's in-progress state. */
  generating: string | null = null,
) {
  const graph = freshGraph();
  const up = vi.fn();
  const apply = vi.fn();
  const applyPlan = vi.fn();
  const flash = vi.fn();
  /**
   * Defaults to a generation that SUCCEEDED, because that is what the real seam resolves on the
   * ordinary path and because the value is load-bearing: the ask box clears her text on `true`
   * and holds it on anything else. A test about the failure path says so itself with
   * `regenerate.mockResolvedValue(false)`.
   */
  const regenerate = vi.fn(async () => true);
  const chunk = vi.fn();
  const openDetail = vi.fn();
  const goTab = vi.fn();
  // The three per-row plan writes. Spies rather than no-ops so a control wired to nothing is
  // distinguishable from one wired correctly — the whole point of the row-action tests.
  const notToday = vi.fn();
  const setDuration = vi.fn();
  const moveItem = vi.fn();
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
    regenerate,
    chunk,
    generating,
    openDetail,
    goTab,
    notToday,
    setDuration,
    moveItem,
  };
  return {
    ctx,
    plan,
    up,
    apply,
    applyPlan,
    flash,
    regenerate,
    chunk,
    openDetail,
    goTab,
    notToday,
    setDuration,
    moveItem,
  };
}
