/**
 * Detail-editor behaviour tests.
 *
 * These pin the branches with no visual signal — the ones a screenshot cannot tell apart:
 * the tri-state inheritance display, the inheritance GATE (which fields may show it at all),
 * the schema-driven layout suppressions, and the Strategy field correction.
 *
 * ⚠ `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never
 * registers and renders accumulate across tests ("found multiple elements"). Explicit below.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, within } from '@testing-library/react';
import { themes } from '@tokens';
import { defaultSchema, seed, seedStrategies } from '../../../fixtures/index.ts';
import { applySchema, index } from '../../../model/index.ts';
import type { Graph, ModelNode, MutationResult } from '../../../model/index.ts';
import { Detail } from '../Detail.tsx';
import { strategyNotes } from '../strategyFields.ts';
import { fmtTime } from '../RecurrenceCard.tsx';
import type { DetailCtx } from '../types.ts';

afterEach(cleanup);

function freshGraph(): Graph {
  return {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
  };
}

interface Harness {
  ctx: DetailCtx;
  apply: ReturnType<typeof vi.fn>;
  up: ReturnType<typeof vi.fn>;
  flash: ReturnType<typeof vi.fn>;
}

function harness(graph: Graph, over: Partial<DetailCtx> = {}): Harness {
  const apply = vi.fn();
  const up = vi.fn();
  const flash = vi.fn();
  const ctx: DetailCtx = {
    T: themes.celestial,
    graph,
    idx: index(graph),
    schema: applySchema(defaultSchema),
    ui: { detail: null, moveFor: null, menuFor: null, chipEdit: null, pickerFilter: '', returnFrom: null },
    up,
    apply,
    flash,
    ...over,
  };
  return { ctx, apply, up, flash };
}

function open(id: string, over: Partial<DetailCtx> = {}) {
  const graph = freshGraph();
  const h = harness(graph, over);
  const onClose = vi.fn();
  const r = render(<Detail ctx={h.ctx} id={id} closing={false} onClose={onClose} />);
  return { ...h, graph, onClose, container: r.container as HTMLElement };
}

/**
 * The block a labelled control lives in. `InheritRow` and `Field` both put the label inside a
 * header row whose PARENT is the whole block, so this is the unit a state assertion is about.
 */
function block(container: HTMLElement, label: string): HTMLElement {
  const lab = [...container.querySelectorAll('label')].find((l) => l.textContent === label);
  if (!lab) throw new Error(`no control labelled "${label}"`);
  const parent = lab.closest('div')?.parentElement;
  if (!parent) throw new Error(`control "${label}" has no block`);
  return parent as HTMLElement;
}

// ── FIXTURE ANCHORS ─────────────────────────────────────────────────────────
// we7liy  TASK    'Put phone case for sale', under sellcase → znqg2i ('Crafts')
// znqg2i  PROJECT 'Crafts', sets access='Involves-leaving-house', blockMin, affective
// Crafts is the nearest schedulable ancestor of we7liy, so we7liy's INHERIT fields inherit.
const TASK_UNDER_CRAFTS = 'we7liy';
const CRAFTS = 'znqg2i';

