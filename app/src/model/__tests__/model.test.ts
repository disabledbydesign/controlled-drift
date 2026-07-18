/**
 * Model-layer tests.
 *
 * These pin the LOGIC ported from v4, not the port's own conveniences — where
 * v4 does something surprising there is a test asserting the surprising thing,
 * so a later "cleanup" fails loudly instead of silently changing data.
 */

import { describe, it, expect } from 'vitest';

import { seed, seedStrategies, defaultSchema } from '../../fixtures/index.ts';
import type { Graph, ModelColors, ModelNode } from '../types.ts';
import {
  addChild,
  INHERIT,
  isOwnValue,
  hasSchedulableAncestor,
  applySchema,
  chipsFor,
  clearVal,
  del,
  effective,
  index,
  isInactive,
  move,
  node,
  pathTo,
  removeNode,
  setTitle,
  setType,
  setVal,
  sideColor,
  statusColor,
  toggleActive,
  toggleDone,
  toggleMulti,
  typeOptions,
} from '../index.ts';

// ── helpers ─────────────────────────────────────────────────────────────────

/** Deep-copied so a mutation in one test cannot leak into another. */
function freshGraph(): Graph {
  return {
    roots: JSON.parse(JSON.stringify(seed)) as ModelNode[],
    strategies: JSON.parse(JSON.stringify(seedStrategies)) as ModelNode[],
  };
}

const C: ModelColors = {
  dimmer: '#dim',
  blue: '#blue',
  green: '#green',
  amber: '#amber',
  teal: '#teal',
  purple: '#purple',
  orange: '#orange',
  red: '#red',
  strategy: '#strategy',
  horizon: '#horizon',
  side: '#side',
};

function n(
  id: string,
  level: ModelNode['level'],
  vals: ModelNode['vals'] = {},
  children: ModelNode[] = [],
): ModelNode {
  const type: ModelNode['type'] =
    level === 'GOAL'
      ? 'Goal'
      : level === 'TASK'
        ? 'Task'
        : level === 'RECURRING'
          ? 'Recurring'
          : level === 'STRATEGY'
            ? 'Strategy'
            : 'Project';
  return { id, level, type, title: id, vals, children };
}

// ── graph + indexing ────────────────────────────────────────────────────────

describe('index / node / pathTo', () => {
  it('indexes every node in the real fixture, roots and strategies alike', () => {
    const g = freshGraph();
    const idx = index(g);
    const count = (nodes: ModelNode[]): number =>
      nodes.reduce((acc, x) => acc + 1 + count(x.children), 0);
    expect(idx.byId.size).toBe(count(g.roots) + count(g.strategies));
    // strategies are indexed with a null parent (v4 constructor line 76)
    const s = g.strategies[0] as ModelNode;
    expect(idx.parentOf.get(s.id)).toBeNull();
  });

  it('pathTo returns root-first and includes the node itself', () => {
    const g: Graph = { roots: [n('g', 'GOAL', {}, [n('p', 'PROJECT', {}, [n('t', 'TASK')])])], strategies: [] };
    const idx = index(g);
    expect(pathTo(idx, 't').map((x) => x.id)).toEqual(['g', 'p', 't']);
  });

  it('pathTo on an unknown id is empty, node() is undefined', () => {
    const idx = index(freshGraph());
    expect(pathTo(idx, 'nope')).toEqual([]);
    expect(node(idx, 'nope')).toBeUndefined();
  });

  it('removeNode on an unknown id returns the SAME graph reference (v4 no-op)', () => {
    const g = freshGraph();
    expect(removeNode(g, 'nope').graph).toBe(g);
  });
});

// ── schema derivation ───────────────────────────────────────────────────────

describe('applySchema', () => {
  const derived = applySchema(defaultSchema);

  it('derives OPTS as copies, not references into the schema', () => {
    expect(derived.OPTS.side).toEqual(defaultSchema.relations.side.options);
    expect(derived.OPTS.side).not.toBe(defaultSchema.relations.side.options);
  });

  it('passes CTRL and TEXT through by reference, as v4 does', () => {
    expect(derived.CTRL).toBe(defaultSchema.controls);
    expect(derived.TEXT).toBe(defaultSchema.notes);
  });

  it('carries all 12 relation vocabularies', () => {
    expect(Object.keys(derived.OPTS)).toHaveLength(12);
  });
});

