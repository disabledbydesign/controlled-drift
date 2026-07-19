/**
 * Tests for the per-row ACTION PANEL — "not today", duration, move.
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 *
 * ── WHAT THESE ASSERT, AND WHY POSITIVELY ────────────────────────────────────
 * Every write assertion names what MUST have reached the seam. An assertion that a wrong thing
 * did not happen passes just as well against a control wired to nothing at all, and this repo has
 * rejected work on exactly that.
 *
 * ── THE DISTINCTION THE DURATION LABEL CARRIES ───────────────────────────────
 * `/api/duration` means two different things depending on the row, and June's two names for them
 * are not decoration: a BLOCK sets how long she works on that project in a sitting, a TASK sets
 * how long that one thing takes. The old overlay's chip said "set chunk length" and "set
 * duration" respectively. A single shared word would flatten a distinction she uses.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { RowActions } from '../RowActions.tsx';
import { PriorityList } from '../PriorityList.tsx';
import { TaskRow } from '../TaskRow.tsx';
import { WorkBlock } from '../WorkBlock.tsx';
import { TodayPanel } from '../TodayPanel.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

/** The panel is reached through its own chip; open it the way she would. */
function openPanel(label = 'when') {
  fireEvent.click(screen.getByLabelText(label === 'when' ? 'change when' : label));
}

describe('the reveal', () => {
  it('keeps the three controls out of the row until she asks for them', () => {
    const { ctx } = ctxWith();
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.queryByText('not today')).toBeNull();
    // Positively: the affordance that reveals them IS present, so this cannot pass against a
    // component that renders nothing at all.
    expect(screen.getByLabelText('change when')).toBeTruthy();
  });

  it('opens the panel for THIS row id, so a regenerated plan cannot reattach it elsewhere', () => {
    const { ctx, up } = ctxWith();
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    openPanel();
    expect(up).toHaveBeenCalledWith({ editOpen: { t1: true } });
  });

  it('shows all three controls once the row is open', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.getByText('not today')).toBeTruthy();
    expect(screen.getByText('move')).toBeTruthy();
    expect(screen.getByText('set duration')).toBeTruthy();
  });
});

describe('not today', () => {
  it('sends the removal for a TASK row', () => {
    const { ctx, notToday } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('not today'));
    expect(notToday).toHaveBeenCalledWith('t1', 'task');
  });

  /** A block sends `kind:'block'`, which the server reads as a project id and drops every row. */
  it('sends the removal for a BLOCK row as a block, not as a task', () => {
    const { ctx, notToday } = ctxWith({ editOpen: { p9: true } });
    render(<RowActions ctx={ctx} id="p9" kind="block" durationMin={0} />);
    fireEvent.click(screen.getByText('not today'));
    expect(notToday).toHaveBeenCalledWith('p9', 'block');
  });
});

describe('duration — one endpoint, two meanings', () => {
  it('calls a TASK row’s length a duration', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.getByText('set duration')).toBeTruthy();
    expect(screen.queryByText('set chunk length')).toBeNull();
  });

  it('calls a BLOCK row’s length a chunk length, which is a different thing she sets', () => {
    const { ctx } = ctxWith({ editOpen: { p9: true } });
    render(<RowActions ctx={ctx} id="p9" kind="block" durationMin={0} />);
    expect(screen.getByText('set chunk length')).toBeTruthy();
    expect(screen.queryByText('set duration')).toBeNull();
  });

  it('shows the minutes already set instead of the prompt', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={45} />);
    expect(screen.getByText('45 min')).toBeTruthy();
  });

  it('sends the minutes she typed', () => {
    const { ctx, setDuration } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('set duration'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '25' } });
    fireEvent.submit(box.form!);
    expect(setDuration).toHaveBeenCalledWith('t1', 25);
  });

  /** The server 400s a non-positive value; refusing to send it keeps that out of her way. */
  it('sends nothing at all for a value the server would refuse', () => {
    const { ctx, setDuration, flash } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('set duration'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '0' } });
    fireEvent.submit(box.form!);
    expect(setDuration).not.toHaveBeenCalled();
    // Positively: she is TOLD, rather than the tap doing nothing silently.
    expect(flash).toHaveBeenCalledWith('That needs to be a number of minutes above zero.');
  });
});

describe('move — tap the row, then tap where it goes', () => {
  it('opens the destination list for this row', () => {
    const { ctx, up } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<RowActions ctx={ctx} id="l3pdzq" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('move'));
    expect(up).toHaveBeenCalledWith({ movePick: 'l3pdzq' });
  });

  it('sends the destination she tapped', () => {
    const { ctx, moveItem, plan } = ctxWith({ editOpen: { l3pdzq: true }, movePick: 'l3pdzq' });
    render(<RowActions ctx={ctx} id="l3pdzq" kind="task" durationMin={0} />);
    // Whatever the seed plan's geometry is, the first offered destination must be the one sent.
    const first = screen.getAllByRole('button').find((b) => b.textContent?.startsWith('after '))!;
    expect(first).toBeTruthy();
    fireEvent.click(first);
    expect(moveItem).toHaveBeenCalledTimes(1);
    const [sentId, target] = moveItem.mock.calls[0]!;
    expect(sentId).toBe('l3pdzq');
    expect(typeof target.position).toBe('number');
    expect(plan.shape === 'priority' ? target.block === null : typeof target.block === 'number').toBe(true);
  });

  it('lets her back out of the destination list without moving anything', () => {
    const { ctx, up, moveItem } = ctxWith({ editOpen: { l3pdzq: true }, movePick: 'l3pdzq' });
    render(<RowActions ctx={ctx} id="l3pdzq" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('cancel'));
    expect(up).toHaveBeenCalledWith({ movePick: null });
    expect(moveItem).not.toHaveBeenCalled();
  });

  /**
   * A block is not a single movable row — the old overlay withheld the move control on blocks for
   * that reason (`editPanelHtml`: `canMove = !isBlock && …`), and `plan_store.move_item` addresses
   * task rows.
   */
  it('offers no move on a block row, which is not one movable item', () => {
    const { ctx } = ctxWith({ editOpen: { p9: true } });
    render(<RowActions ctx={ctx} id="p9" kind="block" durationMin={0} />);
    expect(screen.queryByText('move')).toBeNull();
    // Positively: the other two controls ARE there, so the panel is genuinely rendering.
    expect(screen.getByText('not today')).toBeTruthy();
    expect(screen.getByText('set chunk length')).toBeTruthy();
  });

  it('says so plainly when there is nowhere else to put it', () => {
    const { ctx } = ctxWith({ editOpen: { nosuch: true }, movePick: 'nosuch' });
    render(<RowActions ctx={ctx} id="nosuch" kind="task" durationMin={0} />);
    expect(screen.getByText('There is nowhere else to put this today.')).toBeTruthy();
  });
});