describe('the two states of an inheritable field — inherited, or set here', () => {
  it('state 1 — key ABSENT: shows which ancestor the value comes from', () => {
    const { container } = open(TASK_UNDER_CRAFTS);
    const b = block(container, 'Access conditions');
    expect(b.textContent).toContain('Inheriting from Crafts');
    expect(b.textContent).toContain('Involves leaving house');
    // The dashed box is the visual half of the signal, and it is what state 2 does not have.
    const dashed = [...b.querySelectorAll('div')].filter((d) => d.style.borderStyle === 'dashed');
    expect(dashed).toHaveLength(1);
  });

  it('state 1 with nothing above it — says so rather than showing a blank', () => {
    // r-kitchen sits under a Project that sets no access, so the walk finds no ancestor.
    const { container } = open('r-kitchen');
    const b = block(container, 'Access conditions');
    expect(b.textContent).toContain('Nothing to inherit from a parent yet');
  });

  it('key PRESENT but EMPTY: shows the editor, NOT the inherit box — an empty selection is a valid value', () => {
    const graph = freshGraph();
    const idx = index(graph);
    const n = idx.byId.get(TASK_UNDER_CRAFTS) as ModelNode;
    n.vals.access = ''; // the intentional-none the spec distinguishes
    const h = harness(graph);
    const { container } = render(
      <Detail ctx={h.ctx} id={TASK_UNDER_CRAFTS} closing={false} onClose={vi.fn()} />,
    );
    const b = block(container, 'Access conditions');

    // June 2026-07-18: "Selecting no options is a valid shape (if leaving the house isn't
    // checked, it doesn't involve leaving the house)." So an empty SET field is ordinary —
    // the editor renders, the inherit box does not, and nothing editorialises about it.
    // v4 has no such text either; an earlier pass added it and it was removed.
    expect(b.textContent).not.toContain('Inheriting from');
    expect(b.textContent).not.toContain('Nothing to inherit');
    expect(b.textContent).toContain('Involves leaving house'); // the option list, i.e. the editor
    // The three things that make it a DIFFERENT render from state 1:
    expect(b.textContent).not.toContain('Inheriting from');
    expect([...b.querySelectorAll('div')].filter((d) => d.style.borderStyle === 'dashed')).toHaveLength(0);
    expect(within(b).getByRole('button', { name: 'Involves leaving house' })).toBeTruthy();
  });

  it('state 3 — key PRESENT with a value: editor, and no "none" note', () => {
    const graph = freshGraph();
    const idx = index(graph);
    (idx.byId.get(TASK_UNDER_CRAFTS) as ModelNode).vals.access = 'Induces-pain';
    const h = harness(graph);
    const { container } = render(
      <Detail ctx={h.ctx} id={TASK_UNDER_CRAFTS} closing={false} onClose={vi.fn()} />,
    );
    const b = block(container, 'Access conditions');
    expect(b.textContent).not.toContain('Inheriting from');
    expect(b.textContent).not.toContain('Set here as none');
  });

  it('an ancestor that set the key EMPTY still stops the walk — "from X", not "nothing"', () => {
    const graph = freshGraph();
    const idx = index(graph);
    // sellcase sits between we7liy and Crafts. An intentional none there must win over
    // Crafts' value, and must still name sellcase as the source.
    (idx.byId.get('sellcase') as ModelNode).vals.access = '';
    const h = harness(graph);
    const { container } = render(
      <Detail ctx={h.ctx} id={TASK_UNDER_CRAFTS} closing={false} onClose={vi.fn()} />,
    );
    const b = block(container, 'Access conditions');
    expect(b.textContent).toContain('Inheriting from Sell phone case');
    expect(b.textContent).toContain('none set');
    // ⚠ REVISED 2026-07-18 (June): this used to assert the option labels were ABSENT, because
    // the dashed box REPLACED the editor while inheriting. She asked for the opposite — the
    // editor is now always rendered, greyed, showing what is being inherited. So the labels
    // are present by design. What still distinguishes this state is that the editor is not
    // operable and the source line names the ancestor the walk stopped at.
    const shown = [...b.querySelectorAll('div')].find((d) => d.getAttribute('aria-disabled') === 'true');
    expect(shown).toBeTruthy();
    expect(shown!.style.pointerEvents).toBe('none');
  });

  /**
   * THE BUG JUNE HIT, 2026-07-18. Her screenshot showed "Nothing to inherit from a parent yet"
   * and, on clicking Custom: "Could not save access — it is NOT saved. api_write: 'access' did
   * not persist (wrote [], read back: absent)."
   *
   * With nothing above it, Custom had nothing to copy down, so it wrote `''`. For a multi_select
   * `''` coerces to `[]`, and an empty write DELETES the property in Anytype (verified live) —
   * so the write failed its own read-back and she got an error for pressing a button.
   *
   * A field with nothing to inherit therefore must NOT write on the Custom click at all. It
   * opens the editor and waits; the first option she picks is the first write, and that write
   * has something real to store. No test covered this case before — the existing Custom test
   * uses a node WITH an ancestor value, where the old code happened to work.
   */
  it('Custom with nothing to inherit opens the editor WITHOUT writing an empty value', () => {
    const { container, apply } = open('r-kitchen'); // no ancestor sets access
    const b = block(container, 'Access conditions');
    expect(b.textContent).toContain('Nothing to inherit from a parent yet');

    fireEvent.click(within(b).getByRole('button', { name: 'Custom' }));

    // The click must not have produced a write of any kind.
    expect(apply).not.toHaveBeenCalled();
    // And the editor must now be LIVE. Asserting only that it is no longer greyed would be a
    // negative assertion, which passes just as happily against a control wired to nothing — the
    // pattern this plan's reviewers rejected twice. So the positive claim is made directly:
    // picking an option now produces a real write, carrying the option she picked.
    // Scoped to THIS field's editor via one of its own option buttons: `block()` can return a
    // wrapper holding a neighbouring field, and a loose `querySelectorAll` would then find that
    // neighbour's greyed editor and pass/fail for the wrong reason.
    const after = block(container, 'Access conditions');
    const opt = within(after).getByRole('button', { name: 'Involves leaving house' });
    expect(opt.closest('[aria-disabled="true"]')).toBeNull();

    fireEvent.click(opt);
    const write = apply.mock.calls[0]?.[0] as MutationResult;
    expect(write?.write).toMatchObject({ op: 'patchVals', id: 'r-kitchen' });
    expect(write?.node?.vals.access).toBe('Involves-leaving-house');
  });

  it('Inherit deletes the key; Custom copies the inherited value down', () => {
    const { container, apply } = open(TASK_UNDER_CRAFTS);
    const b = block(container, 'Access conditions');

    fireEvent.click(within(b).getByRole('button', { name: 'Custom' }));
    const custom = apply.mock.calls[0]?.[0] as MutationResult;
    expect(custom.toast).toBe('Saved');
    expect(custom.node?.vals.access).toBe('Involves-leaving-house');

    fireEvent.click(within(b).getByRole('button', { name: 'Inherit' }));
    const inherit = apply.mock.calls[1]?.[0] as MutationResult;
    expect(inherit.toast).toBe('Inheriting');
    // DELETED, not emptied — an empty string here would silently mean state 2.
    expect(Object.prototype.hasOwnProperty.call(inherit.node?.vals ?? {}, 'access')).toBe(false);
  });
});