// ── effective(): the tri-state ──────────────────────────────────────────────

describe('effective — the inherit resolver', () => {
  const build = () =>
    index({
      roots: [
        n('goal', 'GOAL', { side: 'Work' }, [
          n('proj', 'PROJECT', {}, [
            n('sub', 'SUBPROJECT', { side: '' }, [n('task', 'TASK', {}), n('t2', 'TASK', {})]),
            n('plain', 'TASK', {}),
          ]),
        ]),
      ],
      strategies: [],
    });

  it('walks past an ancestor that has no key at all', () => {
    const idx = build();
    const t = node(idx, 'plain') as ModelNode;
    expect(effective(idx, t, 'side')).toEqual({ val: 'Work', from: 'goal' });
  });

  it('TRI-STATE: stops at an ancestor whose key is PRESENT BUT EMPTY', () => {
    // The intentional "none" on `sub` must win over the Goal's 'Work'.
    // Stopping on truthiness instead of presence would wrongly return 'Work'.
    const idx = build();
    const t = node(idx, 'task') as ModelNode;
    expect(effective(idx, t, 'side')).toEqual({ val: '', from: 'sub' });
  });

  it('distinguishes "inherited an empty" from "inherited nothing"', () => {
    const idx = build();
    const inheritedEmpty = effective(idx, node(idx, 'task') as ModelNode, 'side');
    const inheritedNothing = effective(idx, node(idx, 'plain') as ModelNode, 'nosuchkey');
    expect(inheritedEmpty.val).toBe('');
    expect(inheritedEmpty.from).toBe('sub'); // an ancestor answered
    expect(inheritedNothing.val).toBe('');
    expect(inheritedNothing.from).toBeNull(); // nobody answered
  });

  it('starts at the PARENT — a node never inherits from itself', () => {
    const idx = build();
    const sub = node(idx, 'sub') as ModelNode;
    // `sub` has its own side:'' but effective() reports what it WOULD inherit.
    expect(effective(idx, sub, 'side')).toEqual({ val: 'Work', from: 'goal' });
  });

  it('skips a key explicitly set to undefined and keeps walking (v4 !== undefined)', () => {
    const idx = index({
      roots: [n('g', 'GOAL', { side: 'Work' }, [n('p', 'PROJECT', { side: undefined }, [n('t', 'TASK')])])],
      strategies: [],
    });
    expect(effective(idx, node(idx, 't') as ModelNode, 'side')).toEqual({ val: 'Work', from: 'g' });
  });

  it('returns {val:"", from:null} at a root', () => {
    const idx = build();
    expect(effective(idx, node(idx, 'goal') as ModelNode, 'side')).toEqual({ val: '', from: null });
  });
});

// ── isInactive: every level ─────────────────────────────────────────────────

describe('isInactive', () => {
  it('GOAL — Parked or Achieved only', () => {
    expect(isInactive(n('a', 'GOAL', { status: 'Parked' }))).toBe(true);
    expect(isInactive(n('a', 'GOAL', { status: 'Achieved' }))).toBe(true);
    expect(isInactive(n('a', 'GOAL', { status: 'Active' }))).toBe(false);
    expect(isInactive(n('a', 'GOAL', {}))).toBe(false);
  });

  it('TASK — the done checkbox OR a Done/Parked status (both conditions, not one)', () => {
    expect(isInactive(n('a', 'TASK', { done: true }))).toBe(true);
    expect(isInactive(n('a', 'TASK', { status: 'Done' }))).toBe(true);
    expect(isInactive(n('a', 'TASK', { status: 'Parked' }))).toBe(true);
    expect(isInactive(n('a', 'TASK', { status: 'Blocked' }))).toBe(false);
    expect(isInactive(n('a', 'TASK', { done: false, status: 'Ready' }))).toBe(false);
  });

  it('RECURRING — paused only; status is ignored at this level', () => {
    expect(isInactive(n('a', 'RECURRING', { paused: true }))).toBe(true);
    expect(isInactive(n('a', 'RECURRING', { paused: false, status: 'Parked' }))).toBe(false);
  });

  it('STRATEGY — Retired only', () => {
    expect(isInactive(n('a', 'STRATEGY', { status: 'Retired' }))).toBe(true);
    expect(isInactive(n('a', 'STRATEGY', { status: 'Active' }))).toBe(false);
  });

  it('PROJECT / SUBPROJECT / WORKSTREAM — engagement Done, or status Parked/Inactive', () => {
    for (const lvl of ['PROJECT', 'SUBPROJECT', 'WORKSTREAM'] as const) {
      expect(isInactive(n('a', lvl, { engagement: 'Done' }))).toBe(true);
      expect(isInactive(n('a', lvl, { status: 'Parked' }))).toBe(true);
      expect(isInactive(n('a', lvl, { status: 'Inactive' }))).toBe(true);
      expect(isInactive(n('a', lvl, { engagement: 'Open', status: 'Active' }))).toBe(false);
      // 'Achieved' is a GOAL status and must NOT deactivate a project
      expect(isInactive(n('a', lvl, { status: 'Achieved' }))).toBe(false);
    }
  });
});

