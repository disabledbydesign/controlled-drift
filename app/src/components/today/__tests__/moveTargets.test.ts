/**
 * Tests for the MOVE DESTINATION list — the positions `/api/task/move` will accept for one item.
 *
 * Plans here are BUILT EXPLICITLY rather than taken from `seedPlan`, because the subject of every
 * test is plan GEOMETRY: which index sits where, and what the server's index space is against the
 * rendered one. A shared fixture would hide the very thing under test.
 *
 * ── THE TWO INDEX SPACES, WHICH IS WHAT THIS FILE IS REALLY FOR ──────────────
 * `position` is the FINAL index the item lands at, indexed against the SERVER's list. Two things
 * make that differ from what is on screen:
 *
 *  1. APPOINTMENTS. The server keeps them in their own top-level key; `planFromLive` folds them
 *     into the front of `blocks[0]`. The difference is `plan.apptCount`, and ignoring it moves
 *     the item to the wrong slot on any day she has an appointment — silently, both being valid.
 *  2. THE ITEM'S OWN REMOVAL. Inside its own block the item is lifted out before it is
 *     reinserted, so every later anchor shifts down by one. This is the rule the old overlay
 *     verified against the live server (`renderBlockPlacement`: same block uses `j`, another
 *     block uses `j+1`).
 *
 * A destination that is a no-op is not offered at all — `plan_store.move_item` answers "already
 * there" with a 400, and a control that produces a visible failure for a tap she was invited to
 * make is worse than a control that never offered it.
 */

import { describe, expect, it } from 'vitest';
import type { Plan, PlanItem } from '../../../fixtures/index.ts';
import { moveDestinations } from '../moveTargets.ts';

const task = (id: string, title: string): PlanItem =>
  ({ kind: 'task', id, task: title, time: '', durationMin: 30, why: '' }) as PlanItem;
const brk = (): PlanItem => ({ kind: 'break', time: '13:00', task: 'lunch' }) as PlanItem;

const titleOf = (it: PlanItem) => ('task' in it && it.task ? it.task : 'untitled');

function priorityPlan(items: PlanItem[], apptCount = 0): Plan {
  return {
    date: '', generated: '', shape: 'priority', header: '', woven: '',
    apptCount,
    blocks: [{ label: '', time: '', framing: '', items }],
  };
}

function schedulePlan(blocks: { label: string; items: PlanItem[] }[], apptCount = 0): Plan {
  return {
    date: '', generated: '', shape: 'schedule', header: '', woven: '',
    apptCount,
    blocks: blocks.map((b) => ({ label: b.label, time: '', framing: '', items: b.items })),
  };
}

describe('moveDestinations — a fragmented (priority) day', () => {
  const plan = priorityPlan([task('a', 'Call the clinic'), task('b', 'Email Sam'), task('c', 'Laundry')]);

  it('sends NO target_block on a priority day, because the server reads position-only as the list reorder', () => {
    const ds = moveDestinations(plan, 'b', titleOf);
    expect(ds.length).toBeGreaterThan(0);
    for (const d of ds) {
      expect(d.target.block).toBeNull();
    }
  });

  it('offers moving the item EARLIER, to the front of the list', () => {
    const first = moveDestinations(plan, 'b', titleOf).find((d) => d.target.position === 0);
    expect(first).toBeDefined();
    expect(first!.label).toBe('first in the list');
  });

  it('offers moving the item LATER, naming the row it lands after', () => {
    const after = moveDestinations(plan, 'a', titleOf).find((d) => d.label === 'after Laundry');
    expect(after).toBeDefined();
    expect(after!.target.position).toBe(2);
  });

  /** Its own slot and the slot it already sits in would both 400 as "already there". */
  it('never offers the position the item already occupies', () => {
    const positions = moveDestinations(plan, 'b', titleOf).map((d) => d.target.position);
    expect(positions).not.toContain(1);
    expect(positions).toEqual([0, 2]);
  });

  it('offers nothing at all for an id that is not in the plan', () => {
    expect(moveDestinations(plan, 'nope', titleOf)).toEqual([]);
  });

  /**
   * The appointment offset. `Therapy` is a folded-in appointment at rendered index 0, so `b` is
   * rendered third but is the server's index 1. Moving it to the front must send position 0 —
   * the position of the first NON-appointment row — not the rendered index of anything.
   */
  it('subtracts the folded-in appointments from every position, not just the first', () => {
    // Rendered: Therapy(appt), Call, Email, Laundry. The server's list is Call, Email, Laundry —
    // so `Call` is its index 0, and moving it after `Email` is position 1, NOT the rendered 2.
    const withAppt = priorityPlan(
      [task('appt', 'Therapy'), task('a', 'Call'), task('b', 'Email'), task('c', 'Laundry')],
      1,
    );
    expect(moveDestinations(withAppt, 'a', titleOf)).toEqual([
      { key: '0:2', label: 'after Email', target: { block: null, position: 1 } },
      { key: '0:3', label: 'after Laundry', target: { block: null, position: 2 } },
    ]);
  });

  it('never offers an appointment as a landing anchor, having no index the server would accept', () => {
    const withAppt = priorityPlan([task('appt', 'Therapy'), task('a', 'Call'), task('b', 'Email')], 1);
    const labels = moveDestinations(withAppt, 'b', titleOf).map((d) => d.label);
    // Positively: the real anchor IS offered. Without this the assertion below also passes
    // against a control that offers nothing at all.
    expect(labels).toContain('first in the list');
    expect(labels).not.toContain('after Therapy');
  });
});

