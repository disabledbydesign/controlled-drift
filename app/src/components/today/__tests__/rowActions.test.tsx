/**
 * Tests for the per-row ACTION PANEL — "not today", duration, move.
 *
 * ── WHY THIS FILE WAS REWRITTEN ──────────────────────────────────────────────
 * The previous version of these tests passed against a build June then used and found HARDER to
 * use than the surface it replaced. Every one of them asserted that a control sent the right
 * request; none of them could see that the control was named something she could not read, that
 * it pushed her whole list around when it opened, or that it offered a list of sentences where
 * she had asked to see a position. So the assertions here are about the four things she ruled on,
 * in the terms she ruled on them:
 *
 *   A1 · the trigger is IN the row, and the panel does not displace anything (`position:absolute`)
 *   A2 · move fills the PLAN with landing slots, above and below alike — no list of text labels
 *   A3 · the desktop drags; the phone does not
 *   A4 · the trigger says `edit`, and the length is LABELLED (`duration: 45 min`), never a bare verb
 *
 * Each of those fails against the build she rejected, which is the point of writing them.
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 *
 * ── THE DISTINCTION THE DURATION LABEL CARRIES ───────────────────────────────
 * `/api/duration` means two different things depending on the row, and June's two names for them
 * are not decoration: a BLOCK sets how long she works on that project in a sitting, a TASK sets
 * how long that one thing takes. A single shared word would flatten a distinction she uses.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { EditChip } from '../../atoms/index.ts';
import { RowActions } from '../RowActions.tsx';
import { PriorityList } from '../PriorityList.tsx';
import { TaskRow } from '../TaskRow.tsx';
import { WorkBlock } from '../WorkBlock.tsx';
import { TodayPanel } from '../TodayPanel.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

/** The panel is reached through its own trigger; open it the way she would. */
function openPanel() {
  fireEvent.click(screen.getByLabelText('edit timing'));
}

/** The floating pane itself, so its positioning can be asserted rather than assumed. */
function panel(): HTMLElement {
  return screen.getByRole('group', { name: 'edit timing' });
}

describe('A4 — the trigger is named the way the old surface named it', () => {
  /**
   * June: *"'when' is a very unclear name for a menu."* The old surface's trigger said `edit`
   * with the title `edit timing` (`docs/overlay_daily.html:2128`); "when" was the rebuild's own
   * invention. This assertion fails against that build.
   */
  it('says edit, not when', () => {
    const { ctx } = ctxWith();
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    const trigger = screen.getByLabelText('edit timing');
    expect(trigger.textContent).toBe('edit');
    expect(trigger.getAttribute('title')).toBe('edit timing');
    expect(screen.queryByText('when')).toBeNull();
  });

  it('keeps the three controls out of the row until she asks for them', () => {
    const { ctx } = ctxWith();
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.queryByText('not today')).toBeNull();
    // Positively: the affordance that reveals them IS present, so this cannot pass against a
    // component that renders nothing at all.
    expect(screen.getByLabelText('edit timing')).toBeTruthy();
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
    expect(screen.getByText('not set')).toBeTruthy();
  });
});

describe('A1 — the panel expands without knocking anything around', () => {
  /**
   * June: *"it should be a drop down menu that is inline — I click on it, and it expands the
   * options (without knocking the other elements around)."*
   *
   * `position:absolute` is what makes that true and is therefore what is asserted: an in-flow
   * panel adds height to the row and pushes every row below it down, which is exactly what she
   * was looking at. Fails against the build she rejected, where the panel was a normal block.
   */
  it('takes the panel out of the row’s flow so the rows below it do not move', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(panel().style.position).toBe('absolute');
  });

  /** Anchored to the trigger's right edge, so on a 392px phone it opens inward, not off-screen. */
  it('anchors the panel under the trigger rather than at the page’s left edge', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(panel().style.right).toBe('0px');
  });

  /**
   * The trigger sits IN the row's own line, as `editChipHtml` did inside `.item-top`.
   *
   * ⚠ This used to anchor the assertion to the row's `EditChip`, which shared the line. That
   * chip is gone from the row (A5), so the anchor is now the row's CHECK — which is
   * unambiguously on the row's own line and is not going anywhere.
   */
  it('puts the trigger on the row’s own line, beside the check', () => {
    const plan = freshPlan();
    const task = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task')!;
    const { ctx } = ctxWith({}, plan);
    render(<TaskRow ctx={ctx} item={task as never} entryKey="0-0" showProj />);
    const trigger = screen.getByLabelText('edit timing');
    const line = trigger.closest('[data-row-line]');
    expect(line).toBeTruthy();
    // Named positively on both sides: the line the trigger is on is the line the check is on.
    expect(line!.contains(screen.getByLabelText('mark done'))).toBe(true);
    expect(line!.textContent).toContain('edit');
  });
});