// ── colours + chips ─────────────────────────────────────────────────────────

describe('statusColor / sideColor', () => {
  it('maps known values and falls back to dimmer', () => {
    expect(statusColor('Steady', C)).toBe(C.green);
    expect(statusColor('Blocked', C)).toBe(C.red);
    expect(statusColor('In Design', C)).toBe(C.purple);
    expect(statusColor('Needs Clarifying', C)).toBe(C.amber);
    expect(statusColor('nonsense', C)).toBe(C.dimmer);
    expect(statusColor(undefined, C)).toBe(C.dimmer);
  });

  it('sideColor is ONE hue for every Side value — deliberately ignores its argument', () => {
    expect(sideColor('Work', C)).toBe(C.side);
    expect(sideColor('Fun / hobby', C)).toBe(C.side);
    expect(sideColor(undefined, C)).toBe(C.side);
  });
});

describe('chipsFor', () => {
  it('GOAL — status then horizon, both flagged unset when empty', () => {
    const chips = chipsFor(n('a', 'GOAL', {}), C);
    expect(chips.map((c) => [c.text, c.field, c.unset])).toEqual([
      ['set status', 'status', true],
      ['set horizon', 'horizon', true],
    ]);
  });

  it('RECURRING — as_needed short-circuits the interval phrasing', () => {
    expect(chipsFor(n('a', 'RECURRING', { unit: 'as_needed' }), C)).toEqual([
      { text: 'as needed', color: C.teal, field: 'unit' },
    ]);
  });

  it('RECURRING — pluralises only above 1 and defaults to "every week"', () => {
    expect(chipsFor(n('a', 'RECURRING', { count: 1, unit: 'day' }), C)[0]?.text).toBe('every day');
    expect(chipsFor(n('a', 'RECURRING', { count: 3, unit: 'week' }), C)[0]?.text).toBe(
      'every 3 weeks',
    );
    expect(chipsFor(n('a', 'RECURRING', {}), C)[0]?.text).toBe('every week');
  });

  it('PROJECT — engagement plus a side chip; WORKSTREAM gets engagement only', () => {
    expect(chipsFor(n('a', 'PROJECT', { engagement: 'Open', side: 'Work' }), C)).toEqual([
      { text: 'Open', color: C.blue, field: 'engagement', unset: false },
      { text: 'Work', color: C.side, field: 'side', unset: false },
    ]);
    expect(chipsFor(n('a', 'WORKSTREAM', { engagement: 'Open' }), C)).toHaveLength(1);
  });

  it('PROJECT — "Fun / hobby" is abbreviated to "hobby" on the chip', () => {
    expect(chipsFor(n('a', 'PROJECT', { side: 'Fun / hobby' }), C)[1]?.text).toBe('hobby');
  });

  it('STRATEGY — dims when retired, and defaults the when-chip to Always', () => {
    expect(chipsFor(n('a', 'STRATEGY', {}), C)).toEqual([
      { text: 'Active', color: C.strategy, field: 'status' },
      { text: 'when: Always', color: C.dimmer, field: 'when' },
    ]);
    expect(chipsFor(n('a', 'STRATEGY', { status: 'Retired' }), C)[0]?.color).toBe(C.dimmer);
  });
});

// ── typeOptions ─────────────────────────────────────────────────────────────

