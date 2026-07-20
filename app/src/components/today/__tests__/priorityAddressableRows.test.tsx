/**
 * A ROW THE SERVER CANNOT ADDRESS MUST NOT BE IN THE RANKING SHE SENDS.
 *
 * Live-verified 2026-07-20 against June's real plan. Her Priority list sent this:
 *   {"order":["bafyreie47nri7…","bafyreie7xh5td…","","bafyreie47nri7…","bafyreihsi3mak…","…",""]}
 * Two empty strings and a repeated id. `POST /api/plan/priority-order` answered 400 for the
 * WHOLE request, so nothing was saved — and because the screen had already moved the row, she
 * saw her reordering succeed and then quietly revert on the next load. The failure message never
 * reached her: a control claiming a success it did not earn, which is the one thing this surface
 * exists to stop.
 *
 * Where the empty strings came from: an anchor the generator writes with no id ("Lunch", "Rest
 * or light activity") is not a `break`, so `addressedWorkItems` kept it, and it entered `order`
 * as `''`. It never rendered — `node()` cannot resolve `''` — so nothing on screen showed her
 * that the list held rows she could not see.
 *
 * WHAT THESE PIN DOWN, asserted POSITIVELY — each names the exact ids the wire MUST carry, in
 * order. "Does not contain an empty string" would also pass against a button wired to nothing:
 *   1. the ranking sent is exactly the addressable rows, in her order
 *   2. an id named twice is ranked once
 *   3. the numbers she reads run 1, 2, 3 with no gaps, counting only rows that rendered
 *   4. a row that cannot render still keeps its place in the saved ranking
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers —
 * `afterEach(cleanup)` is explicit or renders accumulate and every query finds several.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import type { Plan, PlanItem } from '../../../fixtures/index.ts';
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
  saveMock.mockResolvedValue({ kind: 'saved', plan: null });
  readMock.mockResolvedValue(null);
});

/** Three real seed task rows — ids the graph can resolve, so they render. */
function realRows(): PlanItem[] {
  return freshPlan()
    .blocks.flatMap((b) => b.items)
    .filter((it) => it.kind === 'task')
    .slice(0, 3);
}

function realIds(): string[] {
  return realRows().map((it) => (it as { id: string }).id);
}

/**
 * A fixed anchor exactly as `adapt.ts` converts it: NOT a break (it has no `interstitial` flag
 * on the wire), a task row, and carrying no id at all.
 */
const ANCHOR: PlanItem = {
  kind: 'task',
  id: '',
  time: '',
  durationMin: 0,
  why: '',
  task: 'Rest or light activity',
} as PlanItem;

/** A row whose id is real on the server but absent from the loaded graph, so it cannot render. */
const UNRESOLVABLE: PlanItem = {
  kind: 'task',
  id: 'bafyrei-not-in-this-graph',
  time: '',
  durationMin: 0,
  why: '',
  task: 'A task the graph has not loaded',
} as PlanItem;

function priorityPlan(items: PlanItem[]): Plan {
  return { ...freshPlan(), shape: 'priority', blocks: [{ label: '', time: '', framing: '', items }] };
}

/** The numbers actually printed in the gutter, top to bottom. */
function renderedNumbers(): string[] {
  return screen.getAllByText(/^\d+\.$/).map((el) => el.textContent ?? '');
}

describe('the ranking sent to the server holds only addressable rows', () => {
  it('SENDS exactly the three real ids when an id-less anchor sits among them', async () => {
    const ids = realIds();
    const rows = realRows();
    const plan = priorityPlan([rows[0]!, ANCHOR, rows[1]!, rows[2]!]);
    // The anchor really is in the plan — otherwise this test would pass by not exercising it.
    expect(plan.blocks[0]!.items.filter((it) => it.kind === 'task' && it.id === '')).toHaveLength(1);

    const { ctx } = ctxWith({ todayShape: 'priority' }, plan);
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    expect(saveMock.mock.calls[0]![0]).toEqual([ids[1], ids[0], ids[2]]);
  });

  it('RANKS an id named twice exactly once, keeping her first placement of it', async () => {
    const ids = realIds();
    const rows = realRows();
    // Her stored ranking names the first id twice — the duplication seen live.
    const stored = [ids[0]!, ids[1]!, ids[0]!, ids[2]!];
    const { ctx } = ctxWith(
      { todayShape: 'priority', priOrder: stored },
      priorityPlan([rows[0]!, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[2]!);

    // Moving the LAST of three is a no-op, which is only true if the list is three long.
    expect(saveMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);
    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    expect(saveMock.mock.calls[0]![0]).toEqual([ids[1], ids[0], ids[2]]);
  });

  it('keeps a row it cannot render in the ranking, so her placing of it is not discarded', async () => {
    const ids = realIds();
    const rows = realRows();
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, UNRESOLVABLE, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    expect(saveMock.mock.calls[0]![0]).toEqual([
      'bafyrei-not-in-this-graph',
      ids[0],
      ids[1],
      ids[2],
    ]);
  });
});

describe('the numbers she reads count the rows on screen', () => {
  it('runs 1, 2, 3 when a row between them could not be rendered', () => {
    const rows = realRows();
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, UNRESOLVABLE, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    expect(renderedNumbers()).toEqual(['1.', '2.', '3.']);
  });

  it('runs 1, 2, 3 when an id-less anchor sits among the rows', () => {
    const rows = realRows();
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, ANCHOR, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    expect(renderedNumbers()).toEqual(['1.', '2.', '3.']);
  });

  it('numbers a block row in the same run as the task rows around it', () => {
    const p = freshPlan();
    const block = p.blocks.flatMap((b) => b.items).find((it) => it.kind === 'block')!;
    const rows = realRows();
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, block, UNRESOLVABLE, rows[1]!]),
    );
    render(<PriorityList ctx={ctx} />);

    expect(renderedNumbers()).toEqual(['1.', '2.', '3.']);
  });
});
