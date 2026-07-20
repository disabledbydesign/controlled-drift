/**
 * THE WIRING TEST — is the friction capture actually REACHABLE?
 *
 * Tasks 1–6 built every piece of this feature and each one passes its own tests. That is exactly
 * the state this repo has been bitten by before: 14 of 19 write endpoints existed in the server
 * with nothing able to reach them, every test green, the feature doing nothing. So these tests
 * deliberately do NOT unit-test the mount — they drive the real `Surface` with the real
 * `useFrictionCapture`, the real `AnnotateOverlay` and the real `logDay`, and assert that a click
 * on the button puts a body on the wire at `/api/logday`. Only the browser rasteriser
 * (`modern-screenshot`, which jsdom cannot run) and the HTTP client are stubbed.
 *
 * Three things are pinned that nothing else pins:
 *   1. the button and the overlay exist on BOTH shells, because they are mounted above the fork
 *   2. an in-progress capture SURVIVES crossing the 900px breakpoint — the whole reason the mount
 *      point is `Surface` and not `AppShell`/`DeskShell`
 *   3. the payload carries `view` and `via`, and carries NO key for anything absent
 *
 * Harness: `matchMedia` stub from `desk.test.tsx`, client mock from `logDayExtras.test.tsx`.
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor, act, within } from '@testing-library/react';
import { themes } from '@tokens';

const SHOT = 'data:image/png;base64,AAAA';

// jsdom cannot rasterise a DOM tree, so the renderer is stubbed. Everything between it and the
// server — `capture.ts`, `useFrictionCapture`, `AnnotateOverlay`, `Surface`, `logDay` — is real.
const domToPng = vi.fn();
vi.mock('modern-screenshot', () => ({ domToPng: (...a: unknown[]) => domToPng(...a) }));

const send = vi.fn();
const get = vi.fn();
vi.mock('../../api/client.ts', () => ({
  apiGet: (...a: unknown[]) => get(...a),
  apiSend: (...a: unknown[]) => send(...a),
}));

import { Surface, DESKTOP_MIN_WIDTH } from '../Surface.tsx';

const T = themes.celestial;

/** The `matchMedia` stub from `desk.test.tsx` — the only way to move the viewport mid-session. */
let listeners: Array<(e: MediaQueryListEvent) => void> = [];
let width = 420;

function setWidth(next: number) {
  const wasWide = width >= DESKTOP_MIN_WIDTH;
  width = next;
  const isWide = next >= DESKTOP_MIN_WIDTH;
  if (wasWide !== isWide) {
    act(() => listeners.forEach((l) => l({ matches: isWide } as MediaQueryListEvent)));
  }
}

const TREE = { nodes: [], strategies: [], orphans: {} };

function hydrate() {
  get.mockImplementation(async (path: string) => {
    if (path === '/api/tree') return { ok: true, data: TREE };
    if (path === '/api/schema') return { ok: true, data: { relations: {}, types: {} } };
    if (path === '/api/plan') return { ok: true, data: { shape: 'priority', items: [] } };
    if (path === '/api/periods') return { ok: true, data: { periods: [] } };
    if (path === '/api/settings')
      return { ok: true, data: { backend: 'mistral', options: [], include_hobby_block: false } };
    // Not this test's concern (the honest-values thread added the read) — answered so it
    // doesn't raise a spurious failure toast that these tests' own assertions would trip over.
    if (path === '/api/actions') return { ok: true, data: { presets: [] } };
    return { ok: false, error: 'not part of this test' };
  });
}

