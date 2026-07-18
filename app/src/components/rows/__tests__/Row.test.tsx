/**
 * Row behaviour tests.
 *
 * `row()` serves the tree, Routines, Strategies AND the move picker — four screens from one
 * component — so a subtle regression here is attributed to whichever screen surfaces it, not
 * to this file. These pin the branch logic that has no visual signal.
 *
 * Added 2026-07-18 after the Task 4 review gate found the component shipped with zero tests.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { defaultSchema } from '../../../fixtures/index.ts';
import { applySchema } from '../../../model/index.ts';
import type { ModelNode } from '../../../model/index.ts';
import type { RowCtx } from '../types.ts';
import { Row } from '../Row.tsx';

// vite.config sets `globals: false`, so Testing Library's automatic cleanup never registers
// and renders would accumulate across tests ("found multiple elements"). Explicit here.
afterEach(cleanup);

function ctx(overrides: Partial<RowCtx['ui']> = {}): RowCtx {
  return {
    T: themes.celestial,
    // Added with Task 6: `Row` now renders `ChipStrip` when this row's chip is being edited,
    // and the strip's option lists come from the schema. Without it the chipEdit test throws
    // on `schema.OPTS` rather than exercising the branch it names.
    schema: applySchema(defaultSchema),
    ui: {
      detail: null,
      menuFor: null,
      chipEdit: null,
      dragOverId: null,
      ...overrides,
    },
    up: vi.fn(),
  } as unknown as RowCtx;
}

function task(vals: ModelNode['vals'] = {}): ModelNode {
  return { id: 't1', level: 'TASK', type: 'Task', title: 'Order rivets', vals, children: [] };
}

/**
 * The ROW element itself. Row renders an outer positioning wrapper (`flex-direction:column`,
 * for the drop indicator) with the actual row as its first child — the one carrying
 * `padding-left` and the active background.
 */
function rowEl(container: HTMLElement): HTMLElement {
  return container.firstElementChild!.firstElementChild as HTMLElement;
}

describe('Row — the done/paused title cascade', () => {
  it('strikes through and dims a TASK marked done via the checkbox', () => {
    render(<Row ctx={ctx()} n={task({ done: true })} />);
    const title = screen.getByText('Order rivets');
    expect(title.style.textDecoration).toBe('line-through');
  });

  it('also treats status "Done" as done — v4 checks BOTH, not one', () => {
    render(<Row ctx={ctx()} n={task({ status: 'Done' })} />);
    expect(screen.getByText('Order rivets').style.textDecoration).toBe('line-through');
  });

  it('does NOT strike through a paused RECURRING — only dims it', () => {
    // v4: `done` drives the strike, `paused` only reaches the colour branch.
    const rec: ModelNode = {
      id: 'r1', level: 'RECURRING', type: 'Recurring', title: 'Water plants',
      vals: { paused: true }, children: [],
    };
    render(<Row ctx={ctx()} n={rec} />);
    const title = screen.getByText('Water plants');
    expect(title.style.textDecoration).toBe('none');
  });

  it('leaves an open task untouched', () => {
    render(<Row ctx={ctx()} n={task({ status: 'Ready' })} />);
    expect(screen.getByText('Order rivets').style.textDecoration).toBe('none');
  });
});

describe('Row — the `active` disjunction', () => {
  // v4: sel || detail===id || menuFor===id || (chipEdit && chipEdit.id===id).
  // Four independent reasons a row reads as active; each must work alone.
  it.each([
    ['sel prop', {}, { sel: true }],
    ['detail open on this row', { detail: 't1' }, {}],
    ['menu open on this row', { menuFor: 't1' }, {}],
    ['a chip being edited on this row', { chipEdit: { id: 't1', field: 'status' } }, {}],
  ])('is active from %s alone', (_label, ui, props) => {
    const { container } = render(<Row ctx={ctx(ui)} n={task()} {...props} />);
    expect(rowEl(container).style.background).not.toBe('transparent');
  });

  it('is NOT active when chipEdit belongs to a DIFFERENT row', () => {
    const { container } = render(
      <Row ctx={ctx({ chipEdit: { id: 'someone-else', field: 'status' } })} n={task()} />,
    );
    expect(rowEl(container).style.background).toBe('transparent');
  });
});

describe('Row — chip clicks do not also fire the row tap', () => {
  /**
   * THE REGRESSION THIS FILE EXISTS FOR. v4:452/455 call `e.stopPropagation()` before
   * `onChip(c)`. In the `chipsBelow` branch the chip strip is a CHILD of the row's tap
   * target, so without the stop one tap sets both `chipEdit` and `detail` — and once the
   * detail editor lands (Task 5) it opens on top of the chip strip.
   *
   * The port originally dropped it, because `ChipProps.onClick` was typed `() => void`,
   * which made `stopPropagation` untypeable from any caller.
   */
  it('chipsBelow: tapping a chip does not trigger onTap', () => {
    const onTap = vi.fn();
    render(<Row ctx={ctx()} n={task({ status: 'Ready' })} chipsBelow onTap={onTap} />);
    const chip = screen.getByText('Ready');
    fireEvent.click(chip);
    expect(onTap).not.toHaveBeenCalled();
  });

  it('tapping the title still triggers onTap', () => {
    const onTap = vi.fn();
    render(<Row ctx={ctx()} n={task({ status: 'Ready' })} chipsBelow onTap={onTap} />);
    fireEvent.click(screen.getByText('Order rivets'));
    expect(onTap).toHaveBeenCalledTimes(1);
  });
});

describe('Row — indentation expresses depth, hue does not', () => {
  it('pads 8 + depth*16 (16px is the gallery step, 4a L54/L60)', () => {
    for (const [depth, px] of [[0, '8px'], [1, '24px'], [2, '40px'], [3, '56px']] as const) {
      const { container } = render(<Row ctx={ctx()} n={task()} depth={depth} />);
      expect(rowEl(container).style.paddingLeft).toBe(px);
    }
  });

  it('carries no type-ramp accent on the row itself at any depth', () => {
    const { container } = render(<Row ctx={ctx()} n={task()} depth={3} />);
    const row = rowEl(container);
    expect(row.style.backgroundImage).toBe('none');
    expect(row.style.boxShadow).toBe('none');
  });
});