describe('typeOptions', () => {
  const idx = index({
    roots: [
      n('goal', 'GOAL', {}, [
        n('proj', 'PROJECT', {}, [n('task', 'TASK'), n('ws', 'WORKSTREAM')]),
      ]),
    ],
    strategies: [n('strat', 'STRATEGY')],
  });

  it('is null for levels that cannot convert', () => {
    expect(typeOptions(idx, node(idx, 'goal') as ModelNode)).toBeNull();
    expect(typeOptions(idx, node(idx, 'strat') as ModelNode)).toBeNull();
  });

  it('offers schedulable types under a project, and NOT "Project"', () => {
    expect(typeOptions(idx, node(idx, 'task') as ModelNode)).toEqual([
      'Task',
      'Recurring',
      'Subproject',
      'Workstream',
    ]);
  });

  it('offers only container types with no schedulable ancestor, and NOT "Subproject"', () => {
    expect(typeOptions(idx, node(idx, 'proj') as ModelNode)).toEqual(['Project', 'Workstream']);
  });
});

// ── mutations ───────────────────────────────────────────────────────────────

describe('setVal / setTitle / clearVal', () => {
  it('setVal writes one key, leaves the rest, and does not touch siblings', () => {
    const g: Graph = { roots: [n('g', 'GOAL', { status: 'Active', horizon: 'Ongoing' })], strategies: [] };
    const r = setVal(g, 'g', 'status', 'Parked');
    expect(r.toast).toBe('Saved');
    expect(r.node?.vals).toEqual({ status: 'Parked', horizon: 'Ongoing' });
    expect(g.roots[0]?.vals.status).toBe('Active'); // original untouched
  });

  it('setVal on an unknown id is a no-op with the same graph reference', () => {
    const g = freshGraph();
    const r = setVal(g, 'nope', 'status', 'Parked');
    expect(r.graph).toBe(g);
    expect(r.toast).toBeNull();
  });

  it('setTitle deliberately does NOT toast (it fires per keystroke)', () => {
    const g: Graph = { roots: [n('g', 'GOAL')], strategies: [] };
    const r = setTitle(g, 'g', 'Renamed');
    expect(r.node?.title).toBe('Renamed');
    expect(r.toast).toBeNull();
  });

  it('clearVal REMOVES the key rather than emptying it — the tri-state', () => {
    const g: Graph = { roots: [n('g', 'GOAL', { status: 'Active', horizon: 'Ongoing' })], strategies: [] };
    const r = clearVal(g, 'g', 'status');
    expect(Object.prototype.hasOwnProperty.call(r.node?.vals ?? {}, 'status')).toBe(false);
    expect(r.node?.vals.horizon).toBe('Ongoing');
    expect(r.toast).toBe('Inheriting');
  });
});

describe('toggleMulti', () => {
  it('adds, then removes, round-tripping through the comma-joined string', () => {
    const g: Graph = { roots: [n('t', 'TASK', {})], strategies: [] };
    const a = toggleMulti(g, 't', 'access', 'Induces-pain');
    expect(a.node?.vals.access).toBe('Induces-pain');
    const b = toggleMulti(a.graph, 't', 'access', 'Involves-bureaucracy');
    expect(b.node?.vals.access).toBe('Induces-pain, Involves-bureaucracy');
    const c = toggleMulti(b.graph, 't', 'access', 'Induces-pain');
    expect(c.node?.vals.access).toBe('Involves-bureaucracy');
  });

  it('handles the array form the live API returns (fixtures type it string | string[])', () => {
    const g: Graph = { roots: [n('t', 'TASK', { access: ['A', 'B'] })], strategies: [] };
    expect(toggleMulti(g, 't', 'access', 'C').node?.vals.access).toBe('A, B, C');
  });
});

describe('toggleDone', () => {
  it('checking off a TASK sets done and status Done', () => {
    const g: Graph = { roots: [n('t', 'TASK', { status: 'Ready' })], strategies: [] };
    const r = toggleDone(g, 't');
    expect(r.node?.vals).toEqual({ done: true, status: 'Done' });
    expect(r.toast).toBe('Done · synced');
  });

  it('reopening restores the task OWN status, not a blanket Ready', () => {
    const g: Graph = { roots: [n('t', 'TASK', { done: true, status: 'Blocked' })], strategies: [] };
    const r = toggleDone(g, 't');
    expect(r.node?.vals).toEqual({ done: false, status: 'Blocked' });
    expect(r.toast).toBe('Reopened');
  });

  it('reopening a task whose status is Done falls back to Ready', () => {
    const g: Graph = { roots: [n('t', 'TASK', { done: true, status: 'Done' })], strategies: [] };
    expect(toggleDone(g, 't').node?.vals.status).toBe('Ready');
  });

  it('a non-TASK level gets `done` flipped and NO status write', () => {
    const g: Graph = { roots: [n('p', 'PROJECT', { status: 'Active' })], strategies: [] };
    expect(toggleDone(g, 'p').node?.vals).toEqual({ done: true, status: 'Active' });
  });
});

