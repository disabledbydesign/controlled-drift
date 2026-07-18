/**
 * Tests for the wire→app adapters.
 *
 * Every case below is a shape that came off the RUNNING server on 2026-07-18, not an invented
 * payload — that is the point. Each one is a place the live data and the fixtures disagreed, and
 * three of them were silently wrong until the real endpoint was pointed at the real UI. A test
 * written from the fixture would have passed on all three.
 */

import { describe, expect, it } from 'vitest';
import { graphFromTree, planFromLive } from '../adapt.ts';
import type { LivePlan, TreeResponse } from '../adapt.ts';

describe('graphFromTree', () => {
  /** The endpoint answers orphans as a KEYED OBJECT; the fixture models an ARRAY. */
  it('turns the four keyed orphan buckets into an ordered array', () => {
    const res: TreeResponse = {
      nodes: [],
      strategies: [],
      orphans: {
        // deliberately out of order — the adapter imposes the retiring surface's order
        orphan_recurring: { label: '⚠ NO PROJECT — orphan recurring items', nodes: [] },
        projects_without_goal: { label: '⚠ NO GOAL YET — projects not linked to a goal', nodes: [] },
        parentless_workstreams: { label: '⚙ Workstreams with no parent project', nodes: [] },
        orphan_tasks: { label: '⚠ NO PROJECT — orphan tasks', nodes: [] },
      },
    };
    expect((graphFromTree(res).orphans ?? []).map((b) => b.key)).toEqual([
      'projects_without_goal',
      'orphan_tasks',
      'orphan_recurring',
      'parentless_workstreams',
    ]);
  });

  it('keeps a bucket key the server adds later, after the four known ones', () => {
    const res = {
      nodes: [],
      strategies: [],
      orphans: {
        orphan_tasks: { label: 'a', nodes: [] },
        something_new: { label: 'b', nodes: [] },
      },
    } as TreeResponse;
    expect((graphFromTree(res).orphans ?? []).map((b) => b.key)).toEqual([
      'orphan_tasks',
      'something_new',
    ]);
  });

  it('uses the server labels verbatim — they are June-facing and not ours to reword', () => {
    const res = {
      nodes: [],
      strategies: [],
      orphans: { orphan_tasks: { label: '⚠ NO PROJECT — orphan tasks', nodes: [] } },
    } as TreeResponse;
    expect(graphFromTree(res).orphans?.[0]?.label).toBe('⚠ NO PROJECT — orphan tasks');
  });
});

describe('planFromLive', () => {
  /**
   * THE ONE THAT MATTERED. The live block row for "Work on IOP and recovery" carries NO `id`;
   * its id is in `project_id`. Reading `id` alone produced a block that could not be checked
   * off — a ghost row. `seedPlan`'s blocks all carry a plain `id`, so the fixture hid it.
   */
  it('reads a block id from project_id when id is absent', () => {
    const live: LivePlan = {
      shape: 'priority',
      items: [{ task: 'Work on IOP and recovery', block: true, project_id: 'proj-1', chunk_min: 90 }],
    };
    const item = planFromLive(live).blocks[0]?.items[0];
    expect(item?.kind).toBe('block');
    expect(item && 'id' in item && item.id).toBe('proj-1');
  });

  it('prefers an explicit id over project_id when both are present', () => {
    const live: LivePlan = {
      shape: 'priority',
      items: [{ block: true, id: 'real', project_id: 'other' }],
    };
    const item = planFromLive(live).blocks[0]?.items[0];
    expect(item && 'id' in item && item.id).toBe('real');
  });

  it('collapses the flag-bag into the kind discriminator', () => {
    const live: LivePlan = {
      shape: 'priority',
      items: [
        { id: 't1', task: 'a real task', duration_min: 45 },
        { interstitial: true, task: 'rest', time: '12:00' },
        { block: true, project_id: 'p1' },
      ],
    };
    expect(planFromLive(live).blocks[0]?.items.map((i) => i.kind)).toEqual([
      'task',
      'break',
      'block',
    ]);
  });

  it('renames woven_frame to woven', () => {
    expect(planFromLive({ woven_frame: 'today is about the move' }).woven).toBe(
      'today is about the move',
    );
  });

  it('drops `why` — spec §14 removed the per-item reason', () => {
    const item = planFromLive({
      shape: 'priority',
      items: [{ id: 't1', why: 'because' } as never],
    }).blocks[0]?.items[0];
    expect(item && 'why' in item && item.why).toBe('');
  });

  it('carries held_back_names across as heldBack', () => {
    const item = planFromLive({
      shape: 'priority',
      items: [{ id: 't1', held_back_names: ['one', 'two'] }],
    }).blocks[0]?.items[0];
    expect(item && 'heldBack' in item && item.heldBack).toEqual(['one', 'two']);
  });

  /**
   * Appointments are today's fixed-time anchors. `plan_store._iter_items` walks them separately
   * precisely because omitting them was a real check-off-doesn't-stick bug, so they must reach
   * the render layer with their ids intact.
   */
  it('keeps appointments as checkable rows, ahead of the rest', () => {
    const plan = planFromLive({
      shape: 'priority',
      items: [{ id: 't1', task: 'later' }],
      appointments: [{ id: 'appt', task: 'Therapy', time: '11:00', recurring: true }],
    });
    const items = plan.blocks[0]?.items ?? [];
    expect(items[0] && 'id' in items[0] && items[0].id).toBe('appt');
    expect(items).toHaveLength(2);
  });

  it('gives a priority-shape plan an UNLABELLED container band, so no header renders', () => {
    const plan = planFromLive({ shape: 'priority', items: [{ id: 't1' }] });
    expect(plan.shape).toBe('priority');
    expect(plan.blocks[0]?.label).toBe('');
    expect(plan.blocks[0]?.time).toBe('');
  });

  it('keeps a schedule-shape plan’s real bands', () => {
    const plan = planFromLive({
      shape: 'schedule',
      blocks: [{ label: 'MORNING', time: '9–12', framing: 'f', items: [{ id: 't1' }] }],
    });
    expect(plan.blocks[0]?.label).toBe('MORNING');
    expect(plan.blocks[0]?.items).toHaveLength(1);
  });

  it('defaults an absent shape to schedule — the UI branches on it unconditionally', () => {
    expect(planFromLive({}).shape).toBe('schedule');
  });
});