describe('the inheritance GATE — which fields may show an inheritance story at all', () => {
  it('a field outside INHERIT never gets one, however deep the node sits', () => {
    const { container } = open(TASK_UNDER_CRAFTS);
    // `status` is on the same node, at the same depth, and is not in INHERIT.
    expect(block(container, 'Task status').textContent).not.toContain('Inherit');
  });

  it('an INHERIT field with no SCHEDULABLE ancestor gets a plain control', () => {
    // Crafts is a PROJECT whose only ancestor is a GOAL — `hasSchedulableAncestor` is false.
    const { container } = open(CRAFTS);
    const b = block(container, 'Access conditions');
    expect(b.textContent).not.toContain('Inheriting from');
    expect(within(b).queryByRole('button', { name: 'Inherit' })).toBeNull();
  });

  it('the gate applies to note fields too, not just controls', () => {
    // `affective` is an INHERIT key that arrives through TEXT, not CTRL.
    const { container } = open(TASK_UNDER_CRAFTS);
    expect(within(block(container, 'Affective')).getByRole('button', { name: 'Inherit' })).toBeTruthy();
    // Same key, same schema, no schedulable ancestor → no segments.
    cleanup();
    const c2 = open(CRAFTS).container;
    expect(within(block(c2, 'Affective')).queryByRole('button', { name: 'Inherit' })).toBeNull();
  });
});

