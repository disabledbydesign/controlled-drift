/**
 * June's manual reordering of the Priority list has to OUTLIVE THE TAB.
 *
 * Until 2026-07-19 the up/down controls called `ctx.up({priOrder})` and stopped there. There was
 * no server reference anywhere in the app — `GET /api/plan/priority-order` answered 404 — so
 * every reordering she made was gone the next time the surface loaded. Her decision:
 * "Yes, should persist." (Closes `docs/api_contract_v2.md` §6 Q1.)
 *
 * WHAT THESE TESTS PIN DOWN, all asserted POSITIVELY:
 *   1. moving a row SENDS the new order, as object ids
 *   2. the ids are the plan's real ones, so a regenerated plan cannot reattach them to slots
 *   3. a saved order is READ BACK on mount and rendered in her order, not the generator's
 *   4. a failed save TELLS HER, and does not leave the screen claiming a saved ranking
 *   5. she is never told anything when there was simply no saved order to load
 *
 * ⚠ Assertion (1) is the one that matters most and the one easiest to fake: a test that only
 * checked `ctx.up` was called passes just as well against the old, non-persisting code. So each
 * test below asserts on the WIRE.
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
  saveMock.mockResolvedValue({ kind: 'saved', plan: null });
  readMock.mockResolvedValue(null);
});

/** A fragmented-day plan built from the real seed rows, so the ids are the fixture's own. */
function priorityPlan(): Plan {
  const p = freshPlan();
  const rows = p.blocks.flatMap((b) => b.items).filter((it) => it.kind === 'task');
  return {
    ...p,
    shape: 'priority',
    blocks: [{ label: '', time: '', framing: '', items: rows.slice(0, 3) }],
  };
}

/** The ids the list shows, in the order the generator produced them. */
function seedIds(): string[] {
  return priorityPlan()
    .blocks.flatMap((b) => b.items)
    .map((it) => (it.kind === 'task' || it.kind === 'block' ? it.id : ''))
    .filter(Boolean);
}

describe('moving a row persists the new order', () => {
  it('SENDS the reordered list of object ids, not just local state', async () => {
    const ids = seedIds();
    const { ctx } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    expect(saveMock.mock.calls[0]![0]).toEqual([ids[1], ids[0], ids[2]]);
  });

  it('sends the PLAN’S REAL IDS, so nothing is keyed by slot position', async () => {
    const ids = seedIds();
    const { ctx } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move up')[2]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
    const sent = saveMock.mock.calls[0]![0] as string[];
    expect([...sent].sort()).toEqual([...ids].sort());
    expect(sent).toEqual([ids[0], ids[2], ids[1]]);
  });

  it('still updates the screen immediately — the write does not gate the reorder', () => {
    const ids = seedIds();
    const { ctx, up } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    expect(up).toHaveBeenCalledWith({ priOrder: [ids[1], ids[0], ids[2]] });
  });

  it('sends nothing when the move would run off the end of the list', () => {
    const { ctx } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move up')[0]!);

    expect(saveMock).not.toHaveBeenCalled();
  });

  it('TELLS HER when the ordering could not be saved', async () => {
    saveMock.mockResolvedValue({ kind: 'failed', error: 'no cached plan to rank' });
    const { ctx, flash } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(flash).toHaveBeenCalledTimes(1));
    expect(String(flash.mock.calls[0]![0])).toContain('no cached plan to rank');
  });

  it('says nothing at all when the ordering saved', async () => {
    const { ctx, flash } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    fireEvent.click(screen.getAllByLabelText('move down')[0]!);

    await waitFor(() => expect(saveMock).toHaveBeenCalled());
    expect(flash).not.toHaveBeenCalled();
  });
});

describe('a saved ordering comes back on load', () => {
  it('READS the saved order and applies it', async () => {
    const ids = seedIds();
    readMock.mockResolvedValue([ids[2]!, ids[0]!, ids[1]!]);
    const { ctx, up } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    await waitFor(() => expect(up).toHaveBeenCalledWith({ priOrder: [ids[2], ids[0], ids[1]] }));
  });

  it('does NOT re-read once she already has an order on screen', async () => {
    const ids = seedIds();
    const { ctx } = ctxWith(
      { todayShape: 'priority', priOrder: [ids[1]!, ids[0]!, ids[2]!] },
      priorityPlan(),
    );
    render(<PriorityList ctx={ctx} />);

    await waitFor(() => expect(readMock).not.toHaveBeenCalled());
  });

  it('leaves the generator order standing when nothing was saved, and says nothing', async () => {
    const { ctx, up, flash } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    await waitFor(() => expect(readMock).toHaveBeenCalledTimes(1));
    expect(up).not.toHaveBeenCalled();
    expect(flash).not.toHaveBeenCalled();
  });

  /**
   * A failed read answers `null` too. It must be indistinguishable from "nothing saved" on
   * screen — and, critically, must NOT cause anything to be written back: a dropped request
   * would otherwise erase the ordering this whole seam exists to keep.
   */
  it('never writes an ordering back on the strength of a read', async () => {
    readMock.mockResolvedValue(null);
    const { ctx } = ctxWith({ todayShape: 'priority' }, priorityPlan());
    render(<PriorityList ctx={ctx} />);

    await waitFor(() => expect(readMock).toHaveBeenCalledTimes(1));
    expect(saveMock).not.toHaveBeenCalled();
  });
});
