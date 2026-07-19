import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT CHECKING A STEP INSIDE A WORK BLOCK MUST WRITE.
 *
 * This is `chunkBlock` (see `chunkBlock.test.tsx`) one level deeper. The block header check
 * means "I did a chunk today" and must NEVER finish the project. An arc STEP is different: each
 * step carries a REAL Anytype task id, so checking it off completes that task and nothing else.
 *
 * Before this seam existed, `ArcStep.tsx` called `ctx.applyPlan(toggleArcStep(...))`.
 * `PlanResult` is `{plan, toast}` — there is no `write` on it and `applyPlan` makes no network
 * call. So June tapped a step, read "Nice — one down", and it was gone on reload. Verified
 * against her live plan 2026-07-19: three arc-carrying items, every step carrying a real id,
 * including "Cancel food stamps" and "Respond to Gabe's email".
 *
 * `POST /api/complete` already implemented this. `complete_task_row` (`server.py:163`)
 * dispatches as-needed → recurring → `is_block_item` → real task; a step id is none of the
 * first three, so it lands on `task_actions.complete_task`. Nothing called it.
 *
 * Assertions are POSITIVE — they name the request that must go out and the state that must be
 * true afterwards. "The parent project was not marked done" also passes against a control wired
 * to nothing at all, so it is only ever asserted ALONGSIDE the request that did go out.
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

/** The block's own id — its `project_id` on the wire, per `adapt.ts`. */
const BLOCK_ID = 'bafyproj';
/** The real Anytype TASK id of the step being checked. This is what must reach the server. */
const STEP_ID = 'bafystep2';

const TREE = {
  nodes: [
    {
      id: BLOCK_ID,
      title: 'Life admin',
      level: 'project',
      vals: { done: false },
      children: [
        { id: 'bafystep1', title: 'Back up dotfiles', level: 'task', vals: { done: true }, children: [] },
        { id: STEP_ID, title: 'Cancel food stamps', level: 'task', vals: { done: false }, children: [] },
        { id: 'bafystep3', title: 'Decide about the card offer', level: 'task', vals: { done: false }, children: [] },
      ],
    },
  ],
  strategies: [],
  orphans: {},
};

/**
 * A priority-shaped plan carrying one block with a three-step arc, in the shape `/api/plan`
 * really answers (verified live 2026-07-19). `planFromLive` folds a priority day's flat
 * `items` into ONE unlabelled block, so the step's address is band 0, item 0, step n.
 */
function livePlan(states: [string, string, string] = ['done', 'here', 'ahead']) {
  return {
    shape: 'priority',
    header: '',
    woven_frame: 'Today.',
    generated_at: '2026-07-19T09:00:00',
    items: [
      {
        block: true,
        project_id: BLOCK_ID,
        task: 'Work on Life admin',
        time: '',
        chunk_min: 45,
        arc: [
          { text: 'Back up dotfiles', state: states[0], id: 'bafystep1' },
          { text: 'Cancel food stamps', state: states[1], id: STEP_ID },
          { text: 'Decide about the card offer', state: states[2], id: 'bafystep3' },
        ],
      },
    ],
  };
}

function hydrate(plan: unknown = livePlan()) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: plan };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings')
      return { ok: true, data: { backend: 'mistral', options: [], include_hobby_block: false } };
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
  // ⚠ Waits for the PLAN to be in state, not merely for the fetch to have been issued. These
  // tests address a step by its position in the plan, so a mount that has fired the requests but
  // not yet applied the answers resolves that address against an empty plan — which reads as
  // "the step is not there" and passes nothing to the server. That is a harness artefact, and it
  // looked exactly like the defect under test.
  await waitFor(() => expect(h.result.current.plan.blocks.length).toBeGreaterThan(0));
  return h;
}

/** The step under test, addressed the way `ArcStep` addresses it. */
const REF = { id: STEP_ID, bandIndex: 0, itemIndex: 0, stepIndex: 1 };

function arcOf(result: { current: { plan: { blocks: { items: unknown[] }[] } } }) {
  const item = result.current.plan.blocks[0]!.items[0] as { arc?: { state: string; id?: string }[] };
  return item.arc!;
}