describe('B2 — a row with no backing object gets no control at all', () => {
  /**
   * `server.py`'s comment on `/api/duration` states the invariant: a generated row (a rest
   * suggestion, the walk) never reaches the endpoint because the surface shows it no control —
   * there is nowhere to persist to. The old surface withheld it the same way (`:2135`).
   * Catching this at write time is too late: by then she has tapped something that could only
   * fail.
   */
  it('renders nothing for an empty id', () => {
    const { ctx } = ctxWith();
    const { container } = render(<RowActions ctx={ctx} id="" kind="task" durationMin={0} />);
    expect(container.innerHTML).toBe('');
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

describe('A4/C — the length is labelled, and honest when unset', () => {
  /**
   * The old panel read `duration:` followed by the value, never a bare verb standing in for a
   * reading (`editPanelHtml`, `:2140-2151`). The rebuild showed `set duration`, which is an
   * instruction where she expected a number. Fails against that build.
   */
  it('labels a TASK row’s length a duration and shows the value beside it', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={45} />);
    expect(screen.getByText('duration:')).toBeTruthy();
    expect(screen.getByText('45 min')).toBeTruthy();
    expect(screen.queryByText('chunk length:')).toBeNull();
  });

  it('labels a BLOCK row’s length a chunk length, which is a different thing she sets', () => {
    const { ctx } = ctxWith({ editOpen: { p9: true } });
    render(<RowActions ctx={ctx} id="p9" kind="block" durationMin={30} />);
    expect(screen.getByText('chunk length:')).toBeTruthy();
    expect(screen.getByText('30 min')).toBeTruthy();
    expect(screen.queryByText('duration:')).toBeNull();
  });

  /**
   * ⚠ THE ONE THAT MATTERS MOST HERE. The duration does not currently arrive for task rows — it
   * is dropped server-side at row assembly, which is another task's fix. Until it does, this must
   * say so rather than show a number that was never set. A fabricated default would read as a
   * decision she made.
   */
  it('says the length is not set rather than showing a number nobody chose', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.getByText('duration:')).toBeTruthy();
    expect(screen.getByText('not set')).toBeTruthy();
  });

  it('sends the minutes she typed', () => {
    const { ctx, setDuration } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('not set'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '25' } });
    fireEvent.submit(box.form!);
    expect(setDuration).toHaveBeenCalledWith('t1', 25);
  });

  /** The server 400s a non-positive value; refusing to send it keeps that out of her way. */
  it('sends nothing at all for a value the server would refuse', () => {
    const { ctx, setDuration, notice } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('not set'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '0' } });
    fireEvent.submit(box.form!);
    expect(setDuration).not.toHaveBeenCalled();
    /**
     * Positively: she is TOLD, rather than the tap doing nothing silently — and told through
     * `notice`, which reaches the bar. This assertion used to name `flash`, and it PASSED while
     * the sentence rendered nowhere at all: `flash` raises a success-kind signal with no node,
     * `present()` answers `inline`, and an inline success with no node to settle on is dropped.
     * The test was green and the screen was silent. Naming the seam that can actually be seen is
     * the whole difference.
     */
    expect(notice).toHaveBeenCalledWith('That needs to be a number of minutes above zero.', 't1');
  });

  /**
   * ── THE ESSENTIAL ONE (June, 2026-07-20) ───────────────────────────────────
   * *"if a change can't be made, the UI content needs to show what's really in the data — that's
   * essential."*
   *
   * She typed `0` over a stored 90, pressed save, and the box went on displaying `0` while the
   * data still said 90. A message would not have fixed that: the screen itself was asserting a
   * number that existed nowhere. So the box must PUT THE STORED VALUE BACK.
   *
   * Asserted on what the input DISPLAYS, positively — not on the absence of a write, which would
   * also pass against a box wired to nothing.
   */
  it('puts the stored minutes back in the box when the value is refused', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={90} />);
    fireEvent.click(screen.getByText('90 min'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '0' } });
    fireEvent.submit(box.form!);
    expect((screen.getByLabelText('minutes') as HTMLInputElement).value).toBe('90');
  });

  /** An unset duration has no stored value to show, so the honest revert is an empty box. */
  it('reverts to an empty box when nothing was stored', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('not set'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '-5' } });
    fireEvent.submit(box.form!);
    expect((screen.getByLabelText('minutes') as HTMLInputElement).value).toBe('');
  });

  /**
   * Her *"a line of text and a red outline or something like that"* — the outline half, and its
   * screen-reader equivalent, because a border colour is no signal at all to a screen reader.
   */
  it('marks the box invalid when the value is refused', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={90} />);
    fireEvent.click(screen.getByText('90 min'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '0' } });
    fireEvent.submit(box.form!);
    expect(screen.getByLabelText('minutes').getAttribute('aria-invalid')).toBe('true');
  });

  /**
   * And it clears the moment she types, because from then on the box is showing her own current
   * input and marking it wrong would be a claim about a value nobody has judged yet.
   */
  it('clears the invalid mark as soon as she types again', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={90} />);
    fireEvent.click(screen.getByText('90 min'));
    const box = screen.getByLabelText('minutes') as HTMLInputElement;
    fireEvent.change(box, { target: { value: '0' } });
    fireEvent.submit(box.form!);
    fireEvent.change(screen.getByLabelText('minutes'), { target: { value: '45' } });
    expect(screen.getByLabelText('minutes').getAttribute('aria-invalid')).toBe(null);
    expect((screen.getByLabelText('minutes') as HTMLInputElement).value).toBe('45');
  });
});