describe('moveDestinations — a clock (schedule) day', () => {
  const plan = schedulePlan([
    { label: 'Morning', items: [task('a', 'Call the clinic'), task('b', 'Email Sam')] },
    { label: 'Afternoon', items: [task('c', 'Laundry'), brk(), task('d', 'Walk')] },
  ]);

  it('carries the band index the server dispatches on', () => {
    const ds = moveDestinations(plan, 'a', titleOf);
    expect(ds.find((d) => d.label === 'first in Afternoon')!.target.block).toBe(1);
  });

  it('offers moving into an EARLIER band, which the bidirectional endpoint accepts', () => {
    const ds = moveDestinations(plan, 'd', titleOf);
    const up = ds.find((d) => d.label === 'first in Morning');
    expect(up).toBeDefined();
    expect(up!.target).toEqual({ block: 0, position: 0 });
  });

  /**
   * ANOTHER band: the item is not removed from it, so landing after the anchor at index j is the
   * final index j+1. `Laundry` is index 0 of Afternoon, so after it is position 1.
   */
  it('lands at anchor+1 when moving into a band the item is not already in', () => {
    const ds = moveDestinations(plan, 'a', titleOf);
    expect(ds.find((d) => d.label === 'after Laundry')!.target).toEqual({ block: 1, position: 1 });
  });

  /**
   * ITS OWN band: the item is lifted out first, so a later anchor at index j is the final index
   * j, not j+1. `b` is index 1 of Morning; after `a` (index 0) is a no-op and is not offered.
   */
  it('lands at the anchor index itself when moving later within its own band', () => {
    const three = schedulePlan([
      { label: 'Morning', items: [task('a', 'One'), task('b', 'Two'), task('c', 'Three')] },
    ]);
    const ds = moveDestinations(three, 'a', titleOf);
    expect(ds.find((d) => d.label === 'after Three')!.target).toEqual({ block: 0, position: 2 });
  });

  it('counts a break as occupying a position, since the server indexes it too', () => {
    const ds = moveDestinations(plan, 'a', titleOf);
    expect(ds.find((d) => d.label === 'after Walk')!.target).toEqual({ block: 1, position: 3 });
  });

  it('never offers a break as a landing anchor', () => {
    const labels = moveDestinations(plan, 'a', titleOf).map((d) => d.label);
    // Positively: the rows either side of the break ARE offered, so this cannot pass against a
    // control that offers nothing.
    expect(labels).toContain('after Laundry');
    expect(labels).toContain('after Walk');
    expect(labels).not.toContain('after lunch');
  });

  it('gives every destination a key distinct from every other', () => {
    const keys = moveDestinations(plan, 'a', titleOf).map((d) => d.key);
    expect(keys.length).toBeGreaterThan(1);
    expect(new Set(keys).size).toBe(keys.length);
  });
});
