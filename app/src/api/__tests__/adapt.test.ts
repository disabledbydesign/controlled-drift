// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * Tests for the wire→app adapters.
 *
 * Every case below is a shape that came off the RUNNING server on 2026-07-18, not an invented
 * payload — that is the point. Each one is a place the live data and the fixtures disagreed, and
 * three of them were silently wrong until the real endpoint was pointed at the real UI. A test
 * written from the fixture would have passed on all three.
 */

import { describe, expect, it } from 'vitest';
import { graphFromTree, planFromLive, presetsFromLive } from '../adapt.ts';
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

  /**
   * The move contract depends on this number. The server indexes `/api/task/move`'s `position`
   * against a list that does NOT contain appointments; this adapter folds them into the front of
   * the first block. Without the count carried through, a position computed from the rendered
   * list is off by exactly the number of appointments — a wrong-slot move on any day she has one,
   * silent because both indices are in range.
   */
  it('records how many appointments it folded into the first block', () => {
    const plan = planFromLive({
      shape: 'priority',
      items: [{ id: 't1', task: 'later' }],
      appointments: [
        { id: 'a1', task: 'Therapy', time: '11:00' },
        { id: 'a2', task: 'Dentist', time: '15:00' },
      ],
    });
    expect(plan.apptCount).toBe(2);
  });

  it('records a zero appointment offset when there are none to fold in', () => {
    const plan = planFromLive({ shape: 'priority', items: [{ id: 't1' }] });
    expect(plan.apptCount).toBe(0);
  });

  /**
   * ⚠ 2026-07-20. On a clock day the backend schedules the appointment INTO a block at its real
   * time AND carries it in `appointments[]` — both, every generation. Prepending the second copy
   * put the same object on screen twice, once at the top of the morning band labelled "2:00" and
   * once at its real 14:00 slot, and the block copy read as an ordinary movable task. An
   * appointment already placed in a block is NOT prepended again: it renders once, at its real
   * time, and the offset is zero because the client's bands now match the server's exactly.
   */
  it('does not prepend an appointment that is already scheduled into a block', () => {
    const plan = planFromLive({
      shape: 'schedule',
      blocks: [
        { label: 'MORNING', time: '9–12', framing: '', items: [{ id: 't1', task: 'draft' }] },
        {
          label: 'AFTERNOON', time: '14–17', framing: '',
          items: [{ id: 'appt', task: 'Drop-In', time: '14:00 – 15:00' }],
        },
      ],
      appointments: [{ id: 'appt', task: 'Drop-In', time: '14:00', duration_min: 60 }],
    });
    const allIds = plan.blocks.flatMap((b) => b.items.map((i) => ('id' in i ? i.id : null)));
    expect(allIds.filter((id) => id === 'appt')).toEqual(['appt']); // exactly once
    expect(plan.apptCount).toBe(0); // nothing folded in, so no index offset
  });

  it('flags the in-block appointment row so the surface knows it is fixed', () => {
    const plan = planFromLive({
      shape: 'schedule',
      blocks: [
        {
          label: 'AFTERNOON', time: '14–17', framing: '',
          items: [{ id: 'appt', task: 'Drop-In', time: '14:00 – 15:00' },
                  { id: 't1', task: 'draft' }],
        },
      ],
      appointments: [{ id: 'appt', task: 'Drop-In', time: '14:00', duration_min: 60 }],
    });
    const appt = plan.blocks[0]!.items.find((i) => 'id' in i && i.id === 'appt')!;
    const plain = plan.blocks[0]!.items.find((i) => 'id' in i && i.id === 't1')!;
    expect(appt.kind === 'task' && appt.appointment).toBe(true);
    expect(plain.kind === 'task' && (plain.appointment ?? false)).toBe(false);
  });

  it('still prepends and flags an appointment the model did NOT schedule into any block', () => {
    // The shape-independent guarantee: an appointment absent from every block must still appear.
    const plan = planFromLive({
      shape: 'schedule',
      blocks: [{ label: 'MORNING', time: '9–12', framing: '', items: [{ id: 't1' }] }],
      appointments: [{ id: 'appt', task: 'Drop-In', time: '14:00', duration_min: 60 }],
    });
    const first = plan.blocks[0]!.items[0]!;
    expect('id' in first && first.id).toBe('appt');
    expect(first.kind === 'task' && first.appointment).toBe(true);
    expect(plan.apptCount).toBe(1);
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

/*
 * THE PLAN'S BUILD TIME. `planFromLive` used to blank this, citing a spec line that removed the
 * plan-age display — so the surface lost the only signal distinguishing today's plan from
 * yesterday's. The adapter now carries the server's real timestamp through UNFORMATTED; the
 * words are composed at render time by `planAgeText`, so a surface left open across midnight
 * cannot keep calling yesterday's plan "this morning's".
 *
 * Verified against the live server 2026-07-19: GET /api/plan answers
 * `generated_at: '2026-07-19T10:14:56.941606'` — a naive local ISO, no zone suffix.
 */
describe('planFromLive — the build time she needs to judge the plan by', () => {
  it('carries the server’s generation timestamp through verbatim', () => {
    const plan = planFromLive({ generated_at: '2026-07-19T10:14:56.941606', items: [] });
    expect(plan.generated).toBe('2026-07-19T10:14:56.941606');
  });

  it('leaves the build time empty when the server sends none, never a stand-in', () => {
    expect(planFromLive({ items: [] }).generated).toBe('');
  });
});

/*
 * HER PRESET BUTTONS COME FROM HER FILE.
 *
 * The four plan-action buttons had their labels hardcoded in the app, and the labels had
 * already drifted from `~/.controlled-drift/actions.json`: her stored preset reads "Quick wins
 * first", the button said "Quick wins only". The fix is NOT to correct the string — it is that
 * the button reads its label from her file, so the drift cannot recur.
 *
 * ⚠ LABELS ARE DISPLAY, IDS ARE CONTRACT. `POST /api/negotiate {preset_id}` answers 400 on an
 * unknown id (`server.py:1017`), so the id must survive untouched while the label is free to
 * change. These tests hold those two apart on purpose.
 *
 * Live shape verified 2026-07-19 via `curl -s localhost:5050/api/actions`.
 */
describe('presetsFromLive — the action row reads her own file', () => {
  const live = {
    version: 1,
    presets: [
      { id: 'low-energy', label: 'Low energy today', operation: 'generate' },
      { id: 'quick-wins', label: 'Quick wins first', operation: 'reorder' },
      { id: 'stuck', label: "I'm stuck", operation: 'reorder' },
      { id: 'life-admin', label: 'Life admin & household', operation: 'reorder' },
      { id: 'add', label: '+ Add', operation: 'reorder', payload: null },
    ],
  };

  it('takes each label from the file verbatim, including the one that had drifted', () => {
    expect(presetsFromLive(live).map((p) => p.label)).toEqual([
      'Low energy today',
      'Quick wins first', // NOT the hardcoded 'Quick wins only'
      "I'm stuck",
      'Life admin & household',
    ]);
  });

  it('keeps every id exactly as stored, because the server dispatches on it', () => {
    expect(presetsFromLive(live).map((p) => p.id)).toEqual([
      'low-energy',
      'quick-wins',
      'stuck',
      'life-admin',
    ]);
  });

  /*
   * June removed "Add something" from the plan-action row on 2026-07-18 — it was navigation
   * sitting among plan actions, and the Add tab is one tap away. The `add` entry in her file
   * is a UI-only marker with a null payload, so honouring her file must not undo her decision.
   */
  it('leaves the UI-only "add" entry out of the plan-action row', () => {
    expect(presetsFromLive(live).map((p) => p.id)).not.toContain('add');
  });

  it('shows no buttons rather than invented ones when the file has no presets', () => {
    expect(presetsFromLive({ version: 1, presets: [] })).toEqual([]);
    expect(presetsFromLive({})).toEqual([]);
  });

  /*
   * A preset with no id could never be dispatched, and one with no label would render a blank
   * button. Both are dropped rather than shown with a stand-in — a made-up label here is the
   * very defect this change removes.
   */
  it('drops entries that could not work, rather than filling in a stand-in', () => {
    const broken = {
      presets: [
        { id: 'ok', label: 'Fine' },
        { id: '', label: 'No id' },
        { id: 'no-label' },
        { label: 'No id at all' },
      ],
    };
    expect(presetsFromLive(broken)).toEqual([{ id: 'ok', label: 'Fine' }]);
  });
});