describe('toggleActive', () => {
  it('flips `paused` (the inverse of the backend `active`) with matching toasts', () => {
    const g: Graph = { roots: [n('r', 'RECURRING', {})], strategies: [] };
    const off = toggleActive(g, 'r');
    expect(off.node?.vals.paused).toBe(true);
    expect(off.toast).toBe('Paused — out of plan');
    const on = toggleActive(off.graph, 'r');
    expect(on.node?.vals.paused).toBe(false);
    expect(on.toast).toBe('Active — in plan');
  });
});

describe('del', () => {
  it('removes the node AND its whole subtree', () => {
    const g: Graph = {
      roots: [n('g', 'GOAL', {}, [n('p', 'PROJECT', {}, [n('t1', 'TASK'), n('t2', 'TASK')]), n('p2', 'PROJECT')])],
      strategies: [],
    };
    const r = del(g, 'p');
    const idx = index(r.graph);
    expect(node(idx, 'p')).toBeUndefined();
    expect(node(idx, 't1')).toBeUndefined(); // children go with the parent
    expect(node(idx, 't2')).toBeUndefined();
    expect(node(idx, 'p2')).toBeDefined(); // sibling untouched
    expect(r.toast).toBe('Deleted · synced');
    expect(r.ui).toEqual({ detail: null, moveFor: null, menuFor: null, chipEdit: null });
  });

  it('deletes a strategy from the flat list', () => {
    const g = freshGraph();
    const sid = (g.strategies[0] as ModelNode).id;
    const r = del(g, sid);
    expect(r.graph.strategies.some((s) => s.id === sid)).toBe(false);
  });

  it('still toasts and clears the pane when the id is unknown (v4 behaviour)', () => {
    const g = freshGraph();
    const r = del(g, 'nope');
    expect(r.graph).toBe(g);
    expect(r.toast).toBe('Deleted · synced');
    expect(r.ui).not.toBeNull();
  });
});

describe('move', () => {
  it('reparents the node with its subtree and every value intact, appended last', () => {
    const g: Graph = {
      roots: [
        n('g', 'GOAL', {}, [
          n('a', 'PROJECT', {}, [n('t', 'TASK', { status: 'Blocked' }, [n('sub', 'TASK')])]),
          n('b', 'PROJECT', {}, [n('existing', 'TASK')]),
        ]),
      ],
      strategies: [],
    };
    const r = move(g, 't', 'b');
    const idx = index(r.graph);

    expect(pathTo(idx, 't').map((x) => x.id)).toEqual(['g', 'b', 't']);
    expect((node(idx, 'b') as ModelNode).children.map((c) => c.id)).toEqual(['existing', 't']);
    expect((node(idx, 'a') as ModelNode).children).toHaveLength(0);
    expect((node(idx, 't') as ModelNode).vals.status).toBe('Blocked');
    expect(node(idx, 'sub')).toBeDefined(); // subtree came along
    expect((node(idx, 't') as ModelNode).level).toBe('TASK'); // level is NOT recomputed
    expect(r.toast).toBe('Moved · synced');
    expect(r.ui).toEqual({ moveFor: null, menuFor: null, pickerFilter: '' });
  });

  it('refuses a move into the node own subtree (v4 had no such guard)', () => {
    const g: Graph = { roots: [n('p', 'PROJECT', {}, [n('c', 'PROJECT')])], strategies: [] };
    const r = move(g, 'p', 'c');
    expect(r.graph).toBe(g);
    expect(r.toast).toBeNull();
  });

  it('no-ops on an unknown source or target', () => {
    const g = freshGraph();
    const first = g.roots[0] as ModelNode;
    expect(move(g, 'nope', first.id).graph).toBe(g);
    expect(move(g, first.id, 'nope').graph).toBe(g);
  });
});

