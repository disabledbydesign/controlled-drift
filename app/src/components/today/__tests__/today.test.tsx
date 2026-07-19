/**
 * Behaviour tests for the Today tab (Task 7).
 *
 * These pin the things this task is most likely to get quietly wrong — chiefly the spec §14
 * deltas, which OVERRIDE the mockup and so have no v4 behaviour to fall back on:
 *   1. both plan shapes render, and the switch actually swaps them
 *   2. checking off a task goes through the model's pure `toggleDone` and strikes through
 *   3. checking off a WORK BLOCK reads as completion — strikes the title through — and does
 *      not narrate "did a chunk today"
 *   4. held-back items are hidden until the affordance is tapped, and the affordance itself
 *      is absent when the list is empty
 *   5. the arc "here" advance: checking the current step promotes the next `ahead` step
 *   6. no per-item "why" line and no plan-age line reach the DOM, even though the fixture
 *      still carries both fields
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { seedPeriods, seedPlan } from '../../../fixtures/index.ts';
import type { Plan, PlanBlockItem, PlanTaskItem } from '../../../fixtures/index.ts';
import { index, toggleArcStep, workItems } from '../../../model/index.ts';
import { TodayPanel } from '../TodayPanel.tsx';
import type { TodayCtx } from '../types.ts';
import { ctxWith, freshGraph, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

/**
 * `Plan.blocks[].items[]` is a discriminated union, so the tests narrow rather than cast:
 * a fixture reshuffle that moves the block or the task should fail loudly here, not silently
 * assert against the wrong grain.
 */
function blockAt(p: Plan, bi: number, ii: number): PlanBlockItem {
  const it = p.blocks[bi]?.items[ii];
  if (!it || it.kind !== 'block') throw new Error(`plan[${bi}][${ii}] is not a work block`);
  return it;
}

function taskAt(p: Plan, bi: number, ii: number): PlanTaskItem {
  const it = p.blocks[bi]?.items[ii];
  if (!it || it.kind !== 'task') throw new Error(`plan[${bi}][${ii}] is not a task`);
  return it;
}

/** The arc of the fixture's one arc-carrying block. */
function arcOf(p: Plan): { state: string }[] {
  const arc = blockAt(p, 0, 0).arc;
  if (!arc) throw new Error('the fixture block has no arc');
  return arc;
}

describe('the two plan shapes', () => {
  it('renders the clock bands in schedule shape', () => {
    const { ctx } = ctxWith({ todayShape: 'schedule' });
    render(<TodayPanel ctx={ctx} />);
    // Band labels are the schedule's own structure; the priority view has none.
    expect(screen.getByText('Morning')).toBeTruthy();
    expect(screen.getByText('Afternoon')).toBeTruthy();
    expect(screen.queryByText(/ranked to-do list/)).toBeNull();
  });

  it('renders a flat ranked list in priority shape, with no clock bands', () => {
    const { ctx } = ctxWith({ todayShape: 'priority' });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(/No clock times — a ranked to-do list/)).toBeTruthy();
    expect(screen.queryByText('Morning')).toBeNull();
    // One numbered row per non-break item.
    const n = workItems(seedPlan).length;
    expect(screen.getByText(n + '.')).toBeTruthy();
    expect(screen.queryByText(n + 1 + '.')).toBeNull();
  });

  it('the View switch writes todayShape', () => {
    const { ctx, up } = ctxWith({ todayShape: 'schedule' });
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getByText('Priority'));
    expect(up).toHaveBeenCalledWith({ todayShape: 'priority' });
  });

  it('drops break items from the priority list — they have no id to rank', () => {
    const { ctx } = ctxWith({ todayShape: 'priority' });
    render(<TodayPanel ctx={ctx} />);
    // 'Lunch' is a `break` and appears in the schedule shape only.
    expect(screen.queryByText('Lunch')).toBeNull();
  });
});

describe('checking a task off', () => {
  it('routes through the model mutation and marks the node done', () => {
    const { ctx, apply } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    // 'kt4i6q' is the second Morning item — a real task id in the fixture graph.
    const boxes = screen.getAllByLabelText('mark done');
    fireEvent.click(boxes[1]!);
    expect(apply).toHaveBeenCalledTimes(1);
    const result = apply.mock.calls[0]![0];
    expect(result.node.id).toBe('kt4i6q');
    expect(result.node.vals.done).toBe(true);
    expect(result.node.vals.status).toBe('Done');
    // The mutation is pure — the graph handed in is untouched.
    expect(ctx.idx.byId.get('kt4i6q')!.vals['done']).toBeFalsy();
  });

  it('strikes a done task through', () => {
    const graph = freshGraph();
    const t = index(graph).byId.get('kt4i6q')!;
    t.vals['done'] = true;
    const idx = index(graph);
    const ctx: TodayCtx = {
      ...ctxWith().ctx,
      graph,
      idx,
    };
    render(<TodayPanel ctx={ctx} />);
    const title = screen.getByText(t.title);
    // The strikethrough lives on the wrapping title span, not the text node itself.
    expect(title.closest('span')!.parentElement!.style.textDecoration).toBe('line-through');
  });
});

