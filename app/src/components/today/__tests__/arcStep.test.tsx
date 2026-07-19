/**
 * THE ARC STEP CHECKBOX — the same control in two views, and what it must send.
 *
 * `ArcStep` renders inside BOTH `WorkBlock` (the schedule day) and `PriorityList` (the
 * fragmented day). That is the same two-view arrangement the block header check had, and a
 * previous session found those two disagreeing about what a check meant. So both are driven
 * here, with matching assertions, and a future divergence fails in this file.
 *
 * What it used to do: `ctx.applyPlan(toggleArcStep(...))`. `applyPlan` sets local state and
 * raises a toast — no network call is reachable through it, because `PlanResult` has no
 * `write`. June tapped a step, read "Nice — one down", and it was gone on reload.
 *
 * ⚠ THE STEP'S OWN ID IS THE POINT. Each arc step carries a REAL Anytype task id (verified
 * against her live plan 2026-07-19: every step of all three arc-carrying items). Sending the
 * BLOCK's id instead would route through `plan_store.is_block_item` server-side and log a work
 * chunk rather than completing her task — the right-looking wrong write.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import type { Plan, PlanArcStep, PlanBlockItem } from '../../../fixtures/index.ts';
import { PriorityList } from '../PriorityList.tsx';
import { WorkBlock } from '../WorkBlock.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

/** The block's id, and two step ids that are deliberately NOT it. */
const BLOCK_ID = 'l3pdzq';
const STEP_HERE = 'bafystep-here';
const STEP_AHEAD = 'bafystep-ahead';

const ARC: PlanArcStep[] = [
  { text: 'Read chapter 2', state: 'here', id: STEP_HERE },
  { text: 'Write the summary paragraph', state: 'ahead', id: STEP_AHEAD },
];

function block(arc: PlanArcStep[]): PlanBlockItem {
  const seeded = freshPlan().blocks[0]?.items[0];
  if (!seeded || seeded.kind !== 'block') {
    throw new Error('seedPlan[0][0] is not a work block — the fixture moved');
  }
  const { arc: _drop, ...rest } = seeded;
  return { ...rest, task: 'Work on IOP and recovery', arc };
}

function blockPlan(arc: PlanArcStep[] = ARC): Plan {
  const p = freshPlan();
  return {
    ...p,
    shape: 'priority',
    blocks: [{ label: '', time: '', framing: '', items: [block(arc)] }],
  };
}

describe('an arc step in the priority list', () => {
  it('sends the STEP’s own task id, at the address it really sits at', () => {
    const { ctx, completeStep } = ctxWith({ blocksOpen: { [BLOCK_ID]: true } }, blockPlan());
    render(<PriorityList ctx={ctx} />);

    // The block header's own check is `mark done` too, so the steps are addressed by their text.
    fireEvent.click(screen.getByText('Read chapter 2').parentElement!.querySelector('button')!);

    expect(completeStep).toHaveBeenCalledWith(
      { id: STEP_HERE, bandIndex: 0, itemIndex: 0, stepIndex: 0 },
      true,
    );
  });

  it('sends the second step’s id for the second step, not the first one’s', () => {
    const { ctx, completeStep } = ctxWith({ blocksOpen: { [BLOCK_ID]: true } }, blockPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(
      screen.getByText('Write the summary paragraph').parentElement!.querySelector('button')!,
    );

    expect(completeStep).toHaveBeenCalledWith(
      { id: STEP_AHEAD, bandIndex: 0, itemIndex: 0, stepIndex: 1 },
      true,
    );
  });

  it('asks to REOPEN a step that is already done', () => {
    const done: PlanArcStep[] = [{ text: 'Read chapter 2', state: 'done', id: STEP_HERE }];
    const { ctx, completeStep } = ctxWith({ blocksOpen: { [BLOCK_ID]: true } }, blockPlan(done));
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getByText('Read chapter 2').parentElement!.querySelector('button')!);

    expect(completeStep).toHaveBeenCalledWith(
      { id: STEP_HERE, bandIndex: 0, itemIndex: 0, stepIndex: 0 },
      false,
    );
  });

  it('does not route the step through the block’s local plan seam', () => {
    const { ctx, completeStep, applyPlan, chunk } = ctxWith(
      { blocksOpen: { [BLOCK_ID]: true } },
      blockPlan(),
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getByText('Read chapter 2').parentElement!.querySelector('button')!);

    // Asserted ALONGSIDE the positive call, so it cannot pass against a dead checkbox.
    expect(completeStep).toHaveBeenCalledTimes(1);
    // `applyPlan` writes local state only. `chunk` would log a work chunk against the BLOCK.
    expect(applyPlan).not.toHaveBeenCalled();
    expect(chunk).not.toHaveBeenCalled();
  });
});

describe('the same step in the schedule view', () => {
  it('sends the identical call, so the two views cannot disagree', () => {
    const plan = blockPlan();
    const { ctx, completeStep } = ctxWith({ blocksOpen: { [BLOCK_ID]: true } }, plan);
    const item = plan.blocks[0]!.items[0] as PlanBlockItem;
    render(<WorkBlock ctx={ctx} item={item} bandIndex={0} itemIndex={0} entryKey="0-0" />);

    fireEvent.click(screen.getByText('Read chapter 2').parentElement!.querySelector('button')!);

    expect(completeStep).toHaveBeenCalledWith(
      { id: STEP_HERE, bandIndex: 0, itemIndex: 0, stepIndex: 0 },
      true,
    );
  });
});
