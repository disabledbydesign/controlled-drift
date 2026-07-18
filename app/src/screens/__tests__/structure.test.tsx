/**
 * Behaviour tests for the three structure tabs and their panels (Task 6).
 *
 * These pin the four things this task is most likely to get quietly wrong:
 *   1. the Map is a DRILL-IN, not a nested tree — nothing indents, the chevron changes focus
 *   2. the picker EXCLUDES the moved node's own subtree (dropping it reaches a silent dead end
 *      in `move()`, which returns no toast and no ui patch, so the picker would never close)
 *   3. `subtreeVis` keeps an ancestor visible when only a descendant matches
 *   4. `sideOf` inherits DOWN from an ancestor and is truthiness-based, unlike `effective`
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { defaultSchema, seed, seedStrategies } from '../../fixtures/index.ts';
import { applySchema, index } from '../../model/index.ts';
import type { Graph, ModelNode } from '../../model/index.ts';
import { sideOf } from '../../model/index.ts';
import type { PanelCtx, PanelUi } from '../../components/panels/index.ts';
import { PickerPage } from '../../components/panels/index.ts';
import { MapScreen, subtreeVis } from '../MapScreen.tsx';
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
  };
}

// ── the Map is a drill-in ──────────────────────────────────────────────────────

describe('MapScreen — drill-in, not a nested tree', () => {
  it('renders only the top level at root, not the whole tree', () => {
    const c = ctx();
    render(<MapScreen ctx={c} />);
    // Every goal is present…
    for (const g of c.graph.roots) expect(screen.getByText(g.title)).toBeTruthy();
    // …and none of their children are, because nothing nests.
    const firstChild = c.graph.roots[0]!.children[0]!;
    expect(screen.queryByText(firstChild.title)).toBeNull();
  });

  it('every row sits at depth 0 — no indentation anywhere', () => {
    const { container } = render(<MapScreen ctx={ctx()} />);
    // v4's rule: paddingLeft = 8 + depth*16, so depth 0 is exactly 8px.
    const padded = Array.from(container.querySelectorAll<HTMLElement>('div[style*="padding-left"]'));
    const rowPads = padded.map((e) => e.style.paddingLeft).filter((p) => p.endsWith('px'));
    expect(rowPads.length).toBeGreaterThan(0);
    for (const p of rowPads) expect(['8px', '12px']).toContain(p); // 12px = the breadcrumb bar
  });

  it('the chevron sets focus rather than expanding in place', () => {
    const c = ctx();
    render(<MapScreen ctx={c} />);
    const goal = c.graph.roots[0]!;
    fireEvent.click(screen.getAllByLabelText('expand')[0]!);
    expect(c.up).toHaveBeenCalledWith({ focus: goal.id, menuFor: null, chipEdit: null });
  });

  it('with focus set, shows that node’s children and a breadcrumb back out', () => {
    const g = freshGraph();
    const goal = g.roots[0]!;
    const c = ctx({ focus: goal.id }, g);
    render(<MapScreen ctx={c} />);
    expect(screen.getByText('root')).toBeTruthy();
    expect(screen.getByText(goal.title)).toBeTruthy(); // as a crumb
    for (const kid of goal.children) expect(screen.getByText(kid.title)).toBeTruthy();
  });

  it('the root crumb clears focus', () => {
    const g = freshGraph();
    const c = ctx({ focus: g.roots[0]!.id }, g);
    render(<MapScreen ctx={c} />);
    fireEvent.click(screen.getByText('root'));
    expect(c.up).toHaveBeenCalledWith({ focus: null, menuFor: null, chipEdit: null });
  });

  it('a title filter abandons the drill-in for a flat list — no breadcrumb', () => {
    const g = freshGraph();
    const deep = g.roots[0]!.children[0]!;
    const c = ctx({ search: deep.title }, g);
    render(<MapScreen ctx={c} />);
    expect(screen.queryByText('root')).toBeNull();
    expect(screen.getByText(deep.title)).toBeTruthy();
  });

  it('says so when a filter matches nothing', () => {
    render(<MapScreen ctx={ctx({ search: 'zzzznotathing' })} />);
    expect(screen.getByText('Nothing matches')).toBeTruthy();
  });
});

// ── subtreeVis ────────────────────────────────────────────────────────────────

describe('subtreeVis', () => {
  const leaf = (over: Partial<ModelNode> = {}): ModelNode => ({
    id: 'x',
    level: 'TASK',
    type: 'Task',
    title: 'Order rivets',
    vals: {},
    children: [],
    ...over,
  });

  it('keeps an ancestor visible when only a descendant matches', () => {
    const parent: ModelNode = {
      id: 'p',
      level: 'PROJECT',
      type: 'Project',
      title: 'Quiet',
      vals: { status: 'Parked' },
      children: [leaf()],
    };
    const f = { q: '', hideInactive: true, sideFilter: 'all' };
    expect(subtreeVis(index({ roots: [parent], strategies: [] }), parent, f)).toBe(true);
  });

  it('hides a node whose whole subtree fails', () => {
    const n = leaf({ vals: { done: true } });
    const f = { q: '', hideInactive: true, sideFilter: 'all' };
    expect(subtreeVis(index({ roots: [n], strategies: [] }), n, f)).toBe(false);
  });

  it('passes a node with no side at all when the Side filter is "all"', () => {
    const n = leaf();
    const i = index({ roots: [n], strategies: [] });
    expect(sideOf(i, n)).toBeNull();
    expect(subtreeVis(i, n, { q: '', hideInactive: false, sideFilter: 'all' })).toBe(true);
    // …and fails it under any specific Side, since it inherits none.
    expect(subtreeVis(i, n, { q: '', hideInactive: false, sideFilter: 'Work' })).toBe(false);
  });

  it('filters on an INHERITED side, not just an own one', () => {
    const kid = leaf({ id: 'k', vals: {} });
    const parent: ModelNode = {
      id: 'p',
      level: 'PROJECT',
      type: 'Project',
      title: 'Home',
      vals: { side: 'Daily life' },
      children: [kid],
    };
    const i = index({ roots: [parent], strategies: [] });
    expect(subtreeVis(i, kid, { q: '', hideInactive: false, sideFilter: 'Daily life' })).toBe(true);
    expect(subtreeVis(i, kid, { q: '', hideInactive: false, sideFilter: 'Work' })).toBe(false);
  });
});

describe('sideOf', () => {
  it('starts at the node itself — its own value wins over an ancestor’s', () => {
    const kid: ModelNode = {
      id: 'k',
      level: 'TASK',
      type: 'Task',
      title: 'k',
      vals: { side: 'Work' },
      children: [],
    };
    const parent: ModelNode = {
      id: 'p',
      level: 'PROJECT',
      type: 'Project',
      title: 'p',
      vals: { side: 'Daily life' },
      children: [kid],
    };
    const i = index({ roots: [parent], strategies: [] });
    expect(sideOf(i, kid)).toBe('Work');
  });

  it('is TRUTHINESS-based, so an own empty value keeps walking up — unlike effective()', () => {
    const kid: ModelNode = {
      id: 'k',
      level: 'TASK',
      type: 'Task',
      title: 'k',
      vals: { side: '' },
      children: [],
    };
    const parent: ModelNode = {
      id: 'p',
      level: 'PROJECT',
      type: 'Project',
      title: 'p',
      vals: { side: 'Daily life' },
      children: [kid],
    };
    const i = index({ roots: [parent], strategies: [] });
    // `effective()` would STOP at the present-but-empty key and report an intentional "none".
    // These two rules are deliberately different in v4 and are not harmonised.
    expect(sideOf(i, kid)).toBe('Daily life');
  });

  it('returns null when nothing in the chain names a side', () => {
    const n: ModelNode = { id: 'n', level: 'GOAL', type: 'Goal', title: 'n', vals: {}, children: [] };
    expect(sideOf(index({ roots: [n], strategies: [] }), n)).toBeNull();
  });
});

// ── the picker ────────────────────────────────────────────────────────────────

describe('PickerPage', () => {
  /** The first project in the fixture graph that actually has children. */
  function movable(g: Graph): ModelNode {
    for (const goal of g.roots) {
      for (const p of goal.children) if (p.children.length) return p;
    }
    throw new Error('fixture has no project with children');
  }

  it('renders nothing when neither moveFor nor addParentFor is set', () => {
    const { container } = render(<PickerPage ctx={ctx()} />);
    expect(container.firstChild).toBeNull();
  });

  it('⚠ EXCLUDES the moved node and its whole subtree from the destinations', () => {
    const g = freshGraph();
    const n = movable(g);
    render(<PickerPage ctx={ctx({ moveFor: n.id }, g)} />);
    expect(screen.queryByText(n.title)).toBeNull();
    for (const kid of n.children) expect(screen.queryByText(kid.title)).toBeNull();
  });

  it('still offers other branches as destinations', () => {
    const g = freshGraph();
    const n = movable(g);
    render(<PickerPage ctx={ctx({ moveFor: n.id }, g)} />);
    const other = g.roots.find((r) => !r.children.includes(n))!;
    expect(screen.getByText(other.title)).toBeTruthy();
  });

  it('never lists leaves (TASK / RECURRING / STRATEGY) as destinations', () => {
    const g = freshGraph();
    render(<PickerPage ctx={ctx({ moveFor: movable(g).id }, g)} />);
    const leafTitles: string[] = [];
    const walk = (nodes: ModelNode[]) => {
      for (const n of nodes) {
        if (['TASK', 'RECURRING'].includes(n.level)) leafTitles.push(n.title);
        walk(n.children);
      }
    };
    walk(g.roots);
    for (const t of leafTitles) expect(screen.queryByText(t)).toBeNull();
  });

  it('adding a Task offers only schedulable containers as choosable', () => {
    const g = freshGraph();
    render(<PickerPage ctx={ctx({ addParentFor: 'Task' }, g)} />);
    // A GOAL is shown (you must be able to walk through it) but is NOT choosable, so the
    // "choose" affordance count is strictly less than the number of visible rows.
    expect(screen.getByText(g.roots[0]!.title)).toBeTruthy();
    expect(screen.queryAllByText('choose').length).toBe(0); // goals only at the top level
  });

  it('offers the top-level escape hatch only when adding a Project', () => {
    const g = freshGraph();
    const { rerender } = render(<PickerPage ctx={ctx({ addParentFor: 'Project' }, g)} />);
    expect(screen.getByText('+ At top level (no goal yet)')).toBeTruthy();
    rerender(<PickerPage ctx={ctx({ addParentFor: 'Task' }, g)} />);
    expect(screen.queryByText('+ At top level (no goal yet)')).toBeNull();
  });

  it('Cancel clears every picker field, including the expansion state', () => {
    const c = ctx({ moveFor: freshGraph().roots[0]!.children[0]!.id });
    render(<PickerPage ctx={c} />);
    fireEvent.click(screen.getByText('Cancel'));
    expect(c.up).toHaveBeenCalledWith({
      moveFor: null,
      addParentFor: null,
      pickerFilter: '',
      pickerExpanded: {},
    });
  });

  it('a destination filter forces every branch open, so deep matches are reachable', () => {
    const g = freshGraph();
    // Pick a project nested under a goal; with no filter it is hidden behind a collapsed goal.
    const goal = g.roots[0]!;
    const kid = goal.children.find((k) => k.level !== 'TASK' && k.level !== 'RECURRING')!;
    render(<PickerPage ctx={ctx({ addParentFor: 'Project' }, g)} />);
    expect(screen.queryByText(kid.title)).toBeNull();
    cleanup();
    render(<PickerPage ctx={ctx({ addParentFor: 'Project', pickerFilter: kid.title }, g)} />);
    expect(screen.getByText(kid.title)).toBeTruthy();
  });
});