describe('spec §14 — the work block check reads as completion', () => {
  it('is labelled as completion, not as a chunk note', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(screen.queryByTitle('did a chunk today')).toBeNull();
    expect(screen.queryByText(/chunk/i)).toBeNull();
    expect(screen.queryByText(/tomorrow/i)).toBeNull();
  });

  it('strikes the block title through when checked', () => {
    const { ctx } = ctxWith({ chunked: { l3pdzq: true } });
    render(<TodayPanel ctx={ctx} />);
    const title = screen.getByText('Work on the reviewer response');
    expect(title.style.textDecoration).toBe('line-through');
  });

  it('is not struck through when unchecked', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('Work on the reviewer response').style.textDecoration).toBe('none');
  });

  /**
   * The check is a SERVER write now, not a UI flag: it routes through `ctx.chunk`, which posts
   * `/api/complete` and only then says anything. The old assertion — a `chunked` patch keyed
   * `'0-0'` plus an immediate `flash('Done')` — described a check that vanished on reload and
   * a message raised before any request went out.
   */
  it('checking the block records a chunk against the block’s own id', () => {
    const { ctx, chunk } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(chunk).toHaveBeenCalledWith('l3pdzq', true);
  });

  it('un-checking a recorded chunk reopens it, by the same id', () => {
    const { ctx, chunk } = ctxWith({ chunked: { l3pdzq: true } });
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(chunk).toHaveBeenCalledWith('l3pdzq', false);
  });

  /**
   * The plan the server hands back carries `did_chunk_today` on the block row, so a reload
   * renders the check from the plan alone — with no UI state at all.
   */
  it('renders as checked from the plan’s own record, with no UI state set', () => {
    const plan = freshPlan();
    const item = plan.blocks[0]!.items[0]!;
    if (item.kind !== 'block') throw new Error('seedPlan[0][0] is not a work block');
    item.didChunkToday = true;
    const { ctx } = ctxWith({}, plan);
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('Work on the reviewer response').style.textDecoration).toBe(
      'line-through',
    );
  });

  it('her un-check outranks the server record until the write is answered', () => {
    // The gap this closes: with `||` instead of `??`, an explicit `false` falls THROUGH to
    // `didChunkToday` — so un-checking a block the server already recorded as done springs it
    // straight back to checked, and she cannot undo a mis-tap. Absent means "the server
    // decides"; present means "she decided", including when she decided `false`.
    const plan = freshPlan();
    const item = plan.blocks[0]!.items[0]!;
    if (item.kind !== 'block') throw new Error('seedPlan[0][0] is not a work block');
    item.didChunkToday = true;
    const { ctx } = ctxWith({ chunked: { [item.id]: false } }, plan);
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('Work on the reviewer response').style.textDecoration).toBe('none');
  });
});

describe('spec §14 — held-back items expand inline', () => {
  it('hides the names until the affordance is tapped', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(/· 2 more/)).toBeTruthy();
    expect(screen.queryByText('Re-run the bias metrics')).toBeNull();
  });

  it('lists them once open', () => {
    const { ctx } = ctxWith({ heldOpen: { '0-1': true } });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('Re-run the bias metrics')).toBeTruthy();
    expect(screen.getByText('Write the data-availability note')).toBeTruthy();
    expect(screen.getByText(/held under this thread, not today/)).toBeTruthy();
  });

  it('tapping the affordance opens it', () => {
    const { ctx, up } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getByText(/· 2 more/));
    expect(up).toHaveBeenCalledWith({ heldOpen: { '0-1': true } });
  });

  it('hides the affordance entirely when nothing is held back', () => {
    const plan = freshPlan();
    delete taskAt(plan, 0, 1).heldBack;
    const { ctx } = ctxWith({}, plan);
    render(<TodayPanel ctx={ctx} />);
    expect(screen.queryByText(/more/)).toBeNull();
  });
});

