/**
 * The two carried-forward capabilities from the retiring surface (Task 11).
 *
 * These pin what would otherwise be lost silently:
 *   1. an unparented object RENDERS — in a Goal→Project→Task tree it otherwise appears nowhere,
 *      and June's live space has twelve of them
 *   2. an empty bucket renders NOTHING — no heading, no zero (she declined the count line)
 *   3. an orphan is a real node: it opens, and `move()` can file it
 *   4. searching from any structure tab finds matches on the other two, named by tab
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { defaultSchema, seed, seedOrphans, seedStrategies } from '../../fixtures/index.ts';
import { applySchema, index, move, node, setVal } from '../../model/index.ts';
import type { Graph } from '../../model/index.ts';
import type { PanelCtx, PanelUi } from '../../components/panels/index.ts';
import { MapScreen } from '../MapScreen.tsx';
import { RoutinesScreen } from '../RoutinesScreen.tsx';
import { StrategiesScreen } from '../StrategiesScreen.tsx';

afterEach(cleanup);

const BASE_UI: PanelUi = {
  search: '',
  hideInactive: false,
  sideFilter: 'all',
  filterOpen: false,
  addOpen: false,
  focus: null,
  detail: null,
  menuFor: null,
  chipEdit: null,
  moveFor: null,
  addParentFor: null,
  pickerFilter: '',
  pickerExpanded: {},
  confirmDelete: null,
  dragOverId: null,
  collapsed: {},
  deskPath: [],
  recFilter: 'all',
  stratWhen: 'all',
  stratStatus: 'all',
  stratFilterOpen: false,
};

function freshGraph(): Graph {
  return {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
    orphans: structuredClone(seedOrphans) as Graph['orphans'],
  };
}

function ctx(ui: Partial<PanelUi> = {}, graph: Graph = freshGraph()): PanelCtx {
  return {
    T: themes.celestial,
    graph,
    idx: index(graph),
    schema: applySchema(defaultSchema),
    ui: { ...BASE_UI, ...ui },
    up: vi.fn(),
    apply: vi.fn(),
    fail: vi.fn(),
  };
}

// ── the buckets ───────────────────────────────────────────────────────────────

describe('orphan buckets — the anti-vanishing affordance', () => {
  it('shows an unparented recurring item that appears NOWHERE in the tree', () => {
    const c = ctx();
    // The premise: Shower really is absent from the rooted tree.
    const inTree = (nodes: Graph['roots']): boolean =>
      nodes.some((n) => n.title === 'Shower' || inTree(n.children));
    expect(inTree(c.graph.roots)).toBe(false);

    render(<MapScreen ctx={c} />);
    expect(screen.getByText('Shower')).toBeTruthy();
  });

  it('uses the label the endpoint supplies, verbatim', () => {
    // `scripts/api_tree.py:302` — kept verbatim from the surface being retired, so the wording
    // June already reads does not change. The UI must not reword it.
    render(<MapScreen ctx={ctx()} />);
    expect(screen.getByText('⚠ NO PROJECT — orphan tasks')).toBeTruthy();
  });

  it('renders NOTHING for an empty bucket — no heading, no zero', () => {
    // `parentless_workstreams` is empty in the fixture precisely to prove this.
    render(<MapScreen ctx={ctx()} />);
    expect(screen.queryByText('⚙ Workstreams with no parent project')).toBeNull();
  });

  it('shows no count of the total — the buckets ARE the signal (she declined the count line)', () => {
    const { container } = render(<MapScreen ctx={ctx()} />);
    // The four bucket sizes are 1/3/4/0 → 8. A standing data-health total must not appear.
    expect(container.textContent).not.toMatch(/8 (unfiled|orphan|unparented)/i);
    expect(container.textContent).not.toMatch(/data health/i);
  });

  it('only at the root — drilling into a project does not repeat them', () => {
    const g = freshGraph();
    const c = ctx({ focus: g.roots[0]!.id }, g);
    render(<MapScreen ctx={c} />);
    expect(screen.queryByText('⚠ NO PROJECT — orphan tasks')).toBeNull();
  });

  it('an orphan row opens the detail editor like any other row', () => {
    const c = ctx();
    render(<MapScreen ctx={c} />);
    fireEvent.click(screen.getByText('Shower'));
    expect(c.up).toHaveBeenCalledWith({ detail: 'o-r-shower' });
  });
});

// ── an orphan is a REAL node, not a display-only row ─────────────────────────

describe('orphan nodes go through the model layer like any other', () => {
  it('resolves through the index — so nothing behind the row is a dead end', () => {
    const g = freshGraph();
    expect(node(index(g), 'o-r-shower')?.title).toBe('Shower');
  });

  it('can be EDITED — `setVal` reaches into a bucket', () => {
    const g = freshGraph();
    const r = setVal(g, 'o-r-shower', 'side', 'Wellbeing');
    expect(r.node?.vals.side).toBe('Wellbeing');
    expect(node(index(r.graph), 'o-r-shower')?.vals.side).toBe('Wellbeing');
  });

  it('can be FILED — moving it into a project is the whole point of surfacing it', () => {
    const g = freshGraph();
    const target = g.roots[0]!.children[0]!;
    const r = move(g, 'o-t-1', target.id);
    expect(r.toast).toBe('Moved · synced');
    // It left the bucket…
    const bucket = (r.graph.orphans ?? []).find((b) => b.key === 'orphan_tasks');
    expect(bucket!.nodes.some((n) => n.id === 'o-t-1')).toBe(false);
    // …and arrived under the project.
    expect(node(index(r.graph), 'o-t-1')).toBeTruthy();
    const moved = (node(index(r.graph), target.id)!.children ?? []).some((c) => c.id === 'o-t-1');
    expect(moved).toBe(true);
  });
});

// ── cross-tab search ─────────────────────────────────────────────────────────

describe('cross-tab search — one box, three tabs', () => {
  it('from Strategies, finds a recurring item and says which tab it is on', () => {
    // The gap this closes: v4's Strategies tab filters `graph.strategies` and nothing else, so
    // "dishes" from here reported nothing at all.
    render(<StrategiesScreen ctx={ctx({ search: 'dishes' })} />);
    expect(screen.getByText('In Routines')).toBeTruthy();
    expect(screen.getByText('Do the dishes')).toBeTruthy();
  });

  it('from Routines, finds a strategy and says which tab it is on', () => {
    const c = ctx();
    const strategyTitle = c.graph.strategies[0]!.title;
    cleanup();
    render(<RoutinesScreen ctx={ctx({ search: strategyTitle })} />);
    expect(screen.getByText('In Strategies')).toBeTruthy();
    expect(screen.getByText(strategyTitle)).toBeTruthy();
  });

  it('from Map, finds a strategy — strategies are not in the tree the Map walks', () => {
    const c = ctx();
    const strategyTitle = c.graph.strategies[0]!.title;
    cleanup();
    render(<MapScreen ctx={ctx({ search: strategyTitle })} />);
    expect(screen.getByText('In Strategies')).toBeTruthy();
  });

  it('does not list a hit twice — the Map already shows recurring items in its flat search', () => {
    // The trap this guards: v4's Map search walks the WHOLE tree, so recurring items are already
    // in its own list even though Routines "owns" them. Grouping by owning tab alone would print
    // every one of them a second time under "In Routines".
    render(<MapScreen ctx={ctx({ search: 'dishes' })} />);
    expect(screen.getAllByText('Do the dishes')).toHaveLength(1);
  });

  it('an UNFILED recurring is listed by Routines itself, not punted to the Map', () => {
    // CHANGED 2026-07-18 by June's correction. This previously asserted "In Map", because
    // RoutinesScreen grouped strictly by parent and an orphan has none — so an unparented
    // recurring appeared on NEITHER tab, and after Task 11 only in Map's bucket.
    //
    // Her point: "Don't recurring tasks show in both map and routines tabs?" They do — Map
    // renders RECURRING as a leaf of its parent and this tab groups them by that same parent.
    // A PARENTED routine was therefore on two tabs and an unparented one on one. That is an
    // asymmetry, not a design decision, so Routines now carries the same bucket.
    render(<RoutinesScreen ctx={ctx({ search: 'shower' })} />);
    expect(screen.getByText('Shower')).toBeTruthy();
    // It is in this tab's OWN list now, so the cross-tab block must not also advertise it.
    expect(screen.queryByText('In Map')).toBeNull();
  });

  it('an unfiled recurring appears on the Routines tab with no search at all', () => {
    render(<RoutinesScreen ctx={ctx()} />);
    expect(screen.getByText('Shower')).toBeTruthy();
    // Under the bucket's own label, which comes from the endpoint, not a string invented here.
    expect(screen.getByText(/NO PROJECT/)).toBeTruthy();
  });

  it('renders nothing at all when the box is empty', () => {
    const { container } = render(<MapScreen ctx={ctx()} />);
    expect(container.textContent).not.toContain('Also matching on other tabs');
  });

  it('renders nothing when every match is already in this tab’s own list', () => {
    const c = ctx();
    const goalTitle = c.graph.roots[0]!.title;
    cleanup();
    const { container } = render(<MapScreen ctx={ctx({ search: goalTitle })} />);
    expect(container.textContent).not.toContain('Also matching on other tabs');
  });
});
