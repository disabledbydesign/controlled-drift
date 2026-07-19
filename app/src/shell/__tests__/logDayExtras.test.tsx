import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT A FRICTION ENTRY IS ALLOWED TO CARRY, AND WHAT THE OLD PATH MUST KEEP SENDING.
 *
 * `logDay` gained a third argument so a friction entry can carry a picture of the screen June
 * was looking at, which way she opened the capture, and what she drew on it. The whole point of
 * building the payload key by key rather than spreading an object is the SECOND describe block
 * below: the Add tab's Log button has always called `logDay(text, tags)` with two arguments, 45
 * entries have been written by it, and that call must keep putting a byte-identical body on the
 * wire. `{ ...extras }` or `shot: extras?.shot` would both smuggle `shot: undefined` into the
 * unchanged path.
 *
 * The other thing held here is the ordering `logDay` has always had: the success toast is raised
 * ONLY after the server confirms. An earlier version flashed "Logged" unconditionally, which is
 * the worse half of a silent-drop bug — a dropped entry still looked like a save. Adding a
 * snapshot must not reintroduce that, so the failure case is asserted with extras present too.
 *
 * Harness matches `chunkBlock.test.tsx`: the client module is mocked, the real hook is mounted.
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

const send = vi.fn();
const get = vi.fn();

vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { useAppState } from '../useAppState.ts';
import type { LogExtras, Mark } from '../useAppState.ts';

const TREE = { nodes: [], strategies: [], orphans: {} };

function hydrate() {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { shape: 'priority', items: [] } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings')
      return {
        ok: true,
        data: { backend: 'mistral', options: [], include_hobby_block: false },
      };
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  send.mockReset();
  get.mockReset();
  hydrate();
});

afterEach(cleanup);

async function mount() {
  const h = renderHook(() => useAppState('live'));
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  return h;
}

/** The body of the single POST that went out. */
function sentBody(): Record<string, unknown> {
  const call = send.mock.calls.find((c) => c[1] === '/api/logday');
  expect(call).toBeDefined();
  return call![2] as Record<string, unknown>;
}

describe('a capture carries its context through to /api/logday', () => {
  it('sends the snapshot, the view and the pressed element', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'], shot: 'a.png' } });
    const { result } = await mount();

    const target = {
      tag: 'button',
      label: 'Not today',
      text: 'Not today',
      data: {},
      chain: [{ tag: 'button', label: 'Not today' }],
    };

    await act(async () => {
      await result.current.logDay('this row is wrong', ['issue'], {
        shot: 'data:image/png;base64,AAAA',
        view: { tab: 'today', detailId: null },
        target,
      });
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/logday', {
      text: 'this row is wrong',
      tags: ['issue'],
      shot: 'data:image/png;base64,AAAA',
      view: { tab: 'today', detailId: null },
      target,
    });
  });

  it('records which way in she used, so an unused entry point can be found', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.logDay('x', ['issue'], { via: 'longpress' });
    });

    expect(sentBody()['via']).toBe('longpress');
  });

  it('sends drawn marks together with the size they were drawn against', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
    const { result } = await mount();

    const marks: Mark[] = [
      { points: [[10, 10], [20, 20]], box: [10, 10, 10, 10], closed: false },
    ];

    await act(async () => {
      await result.current.logDay('x', ['issue'], {
        shot: 'data:image/png;base64,AAAA',
        marks,
        size: { w: 392, h: 860 },
      });
    });

    const body = sentBody();
    expect(body['marks']).toEqual(marks);
    // Mark coordinates are in image pixels, so they are meaningless without the dimensions.
    expect(body['size']).toEqual({ w: 392, h: 860 });
  });

  it('omits marks when nothing was drawn, rather than sending an empty list', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.logDay('x', ['issue'], {
        shot: 'data:image/png;base64,AAAA',
        marks: [],
      });
    });

    expect(sentBody()).not.toHaveProperty('marks');
  });

  it('drops a null field rather than putting a null on the wire', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
    const { result } = await mount();

    // The overlay passes `shot: null` when the render failed — that is a text-only entry, not
    // an entry with a null image.
    const extras: LogExtras = { shot: null, view: null, target: null, via: null, size: null };
    await act(async () => {
      await result.current.logDay('render failed but I still want to say this', ['issue'], extras);
    });

    expect(sentBody()).toEqual({
      text: 'render failed but I still want to say this',
      tags: ['issue'],
    });
  });
});

describe('the unchanged path stays byte-identical', () => {
  /**
   * ⚠ THE MOST IMPORTANT TEST IN THIS FILE. The Add tab's Log button calls `logDay(text, tags)`
   * and nothing else. Its request body must be exactly what it has always been — no `shot` key
   * carrying `undefined`, no `view: null`. `toEqual` alone would not catch an `undefined`-valued
   * key, so the key set is asserted directly.
   */
  it('omits the extra keys entirely when there are none', async () => {
    send.mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
    const { result } = await mount();

    await act(async () => {
      await result.current.logDay('plain', ['issue']);
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/logday', { text: 'plain', tags: ['issue'] });
    // `toEqual` treats `{a: 1, b: undefined}` as equal to `{a: 1}`, so the key set is the real
    // guard: a present-but-undefined `shot` still serialises differently and still changes the
    // shape a reader sees.
    expect(Object.keys(sentBody()).sort()).toEqual(['tags', 'text']);
  });

  it('still trims and refuses empty text before reaching the network', async () => {
    const { result } = await mount();

    let landed = true;
    await act(async () => {
      landed = await result.current.logDay('   ', ['day']);
    });

    expect(landed).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });
});

describe('the toast still waits for the server, snapshot or not', () => {
  it('raises no success while the request is in flight, and one once it resolves', async () => {
    let settle: (v: unknown) => void = () => {};
    send.mockReturnValue(
      new Promise((resolve) => {
        settle = resolve;
      }),
    );
    const { result } = await mount();

    let done: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      done = result.current.logDay('this row is wrong', ['issue'], {
        shot: 'data:image/png;base64,AAAA',
      });
    });

    // In flight, nothing has claimed to have saved.
    expect(result.current.toast).toBeNull();

    await act(async () => {
      settle({ ok: true, data: { ok: true, tags: ['issue'], shot: 'a.png' } });
      await done;
    });

    expect(result.current.toast?.kind).toBe('success');
    expect(result.current.toast?.msg).toBe('Logged');
  });

  it('says plainly that nothing was saved when a capture fails', async () => {
    send.mockResolvedValue({ ok: false, error: "that snapshot's bytes are not a PNG" });
    const { result } = await mount();

    let landed = true;
    await act(async () => {
      landed = await result.current.logDay('this row is wrong', ['issue'], {
        shot: 'data:image/png;base64,AAAA',
      });
    });

    // False so the overlay keeps her text and her drawing rather than clearing them.
    expect(landed).toBe(false);
    expect(result.current.toast?.kind).toBe('failure');
    expect(result.current.toast?.msg).toContain('NOT logged');
    expect(result.current.toast?.msg).toContain("that snapshot's bytes are not a PNG");
  });
});