describe('A2 — move shows WHERE things go, in the plan', () => {
  /**
   * June: *"move makes me select where things go using text labels. It should be a visual
   * representation of where things go."* Tapping `move` no longer opens a menu of sentences; it
   * puts the plan into a placement mode. Both halves are asserted, because the first alone would
   * pass against a control that opened a list somewhere else.
   */
  it('enters placement mode and gets out of its own way', () => {
    const { ctx, up } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<RowActions ctx={ctx} id="l3pdzq" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('move'));
    expect(up).toHaveBeenCalledWith({ editOpen: {}, movePick: 'l3pdzq' });
  });

  it('offers no list of text destinations inside the panel any more', () => {
    const { ctx } = ctxWith({ editOpen: { l3pdzq: true }, movePick: 'l3pdzq' });
    render(<RowActions ctx={ctx} id="l3pdzq" kind="task" durationMin={0} />);
    // Positively: the row shows the way OUT of the placement instead.
    expect(screen.getByText('cancel')).toBeTruthy();
    expect(screen.queryByText(/^after /)).toBeNull();
    expect(screen.queryByText(/^first in /)).toBeNull();
  });

  /**
   * ⚠ THE RECOVERED MECHANISM. The old surface filled the plan with "move here" targets while
   * placing (`_placeTargetHtml`, `renderBlockPlacement`). This asserts they are back, in the plan
   * itself — the whole of A2 in one line, and it fails against the build she rejected.
   */
  it('draws landing slots in the plan itself', () => {
    const { ctx } = ctxWith({ todayShape: 'priority', movePick: 'kt4i6q' });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getAllByText('move here').length).toBeGreaterThan(0);
  });

  /**
   * ⚠ BILATERAL, AND VISIBLY SO. June had `plan_store.move_item` generalised (commit 3940fe7)
   * precisely so she could move things EARLIER as well as later, so a slot must appear ABOVE the
   * moving row as well as below it. The old surface's later-only limit is the thing she rejected;
   * this test is what stops it coming back.
   */
  it('puts slots both above and below the row being moved', () => {
    // A middle row, so both directions are genuinely available.
    const { ctx } = ctxWith({ todayShape: 'priority', movePick: 'ieshky' });
    const { container } = render(<TodayPanel ctx={ctx} />);
    const nodes = Array.from(container.querySelectorAll('[data-place-target],[data-moving-row]'));
    const rowIx = nodes.findIndex((n) => n.hasAttribute('data-moving-row'));
    expect(rowIx).toBeGreaterThan(-1);
    expect(nodes.filter((n) => n.hasAttribute('data-place-target')).length).toBeGreaterThan(1);
    expect(nodes.slice(0, rowIx).some((n) => n.hasAttribute('data-place-target'))).toBe(true);
    expect(nodes.slice(rowIx).some((n) => n.hasAttribute('data-place-target'))).toBe(true);
  });

  it('sends the slot she tapped', () => {
    const { ctx, moveItem } = ctxWith({ todayShape: 'priority', movePick: 'kt4i6q' });
    render(<TodayPanel ctx={ctx} />);
    const slots = screen.getAllByText('move here');
    fireEvent.click(slots[0]!);
    expect(moveItem).toHaveBeenCalledTimes(1);
    const [sentId, target] = moveItem.mock.calls[0]!;
    expect(sentId).toBe('kt4i6q');
    expect(typeof target.position).toBe('number');
  });

  /** One thing at a time — transcribed from the old surface's `_placing` collapse. */
  it('collapses every other row’s affordance while a placement is in flight', () => {
    const { ctx } = ctxWith({ movePick: 'someone-else' });
    const { container } = render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(container.innerHTML).toBe('');
  });

  it('lets her back out of the placement without moving anything', () => {
    const { ctx, up, moveItem } = ctxWith({ movePick: 'l3pdzq' });
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
    expect(screen.getByText('chunk length:')).toBeTruthy();
  });
});

