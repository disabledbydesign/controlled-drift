import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup, waitFor } from '@testing-library/react';

/**
 * WHAT SETTINGS IS ALLOWED TO CLAIM, AND WHAT IT MUST WRITE.
 *
 * Neither control reached the server before this: `ctx.up({backend:id})` and
 * `ctx.up({hobby:!hobby})` only ever touched the in-memory UI bag, and the option list itself
 * was three hardcoded strings (`claude | local | api`) that do not match what the server accepts
 * (`mistral | openrouter | claude | local`, `server.py` `VALID_BACKENDS`). `api` would 400 on
 * contact; `mistral` — June's decided production default — was not offered at all. Because
 * nothing was ever sent, choosing either produced no visible error — she would never learn it
 * did nothing.
 *
 * Two things every test below is here to hold:
 *
 * 1. **The option list rendered is the one the server actually returned**, read from
 *    `GET /api/settings` on hydration — never a hardcoded list. `backend_descriptor` is computed
 *    server-side so the id/label/mechanism/model are the truth, not marketing copy that can
 *    drift from it.
 * 2. **Selecting an option sends the value the server accepts**, and the success signal
 *    (`logDay`'s rule) comes only once the server has confirmed it — a refusal must put the
 *    choice back, not leave a phantom selection standing.
 *
 * Assertions are POSITIVE: they name the request that must go out and the value that must be
 * true afterwards. "A wrong write did not happen" passes just as well against a control wired to
 * nothing at all.
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

/** The real `GET /api/settings` shape, verbatim from `curl -s localhost:5050/api/settings`. */
const SETTINGS_RESPONSE = {
  backend: 'mistral',
  options: [
    { id: 'mistral', label: 'Mistral', mechanism: 'Mistral API (direct)', model: 'mistral-large-latest' },
    { id: 'openrouter', label: 'OpenRouter', mechanism: 'OpenRouter API', model: 'anthropic/claude-sonnet-4' },
    { id: 'claude', label: 'Claude', mechanism: 'claude -p CLI (your subscription)', model: null },
    { id: 'local', label: 'Local', mechanism: 'on-device (MLX)', model: 'mlx-community/Qwen2.5-7B-Instruct-4bit' },
  ],
  include_hobby_block: false,
  health: {},
};

function hydrate(settings: unknown = SETTINGS_RESPONSE) {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { empty: true } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings') return { ok: true, data: settings };
    // Not this test's concern (the honest-values thread added the read) — answered so it
    // doesn't raise a spurious failure toast that these tests' own assertions would trip over.
    if (path === '/api/actions') return { ok: true, data: { presets: [] } };
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
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/settings'));
  return h;
}

describe('hydration reads the real backend list from the server', () => {
  it('exposes exactly the options GET /api/settings returned, not a hardcoded list', async () => {
    hydrate();
    const { result } = await mount();

    await waitFor(() => expect(result.current.backendOptions.length).toBe(4));
    // `mistral` is June's production default and was not in the old hardcoded three
    // (`claude | local | api`) at all — its presence here is the mutation-sensitive assertion.
    expect(result.current.backendOptions).toEqual([
      { id: 'mistral', label: 'Mistral', mechanism: 'Mistral API (direct)', model: 'mistral-large-latest' },
      { id: 'openrouter', label: 'OpenRouter', mechanism: 'OpenRouter API', model: 'anthropic/claude-sonnet-4' },
      { id: 'claude', label: 'Claude', mechanism: 'claude -p CLI (your subscription)', model: null },
      { id: 'local', label: 'Local', mechanism: 'on-device (MLX)', model: 'mlx-community/Qwen2.5-7B-Instruct-4bit' },
    ]);
  });

  it('sets the current choice from the server, not the client default', async () => {
    hydrate();
    const { result } = await mount();

    await waitFor(() => expect(result.current.ui.backend).toBe('mistral'));
    expect(result.current.ui.hobby).toBe(false);
  });

  it('maps the server key `include_hobby_block` onto the client key `hobby`', async () => {
    hydrate({ ...SETTINGS_RESPONSE, include_hobby_block: true });
    const { result } = await mount();

    await waitFor(() => expect(result.current.ui.hobby).toBe(true));
  });

  it('a failed settings read leaves no options rather than fabricating a list', async () => {
    get.mockImplementation(async (path: string) => {
      if (path === '/api/tree') return { ok: true, data: { nodes: [], strategies: [], orphans: {} } };
      if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
      if (path === '/api/plan') return { ok: true, data: { empty: true } };
      if (path === '/api/periods') return { ok: true, data: { periods: [] } };
      if (path === '/api/settings') return { ok: false, error: 'could not reach the server' };
      return { ok: false, error: 'not part of this test' };
    });
    const { result } = await mount();

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(result.current.backendOptions).toEqual([]);
  });
});

describe('choosing a backend sends the id the server accepts', () => {
  it('issues POST /api/settings carrying `backend`, unmapped', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { backend: 'openrouter', include_hobby_block: false } });
    const { result } = await mount();

    await act(async () => {
      result.current.saveSettings({ backend: 'openrouter' });
      await Promise.resolve();
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/settings', { backend: 'openrouter' });
  });

  it('updates the choice optimistically, before the server has answered', async () => {
    hydrate();
    let settle: (v: unknown) => void = () => {};
    send.mockReturnValue(
      new Promise((resolve) => {
        settle = resolve;
      }),
    );
    const { result } = await mount();

    act(() => {
      result.current.saveSettings({ backend: 'local' });
    });

    expect(result.current.ui.backend).toBe('local');
    expect(result.current.toast).toBeNull();

    await act(async () => {
      settle({ ok: true, data: { backend: 'local', include_hobby_block: false } });
      await Promise.resolve();
    });

    expect(result.current.toast?.kind).toBe('success');
  });

  it('a refused write puts the previous choice back and says so', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'unknown backend' });
    const { result } = await mount();

    await waitFor(() => expect(result.current.ui.backend).toBe('mistral'));

    act(() => {
      result.current.saveSettings({ backend: 'local' });
    });

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(result.current.toast?.msg).toContain('NOT saved');
    expect(result.current.toast?.msg).toContain('unknown backend');
    // The optimistic move is undone — the screen matches what the server actually holds.
    expect(result.current.ui.backend).toBe('mistral');
  });
});

describe('the hobby toggle translates the client key to the server key', () => {
  it('sends `include_hobby_block`, not `hobby`, on the wire', async () => {
    hydrate();
    send.mockResolvedValue({ ok: true, data: { backend: 'mistral', include_hobby_block: true } });
    const { result } = await mount();

    await act(async () => {
      result.current.saveSettings({ hobby: true });
      await Promise.resolve();
    });

    expect(send).toHaveBeenCalledWith('POST', '/api/settings', { include_hobby_block: true });
  });

  it('a failed toggle reverts `ui.hobby`', async () => {
    hydrate();
    send.mockResolvedValue({ ok: false, error: 'could not reach the server' });
    const { result } = await mount();

    await waitFor(() => expect(result.current.ui.hobby).toBe(false));

    act(() => {
      result.current.saveSettings({ hobby: true });
    });

    await waitFor(() => expect(result.current.toast?.kind).toBe('failure'));
    expect(result.current.ui.hobby).toBe(false);
  });
});
