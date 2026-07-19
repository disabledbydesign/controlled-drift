import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT CHECKING A WORK BLOCK IS ALLOWED TO CLAIM, AND WHAT IT MUST WRITE.
 *
 * The check used to write `ui.chunked` and nothing else — UI state that dies on reload. She
 * checked a block off, read "Done", reloaded, and it was gone. `POST /api/complete` already
 * implements this correctly: `plan_store.is_block_item` routes a block id to the chunk log
 * (`chunk_log.log_chunk`) and flips `did_chunk_today` on the cached plan row. It does NOT
 * write a done status to the underlying project.
 *
 * Three things every test below is here to hold:
 *
 * 1. **The request goes out, carrying the block's real id.** A block's id is its `project_id`
 *    on the wire (`api/adapt.ts` planFromLive), which is what `is_block_item` matches.
 * 2. **The success signal comes only after the server answers.** `logDay` is the model.
 * 3. **The state is keyed by that id, not by the slot the block sits in.** `bandIndex-itemIndex`
 *    is reassigned by every regeneration, so a persisted check keyed that way would reattach to
 *    whatever item now occupies the slot — the wrong row showing as done.
 *
 * Assertions are POSITIVE: they name the request that must go out and the value that must be
 * true afterwards. "A wrong write did not happen" passes just as well against a control wired
 * to nothing at all.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';

/** The block id as the live plan carries it — the project id, per `adapt.ts`. */
const BLOCK_ID = 'bafyproj';

/**
 * A tree holding that project as a real node, so "the project is not marked finished" can be
 * asserted on an object that exists rather than on an absence.
 */
const TREE = {
  nodes: [
    {
      id: BLOCK_ID,
      title: 'IOP and recovery',
      level: 'project',
      vals: { done: false },
      children: [],
    },
  ],
  strategies: [],
  orphans: {},
};

/** A priority-shaped plan carrying the block row, in the shape `/api/plan` really answers. */
function livePlan(didChunkToday: boolean) {
  return {
    shape: 'priority',
    header: '',
    woven_frame: 'Today.',
    generated_at: '2026-07-18T09:00:00',
    items: [
      {
        block: true,
        project_id: BLOCK_ID,
        task: 'Work on IOP and recovery',
        time: '',
        chunk_min: 45,
        did_chunk_today: didChunkToday,
      },
    ],
  };
}

function hydrate(plan: unknown = livePlan(false)) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: plan };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    // Not this test's concern (Task 10 added the read) — answered so it doesn't raise a
    // spurious failure toast that these tests' own assertions would then trip over.
    if (path === '/api/settings') return { ok: true, data: { backend: 'mistral', options: [], include_hobby_block: false } };
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  send.mockReset();
  get.mockReset();
});

afterEach(cleanup);

async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  return h;
}

describe('checking a work block records a chunk on the server', () => {
  it('issues POST /api/complete carrying the block’s project id', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: BLOCK_ID, did_chunk_today: true, block: true }, plan: livePlan(true) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, true);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/complete', { id: BLOCK_ID });
  });

  it('issues POST /api/uncomplete when she un-checks it', async () => {
    hydrate(livePlan(true));
    send.mockResolvedValue({
      ok: true,
      data: {
        uncompleted: { id: BLOCK_ID, did_chunk_today: false, block: true },
        plan: livePlan(false),
      },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, false);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/uncomplete', { id: BLOCK_ID });
  });

  it('keys the checked state by the block’s id, not by the slot it sits in', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: BLOCK_ID, did_chunk_today: true, block: true }, plan: livePlan(true) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, true);
    });

    // The id is the key. A slot address ('0-0') would reattach to a different item after the
    // next generation, which is exactly the wrong-row-shows-done bug.
    expect(result.current.ui.chunked[BLOCK_ID]).toBe(true);
    expect(Object.keys(result.current.ui.chunked)).toEqual([BLOCK_ID]);
  });

  it('takes the refreshed plan from the response, so the check survives a reload', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: BLOCK_ID, did_chunk_today: true, block: true }, plan: livePlan(true) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, true);
    });

    const item = result.current.plan.blocks[0]!.items[0]!;
    expect(item.kind).toBe('block');
    // `did_chunk_today` is the server's own record of the chunk, now carried on the plan the
    // surface renders — which is what a reload reads back.
    expect(item.kind === 'block' && item.didChunkToday).toBe(true);
  });

  it('leaves the underlying project unfinished — a chunk is time spent, not a project closed', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: BLOCK_ID, did_chunk_today: true, block: true }, plan: livePlan(true) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, true);
    });

    // The project node still reads as NOT done. `display_grain_design.md` §REVISION §B: the
    // block header check means "did a chunk today", never "this project is finished."
    expect(result.current.idx.byId.get(BLOCK_ID)!.vals['done']).toBe(false);
    expect(send).toHaveBeenCalledTimes(1);
  });
});

describe('the success signal waits for the server', () => {
  it('raises no success while the request is still in flight, and one once it resolves', async () => {
    hydrate();
    let settle: (v: unknown) => void = () => {};
    send.mockReturnValue(
      new Promise((resolve) => {
        settle = resolve;
      }),
    );
    const { result } = await mount();

    let done: Promise<void> = Promise.resolve();
    await act(async () => {
      done = result.current.chunkBlock(BLOCK_ID, true);
    });

    // In flight: the box is already checked (optimistic VISUAL state is allowed) and no claim
    // about saving has been made yet.
    expect(result.current.ui.chunked[BLOCK_ID]).toBe(true);
    expect(result.current.toast).toBeNull();

    await act(async () => {
      settle({
        ok: true,
        data: {
          completed: { id: BLOCK_ID, did_chunk_today: true, block: true },
          plan: livePlan(true),
        },
      });
      await done;
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Done');
  });

  it('says "Reopened" once an un-check is confirmed', async () => {
    hydrate(livePlan(true));
    send.mockResolvedValue({
      ok: true,
      data: {
        uncompleted: { id: BLOCK_ID, did_chunk_today: false, block: true },
        plan: livePlan(false),
      },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, false);
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Reopened');
  });
});

describe('a failed chunk tells her it did not save', () => {
  it('reports the server error and puts the box back to unchecked', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'could not reach the server' });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, true);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(result.current.toast?.msg).toContain('could not reach the server');
    // The optimistic check is undone, so the screen matches what the server holds.
    expect(result.current.ui.chunked[BLOCK_ID]).toBe(false);
  });

  it('reports an un-check that failed, and leaves the box checked', async () => {
    hydrate(livePlan(true));
    send.mockResolvedValue({ ok: false, error: 'could not reach the server' });
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock(BLOCK_ID, false);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.ui.chunked[BLOCK_ID]).toBe(true);
  });

  it('refuses a block with no id rather than writing an empty key', async () => {
    hydrate();
    const { result } = await mount();

    await act(async () => {
      await result.current.chunkBlock('', true);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(result.current.ui.chunked).toEqual({});
    expect(send).not.toHaveBeenCalled();
  });
});
