/**
 * A work block inside the PRIORITY list (Task 3 of the shape-driven-rendering plan).
 *
 * June's decision (2026-07-18): a block is a numbered row that expands to its arc, collapsed
 * by default — on a fragmented day the point is a short scannable list.
 *
 * Every assertion here is POSITIVE where it can be: it names what must be true. An earlier
 * draft of this task asserted only that a wrong write did NOT happen, which passes just as
 * well against a checkbox wired to nothing at all — the worst outcome available, because it
 * looks live and records nothing.
 *
 * The fixture is the real `seedPlan` block, not an invented one, so the project-prefix test
 * has something to actually stutter with: block id `l3pdzq` resolves in the seed graph to the
 * task "Write response to the commentary" under the project "Cultural Anthropology — reviewer
 * response". The old code rendered exactly that pair; the plan phrasing "Work on the reviewer
 * response" is what must appear instead.
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import type { Plan, PlanArcStep, PlanBlockItem } from '../../../fixtures/index.ts';
import { PriorityList } from '../PriorityList.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

const ARC: PlanArcStep[] = [
  { text: 'Read chapter 2', state: 'here', id: 'l3pdzq' },
  { text: 'Write the summary paragraph', state: 'ahead' },
];

/**
 * The seed plan's real block, re-phrased to the live payload's wording.
 *
 * ⚠ `null` means "no arc", never `undefined`: an `undefined` argument re-triggers the default
 * parameter below, so the no-arc test would silently run WITH the arc and pass for the wrong
 * reason. It did, on the first run.
 */
function block(arc: PlanArcStep[] | null): PlanBlockItem {
  const seeded = freshPlan().blocks[0]?.items[0];
  if (!seeded || seeded.kind !== 'block') {
    throw new Error('seedPlan[0][0] is not a work block — the fixture moved');
  }
  const { arc: _drop, ...rest } = seeded;
  return { ...rest, task: 'Work on IOP and recovery', ...(arc ? { arc } : null) };
}

/**
 * A priority-shaped plan: ONE unlabelled container band holding the block. That container is
 * what `adapt.ts` builds for a priority day, and it is what makes the `0-0` address real.
 */
function blockPlan(arc: PlanArcStep[] | null = ARC): Plan {
  const p = freshPlan();
  return {
    ...p,
    shape: 'priority',
    blocks: [{ label: '', time: '', framing: '', items: [block(arc)] }],
  };
}

function blockCtx(arc: PlanArcStep[] | null = ARC) {
  return ctxWith({}, blockPlan(arc));
}

describe('PriorityList — a block row', () => {
  it('renders the plan phrasing, with no project prefix stuttering in front of it', () => {
    const { ctx } = blockCtx();
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('Work on IOP and recovery')).toBeTruthy();
    // The graph node's own title and its project are what the old path rendered.
    expect(screen.queryByText(/Cultural Anthropology/)).toBeNull();
    expect(screen.queryByText('Write response to the commentary')).toBeNull();
  });

  it('is collapsed until tapped, then shows its arc steps', () => {
    const { ctx, up } = blockCtx();
    render(<PriorityList ctx={ctx} />);
    expect(screen.queryByText('Read chapter 2')).toBeNull();
    fireEvent.click(screen.getByText('Work on IOP and recovery'));
    // Keyed by the block's own id — the same key the schedule view uses, so one block has one
    // expand state across the Schedule/Priority toggle, and a regenerated plan cannot hand that
    // state to whatever item lands in the old slot.
    expect(up).toHaveBeenCalledWith({ blocksOpen: { l3pdzq: true } });
  });

  it('shows the arc steps once the open state is set', () => {
    const { ctx } = ctxWith({ blocksOpen: { l3pdzq: true } }, blockPlan());
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('Read chapter 2')).toBeTruthy();
    expect(screen.getByText('Write the summary paragraph')).toBeTruthy();
  });

  /**
   * ⚠ THE POINT OF THIS FILE: this row and `WorkBlock`'s are the same control in two views. A
   * previous session found them disagreeing about what checking a block means. Both now call
   * `ctx.chunk` with the block's id, and these assertions are written to match `today.test.tsx`
   * line for line so a future divergence fails here.
   */
  it('checking it records a chunk against the block’s own id', () => {
    const { ctx, chunk } = blockCtx();
    render(<PriorityList ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(chunk).toHaveBeenCalledWith('l3pdzq', true);
  });

  it('un-checking a recorded chunk reopens it, by the same id', () => {
    const { ctx, chunk } = ctxWith({ chunked: { l3pdzq: true } }, blockPlan());
    render(<PriorityList ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(chunk).toHaveBeenCalledWith('l3pdzq', false);
  });

  it('renders as checked from the plan’s own record, with no UI state set', () => {
    const p = blockPlan();
    const item = p.blocks[0]!.items[0]!;
    if (item.kind !== 'block') throw new Error('the block row moved');
    item.didChunkToday = true;
    const { ctx } = ctxWith({}, p);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('Work on IOP and recovery').style.textDecoration).toBe('line-through');
  });

  it('leaves the underlying project unfinished — the check is time spent, not a project closed', () => {
    const { ctx, apply, chunk } = blockCtx();
    render(<PriorityList ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    // The one write it makes is the chunk. `apply` is the graph-mutation seam, and a block
    // check must never reach it: `display_grain_design.md` §REVISION §B.
    expect(chunk).toHaveBeenCalledTimes(1);
    expect(apply).not.toHaveBeenCalled();
  });

  it('renders a block with no arc as a bare row with nothing to expand', () => {
    // display_grain_design.md decision 4 — a container project with no discrete tasks is a
    // bare did-a-chunk block. It still renders, and tapping it must not claim an open state.
    const { ctx, up } = blockCtx(null);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('Work on IOP and recovery')).toBeTruthy();
    expect(screen.getByText('1.')).toBeTruthy();
    fireEvent.click(screen.getByText('Work on IOP and recovery'));
    expect(up).not.toHaveBeenCalled();
  });
});