beforeEach(() => {
  listeners = [];
  width = 420;
  domToPng.mockReset().mockResolvedValue(SHOT);
  send.mockReset().mockResolvedValue({ ok: true, data: { ok: true, tags: ['issue'] } });
  get.mockReset();
  hydrate();
  vi.stubGlobal(
    'matchMedia',
    (q: string) =>
      ({
        media: q,
        get matches() {
          return width >= DESKTOP_MIN_WIDTH;
        },
        addEventListener: (_: string, l: (e: MediaQueryListEvent) => void) => listeners.push(l),
        removeEventListener: (_: string, l: (e: MediaQueryListEvent) => void) => {
          listeners = listeners.filter((x) => x !== l);
        },
      }) as unknown as MediaQueryList,
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/**
 * `source="live"` so `logDay` actually reaches the (mocked) client. In `'fixtures'` mode
 * `useAppState` sets `live = false` and `logDay` refuses before it ever builds a body, which
 * would make a send test assert nothing.
 */
async function mount() {
  const r = render(<Surface T={T} name="celestial" setTheme={() => {}} />);
  await waitFor(() => expect(get).toHaveBeenCalledWith('/api/periods'));
  return r;
}

const theButton = () => screen.getByRole('button', { name: /log what is wrong/i });

const dialog = () => screen.getByRole('dialog', { name: /log what is wrong here/i });

/**
 * The comment box and Send, scoped INSIDE the overlay. The real shell has textboxes of its own
 * (the Today ask box, the Map filter), so an unscoped `getByRole('textbox')` finds several and
 * throws — which is the difference between mounting this over the real app and testing it alone.
 */
const comment = () => within(dialog()).getByRole('textbox');
const sendBtn = () => within(dialog()).getByRole('button', { name: /^send$/i });

/** Open the capture from the quiet button and wait for the (async) snapshot to resolve. */
async function openCapture() {
  fireEvent.click(theButton());
  return waitFor(() => expect(dialog()).toBeTruthy());
}

/** The body of the POST that went out to the log endpoint. */
function sentBody(): Record<string, unknown> {
  const call = send.mock.calls.find((c) => c[1] === '/api/logday');
  expect(call).toBeDefined();
  return call![2] as Record<string, unknown>;
}

describe('the capture is reachable from every screen', () => {
  it('offers the button on the phone shell', async () => {
    setWidth(420);
    await mount();
    expect(theButton()).toBeTruthy();
  });

  it('offers the SAME button on the desktop shell — one mount above the fork, not two', async () => {
    setWidth(1440);
    await mount();
    // Exactly one, on either side of the breakpoint. Two would mean each shell grew its own.
    expect(screen.getAllByRole('button', { name: /log what is wrong/i })).toHaveLength(1);
  });

  it('is still there after a tab change, so it is not scoped to one screen', async () => {
    setWidth(420);
    await mount();
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    expect(theButton()).toBeTruthy();
  });

  it('does not appear in the picture it takes', async () => {
    setWidth(420);
    await mount();
    // The button carries the chrome attribute itself; `snapshot()`'s filter drops any element
    // that has it, which is what keeps it out of every image.
    expect(theButton().hasAttribute('data-cd-capture-chrome')).toBe(true);
  });

  it('opens the annotate overlay, and stands down while it is open', async () => {
    setWidth(420);
    await mount();
    await openCapture();
    expect(screen.queryByRole('button', { name: /log what is wrong here$/i })).toBeNull();
  });
});

describe('what the capture puts on the wire', () => {
  it('sends the comment, the picture, where she was and which way in she used', async () => {
    setWidth(420);
    await mount();
    await openCapture();

    fireEvent.change(comment(), { target: { value: 'this row is wrong' } });
    fireEvent.click(sendBtn());

    await waitFor(() => expect(send).toHaveBeenCalledWith('POST', '/api/logday', expect.anything()));
    const body = sentBody();
    expect(body['text']).toBe('this row is wrong');
    expect(body['tags']).toEqual(['issue']);
    // The quiet button is the way in, and Today is where she was — the two values the triage
    // pass reads to find the screen again.
    expect(body['via']).toBe('button');
    expect(body['view']).toEqual({ tab: 'today', detailId: null });
    expect(typeof body['shot']).toBe('string');
  });

  it('records the tab she was actually on, not a hardcoded one', async () => {
    setWidth(420);
    await mount();
    fireEvent.click(screen.getByRole('button', { name: 'Routines' }));
    await openCapture();

    fireEvent.change(comment(), { target: { value: 'wrong here too' } });
    fireEvent.click(sendBtn());

    await waitFor(() => expect(send).toHaveBeenCalled());
    expect(sentBody()['view']).toEqual({ tab: 'routines', detailId: null });
  });

  it('sends NO key for anything absent — nothing was drawn, so there are no marks', async () => {
    setWidth(420);
    await mount();
    await openCapture();
    fireEvent.change(comment(), { target: { value: 'no drawing' } });
    fireEvent.click(sendBtn());

    await waitFor(() => expect(send).toHaveBeenCalled());
    // ⚠ ASSERTED ON THE KEYS, not with `toHaveBeenCalledWith`. Vitest's deep equality treats
    // `{a: 1, b: undefined}` as equal to `{a: 1}`, so an object comparison CANNOT prove a key is
    // absent — and "only present keys are sent" is precisely the claim `logDay` makes.
    expect(Object.keys(sentBody()).sort()).toEqual(
      // `size` rides along with the picture — mark coordinates are meaningless without the
      // dimensions they were drawn against, so the overlay sends it whenever there is a canvas.
      // `marks` and `target` are the absent ones: nothing was drawn, and the quiet button
      // carries no pressed element.
      ['shot', 'size', 'tags', 'text', 'via', 'view'].sort(),
    );
  });

  it('closes on a confirmed write', async () => {
    setWidth(420);
    await mount();
    await openCapture();
    fireEvent.change(comment(), { target: { value: 'landed' } });
    fireEvent.click(sendBtn());
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    // …and the way back in is offered again.
    expect(theButton()).toBeTruthy();
  });

  it('keeps her comment on screen when the write fails', async () => {
    send.mockResolvedValue({ ok: false, error: 'the server said no' });
    setWidth(420);
    await mount();
    await openCapture();
    fireEvent.change(comment(), { target: { value: 'keep me' } });
    fireEvent.click(sendBtn());

    await waitFor(() => expect(send).toHaveBeenCalled());
    expect(dialog()).toBeTruthy();
    expect((comment() as HTMLTextAreaElement).value).toBe('keep me');
  });

  it('still opens, and still sends, when the picture could not be rendered', async () => {
    domToPng.mockRejectedValue(new Error('cannot rasterise'));
    setWidth(420);
    await mount();
    await openCapture();
    expect(within(dialog()).getByText(/could not take a picture/i)).toBeTruthy();

    fireEvent.change(comment(), { target: { value: 'text only' } });
    fireEvent.click(sendBtn());
    await waitFor(() => expect(send).toHaveBeenCalled());
    // No image, so no `shot` key — but the entry still lands with everything else.
    expect(Object.keys(sentBody()).sort()).toEqual(['tags', 'text', 'via', 'view'].sort());
  });
});

describe('why the mount point is Surface and not either shell', () => {
  it('an in-progress capture SURVIVES a resize across the 900px breakpoint', async () => {
    setWidth(1440);
    await mount();
    await openCapture();
    fireEvent.change(comment(), { target: { value: 'half a sentence she has not finished' } });

    // Cross to the phone shell. Had each shell owned the capture state, this would unmount one
    // and mount the other, and everything she had written would be gone.
    setWidth(420);

    expect(dialog()).toBeTruthy();
    expect((comment() as HTMLTextAreaElement).value).toBe('half a sentence she has not finished');
  });
});

describe('the quiet button and the persistent bars', () => {
  it('stands down while a failure bar is showing, so its dismiss stays reachable', async () => {
    send.mockResolvedValue({ ok: false, error: 'the server said no' });
    setWidth(420);
    await mount();
    await openCapture();
    fireEvent.change(comment(), { target: { value: 'boom' } });
    fireEvent.click(sendBtn());
    await waitFor(() => expect(send).toHaveBeenCalled());

    // Leave the overlay; the failure bar it raised is still up, and does not fade.
    fireEvent.click(within(dialog()).getByRole('button', { name: /cancel/i }));
    expect(screen.getByRole('alert')).toBeTruthy();
    // The bar is `bottom:22px` and full width — its ✕ sits exactly where the button would be.
    expect(screen.queryByRole('button', { name: /log what is wrong/i })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'dismiss' }));
    expect(theButton()).toBeTruthy();
  });
});
