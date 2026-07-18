/**
 * Every mutation must SAY what it means on the wire.
 *
 * ── why this is tested at all ────────────────────────────────────────────────
 * A mutation that changes local state and emits no `write` looks completely correct in the UI
 * and in every existing test — and loses the edit on reload. That is the built-but-dead shape
 * `docs/BUILD_DOC.md` §3 exists to prevent, arriving through the one door the type system
 * cannot close (`write` is optional, because a no-op legitimately has none).
 *
 * So the assertion here is coverage: for each mutation, a SUCCESSFUL call carries an intent, a
 * no-op carries none, and the two mutations with no endpoint say so explicitly rather than
 * reporting a success that will not survive a refresh.
 */
import { describe, expect, it } from 'vitest';
import type { Graph } from '../types.ts';
import {
  addChild, clearVal, del, move, setTitle, setType, setVal,
  toggleActive, toggleDone, toggleMulti,
} from '../mutations.ts';

function graph(): Graph {
  return {
    roots: [
      { id: 'g1', level: 'GOAL', type: 'Goal', title: 'A goal', vals: {}, children: [
        { id: 'p1', level: 'PROJECT', type: 'Project', title: 'A project', vals: {}, children: [
          { id: 't1', level: 'TASK', type: 'Task', title: 'A task', vals: { status: 'Ready' }, children: [] },
          { id: 'r1', level: 'RECURRING', type: 'Recurring', title: 'A routine', vals: {}, children: [] },
        ] },
        { id: 'p2', level: 'PROJECT', type: 'Project', title: 'Another project', vals: {}, children: [] },
      ] },
    ],
    strategies: [],
    orphans: [],
  };
}

describe('write intents', () => {
  it('setVal patches exactly the one key it changed', () => {
    expect(setVal(graph(), 'p1', 'engagement', 'Steady').write).toEqual({
      op: 'patchVals', id: 'p1', vals: { engagement: 'Steady' },
    });
  });

  it('toggleMulti patches the JOINED set, not the option tapped', () => {
    const once = toggleMulti(graph(), 't1', 'access', 'Involves-leaving-house');
    expect(once.write).toEqual({
      op: 'patchVals', id: 't1', vals: { access: 'Involves-leaving-house' },
    });
    const twice = toggleMulti(once.graph, 't1', 'access', 'Induces-pain');
    expect(twice.write).toEqual({
      op: 'patchVals', id: 't1', vals: { access: 'Involves-leaving-house, Induces-pain' },
    });
  });

  it('setTitle patches the title', () => {
    expect(setTitle(graph(), 't1', 'renamed').write).toEqual({
      op: 'patchTitle', id: 't1', title: 'renamed',
    });
  });

  it('move re-parents against the chosen destination', () => {
    expect(move(graph(), 't1', 'p2').write).toEqual({ op: 'move', id: 't1', parentId: 'p2' });
  });

  it('del archives', () => {
    expect(del(graph(), 't1').write).toEqual({ op: 'archive', id: 't1' });
  });

  it('toggleDone completes, and un-completes on the way back', () => {
    const done = toggleDone(graph(), 't1');
    expect(done.write).toEqual({ op: 'complete', id: 't1', done: true });
    expect(toggleDone(done.graph, 't1').write).toEqual({ op: 'complete', id: 't1', done: false });
  });

  /** The polarity flip of contract §6 Q3 happens once, here, not at 30 call sites. */
  it('toggleActive INVERTS paused into active', () => {
    const paused = toggleActive(graph(), 'r1');   // paused: undefined -> true
    expect(paused.write).toEqual({ op: 'recurringActive', id: 'r1', active: false });
    expect(toggleActive(paused.graph, 'r1').write).toEqual({
      op: 'recurringActive', id: 'r1', active: true,
    });
  });

  /**
   * `api_write.create_child` REFUSES an empty title (400), because an empty name matches every
   * other empty-named object under `gsdo_objects.create`'s dedup-by-name. v4 creates blank and
   * fills in afterwards, so the intent must carry a placeholder or every create fails.
   */
  it('addChild sends a non-empty title and the level it computed', () => {
    const w = addChild(graph(), 'p1', 'Task', () => 'tmp').write;
    expect(w).toEqual({
      op: 'create', tempId: 'tmp', level: 'TASK', title: 'Untitled task', parentId: 'p1',
    });
  });

  it('addChild files a Strategy at the top level, ignoring the parent', () => {
    const w = addChild(graph(), 'p1', 'Strategy', () => 'tmp').write;
    expect(w).toMatchObject({ level: 'STRATEGY', parentId: null });
  });

  /** No endpoint — must be REPORTED, never shown as a success that vanishes on reload. */
  it('clearVal and setType declare themselves unsupported', () => {
    expect(clearVal(graph(), 't1', 'status').write).toEqual({
      op: 'unsupported', id: 't1', what: 'inherit again (clear-field)',
    });
    expect(setType(graph(), 't1', 'Recurring').write).toEqual({
      op: 'unsupported', id: 't1', what: 'change the type',
    });
  });

  it('a no-op carries NO intent, so nothing is sent', () => {
    expect(setVal(graph(), 'nope', 'engagement', 'Steady').write).toBeUndefined();
    expect(move(graph(), 't1', 'nope').write).toBeUndefined();
    expect(del(graph(), 'nope').write).toBeUndefined();
    // The leaf guard refuses and changes nothing — it must not write either.
    expect(setType(graph(), 'p1', 'Task').write).toBeUndefined();
  });
});