describe('spec §14 — the arc "here" advance', () => {
  it('promotes the next `ahead` step when the current one is checked', () => {
    const p = toggleArcStep(freshPlan(), 0, 0, 1).plan;
    const arc = arcOf(p);
    expect(arc[1]!.state).toBe('done');
    expect(arc[2]!.state).toBe('here');
    expect(arc[3]!.state).toBe('ahead');
  });

  it('does not promote anything when a non-current step is checked', () => {
    const p = toggleArcStep(freshPlan(), 0, 0, 2).plan;
    const arc = arcOf(p);
    expect(arc[1]!.state).toBe('here');
    expect(arc[2]!.state).toBe('done');
    expect(arc[3]!.state).toBe('ahead');
  });

  it('reopening sends the step to `ahead` and demotes nothing', () => {
    const p = toggleArcStep(freshPlan(), 0, 0, 0).plan;
    const arc = arcOf(p);
    expect(arc[0]!.state).toBe('ahead');
    expect(arc[1]!.state).toBe('here');
  });

  it('is pure — the plan handed in is unchanged', () => {
    const before = freshPlan();
    toggleArcStep(before, 0, 0, 1);
    expect(arcOf(before)[1]!.state).toBe('here');
  });

  /**
   * ⚠ REWRITTEN 2026-07-19. This test used to assert that checking a step "routes through
   * applyPlan", and it passed — against a control that saved nothing. `applyPlan` sets local
   * state and raises a toast; `PlanResult` has no `write`, so no request was reachable from it.
   * June checked steps off, read "Nice — one down", and lost them on reload.
   *
   * The arc's own state machine is still exercised — by the four pure `toggleArcStep` tests
   * directly above, which is where that logic lives. What this one holds is the WIRING: the
   * step's checkbox reaches the writer that talks to the server, carrying the step's own id.
   * `shell/__tests__/completeArcStep.test.tsx` covers what that writer then does.
   */
  it('renders the arc only when the block is expanded, and checking sends the step to the server writer', () => {
    const closed = ctxWith();
    render(<TodayPanel ctx={closed.ctx} />);
    expect(screen.queryByText('Draft the rebuttal paragraph')).toBeNull();
    cleanup();

    const open = ctxWith({ blocksOpen: { l3pdzq: true } });
    render(<TodayPanel ctx={open.ctx} />);
    const step = screen.getByText('Draft the rebuttal paragraph');
    expect(step).toBeTruthy();
    // The step's own checkbox is the sibling button inside the arc row.
    fireEvent.click(step.parentElement!.querySelector('button')!);
    expect(open.completeStep).toHaveBeenCalledTimes(1);
    expect(open.completeStep).toHaveBeenCalledWith(
      { id: 'l3pdzq', bandIndex: 0, itemIndex: 0, stepIndex: 1 },
      true,
    );
    // The seam that cannot write is not the one it went to.
    expect(open.applyPlan).not.toHaveBeenCalled();
  });
});

describe('spec §14 — what must NOT be rendered', () => {
  it('renders no per-item "why" line, though the fixture carries one', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(blockAt(seedPlan, 0, 0).why).toBeTruthy();
    for (const b of seedPlan.blocks) {
      for (const it of b.items) {
        if (it.kind === 'break') continue;
        expect(screen.queryByText(new RegExp(it.why))).toBeNull();
      }
    }
  });

  /*
   * THE PLAN-AGE LINE. Restored 2026-07-19. The test that stood here asserted the OPPOSITE —
   * that no age line reached the DOM — and it passed, because the code did what the code said.
   * What it never asked was whether what she sees is true. It was not: with the line gone she
   * saw a date she read as today's on a plan that could have been built yesterday.
   *
   * These assert the truth condition — given a plan built at a stated time, what must be on
   * screen — and are POSITIVE: they name the words she must see.
   */
  it('states when the plan was built, when the plan says when it was built', () => {
    const built = new Date();
    built.setHours(9, 2, 0, 0);
    const { ctx } = ctxWith({}, { ...freshPlan(), generated: built.toISOString() });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(/^built this morning at /)).toBeTruthy();
  });

  it('tells her a leftover plan is not today’s, and how to get today’s', () => {
    const built = new Date();
    built.setDate(built.getDate() - 1);
    built.setHours(19, 42, 0, 0);
    const { ctx } = ctxWith({}, { ...freshPlan(), generated: built.toISOString() });
    render(<TodayPanel ctx={ctx} />);
    const line = screen.getByText(/^built yesterday evening at /);
    expect(line.textContent).toContain('tap Fresh plan for today’s');
    // The control that sentence names must actually be on screen.
    expect(screen.getByText('↻ Fresh plan')).toBeTruthy();
  });

  it('says nothing about the age when the plan carries no build time', () => {
    const { ctx } = ctxWith({}, { ...freshPlan(), generated: '' });
    render(<TodayPanel ctx={ctx} />);
    expect(screen.queryByText(/^built /)).toBeNull();
  });

  it('renders the woven frame expanded, with no disclosure control', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(seedPlan.woven)).toBeTruthy();
  });
});