describe('B1/B5 — the three reasons a move is not on offer, said apart', () => {
  /**
   * B5. One sentence used to cover all three, and this file used to ENSHRINE the conflation by
   * asserting "There is nowhere else to put this today." for an id that is not in the plan. That
   * is not what happened; the row was not found. Fixed here rather than worked around.
   */
  it('says it could not find a row that is not in the plan, not that there is nowhere to put it', () => {
    const { ctx, notice, up } = ctxWith({ editOpen: { nosuch: true } });
    render(<RowActions ctx={ctx} id="nosuch" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('move'));
    // `notice`, not `flash` — see the duration test above for why a `flash` refusal is silence.
    expect(notice).toHaveBeenCalledWith(
      'I could not find this row in today’s plan, so it cannot be moved.',
      'nosuch',
    );
    // And it does NOT enter a placement mode with nowhere to place anything.
    expect(up).not.toHaveBeenCalled();
  });

  it('says there is nowhere else to put it only when that is the truth', () => {
    const plan = freshPlan();
    // One task, alone: real, movable in principle, and with no other position to take.
    const only = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task') as {
      id: string;
    };
    plan.blocks = [{ label: '', time: '', framing: '', items: [only as never] }];
    const { ctx, notice } = ctxWith({ editOpen: { [only.id]: true } }, plan);
    render(<RowActions ctx={ctx} id={only.id} kind="task" durationMin={0} />);
    fireEvent.click(screen.getByText('move'));
    expect(notice).toHaveBeenCalledWith('There is nowhere else to put this today.', only.id);
  });

  /**
   * ⚠ B1, controller-confirmed. `adapt.ts` turns an appointment into a `kind:'task'` row, so the
   * panel mounts on it; `offsetOf` then computes its position as −1 and the server answers
   * "no scheduled item with id 'a1' to move." She was being invited to tap something that could
   * only fail. The control is withheld entirely — an appointment is at a fixed time.
   */
  it('offers no move at all on an appointment row', () => {
    const plan = freshPlan();
    const appt = plan.blocks[0]!.items[0] as { id: string };
    plan.apptCount = 1;
    const { ctx } = ctxWith({ editOpen: { [appt.id]: true } }, plan);
    render(<RowActions ctx={ctx} id={appt.id} kind="task" durationMin={0} />);
    expect(screen.queryByText('move')).toBeNull();
    // Positively: the row's other two controls are still there, so the panel IS rendering.
    expect(screen.getByText('not today')).toBeTruthy();
    expect(screen.getByText('duration:')).toBeTruthy();
  });
});