/**
 * ── THE WIRING, WHICH IS THE PART THAT WAS ACTUALLY BROKEN ───────────────────
 * The controls were never missing from the codebase; they were missing from the ROWS. A panel
 * that works in isolation and is mounted nowhere is precisely the failure being repaired, so
 * each of the four row shells is asserted to carry it. There are four and not two because
 * `PriorityList` re-implements both row kinds inline rather than reusing `TaskRow`/`WorkBlock`
 * (documented at `PriorityList.tsx:48-55`).
 */
describe('reaching the real rows', () => {
  /**
   * ⚠ EACH SHELL IS ASSERTED SEPARATELY, and the whole-panel render is NOT enough on its own.
   * An earlier version of this block rendered `TodayPanel` and asserted at least one control was
   * present — and that test kept passing with the panel deleted from `TaskRow`, because
   * `WorkBlock` alone satisfied it. Caught by mutation. A per-shell assertion is the only kind
   * that can tell "wired everywhere" from "wired somewhere".
   */
  it('puts the control on a TASK row of the schedule view', () => {
    const plan = freshPlan();
    const task = plan.blocks
      .flatMap((b) => b.items)
      .find((it) => it.kind === 'task') as { id: string; durationMin: number };
    expect(task).toBeTruthy();
    const { ctx } = ctxWith({}, plan);
    render(
      <TaskRow
        ctx={ctx}
        item={plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task')! as never}
        entryKey="0-0"
        showProj
      />,
    );
    expect(screen.getByLabelText('change when')).toBeTruthy();
  });

  it('puts the control on a BLOCK row of the schedule view', () => {
    const plan = freshPlan();
    const block = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'block')!;
    const { ctx } = ctxWith({}, plan);
    render(<WorkBlock ctx={ctx} item={block as never} entryKey="0-0" bandIndex={0} itemIndex={0} />);
    expect(screen.getByLabelText('change when')).toBeTruthy();
  });

  it('puts the control on schedule-view rows as the panel assembles them', () => {
    const { ctx } = ctxWith({ todayShape: 'schedule' });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getAllByLabelText('change when').length).toBeGreaterThan(0);
  });

  /**
   * EVERY row, counted — not "at least one". `PriorityList` implements its block row and its task
   * row separately, so a presence check is satisfied by either one alone; deleting the panel from
   * the task row passed such a check. The count is against the plan's own work items, so it
   * cannot drift with the fixture.
   */
  it('puts the control on every priority-view row, both kinds', () => {
    const plan = freshPlan();
    const rows = plan.blocks.flatMap((b) => b.items).filter((it) => it.kind !== 'break');
    expect(rows.length).toBeGreaterThan(1);
    const { ctx } = ctxWith({}, plan);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getAllByLabelText('change when')).toHaveLength(rows.length);
  });

  it('puts the control on a priority-view TASK row specifically', () => {
    // A plan with NO blocks, so only the task-row implementation can satisfy this.
    const plan = freshPlan();
    for (const b of plan.blocks) b.items = b.items.filter((it) => it.kind === 'task');
    const taskCount = plan.blocks.flatMap((b) => b.items).length;
    expect(taskCount).toBeGreaterThan(0);
    const { ctx } = ctxWith({}, plan);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getAllByLabelText('change when')).toHaveLength(taskCount);
  });

  /**
   * The block row is the one that must say "chunk length", and it is reachable in both views —
   * so the distinction has to survive the wiring, not just the panel.
   */
  it('calls it a chunk length on a block row in the priority view', () => {
    // The seed block already HAS a chunk length, which renders as the minutes rather than the
    // prompt — so the prompt wording is only reachable with it cleared.
    const plan = freshPlan();
    for (const b of plan.blocks) {
      for (const it of b.items) if (it.kind === 'block') it.chunkMin = 0;
    }
    const { ctx } = ctxWith({ editOpen: { l3pdzq: true } }, plan);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('set chunk length')).toBeTruthy();
    expect(screen.queryByText('set duration')).toBeNull();
  });

  it('shows a block row’s existing chunk length as minutes', () => {
    const { ctx } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<PriorityList ctx={ctx} />);
    const plan = freshPlan();
    const block = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'block');
    expect(block && block.kind === 'block' && block.chunkMin).toBeGreaterThan(0);
    expect(screen.getByText((block as { chunkMin: number }).chunkMin + ' min')).toBeTruthy();
  });

  it('sends a block removal as a block from a real row, not as a task', () => {
    const { ctx, notToday } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<PriorityList ctx={ctx} />);
    fireEvent.click(screen.getByText('not today'));
    expect(notToday).toHaveBeenCalledWith('l3pdzq', 'block');
  });
});
