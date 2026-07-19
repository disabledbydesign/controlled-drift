/**
 * Behaviour tests for the annotate overlay — the editor June actually touches when something on
 * screen is wrong.
 *
 * ⚠ `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers
 * and jest-dom is NOT installed in this app. `afterEach(cleanup)` is explicit, and assertions use
 * plain vitest matchers (`toBe`, `not.toBeNull`) rather than `toBeInTheDocument`/`toHaveValue`.
 *
 * ⚠ jsdom gives a canvas a ZERO-SIZE bounding rect and no 2d context. `getContext` is stubbed
 * below rather than weakening the component, and the drawing test pins STRUCTURE — one stroke
 * produces one mark with a four-element box and a boolean `closed` — not the coordinate
 * arithmetic. Only a live run against the real app can prove the coordinates.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { ComponentProps } from 'react';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { themes } from '@tokens';
import { AnnotateOverlay } from '../AnnotateOverlay.tsx';

const T = themes.celestial;
const SHOT = 'data:image/png;base64,AAAA';

/** The handful of 2d-context calls the component makes. jsdom supplies none of them. */
function stubContext() {
  const ctx = {
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    drawImage: vi.fn(),
    strokeStyle: '',
    lineWidth: 0,
    lineCap: '',
    lineJoin: '',
  };
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    ctx as unknown as CanvasRenderingContext2D,
  );
  return ctx;
}

function setup(over: Partial<ComponentProps<typeof AnnotateOverlay>> = {}) {
  const onCancel = vi.fn();
  const onSend = vi.fn().mockResolvedValue(true);
  render(
    <AnnotateOverlay T={T} shot={SHOT} target={null} onCancel={onCancel} onSend={onSend} {...over} />,
  );
  return { onCancel, onSend };
}