// ── Routines ──────────────────────────────────────────────────────────────────

describe('RoutinesScreen', () => {
  it('groups every recurring under its parent’s path', () => {
    const g = freshGraph();
    const c = ctx({}, g);
    render(<RoutinesScreen ctx={c} />);
    const recs: ModelNode[] = [];
    const walk = (nodes: ModelNode[]) => {
      for (const n of nodes) {
        if (n.level === 'RECURRING') recs.push(n);
        walk(n.children);
      }
    };
    walk(g.roots);
    expect(recs.length).toBeGreaterThan(0);
    for (const r of recs) expect(screen.getByText(r.title)).toBeTruthy();
  });

  it('the cadence chips filter to as-needed only', () => {
    const g = freshGraph();
    render(<RoutinesScreen ctx={ctx({ recFilter: 'asneeded' }, g)} />);
    const scheduled: ModelNode[] = [];
    const walk = (nodes: ModelNode[]) => {
      for (const n of nodes) {
        if (n.level === 'RECURRING' && n.vals.unit !== 'as_needed') scheduled.push(n);
        walk(n.children);
      }
    };
    walk(g.roots);
    for (const r of scheduled) expect(screen.queryByText(r.title)).toBeNull();
  });

  it('collapsing a group header hides its rows but keeps the header', () => {
    const g = freshGraph();
    let parentId = '';
    let recTitle = '';
    const walk = (nodes: ModelNode[]) => {
      for (const n of nodes) {
        const recs = n.children.filter((c) => c.level === 'RECURRING');
        if (recs.length && !parentId) {
          parentId = n.id;
          recTitle = recs[0]!.title;
        }
        walk(n.children);
      }
    };
    walk(g.roots);
    render(<RoutinesScreen ctx={ctx({ collapsed: { [parentId]: true } }, g)} />);
    expect(screen.queryByText(recTitle)).toBeNull();
  });

  it('the title filter narrows the list', () => {
    render(<RoutinesScreen ctx={ctx({ search: 'zzzznotathing' })} />);
    expect(screen.getByText('No recurring items')).toBeTruthy();
  });
});

