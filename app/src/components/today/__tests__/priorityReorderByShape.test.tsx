/**
 * THE ▲/▼ CONTROLS HAVE TO ROUTE BY THE PLAN'S SHAPE.
 *
 * Live-verified against June's real plan, 2026-07-20: she pressed ▲/▼ in the Priority view, the
 * row moved on screen, the app posted `/api/plan/priority-order`, the server answered 400, the app
 * said NOTHING, and her ordering reverted on the next load.
 *
 * Two causes. The first — empty and duplicate ids in the payload — was fixed in 4bc94b9. The
 * second is the subject of this file: `plan_store.set_priority_order` raises `LookupError` for a
 * CLOCK-SHAPE plan, deliberately, because a clock-shape day orders its rows under `blocks[]` and
 * has no flat ranking to store. Her plan that day was clock-shape. So the endpoint could not have
 * accepted the request no matter what was in it.
 *
 * June's ruling on what the Priority toggle should show on a timed day: "the same list as the
 * clock times, but as a list rather than a schedule with clock times." Same rows, same order. She
 * did not design a ranking for a timed day, and none is invented here.
 *
 * WHAT THESE TESTS PIN DOWN, all asserted POSITIVELY — each names the call that must HAPPEN:
 *   1. a clock-shape nudge calls `ctx.moveItem` with the id and the position for that slot
 *   2. moving up into the top of a band sends that band's first position
 *   3. a row in another band lands in the band it is nudged into
 *   4. a clock-shape day shows the PLAN's order, even with a stale fragmented-day ranking in `ui`
 *   5. a row the server would refuse (a fixed-time appointment) is REFUSED IN WORDS, and the
 *      words say her ordering did not change
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers —
 * `afterEach(cleanup)` is explicit or renders accumulate and every query finds several.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import type { Plan } from '../../../fixtures/index.ts';
import { PriorityList } from '../PriorityList.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

vi.mock('../../../api/planRow.ts', async () => {
  const real = await vi.importActual<typeof import('../../../api/planRow.ts')>(
    '../../../api/planRow.ts',
  );
  return {
    ...real,
    savePriorityOrder: vi.fn(async () => ({ kind: 'saved', plan: null })),
    readPriorityOrder: vi.fn(async () => null),
  };
});

import { readPriorityOrder, savePriorityOrder } from '../../../api/planRow.ts';

const saveMock = vi.mocked(savePriorityOrder);
const readMock = vi.mocked(readPriorityOrder);

afterEach(cleanup);
beforeEach(() => {
  saveMock.mockClear();
  readMock.mockClear();
});

/**
 * The seed plan is already clock-shape (`shape:'schedule'`), which is what `adapt.ts` normalizes
 * the server's `"clock"` to. Its rendered rows, breaks dropped, are:
 *
 *   0 l3pdzq  block, Morning   (band 0, server position 0)
 *   1 kt4i6q  task,  Morning   (band 0, server position 1)
 *   2 ieshky  task,  Afternoon (band 2, server position 0)
 *   3 fwjisq  task,  Afternoon (band 2, server position 1)
 *   4 4r3464  block, Afternoon (band 2, server position 2)
 */
function clockPlan(): Plan {
  return freshPlan();
}

const ROWS = ['l3pdzq', 'kt4i6q', 'ieshky', 'fwjisq', '4r3464'];

describe('a clock-shape day nudges the row through /api/task/move', () => {
  it('sends the row and the position of the slot below its neighbour', () => {
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(moveItem).toHaveBeenCalledTimes(1);
    expect(moveItem).toHaveBeenCalledWith('l3pdzq', { block: 0, position: 1 });
  });

  it('does NOT route a timed day to the fragmented-day ranking endpoint', async () => {
    const { ctx, moveItem, up } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(moveItem).toHaveBeenCalledTimes(1));
    expect(saveMock).not.toHaveBeenCalled();
    // Nor is a local ranking written: `ui.priOrder` is a fragmented-day value and a timed day
    // does not have one. What changes the order is the plan the server sends back.
    expect(up).not.toHaveBeenCalled();
  });

  it('moving up into the top of the list sends that band’s first position', () => {
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    // Row 1 (kt4i6q) moving up passes row 0, which is the first row of band 0.
    fireEvent.click(screen.getAllByLabelText('move up')[1]!);

    expect(moveItem).toHaveBeenCalledTimes(1);
    expect(moveItem).toHaveBeenCalledWith('kt4i6q', { block: 0, position: 0 });
  });

  it('lands in the band it is nudged into, not the one it came from', () => {
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    // Row 2 (ieshky, Afternoon) moving up passes row 1 (kt4i6q, Morning), so it lands in Morning
    // immediately after it — server position 1 in band 0.
    fireEvent.click(screen.getAllByLabelText('move up')[2]!);

    expect(moveItem).toHaveBeenCalledTimes(1);
    expect(moveItem).toHaveBeenCalledWith('ieshky', { block: 0, position: 1 });
  });

  it('sends a target with no target_block key of its own to omit — block is always a number here', () => {
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    const target = moveItem.mock.calls[0]![1] as { block: number | null; position: number };
    // `Object.keys`, not a `toHaveBeenCalledWith` shape: deep equality treats an explicit
    // `undefined` as an absent key, so a target that had lost `block` would still match.
    expect(Object.keys(target).sort()).toEqual(['block', 'position']);
    expect(typeof target.block).toBe('number');
  });

  it('sends nothing when the nudge would run off the end of the list', () => {
    const { ctx, moveItem, fail } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move up')[0]!);

    expect(moveItem).not.toHaveBeenCalled();
    expect(fail).not.toHaveBeenCalled();
  });
});