describe('A3 — the desktop drags, the phone does not', () => {
  /**
   * June: *"on the desktop, i should be able to click and drag — the move menu becomes higher
   * friction than needed in that context."* This does NOT reverse her no-drag rule, which was
   * about her phone, where drag does not work. Both are asserted, because either one alone is
   * the wrong build.
   */
  function taskRowOf(wide: boolean) {
    const plan = freshPlan();
    const task = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task')!;
    const h = ctxWith({}, plan, null, wide);
    const r = render(<TaskRow ctx={h.ctx} item={task as never} entryKey="0-0" showProj />);
    return { ...h, ...r, task: task as { id: string } };
  }

  it('makes the row draggable on the desktop', () => {
    const { container } = taskRowOf(true);
    expect(container.querySelector('[draggable="true"]')).toBeTruthy();
  });

  it('leaves the row undraggable on the phone, where drag does not work for her', () => {
    const { container } = taskRowOf(false);
    expect(container.querySelector('[draggable="true"]')).toBeNull();
    // Positively: the tap path IS present on the phone, so this is a choice of input and not an
    // absent control.
    expect(screen.getByLabelText('edit timing')).toBeTruthy();
  });

  /** Dragging enters the SAME placement mode a tap does — one set of legal destinations. */
  it('opens the same landing slots a tap would', () => {
    const { container, up, task } = taskRowOf(true);
    const row = container.querySelector('[draggable="true"]')!;
    fireEvent.dragStart(row, { dataTransfer: { setData: () => {}, effectAllowed: '' } });
    expect(up).toHaveBeenCalledWith({ movePick: task.id });
  });

  /**
   * ⚠ REFUSES IN WORDS, never a silent snap-back. `desk.test.tsx` documents this for the Map
   * drag; an appointment reaching here by another route must behave the same way.
   */
  it('refuses to start a drag on an appointment, and says why', () => {
    const plan = freshPlan();
    plan.apptCount = 1;
    const first = plan.blocks[0]!.items[0]!;
    const { ctx, notice, up } = ctxWith({}, plan, null, true);
    const { container } = render(
      <TaskRow ctx={ctx} item={first as never} entryKey="0-0" showProj />,
    );
    const row = container.querySelector('[draggable="true"]')!;
    fireEvent.dragStart(row, { dataTransfer: { setData: () => {}, effectAllowed: '' } });
    expect(notice).toHaveBeenCalledWith(
      'This is an appointment at a fixed time, so it does not move.',
      (first as { id: string }).id,
    );
    expect(up).not.toHaveBeenCalled();
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
    const task = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task')!;
    const { ctx } = ctxWith({}, plan);
    render(<TaskRow ctx={ctx} item={task as never} entryKey="0-0" showProj />);
    expect(screen.getByLabelText('edit timing')).toBeTruthy();
  });

  it('puts the control on a BLOCK row of the schedule view', () => {
    const plan = freshPlan();
    const block = plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'block')!;
    const { ctx } = ctxWith({}, plan);
    render(<WorkBlock ctx={ctx} item={block as never} entryKey="0-0" bandIndex={0} itemIndex={0} />);
    expect(screen.getByLabelText('edit timing')).toBeTruthy();
  });

  it('puts the control on schedule-view rows as the panel assembles them', () => {
    const { ctx } = ctxWith({ todayShape: 'schedule' });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getAllByLabelText('edit timing').length).toBeGreaterThan(0);
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
    expect(screen.getAllByLabelText('edit timing')).toHaveLength(rows.length);
  });

  it('puts the control on a priority-view TASK row specifically', () => {
    // A plan with NO blocks, so only the task-row implementation can satisfy this.
    const plan = freshPlan();
    for (const b of plan.blocks) b.items = b.items.filter((it) => it.kind === 'task');
    const taskCount = plan.blocks.flatMap((b) => b.items).length;
    expect(taskCount).toBeGreaterThan(0);
    const { ctx } = ctxWith({}, plan);
    render(<PriorityList ctx={ctx} />);
    expect(screen.getAllByLabelText('edit timing')).toHaveLength(taskCount);
  });

  /**
   * The block row is the one that must say "chunk length", and it is reachable in both views —
   * so the distinction has to survive the wiring, not just the panel.
   */
  it('calls it a chunk length on a block row in the priority view', () => {
    const { ctx } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<PriorityList ctx={ctx} />);
    expect(screen.getByText('chunk length:')).toBeTruthy();
    expect(screen.queryByText('duration:')).toBeNull();
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

/**
 * ── ONE `edit` PER ROW ───────────────────────────────────────────────────────
 *
 * June ruled the timing trigger back to the word `edit` (A4). The v4 rebuild's `EditChip`
 * already rendered that same word on the same line and opened the object editor, so the row
 * carried the word twice, separated only by `aria-label`.
 *
 * Her decision, in her words: *"Maybe we make the detail view another item in the edit menu?"*
 * — and, when renaming the other chip to `details` was offered instead, *"the details page was
 * designed so i could edit it."* Both controls genuinely edit, so renaming one cannot resolve
 * it; one of them has to stop being a row control.
 *
 * ⚠ This costs a tap to reach the editor. That is a known, accepted trade she chose knowingly,
 * on a surface whose primary use is a phone.
 *
 * The editor item is a NAVIGATION among three controls that write in place. It therefore keeps
 * the codebase's existing vocabulary for "the way into the object editor" — `EditChip`'s
 * bordered box — rather than the underlined text of the three that mutate. No new visual
 * vocabulary was introduced.
 */
describe('one `edit` per row — the object editor moved into the panel', () => {
  /** Every button on screen whose whole word is `edit`. Counting buttons, not text nodes, so a
   *  chip's inner span cannot be double-counted as a second control. */
  function editButtons(container: HTMLElement): HTMLElement[] {
    return Array.from(container.querySelectorAll('button')).filter(
      (b) => (b.textContent || '').trim() === 'edit',
    );
  }

  function firstTask() {
    const plan = freshPlan();
    return plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'task')!;
  }

  function firstBlock() {
    const plan = freshPlan();
    return plan.blocks.flatMap((b) => b.items).find((it) => it.kind === 'block')!;
  }

  it('a task row carries the word edit exactly once, and it is the timing trigger', () => {
    const plan = freshPlan();
    const { ctx } = ctxWith({}, plan);
    const { container } = render(
      <TaskRow ctx={ctx} item={firstTask() as never} entryKey="0-0" showProj />,
    );
    const found = editButtons(container);
    expect(found).toHaveLength(1);
    expect(found[0]!.getAttribute('aria-label')).toBe('edit timing');
  });

  it('a work block row carries the word edit exactly once, and it is the timing trigger', () => {
    const plan = freshPlan();
    const { ctx } = ctxWith({}, plan);
    const { container } = render(
      <WorkBlock
        ctx={ctx}
        item={firstBlock() as never}
        entryKey="0-0"
        bandIndex={0}
        itemIndex={0}
      />,
    );
    const found = editButtons(container);
    expect(found).toHaveLength(1);
    expect(found[0]!.getAttribute('aria-label')).toBe('edit timing');
  });

  it('the panel opens the object editor for THIS row', () => {
    const { ctx, openDetail } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByLabelText('open editor'));
    expect(openDetail).toHaveBeenCalledWith('t1');
  });

  /** A block's panel dispatches on the PROJECT id it was given — the same id its removal and
   *  its chunk length use. Asserted separately so the two kinds cannot be confused. */
  it('the panel opens the object editor for a BLOCK row’s own object', () => {
    const { ctx, openDetail } = ctxWith({ editOpen: { p9: true } });
    render(<RowActions ctx={ctx} id="p9" kind="block" durationMin={0} />);
    fireEvent.click(screen.getByLabelText('open editor'));
    expect(openDetail).toHaveBeenCalledWith('p9');
  });

  it('says open editor in words, not only to assistive tech', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.getByText('open editor')).toBeTruthy();
  });

  /**
   * A1 must not regress. The editor item is INSIDE the floating pane, so it is subject to the
   * same `position:absolute` that keeps the rows below from moving — it cannot have added a
   * line of height to the row.
   */
  it('puts the editor item inside the floating pane, not back in the row', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(panel().contains(screen.getByLabelText('open editor'))).toBe(true);
    expect(panel().style.position).toBe('absolute');
  });

  /** Leaving for another screen closes what she opened here, so returning does not land her in
   *  a panel she has finished with. */
  it('closes the panel when she leaves for the editor', () => {
    const { ctx, up } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    fireEvent.click(screen.getByLabelText('open editor'));
    expect(up).toHaveBeenCalledWith({ editOpen: {} });
  });

  /**
   * It is a navigation, and it must not read as one of the three writes. The three that mutate
   * are underlined text; this one is the bordered box the codebase already uses for the way into
   * the editor. Both sides asserted positively.
   */
  it('does not dress the editor item like the controls that write in place', () => {
    const { ctx } = ctxWith({ editOpen: { t1: true } });
    render(<RowActions ctx={ctx} id="t1" kind="task" durationMin={0} />);
    expect(screen.getByText('not today').style.textDecoration).toBe('underline');
    const editor = screen.getByText('open editor');
    expect(editor.style.textDecoration).toBe('');
    expect(editor.style.border).toContain('1px solid');
  });

  /** `EditChip` is still a live atom — `CheckPage`'s gallery renders it and its default word is
   *  unchanged. Removing it from the plan rows must not have removed it from the codebase. */
  it('leaves EditChip itself intact for its other caller', () => {
    const { ctx } = ctxWith();
    const { container } = render(<EditChip T={ctx.T} onClick={() => {}} />);
    expect(editButtons(container)).toHaveLength(1);
    expect(screen.getByLabelText('open editor')).toBeTruthy();
  });
});
