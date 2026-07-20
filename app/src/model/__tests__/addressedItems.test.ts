// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * `addressedWorkItems` — the address an arc checkbox needs, carried with the item.
 *
 * ── why this is tested at all, given how small the function is ──
 *
 * `toggleArcStep` resolves a step as `plan.blocks[bandIndex].items[itemIndex].arc[stepIndex]`
 * and answers a miss with `{plan, toast: null}`. SILENTLY: no throw, no toast, no visual
 * change. A wrong address therefore does not fail loudly — it ships a checkbox that is tapped
 * and does nothing, forever, with nothing on screen to say so.
 *
 * The failure mode these tests pin is a running counter across the whole plan standing in for
 * the per-band index. On a single-band plan the two are identical, so every assertion still
 * passes; on a two-band plan the counter addresses a different item, or none. Hence the
 * two-band fixture and the round-trip assertion below: an equality check on the numbers alone
 * would restate whatever the implementation computed, so the test resolves the address back
 * through the plan and demands the SAME OBJECT.
 */

import { describe, it, expect } from 'vitest';

import type { Plan, PlanArcStep } from '../../fixtures/index.ts';
import { addressedWorkItems, workItems } from '../plan.ts';

const ARC: PlanArcStep[] = [
  { text: 'Read chapter 2', state: 'done' },
  { text: 'Write the notes', state: 'here', id: 'bafy-notes' },
];

/**
 * Two bands. Band 0 holds a break in the MIDDLE, so a filtered-index implementation (one that
 * numbers only the items it kept) also diverges from the true `items[]` index.
 */
function twoBandPlan(): Plan {
  return {
    date: '2026-07-18',
    generated: '2026-07-18T08:00:00Z',
    shape: 'schedule',
    header: 'Two bands today.',
    woven: '',
    blocks: [
      {
        label: 'Morning',
        time: '9–12',
        framing: '',
        items: [
          { kind: 'task', id: 'bafy-dishes', time: '9:00', durationMin: 20, why: '' },
          { kind: 'break', time: '9:20', task: 'Tea' },
          {
            kind: 'block',
            id: 'bafy-iop',
            task: 'Work on IOP and recovery',
            time: '9:30',
            chunkMin: 90,
            why: '',
            arc: ARC,
          },
        ],
      },
      {
        label: 'Afternoon',
        time: '1–5',
        framing: '',
        items: [
          { kind: 'task', id: 'bafy-groceries', time: '13:00', durationMin: 45, why: '' },
          { kind: 'task', id: 'bafy-laundry', time: '14:00', durationMin: 30, why: '' },
        ],
      },
    ],
  };
}

describe('addressedWorkItems', () => {
  it('returns every non-break item with the band and item index at which it actually sits', () => {
    const plan = twoBandPlan();
    const addressed = addressedWorkItems(plan);

    expect(
      addressed.map((a) => [a.item.id, a.bandIndex, a.itemIndex] as [string, number, number]),
    ).toEqual([
      // ⚠ itemIndex 2, not 1: the break at index 1 is skipped from the OUTPUT but still
      // occupies its slot in `items[]`, which is what `toggleArcStep` indexes into.
      ['bafy-dishes', 0, 0],
      ['bafy-iop', 0, 2],
      // ⚠ band 1 restarts at 0. A running counter would say 2 and 3 here.
      ['bafy-groceries', 1, 0],
      ['bafy-laundry', 1, 1],
    ]);
  });

  it('round-trips: each address resolves back through the plan to the same item object', () => {
    const plan = twoBandPlan();

    for (const { item, bandIndex, itemIndex } of addressedWorkItems(plan)) {
      const band = plan.blocks[bandIndex];
      if (!band) throw new Error(`bandIndex ${bandIndex} does not resolve to a band`);
      // Identity, not deep equality — a structurally-equal item at the wrong address would
      // satisfy `toEqual` and still send `toggleArcStep` to the wrong step.
      expect(band.items[itemIndex]).toBe(item);
    }
  });

  it('addresses the block whose arc gets checked off, all the way down to the step', () => {
    const plan = twoBandPlan();
    const block = addressedWorkItems(plan).find((a) => a.item.kind === 'block');
    if (!block) throw new Error('fixture no longer contains a block item');

    // The exact expression `toggleArcStep` evaluates. If this misses, that function returns
    // `{plan, toast: null}` and the user sees nothing at all.
    const resolved = plan.blocks[block.bandIndex]?.items[block.itemIndex];
    expect(resolved?.kind).toBe('block');
    expect(resolved).toBe(block.item);
    expect(resolved && 'arc' in resolved ? resolved.arc?.[1]?.text : undefined).toBe(
      'Write the notes',
    );
  });

  it('excludes break items, exactly as workItems excludes them', () => {
    const plan = twoBandPlan();

    expect(addressedWorkItems(plan).some((a) => (a.item as { kind: string }).kind === 'break')).toBe(
      false,
    );
    // Same membership and same order as the function it addresses — the two must not drift.
    expect(addressedWorkItems(plan).map((a) => a.item)).toEqual(workItems(plan));
  });

  it('holds for a single-band priority plan, where the container band is index 0', () => {
    const plan = twoBandPlan();
    const priority: Plan = { ...plan, shape: 'priority', blocks: [plan.blocks[0]!] };

    expect(addressedWorkItems(priority).map((a) => [a.bandIndex, a.itemIndex])).toEqual([
      [0, 0],
      [0, 2],
    ]);
  });

  it('returns nothing for an empty plan rather than inventing an address', () => {
    const plan = twoBandPlan();
    expect(addressedWorkItems({ ...plan, blocks: [] })).toEqual([]);
    expect(addressedWorkItems({ ...plan, blocks: [{ ...plan.blocks[0]!, items: [] }] })).toEqual([]);
  });
});