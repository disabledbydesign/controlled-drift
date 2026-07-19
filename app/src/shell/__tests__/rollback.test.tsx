import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * What a failed write is allowed to undo — and what it must leave alone.
 *
 * Found by the cross-family review gate, 2026-07-18. `rollback` restored a whole-graph snapshot
 * taken when the write STARTED, so any edit she made while that write was in flight was wiped
 * off the screen when it failed — even though that second edit's own write had succeeded on the
 * server. The screen and Anytype then disagreed, with nothing on screen saying so.
 *
 * The 600ms title debounce makes the window wide enough to hit by typing normally: rename a
 * task, tap a checkbox on another row before the rename lands, watch the rename fail.
 *
 * A comment above `graphRef` claimed the rollback already edited the live graph rather than
 * replacing it. It was aspirational, and it is why nobody looked. Both are fixed together.
 */

const send = vi.fn();
/**
 * Two rooted nodes is the whole fixture this needs: the point is which of them a rollback
 * touches, not what is on them. LIVE mode, not `fixture` — `apply` short-circuits before the
 * network in fixture mode, so a fixture-mode test would assert nothing about writes at all.
 */
const TREE = {
  nodes: [
    { id: 'n-a', title: 'Call the surgeon', level: 'TASK', vals: {}, children: [] },
    { id: 'n-b', title: 'Update the CV', level: 'TASK', vals: {}, children: [] },
  ],
  strategies: [],
  orphans: {},
};
vi.mock('../../api/client.ts', () => ({
  apiGet: vi.fn(async (path: string) =>
    path === '/api/tree'
      ? { ok: true, data: TREE }
      : { ok: false, error: 'not part of this test' },
  ),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';
import { setVal, toggleDone } from '../../model/mutations.ts';

beforeEach(() => send.mockReset());
afterEach(cleanup);

/** Mount live and wait for the tree to land, so there is a real graph to write against. */
async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(h.result.current.graph.roots.length).toBe(2));
  return h;
}

/**
 * Every node, flattened, carrying `vals` — not just id and title.
 *
 * ⚠ The first version of this helper returned `{id, title}` only, and the mutation check caught
 * it: `toggleDone` writes `vals.done`, so both tests passed against the broken rollback they
 * were written to catch. A test that cannot see the field under test is worse than no test,
 * because it reports the bug as fixed.
 */
function flatten(graph: { roots: unknown[] }) {
  const flat: Array<{ id: string; title: string; vals: Record<string, unknown> }> = [];
  const walk = (ns: unknown[]): void => {
    (ns as Array<{ id: string; title: string; vals: Record<string, unknown>; children: unknown[] }>)
      .forEach((n) => {
        flat.push({ id: n.id, title: n.title, vals: { ...n.vals } });
        walk(n.children);
      });
  };
  walk(graph.roots);
  return flat;
}

/** One node by id, with its values — what the assertions actually compare. */
function pick(graph: { roots: unknown[] }, id: string) {
  return flatten(graph).find((n) => n.id === id);
}

describe('a failed write undoes itself and nothing else', () => {
  it('leaves an edit made to ANOTHER row while the write was in flight', async () => {
    const { result } = await mount();
    const a = { id: 'n-a' };
    const b = { id: 'n-b' };

    // The failing write on A, held open so B can be edited underneath it.
    let settle: (v: { ok: false; error: string }) => void = () => {};
    send.mockImplementationOnce(
      () => new Promise((res) => { settle = res as typeof settle; }),
    );

    act(() => { result.current.apply(setVal(result.current.graph, a.id, 'duration', 45)); });

    // Her second edit, on a DIFFERENT row, while A's write is still open.
    // A realistic `/api/complete` body. It matters that this carries `done`: the success path
    // merges `Boolean(confirmed['done'])` into the node, so an empty body would uncheck the box
    // itself and the test would be measuring its own mock rather than the rollback.
    send.mockImplementationOnce(async () => ({
      ok: true,
      data: { completed: { done: true, status: 'Done' } },
    }));
    act(() => { result.current.apply(toggleDone(result.current.graph, b.id)); });
    const bAfterEdit = pick(result.current.graph, b.id);
    expect(bAfterEdit?.vals['done']).toBe(true);   // the edit really landed before A failed

    // Now A fails.
    await act(async () => { settle({ ok: false, error: 'Anytype said no' }); });

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));

    // A is reverted — that part already worked.
    expect(pick(result.current.graph, a.id)?.vals['duration']).toBeUndefined();
    // B is untouched. THIS is the assertion the snapshot rollback fails.
    expect(pick(result.current.graph, b.id)).toEqual(bAfterEdit);
  });

  it('still reverts the row the failed write was actually about', async () => {
    const { result } = await mount();
    const a = { id: 'n-a' };
    const before = result.current.graph;

    send.mockImplementationOnce(async () => ({ ok: false, error: 'Anytype said no' }));
    await act(async () => { result.current.apply(setVal(before, a.id, 'duration', 999)); });

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(pick(result.current.graph, a.id)).toEqual(pick(before, a.id));
    expect(pick(result.current.graph, a.id)?.vals['duration']).toBeUndefined();
  });
});