describe('checking a step inside a work block completes that task on the server', () => {
  it('issues POST /api/complete carrying the STEP’s own task id, not the block’s', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: STEP_ID, done: true }, plan: livePlan(['done', 'done', 'here']) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, true);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/complete', { id: STEP_ID });
  });

  it('issues POST /api/uncomplete when she reopens a step', async () => {
    hydrate(livePlan(['done', 'done', 'here']));
    send.mockResolvedValue({
      ok: true,
      data: { uncompleted: { id: STEP_ID, done: false }, plan: livePlan(['done', 'ahead', 'here']) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, false);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/uncomplete', { id: STEP_ID });
  });

  it('takes the refreshed plan from the response, so the check survives a reload', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: STEP_ID, done: true }, plan: livePlan(['done', 'done', 'here']) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, true);
    });

    // The SERVER's record of the arc, adopted. This is what a reload reads back — the optimistic
    // change alone dies with the page.
    expect(arcOf(result).map((s) => s.state)).toEqual(['done', 'done', 'here']);
  });

  it('leaves the parent project unfinished — a step is one task, not the project', async () => {
    hydrate();
    send.mockResolvedValue({
      ok: true,
      data: { completed: { id: STEP_ID, done: true }, plan: livePlan(['done', 'done', 'here']) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, true);
    });

    // Asserted alongside the request that DID go out, so this cannot pass against a dead control.
    expect(send).toHaveBeenCalledWith('POST', '/api/complete', { id: STEP_ID });
    expect(send).toHaveBeenCalledTimes(1);
    expect(result.current.idx.byId.get(BLOCK_ID)!.vals['done']).toBe(false);
  });
});

describe('the success signal waits for the server', () => {
  it('checks the box immediately but claims nothing until the request resolves', async () => {
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
      done = result.current.completeArcStep(REF, true);
    });

    // In flight: the optimistic plan edit has landed, INCLUDING spec §14's advance of the next
    // step from `ahead` to `here` — and no claim about saving has been made yet.
    expect(arcOf(result).map((s) => s.state)).toEqual(['done', 'done', 'here']);
    expect(result.current.toast).toBeNull();

    await act(async () => {
      settle({
        ok: true,
        data: { completed: { id: STEP_ID, done: true }, plan: livePlan(['done', 'done', 'here']) },
      });
      await done;
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Nice — one down');
  });

  it('says "Reopened" once a reopen is confirmed', async () => {
    hydrate(livePlan(['done', 'done', 'here']));
    send.mockResolvedValue({
      ok: true,
      data: { uncompleted: { id: STEP_ID, done: false }, plan: livePlan(['done', 'ahead', 'here']) },
    });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, false);
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Reopened');
  });
});

describe('a step that did not save says so', () => {
  it('reports the server error and puts the arc back exactly as it was', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'could not reach the server' });
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep(REF, true);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(result.current.toast?.msg).toContain('could not reach the server');
    // The WHOLE arc is restored, not just the tapped step. `toggleArcStep` is not its own
    // inverse: re-toggling step 1 would leave step 2 promoted to `here`, so a rollback that
    // re-toggled would leave the wrong step highlighted as the current one.
    expect(arcOf(result).map((s) => s.state)).toEqual(['done', 'here', 'ahead']);
  });

  it('refuses a step with no id rather than sending an empty one', async () => {
    hydrate();
    const { result } = await mount();

    await act(async () => {
      await result.current.completeArcStep({ ...REF, id: '' }, true);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(send).not.toHaveBeenCalled();
    // Nothing moved on screen either — a silent local toggle would look exactly like a save.
    expect(arcOf(result).map((s) => s.state)).toEqual(['done', 'here', 'ahead']);
  });

  it('reports an address that resolves to no step instead of going quiet', async () => {
    hydrate();
    const { result } = await mount();

    await act(async () => {
      // `toggleArcStep` answers a bad address with a SILENT no-op — same plan back, no toast.
      // Left alone that is a checkbox that is tapped and does nothing, forever.
      await result.current.completeArcStep({ ...REF, stepIndex: 99 }, true);
    });

    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(send).not.toHaveBeenCalled();
  });
});