describe('the form is generated from the schema', () => {
  it('offers exactly the option list the schema carries, in order', () => {
    const { container } = open(TASK_UNDER_CRAFTS);
    const sel = within(block(container, 'Task status')).getByRole('combobox') as HTMLSelectElement;
    expect([...sel.options].map((o) => o.value)).toEqual([
      '', // v4's '—' placeholder
      ...defaultSchema.relations.taskStatus.options,
    ]);
  });

  it('renders a field for every control the level declares, minus v4 layout suppressions', () => {
    const { container } = open(CRAFTS);
    for (const [, label] of defaultSchema.controls.PROJECT) {
      expect(
        [...container.querySelectorAll('label')].some((l) => l.textContent === label),
        `PROJECT control "${label}" is missing`,
      ).toBe(true);
    }
  });

  it('suppresses Scheduled from the control flow and pairs it beside Due date', () => {
    const { container } = open(TASK_UNDER_CRAFTS);
    const due = block(container, 'Due date');
    // `pairRow` wraps the two halves in one flex row, so they share a grandparent.
    expect(due.parentElement?.parentElement?.textContent).toContain('Scheduled');
  });

  it('writes through the pure mutation seam, never directly', () => {
    const { container, apply } = open(TASK_UNDER_CRAFTS);
    const sel = within(block(container, 'Task status')).getByRole('combobox');
    fireEvent.change(sel, { target: { value: 'Blocked' } });
    const res = apply.mock.calls[0]?.[0] as MutationResult;
    expect(res.node?.vals.status).toBe('Blocked');
    expect(res.toast).toBe('Saved');
  });
});

describe('RECURRING gets the schedule block instead of loose schedule fields', () => {
  it('strips the five interdependent controls out of the generated form', () => {
    const { container } = open('r-kitchen');
    for (const gone of ['Repeats', 'Day of week', 'Day of month', 'Time of day']) {
      expect([...container.querySelectorAll('label')].some((l) => l.textContent === gone)).toBe(false);
    }
    // Uppercasing is CSS (`textTransform`), so `textContent` carries the source casing.
    expect(container.textContent).toContain('Recurrence');
  });

  it('the day row follows the cadence: week → day-of-week, month → day-of-month', () => {
    const { container } = open('r-kitchen'); // unit: 'week'
    expect(container.textContent).toContain('MonTueWedThuFriSatSun');
    expect(container.textContent).not.toContain('Day of month');

    cleanup();
    const graph = freshGraph();
    (index(graph).byId.get('r-kitchen') as ModelNode).vals.unit = 'month';
    const h = harness(graph);
    const r = render(<Detail ctx={h.ctx} id="r-kitchen" closing={false} onClose={vi.fn()} />);
    expect(r.container.textContent).toContain('Day of month');
  });

  it('an as_needed recurring reads OPEN/CLOSED and drops the count and time rows', () => {
    const { container } = open('r-groc');
    expect(container.textContent).toContain('OPEN');
    expect(container.textContent).not.toContain('IN PLAN');
    expect(container.textContent).not.toContain('every');
  });

  it('fmtTime renders 24h values as 12h, and nothing as an em dash', () => {
    expect(fmtTime('14:05')).toBe('2:05 PM');
    expect(fmtTime('00:30')).toBe('12:30 AM');
    expect(fmtTime('')).toBe('—');
  });
});

describe('Strategy — the data model overrides the mockup (BUILD_DOC 2026-07-18)', () => {
  it('shows the instruction field under its live name, and adds NO Directive field', () => {
    const { container } = open('strat1');
    const labels = [...container.querySelectorAll('label')].map((l) => l.textContent);
    expect(labels).toContain('What for');
    expect(labels).not.toContain('Directive');
  });

  it('surfaces Context and Learning notes, which the mockup form omits', () => {
    const { container } = open('strat1');
    const labels = [...container.querySelectorAll('label')].map((l) => l.textContent);
    expect(labels).toContain('Context');
    expect(labels).toContain('Learning notes');
  });

  it('keeps the fixture VALUE KEYS unchanged — the rename is a label, not a migration', () => {
    const mapped = strategyNotes(defaultSchema.notes.STRATEGY);
    expect(mapped.map(([, key]) => key)).toEqual(['directive', 'context', 'learningNotes']);
    const { container, apply } = open('strat1');
    fireEvent.change(screen.getByLabelText('What for'), { target: { value: 'x' } });
    expect((apply.mock.calls[0]?.[0] as MutationResult).node?.vals.directive).toBe('x');
    expect(container).toBeTruthy();
  });

  it('a Strategy is scoped, not filed — no parent, no move affordance', () => {
    const { container, up } = open('strat1');
    expect(container.textContent).toContain('Applies globally');
    expect(container.textContent).not.toContain('· move ›');
    expect(up).not.toHaveBeenCalled();
  });
});

