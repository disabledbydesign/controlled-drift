// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * Done-state, read and written from the SAME predicate.
 *
 * ── the two live bugs this pins (both observed on June's real plan, 2026-07-18) ──
 *
 * 1. THREE COMPLETED CHORES RENDERED AS OUTSTANDING. "Do the dishes", "Clean the kitchen"
 *    and "Do laundry" are Recurring. A recurring's completion for the day is written to
 *    `completion_log`, NOT to the object — so the graph node carries no `done` and no
 *    `status`. The surface derived done-state from the graph alone, so it showed her three
 *    chores she had already finished as still to do. The plan payload knew (`done: true`)
 *    and nothing read it.
 *
 *    On a day framed around very little capacity, telling her she still has work she
 *    already did is the most costly thing this surface can get wrong.
 *
 * 2. A CHECKBOX THAT COULD NOT BE UNCHECKED. "Go to the grocery store" has `done: false`
 *    and `status: 'Done'`. `isDone` accepts either, so it rendered as checked — but
 *    `toggleDone` computed `!n.vals.done`, i.e. `!false`, and asked the server to complete
 *    it AGAIN. The control disagreed with itself: checked, and un-uncheckable.
 *
 * The shared root is that done-ness was READ by one rule (`isDone`, which accepts `status`)
 * and WRITTEN by another (raw `!vals.done`). These tests hold the two rules together.
 */

import { describe, it, expect } from 'vitest';

import { seed, seedStrategies } from '../../fixtures/index.ts';
import type { Graph, ModelNode } from '../types.ts';
import { isDone, planItemDone } from '../plan.ts';
import { toggleDone } from '../mutations.ts';
import { index, node } from '../index.ts';

function graphWith(overrides: { id: string; level: string; vals: Record<string, unknown> }): Graph {
  const g: Graph = {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
  };
  // Park the probe node at the top level; ancestry is irrelevant to done-state.
  (g.roots as unknown as ModelNode[]).push({
    id: overrides.id,
    level: overrides.level,
    title: 'probe',
    vals: overrides.vals,
    children: [],
  } as unknown as ModelNode);
  return g;
}

describe('planItemDone — the plan is the authority for a row that is IN the plan', () => {
  it('reports a recurring done when the plan says so, even though the graph cannot know', () => {
    // The exact live shape: a Recurring with nothing on the node, completed today.
    const g = graphWith({ id: 'rec1', level: 'RECURRING', vals: {} });
    const n = node(index(g), 'rec1')!;

    expect(isDone(n)).toBe(false); // the graph genuinely does not know
    expect(planItemDone({ done: true }, n)).toBe(true); // the plan does
  });

  it('falls back to the graph when the plan item says nothing', () => {
    const g = graphWith({ id: 't1', level: 'TASK', vals: { status: 'Done' } });
    const n = node(index(g), 't1')!;
    expect(planItemDone({}, n)).toBe(true);
    expect(planItemDone(undefined, n)).toBe(true);
  });

  it('an explicit false from the plan is honoured, not treated as absent', () => {
    // `done: false` must not fall through to the graph — that would resurrect a row she
    // reopened today on an object whose status still reads Done.
    const g = graphWith({ id: 't2', level: 'TASK', vals: { status: 'Done' } });
    const n = node(index(g), 't2')!;
    expect(planItemDone({ done: false }, n)).toBe(false);
  });
});

describe('toggleDone — writes against the same rule the screen reads', () => {
  it('reopens a task whose done-ness comes from status, instead of completing it twice', () => {
    // The live "Go to the grocery store" shape.
    const g = graphWith({ id: 'g1', level: 'TASK', vals: { done: false, status: 'Done' } });
    const res = toggleDone(g, 'g1');
    expect(res.write).toEqual({ op: 'complete', id: 'g1', done: false });
    expect(res.toast).toBe('Reopened');
  });

  it('takes an explicit current state, so a recurring can be reopened from the plan', () => {
    const g = graphWith({ id: 'rec2', level: 'RECURRING', vals: {} });
    // The graph says not-done; the PLAN says done. Tapping must reopen, not re-complete.
    const res = toggleDone(g, 'rec2', true);
    expect(res.write).toEqual({ op: 'complete', id: 'rec2', done: false });
  });

  it('still completes a genuinely open task', () => {
    const g = graphWith({ id: 'o1', level: 'TASK', vals: { status: 'Ready' } });
    const res = toggleDone(g, 'o1');
    expect(res.write).toEqual({ op: 'complete', id: 'o1', done: true });
  });
});