describe('the priority list reorder', () => {
  it('moves an item up and writes the new order', () => {
    const { ctx, up } = ctxWith({ todayShape: 'priority' });
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('move up')[1]!);
    const ids = workItems(seedPlan).map((it) => it.id);
    const expected = [ids[1], ids[0], ...ids.slice(2)];
    expect(up).toHaveBeenCalledWith({ priOrder: expected });
  });

  it('appends plan items a stale stored order does not mention', () => {
    const ids = workItems(seedPlan).map((it) => it.id);
    const { ctx } = ctxWith({ todayShape: 'priority', priOrder: ['gone', ids[2]!] });
    render(<TodayPanel ctx={ctx} />);
    // The unknown id is dropped and the three unmentioned items are appended, so the count
    // still matches the plan — a stale reorder cannot lose an item.
    expect(screen.getAllByLabelText('move up').length).toBe(ids.length);
  });
});

describe('the theme SHAPE fork', () => {
  it('bands are a mono bracket in hardware and a dot label in celestial', () => {
    const cel = ctxWith();
    render(<TodayPanel ctx={cel.ctx} />);
    expect(screen.getByText('Morning')).toBeTruthy();
    expect(screen.queryByText('┌ MORNING')).toBeNull();
    cleanup();

    const hw = ctxWith();
    render(<TodayPanel ctx={{ ...hw.ctx, T: themes.hardware }} />);
    expect(screen.getByText('┌ MORNING')).toBeTruthy();
    expect(screen.queryByText('Morning')).toBeNull();
  });

  it('the woven eyebrow and the send button fork on theme', () => {
    const cel = ctxWith();
    render(<TodayPanel ctx={cel.ctx} />);
    expect(screen.getByText('✦ today')).toBeTruthy();
    expect(screen.getByText('✦ Send')).toBeTruthy();
    cleanup();

    const hw = ctxWith();
    render(<TodayPanel ctx={{ ...hw.ctx, T: themes.hardware }} />);
    expect(screen.getByText('// today')).toBeTruthy();
    expect(screen.getByText('EXEC ⏎')).toBeTruthy();
  });
});

describe('navigation out of Today', () => {
  /**
   * ⚠ REACHED THROUGH THE PANEL NOW (A5). The row used to carry its own `EditChip`; it said
   * `edit`, and so does the timing trigger June ruled back into the row, so one of the two had
   * to stop being a row control. The destination is unchanged — this still asserts that the
   * plan row reaches the object editor for its own id.
   */
  it('the panel opens the detail editor for that item', () => {
    const { ctx, openDetail } = ctxWith({ editOpen: { l3pdzq: true } });
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getAllByLabelText('open editor')[0]!);
    expect(openDetail).toHaveBeenCalledWith('l3pdzq');
  });

  /**
   * The Map pointer is now the ONLY thing on Today that changes tab. "Add something" was removed
   * from the action row on June's direction (2026-07-18) — it was navigation among plan actions,
   * and the tab bar already reaches the Add tab. See `actionRow.test.tsx` for the row's contents.
   */
  it('the Map pointer changes tab', () => {
    const { ctx, goTab } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    fireEvent.click(screen.getByText(/Open the Map to pick a thread/));
    expect(goTab).toHaveBeenCalledWith('map');
  });
});

describe('the focus slot', () => {
  it('shows the running period and toggles expansion', () => {
    const { ctx, up } = ctxWith();
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(seedPeriods[0]!.name)).toBeTruthy();
    expect(screen.getByText('Jul 14 – Jul 20')).toBeTruthy();
    fireEvent.click(screen.getByText('See focus periods'));
    expect(up).toHaveBeenCalledWith({ focusExpanded: true });
  });

  it('renders no period header when none is running', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={{ ...ctx, periods: [] }} />);
    expect(screen.queryByText(seedPeriods[0]!.name)).toBeNull();
    expect(screen.getByText('See focus periods')).toBeTruthy();
  });
});

/**
 * The ask box's behaviour moved to `askBox.test.tsx` when the box was wired to the server
 * (2026-07-18). The test that lived here asserted the bug: `flash('Sent')` plus an unconditional
 * `up({ask:''})`, i.e. it certified that her text was deleted whether or not anything had been
 * sent — nothing read `ui.ask` at all. What replaces it is a send that carries her words to
 * `/api/negotiate` and clears the box only on a confirmed generation.
 */