describe('the header', () => {
  it('check-off is TASK-only, and flips status with it', () => {
    const { container, apply } = open(TASK_UNDER_CRAFTS);
    fireEvent.click(within(container).getByRole('button', { name: 'mark done' }));
    const res = apply.mock.calls[0]?.[0] as MutationResult;
    expect(res.node?.vals.done).toBe(true);
    expect(res.node?.vals.status).toBe('Done');

    cleanup();
    const proj = open(CRAFTS).container;
    expect(within(proj).queryByRole('button', { name: /mark done|reopen/ })).toBeNull();
  });

  it('a GOAL cannot be converted, so the badge is not a control', () => {
    const { container } = open('kidvlq');
    expect(within(container).queryByRole('button', { name: 'change type' })).toBeNull();
  });

  it('the type dropdown blocks Task/Recurring while the node has children', () => {
    const { container, apply } = open('sellcase'); // SUBPROJECT with one child
    fireEvent.click(within(container).getByRole('button', { name: 'change type' }));
    const taskBtn = within(container).getByRole('button', { name: /^\s*Task/ }) as HTMLButtonElement;
    expect(taskBtn.disabled).toBe(true);
    fireEvent.click(taskBtn);
    expect(apply).not.toHaveBeenCalled();
  });

  it('converting a leaf goes through setType and keeps its values', () => {
    const { container, apply } = open(TASK_UNDER_CRAFTS);
    fireEvent.click(within(container).getByRole('button', { name: 'change type' }));
    fireEvent.click(within(container).getByRole('button', { name: /^\s*Recurring/ }));
    const res = apply.mock.calls[0]?.[0] as MutationResult;
    expect(res.node?.level).toBe('RECURRING');
    expect(res.node?.vals.status).toBe('Needs Clarifying'); // "fields kept" is literal
  });

  it('the back button names the tab the user came from', () => {
    const { container } = open(TASK_UNDER_CRAFTS, {
      ui: { detail: null, moveFor: null, menuFor: null, chipEdit: null, pickerFilter: '', returnFrom: 'today' },
    });
    expect(container.textContent).toContain('Today');
  });

  it('the desktop branch swaps Back for a Close pill', () => {
    const { container } = open(TASK_UNDER_CRAFTS, { wide: true });
    expect(within(container).getByRole('button', { name: 'close' })).toBeTruthy();
  });

  it('the title writes per keystroke and flashes only on blur', () => {
    const { container, apply, flash } = open(TASK_UNDER_CRAFTS);
    const title = within(container).getByLabelText('Title');
    fireEvent.change(title, { target: { value: 'Sell the case' } });
    expect((apply.mock.calls[0]?.[0] as MutationResult).node?.title).toBe('Sell the case');
    expect(flash).not.toHaveBeenCalled();
    fireEvent.blur(title);
    expect(flash).toHaveBeenCalledWith('Saved');
  });
});

describe('location block', () => {
  it('a movable object opens the move picker', () => {
    const { container, up } = open(TASK_UNDER_CRAFTS);
    fireEvent.click(within(container).getByText('Move'));
    expect(up).toHaveBeenCalledWith({ moveFor: TASK_UNDER_CRAFTS, pickerFilter: '' });
  });

  it('a GOAL states its position instead of offering a dead control', () => {
    const { container, up } = open('kidvlq');
    expect(container.textContent).toContain('Top-level goal');
    expect(within(container).queryByText('Move')).toBeNull();
    expect(up).not.toHaveBeenCalled();
  });
});

describe('delete', () => {
  it('takes two taps, and the first one changes nothing', () => {
    const { container, apply } = open(TASK_UNDER_CRAFTS);
    const btn = within(container).getByRole('button', { name: 'Delete' });
    fireEvent.click(btn);
    expect(apply).not.toHaveBeenCalled();
    fireEvent.click(within(container).getByRole('button', { name: 'Tap again to delete' }));
    const res = apply.mock.calls[0]?.[0] as MutationResult;
    expect(res.toast).toBe('Deleted · synced');
    expect(res.ui).toMatchObject({ detail: null });
  });
});