describe('setType', () => {
  it('converts a Task to a Subproject and KEEPS every field', () => {
    const g: Graph = {
      roots: [n('p', 'PROJECT', {}, [n('t', 'TASK', { status: 'Ready', due: '2026-07-20', duration: 30 })])],
      strategies: [],
    };
    const r = setType(g, 't', 'Subproject');
    expect(r.node?.type).toBe('Project');
    expect(r.node?.level).toBe('SUBPROJECT');
    expect(r.node?.vals).toEqual({ status: 'Ready', due: '2026-07-20', duration: 30 });
    expect(r.toast).toBe('Type → Subproject · fields kept');
  });

  it('maps each target to its (type, level) pair', () => {
    const g: Graph = { roots: [n('p', 'PROJECT', {}, [n('t', 'TASK')])], strategies: [] };
    const cases: [string, string, string][] = [
      ['Task', 'Task', 'TASK'],
      ['Recurring', 'Recurring', 'RECURRING'],
      ['Subproject', 'Project', 'SUBPROJECT'],
      ['Workstream', 'Project', 'WORKSTREAM'],
      ['Project', 'Project', 'PROJECT'],
    ];
    for (const [target, type, level] of cases) {
      const r = setType(g, 't', target);
      expect([r.node?.type, r.node?.level]).toEqual([type, level]);
    }
  });

  it('refuses to make a node with children into a leaf type, changing nothing', () => {
    const g: Graph = { roots: [n('p', 'PROJECT', {}, [n('c', 'TASK')])], strategies: [] };
    const r = setType(g, 'p', 'Task');
    expect(r.graph).toBe(g);
    expect(r.node).toBeNull();
    expect(r.toast).toBe('Can’t convert — has sub-items, move them first');
  });

  it('allows a leaf-type conversion once the node has no children', () => {
    const g: Graph = { roots: [n('p', 'PROJECT')], strategies: [] };
    expect(setType(g, 'p', 'Task').node?.level).toBe('TASK');
  });
});

describe('addChild', () => {
  const ids = () => {
    let i = 0;
    return () => 'new' + ++i;
  };

  it('derives the level from the TYPE for Goal / Task / Recurring / Strategy', () => {
    const g: Graph = { roots: [n('p', 'PROJECT')], strategies: [] };
    expect(addChild(g, 'p', 'Task', ids()).node?.level).toBe('TASK');
    expect(addChild(g, 'p', 'Recurring', ids()).node?.level).toBe('RECURRING');
    expect(addChild(g, 'p', 'Goal', ids()).node?.level).toBe('GOAL');
    expect(addChild(g, 'p', 'Strategy', ids()).node?.level).toBe('STRATEGY');
  });

  it('derives a Project level from the PARENT: root/Goal -> PROJECT', () => {
    const g: Graph = { roots: [n('g', 'GOAL')], strategies: [] };
    expect(addChild(g, 'g', 'Project', ids()).node?.level).toBe('PROJECT');
    expect(addChild(g, null, 'Project', ids()).node?.level).toBe('PROJECT');
  });

  it('a Project under a WORKSTREAM is another WORKSTREAM; under anything else a SUBPROJECT', () => {
    const g: Graph = { roots: [n('w', 'WORKSTREAM'), n('p', 'PROJECT')], strategies: [] };
    expect(addChild(g, 'w', 'Project', ids()).node?.level).toBe('WORKSTREAM');
    expect(addChild(g, 'p', 'Project', ids()).node?.level).toBe('SUBPROJECT');
  });

  it('places the new node under the parent, marked _new, blank, and opens it', () => {
    const g: Graph = { roots: [n('p', 'PROJECT')], strategies: [] };
    const r = addChild(g, 'p', 'Task', ids());
    const idx = index(r.graph);
    expect(pathTo(idx, 'new1').map((x) => x.id)).toEqual(['p', 'new1']);
    expect(r.node).toMatchObject({ title: '', vals: {}, children: [], _new: true });
    expect(r.ui).toEqual({ detail: 'new1', addOpen: false, addParentFor: null, pickerFilter: '' });
    expect(r.toast).toBe('Created · editing');
  });

  it('a Strategy goes to the flat strategies list even when a parent is given', () => {
    const g: Graph = { roots: [n('p', 'PROJECT')], strategies: [] };
    const r = addChild(g, 'p', 'Strategy', ids());
    expect(r.graph.strategies.map((s) => s.id)).toEqual(['new1']);
    expect(r.graph.roots[0]?.children).toHaveLength(0);
  });
});