describe('a clock-shape day shows the plan’s own order', () => {
  it('ignores a stale fragmented-day ranking left in ui', () => {
    const stale = [...ROWS].reverse();
    const { ctx, moveItem } = ctxWith(
      { todayShape: 'priority', priOrder: stale },
      clockPlan(),
    );
    render(<PriorityList ctx={ctx} />);

    // If the stale ranking were applied, the first row would be `4r3464`. It is the plan's own
    // first row that the first control moves.
    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(moveItem).toHaveBeenCalledWith('l3pdzq', { block: 0, position: 1 });
  });

  it('does not spend a read on a ranking it will not apply', async () => {
    const { ctx } = ctxWith({ todayShape: 'priority' }, clockPlan());
    render(<PriorityList ctx={ctx} />);

    await waitFor(() => expect(screen.getAllByLabelText('move down')).toHaveLength(ROWS.length));
    expect(readMock).not.toHaveBeenCalled();
  });
});

describe('a nudge the server would refuse is refused IN WORDS', () => {
  /**
   * `planFromLive` folds appointments into the front of `blocks[0]` as ordinary task rows, but the
   * server keeps them in their own key and never indexes them — so every position offered for one
   * can only fail. `apptCount` is the only surviving trace of which rows they are.
   */
  it('tells her a fixed-time row did not move, and that her ordering did not change', () => {
    const { ctx, fail, moveItem } = ctxWith(
      { todayShape: 'priority' },
      { ...clockPlan(), apptCount: 1 },
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(fail).toHaveBeenCalledTimes(1);
    const msg = String(fail.mock.calls[0]![0]);
    expect(msg).toContain('fixed time');
    expect(msg).toContain('your ordering did not change');
    // The refusal is the whole outcome: nothing was sent, so nothing can revert underneath her.
    expect(moveItem).not.toHaveBeenCalled();
    expect(saveMock).not.toHaveBeenCalled();
  });

  it('names the row it refused, so the failure is diagnosable afterwards', () => {
    const { ctx, fail } = ctxWith({ todayShape: 'priority' }, { ...clockPlan(), apptCount: 1 });
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(fail.mock.calls[0]![1]).toBe('l3pdzq');
  });

  it('reports it as a FAILURE, never as a flash — a flash is the success signal', () => {
    const { ctx, fail, flash } = ctxWith(
      { todayShape: 'priority' },
      { ...clockPlan(), apptCount: 1 },
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(fail).toHaveBeenCalledTimes(1);
    expect(flash).not.toHaveBeenCalled();
  });
});

describe('a fragmented day still ranks', () => {
  /** The regression guard: routing by shape must not take the ranking away from the day that has one. */
  it('sends the id ordering to the ranking endpoint on a priority-shape plan', async () => {
    const p = freshPlan();
    const rows = p.blocks.flatMap((b) => b.items).filter((it) => it.kind === 'task');
    const priority: Plan = {
      ...p,
      shape: 'priority',
      blocks: [{ label: '', time: '', framing: '', items: rows.slice(0, 3) }],
    };
    const ids = rows.slice(0, 3).map((it) => (it.kind === 'task' ? it.id : ''));
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority' }, priority);
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    expect(saveMock.mock.calls[0]![0]).toEqual([ids[1], ids[0], ids[2]]);
    expect(moveItem).not.toHaveBeenCalled();
  });
});