beforeEach(() => {
  vi.clearAllMocks();
  stubContext();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('AnnotateOverlay', () => {
  it('shows the snapshot it was given', () => {
    setup();
    expect(screen.getByAltText(/what you were looking at/i).getAttribute('src')).toBe(SHOT);
  });

  it('is marked as capture chrome so it stays out of the picture it sits on', () => {
    setup();
    expect(screen.getByRole('dialog').hasAttribute('data-cd-capture-chrome')).toBe(true);
  });

  it('offers a multi-line comment box, not a single line', () => {
    setup();
    expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA');
  });

  it('will not send an empty comment', () => {
    const { onSend } = setup();
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('sends the typed comment', async () => {
    const { onSend } = setup();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'this row is wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() =>
      expect(onSend).toHaveBeenCalledWith('this row is wrong', expect.any(String), [], expect.anything()),
    );
  });

  it('sends a drawn mark as geometry, not only as pixels', async () => {
    const { onSend } = setup();
    const canvas = document.querySelector('canvas')!;
    // jsdom gives a zero-size rect, so `at()` maps points through a degenerate scale — what this
    // pins is that a stroke produces ONE mark with a box and a `closed` flag, not the arithmetic.
    canvas.setPointerCapture = vi.fn();
    fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerMove(canvas, { clientX: 40, clientY: 40, pointerId: 1 });
    fireEvent.pointerUp(canvas, { pointerId: 1 });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'here' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    const marks = onSend.mock.calls[0]![2];
    expect(marks).toHaveLength(1);
    expect(marks[0].box).toHaveLength(4);
    expect(typeof marks[0].closed).toBe('boolean');
  });

  it('undoes the last mark without clearing the rest', async () => {
    const { onSend } = setup();
    const canvas = document.querySelector('canvas')!;
    canvas.setPointerCapture = vi.fn();
    for (const id of [1, 2]) {
      fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: id });
      fireEvent.pointerMove(canvas, { clientX: 40, clientY: 40, pointerId: id });
      fireEvent.pointerUp(canvas, { pointerId: id });
    }
    fireEvent.click(screen.getByRole('button', { name: /undo mark/i }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'here' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    expect(onSend.mock.calls[0]![2]).toHaveLength(1);
  });

  it('cancels without sending', () => {
    const { onCancel, onSend } = setup();
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
    expect(onSend).not.toHaveBeenCalled();
  });

  it('closes on Escape', () => {
    const { onCancel } = setup();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCancel).toHaveBeenCalled();
  });

  it('stays open with the text intact when the send fails', async () => {
    const onSend = vi.fn().mockResolvedValue(false);
    const { onCancel } = setup({ onSend });
    const box = screen.getByRole('textbox');
    fireEvent.change(box, { target: { value: 'keep me' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).toBe('keep me');
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('keeps the marks too when the send fails', async () => {
    const onSend = vi.fn().mockResolvedValue(false);
    setup({ onSend });
    const canvas = document.querySelector('canvas')!;
    canvas.setPointerCapture = vi.fn();
    fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerMove(canvas, { clientX: 40, clientY: 40, pointerId: 1 });
    fireEvent.pointerUp(canvas, { pointerId: 1 });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'keep me' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    // The undo control is only rendered while there is something to undo, so its survival is
    // the visible proof the strokes were not thrown away with the failed send.
    expect(screen.queryByRole('button', { name: /undo mark/i })).not.toBeNull();
  });

  it('falls back to text only when there is no snapshot', async () => {
    const { onSend } = setup({ shot: null });
    expect(screen.queryByAltText(/what you were looking at/i)).toBeNull();
    expect(screen.queryByText(/could not take a picture/i)).not.toBeNull();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'still works' } });
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => expect(onSend).toHaveBeenCalledWith('still works', null, [], null));
  });

  it('names what she pressed when a target is known', () => {
    setup({ target: { tag: 'button', label: 'Not today', text: 'Not today', data: {}, chain: [] } });
    expect(screen.queryByText(/Not today/)).not.toBeNull();
  });

  it('hides the drawing controls until something has been drawn', () => {
    setup();
    expect(screen.queryByRole('button', { name: /undo/i })).toBeNull();
  });

  it('uses no metaphors in what she reads', () => {
    setup({ shot: null });
    // The access guard is hard: every visible string must be literal. Pinned as a test so a
    // later copy edit that reaches for a figure of speech fails here rather than reaching her.
    const body = screen.getByRole('dialog').textContent || '';
    for (const figure of [/runway/i, /stream/i, /sandcastle/i, /snapshot/i, /capture/i, /flag it/i]) {
      expect(body).not.toMatch(figure);
    }
  });
});

/**
 * Regression: the stroke canvas must be positioned to the PICTURE, not to the scrolling window.
 *
 * These two were one element until 2026-07-19. A snapshot of a phone screen renders ~1155px tall
 * inside a ~385px window, so a canvas at `inset: 0` of the window was a third of the picture's
 * height, and a mark drawn halfway down what June could see landed a third of the way off in the
 * saved file. Every test here passed anyway — jsdom has no layout engine, so the two boxes only
 * diverge once something actually gives them a size.
 *
 * jsdom still cannot measure them, so this pins the STRUCTURE that made them diverge: the canvas's
 * own offset parent must not be the element that scrolls.
 */
it('positions the stroke canvas to the picture, not to the scrolling window', () => {
  setup();
  const canvas = document.querySelector('[role="dialog"] canvas') as HTMLCanvasElement;
  const img = document.querySelector('img[alt="What you were looking at"]') as HTMLImageElement;

  // the canvas and the picture share one positioned wrapper
  const wrapper = canvas.parentElement!;
  expect(img.parentElement).toBe(wrapper);
  expect(wrapper.style.position).toBe('relative');

  // ...and that wrapper is NOT the box that clips/scrolls. If a later edit collapses the two,
  // this fails here rather than silently misplacing her marks in the saved image.
  expect(wrapper.style.maxHeight).toBe('');
  expect(wrapper.style.overflow).toBe('');

  const scroller = wrapper.parentElement!;
  expect(scroller.style.maxHeight).toBe('45vh');
  // scroll, never hide: anything below the fold of a tall page must stay reachable to draw on.
  expect(scroller.style.overflow).toBe('auto');
});