// ── Strategies ────────────────────────────────────────────────────────────────

describe('StrategiesScreen', () => {
  it('lists every strategy', () => {
    const g = freshGraph();
    render(<StrategiesScreen ctx={ctx({}, g)} />);
    for (const s of g.strategies) expect(screen.getByText(s.title)).toBeTruthy();
  });

  it('the title filter narrows the list', () => {
    render(<StrategiesScreen ctx={ctx({ search: 'zzzznotathing' })} />);
    expect(screen.getByText('No strategies — add one with +')).toBeTruthy();
  });

  it('hides the When/Status block until the Filter button is pressed', () => {
    const c = ctx();
    render(<StrategiesScreen ctx={c} />);
    expect(screen.queryByText('Active only')).toBeNull();
    fireEvent.click(screen.getByText('Filter'));
    expect(c.up).toHaveBeenCalledWith({ stratFilterOpen: true });
  });

  it('shows the When/Status block when it is open', () => {
    render(<StrategiesScreen ctx={ctx({ stratFilterOpen: true })} />);
    expect(screen.getByText('Active only')).toBeTruthy();
    expect(screen.getByText('When')).toBeTruthy();
  });

  it('offers Clear only while a filter is actually narrowing the list', () => {
    const { rerender } = render(<StrategiesScreen ctx={ctx()} />);
    expect(screen.queryByText('Clear')).toBeNull();
    rerender(<StrategiesScreen ctx={ctx({ stratStatus: 'active' })} />);
    expect(screen.getByText('Clear')).toBeTruthy();
  });

  it('the "When" filter matches the v4 default of Always for an unset value', () => {
    const g = freshGraph();
    const unset = g.strategies.filter((s) => !s.vals.when);
    render(<StrategiesScreen ctx={ctx({ stratWhen: 'Always' }, g)} />);
    for (const s of unset) expect(screen.getByText(s.title)).toBeTruthy();
  });
});
