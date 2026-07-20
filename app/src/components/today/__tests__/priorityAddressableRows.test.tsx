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

  /**
   * ⚠ EXPECTATION CHANGED 2026-07-20, and the old one encoded the defect.
   *
   * It read `['bafyrei-not-in-this-graph', ids[0], ids[1], ids[2]]` — the first row swapping with
   * the row NOBODY CAN SEE. On screen that is no change at all: the visible list reads the same
   * before and after, while the save fires and reports success. A control claiming a success she
   * cannot perceive is the same broken promise as one that silently fails.
   *
   * The nudge now steps to the next VISIBLE row, so `ids[0]` and `ids[1]` trade places and she
   * watches it happen. The unrenderable row keeps its own slot in the ranking — which is what this
   * test is named for, and it still holds: it is still in the payload, still second.
   */
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
      ids[1],
      'bafyrei-not-in-this-graph',
      ids[0],
      ids[2],
    ]);
  });

  /**
   * THE SAME NUDGE, READ AS SHE READS IT. The assertion above is about the wire; this one is about
   * the screen, and it is the half that was missing — the wire payload changed in the broken build
   * too, which is exactly why the defect survived review.
   */
  it('MOVES A ROW SHE CAN SEE when the next row in the ranking renders nothing', () => {
    const rows = realRows();
    /**
     * The words on each rendered row line, top to bottom, WITHOUT the gutter number — the number
     * is positional, so leaving it in would make every row differ from every row and the
     * comparison below would pass whatever happened.
     */
    const lines = () =>
      Array.from(document.querySelectorAll('[data-row-line="1"]')).map((el) =>
        (el.textContent ?? '').replace(/^\d+\./, ''),
      );
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, UNRESOLVABLE, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    const before = lines();
    expect(before).toHaveLength(3);
    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    // `up` is a spy, so the component does not re-render itself — the new ranking is read off the
    // call and rendered back, which is what the shell does with it.
    const next = (ctx.up as unknown as { mock: { calls: [{ priOrder: string[] }][] } }).mock
      .calls[0]![0].priOrder;
    cleanup();
    const { ctx: ctx2 } = ctxWith(
      { todayShape: 'priority', priOrder: next },
      priorityPlan([rows[0]!, UNRESOLVABLE, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx2} />);

    // Three rows render either way; what must change is WHICH ROW READS FIRST. Named positively:
    // the row that was second is now first, and the one that was first is now second.
    expect(renderedNumbers()).toEqual(['1.', '2.', '3.']);
    const after = lines();
    expect(after[0]).toBe(before[1]);
    expect(after[1]).toBe(before[0]);
    expect(after[2]).toBe(before[2]);
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

/**
 * ── WHEN THE ORDER DOES NOT SAVE, THE LOG MUST NAME THE ROW SHE MOVED ────────
 *
 * `ctx.fail` writes to `corrections_log` through `POST /api/log/correction`, and its second
 * argument is the row the entry is ABOUT. The handler read `a[i]` — but `a` had already been
 * swapped in place three lines earlier, so `a[i]` was by then the NEIGHBOUR. Every unsaved reorder
 * was therefore recorded against a row she had not touched, and the log pointed at the wrong
 * object for anyone reading it back.
 *
 * Asserted positively on the id the log must carry, not on the neighbour's absence.
 */
describe('a reorder that does not save is logged against the row she moved', () => {
  it('names the MOVED row, not the neighbour it changed places with', async () => {
    saveMock.mockResolvedValue({ kind: 'failed', error: 'the server said no' });
    const ids = realIds();
    const rows = realRows();
    const { ctx, fail } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, rows[1]!, rows[2]!]),
    );
    render(<PriorityList ctx={ctx} />);

    // The first row moves DOWN, so it and the second row trade places.
    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(fail).toHaveBeenCalledTimes(1));
    expect(fail.mock.calls[0]![1]).toBe(ids[0]);
    // And she is told plainly that it will not be there next time — no metaphors, and the
    // server's own words are carried through rather than replaced.
    expect(String(fail.mock.calls[0]![0])).toContain('did not save');
    expect(String(fail.mock.calls[0]![0])).toContain('the server said no');
  });
});

/**
 * ── AN ARROW MUST LOOK LIKE WHAT IT CAN DO ───────────────────────────────────
 *
 * The ▲▼ unavailable styling tested `i === 0` and `i === order.length - 1`, which are positions in
 * `order` — a list that includes rows the graph cannot resolve and which therefore render nothing.
 * So when the ranking ENDED with such a row, the last row she could see showed a ▼ styled as
 * available with nothing below it to move past. Tapping it did nothing and said nothing.
 *
 * Both halves are pinned here: how the control looks, and what it says when she presses it.
 */
describe('the last row she can see is shown as the last row', () => {
  const lastVisibleDown = () => screen.getAllByLabelText('move down')[1]!;

  it('styles the last VISIBLE row’s ▼ as unavailable, not the last entry in the ranking', () => {
    const rows = realRows();
    const { ctx } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, rows[1]!, UNRESOLVABLE]),
    );
    render(<PriorityList ctx={ctx} />);

    // Two rows render; the second is the last one she can see.
    expect(screen.getAllByLabelText('move down')).toHaveLength(2);
    expect(lastVisibleDown().style.cursor).toBe('default');
    // And the first row's ▼ is still live, so this cannot pass against a list that disables all.
    expect(screen.getAllByLabelText('move down')[0]!.style.cursor).toBe('pointer');
  });

  it('says out loud that the row is already last, and saves nothing', async () => {
    const rows = realRows();
    const { ctx, notice } = ctxWith(
      { todayShape: 'priority' },
      priorityPlan([rows[0]!, rows[1]!, UNRESOLVABLE]),
    );
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(lastVisibleDown());

    expect(notice).toHaveBeenCalledTimes(1);
    const [msg, , hold] = notice.mock.calls[0]!;
    expect(String(msg)).toContain('already last');
    expect(String(msg)).toContain('your ordering did not change');
    // It HOLDS: nothing on screen changed, so no control is carrying the message for her.
    expect(hold).toBe(true);
    expect(saveMock).not.toHaveBeenCalled();
  });
});
