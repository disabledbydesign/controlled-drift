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
import type { Preset } from '../../../api/adapt.ts';
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
  /** Desktop shell? Phone by default, which is the surface June actually carries. */
  wide = false,
  /*
   * Her plan-action presets, as `GET /api/actions` serves them from her own
   * `~/.controlled-drift/actions.json`. The default is HER LIVE FILE, read 2026-07-19 — so a
   * test that does not care about presets still renders the row she actually has, and the
   * labels in these tests stay answerable to the file rather than to the app.
   *
   * ⚠ Note `quick-wins` reads "Quick wins first". The app used to hardcode "Quick wins only";
   * that drift is the reason the row now reads her file.
   */
  presets: readonly Preset[] = [
    { id: 'low-energy', label: 'Low energy today' },
    { id: 'quick-wins', label: 'Quick wins first' },
    { id: 'stuck', label: "I'm stuck" },
    { id: 'life-admin', label: 'Life admin & household' },
  ],
) {
  const graph = freshGraph();
  const up = vi.fn();
  const apply = vi.fn();
  const applyPlan = vi.fn();
  const flash = vi.fn();
  /**
   * Spied SEPARATELY from `flash`, because the two say opposite things: `flash` is a success
   * signal and `fail` is a not-saved one. A single spy would let a test about an honest failure
   * pass against a control that reported it as a success.
   */
  const fail = vi.fn();
  /**
   * Defaults to a generation that SUCCEEDED, because that is what the real seam resolves on the
   * ordinary path and because the value is load-bearing: the ask box clears her text on `true`
   * and holds it on anything else. A test about the failure path says so itself with
   * `regenerate.mockResolvedValue(false)`.
   */
  const regenerate = vi.fn(async () => true);
  const chunk = vi.fn();
  /** The arc STEP check — a different writer from `chunk`, and spied separately so the two
   * cannot be confused for each other in an assertion. */
  const completeStep = vi.fn();
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
    wide,
    presets,
    up,
    apply,
    applyPlan,
    flash,
    fail,
    regenerate,
    chunk,
    completeStep,
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
    presets,
    up,
    apply,
    applyPlan,
    flash,
    fail,
    regenerate,
    chunk,
    completeStep,
    openDetail,
    goTab,
    notToday,
    setDuration,
    moveItem,
  };
}