// ── real-fixture smoke ──────────────────────────────────────────────────────

describe('against the real v4 fixture', () => {
  it('every node resolves, and a task inherits side from up the tree', () => {
    const g = freshGraph();
    const idx = index(g);
    for (const [id, nd] of idx.byId) expect(nd.id).toBe(id);

    // find any TASK with a PROJECT ancestor carrying a side
    let found = false;
    for (const [, nd] of idx.byId) {
      if (nd.level !== 'TASK') continue;
      const eff = effective(idx, nd, 'side');
      if (eff.from) {
        expect(typeof eff.val).toBe('string');
        found = true;
        break;
      }
    }
    expect(found).toBe(true);
  });
});

// ── gaps closed by the 2026-07-18 review gate ────────────────────────────────

describe('structural sharing', () => {
  /**
   * This is the ENTIRE justification for dropping v4's `parent` back-pointers:
   * a cyclic graph cannot be structurally shared, so every keystroke would deep
   * clone the tree. Path-copying is currently correct but was unpinned — without
   * this test a later "simplify" to a deep clone passes all other tests.
   */
  it('leaves untouched subtrees reference-identical after a deep edit', () => {
    const g = freshGraph();
    const idx = index(g);

    // Find a node that is NOT under roots[0], so roots[0] must be untouched.
    const target = [...idx.byId.values()].find(
      (n) => n.level === 'TASK' && pathTo(idx, n.id)[0]?.id !== g.roots[0]?.id,
    );
    expect(target).toBeTruthy();

    const r = setVal(g, target!.id, 'status', 'Blocked');
    expect(r.graph).not.toBe(g); // the edit did happen

    const untouched = g.roots.find((root) => root.id !== pathTo(idx, target!.id)[0]?.id);
    const after = r.graph.roots.find((root) => root.id === untouched?.id);
    expect(after).toBe(untouched); // same reference, not a copy
  });

  it('returns the SAME graph reference for a no-op, all the way up', () => {
    const g = freshGraph();
    expect(setVal(g, 'no-such-id', 'status', 'Ready').graph).toBe(g);
    expect(setTitle(g, 'no-such-id', 'x').graph).toBe(g);
    expect(clearVal(g, 'no-such-id', 'status').graph).toBe(g);
  });
});

describe('isOwnValue', () => {
  /**
   * The half of the tri-state that lives on the NODE rather than the ancestors.
   * `effective()` deliberately starts at the parent, so this is what tells a
   * caller "this node set it itself" vs "this is inherited". Task 5's
   * inheritRow depends on it; it had zero tests.
   */
  it('is true for a key present but EMPTY — an intentional none, not inheritance', () => {
    expect(isOwnValue(n('x', 'TASK', { side: '' }), 'side')).toBe(true);
  });

  it('is false for an absent key', () => {
    expect(isOwnValue(n('x', 'TASK', {}), 'side')).toBe(false);
  });

  it('is true even when the value is falsy but present', () => {
    expect(isOwnValue(n('x', 'TASK', { done: false }), 'done')).toBe(true);
  });
});

describe('INHERIT', () => {
  /**
   * v4:74. The model-layer half of the inheritance gate — WHICH fields inherit
   * at all. Pairs with hasSchedulableAncestor at v4:572. Applying effective()
   * to a field outside this set renders a wrong inheritance display with no
   * visual signal, which is why the set is pinned rather than re-derived.
   */
  it('contains exactly v4:74s three inheritable fields', () => {
    expect([...INHERIT].sort()).toEqual(['access', 'affective', 'blockMin']);
  });

  it('gates with hasSchedulableAncestor: a task under a project inherits', () => {
    const g = freshGraph();
    const idx = index(g);
    const task = [...idx.byId.values()].find((n) => n.level === 'TASK');
    expect(task).toBeTruthy();
    expect(INHERIT.has('access')).toBe(true);
    expect(hasSchedulableAncestor(idx, task!)).toBe(true);
    // and a field outside the set is not inheritable regardless of ancestry
    expect(INHERIT.has('status')).toBe(false);
  });
});
