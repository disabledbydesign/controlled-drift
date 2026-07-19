import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

const snapshot = vi.fn();
vi.mock('../capture.ts', async (orig) => ({
  ...(await orig<typeof import('../capture.ts')>()),
  snapshot: (...a: unknown[]) => snapshot(...a),
}));
const isNative = vi.fn();
vi.mock('../../shell/native.ts', () => ({ isNative: () => isNative() }));

import { useFrictionCapture, LONG_PRESS_MS } from '../useFrictionCapture.ts';

beforeEach(() => {
  vi.useFakeTimers();
  snapshot.mockReset().mockResolvedValue('data:image/png;base64,AAAA');
  isNative.mockReset().mockReturnValue(false);
  document.body.innerHTML = '<button id="t">Not today</button>';
});
afterEach(() => vi.useRealTimers());

describe('useFrictionCapture', () => {
  it('starts closed', () => {
    const { result } = renderHook(() => useFrictionCapture());
    expect(result.current.state.open).toBe(false);
  });

  it('opens with a snapshot when begin is called', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(null);
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(true);
    expect(result.current.state.shot).toBe('data:image/png;base64,AAAA');
  });

  it('records what was pressed', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(document.getElementById('t'));
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.target?.label).toBe('Not today');
  });

  it('opens after a long press and not before', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    const el = document.getElementById('t')!;
    act(() => {
      el.dispatchEvent(
        new PointerEvent('pointerdown', {
          bubbles: true,
          clientX: 5,
          clientY: 5,
          pointerType: 'touch',
        }),
      );
    });
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS - 50);
    });
    expect(result.current.state.open).toBe(false);
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(true);
  });

  it('cancels the long press when the finger moves — a scroll must not open it', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    const el = document.getElementById('t')!;
    act(() => {
      el.dispatchEvent(
        new PointerEvent('pointerdown', {
          bubbles: true,
          clientX: 5,
          clientY: 5,
          pointerType: 'touch',
        }),
      );
      window.dispatchEvent(
        new PointerEvent('pointermove', { bubbles: true, clientX: 5, clientY: 60 }),
      );
    });
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(false);
  });

  it('cancels the long press when the finger lifts early', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    const el = document.getElementById('t')!;
    act(() => {
      el.dispatchEvent(
        new PointerEvent('pointerdown', {
          bubbles: true,
          clientX: 5,
          clientY: 5,
          pointerType: 'touch',
        }),
      );
      window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
    });
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(false);
  });

  it('does not long-press on a mouse — that would break click-and-hold', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    const el = document.getElementById('t')!;
    act(() => {
      el.dispatchEvent(
        new PointerEvent('pointerdown', {
          bubbles: true,
          clientX: 5,
          clientY: 5,
          pointerType: 'mouse',
        }),
      );
    });
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(false);
  });

  it('opens on the keyboard shortcut', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'F', shiftKey: true, metaKey: true, bubbles: true }),
      );
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(true);
    expect(result.current.state.via).toBe('shortcut');
  });

  it('records which way in was used', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(null, 'button');
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.via).toBe('button');
  });

  it('records a long press as a long press, not as the button', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    act(() => {
      document
        .getElementById('t')!
        .dispatchEvent(
          new PointerEvent('pointerdown', {
            bubbles: true,
            clientX: 5,
            clientY: 5,
            pointerType: 'touch',
          }),
        );
    });
    await act(async () => {
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.via).toBe('longpress');
  });

  it('opens on right click in the native app', async () => {
    isNative.mockReturnValue(true);
    const { result } = renderHook(() => useFrictionCapture());
    const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    await act(async () => {
      document.getElementById('t')!.dispatchEvent(ev);
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(true);
    expect(result.current.state.via).toBe('rightclick');
    expect(ev.defaultPrevented).toBe(true);
  });

  it('leaves the browser context menu alone when not native', async () => {
    isNative.mockReturnValue(false);
    const { result } = renderHook(() => useFrictionCapture());
    const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    await act(async () => {
      document.getElementById('t')!.dispatchEvent(ev);
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(false);
    expect(ev.defaultPrevented).toBe(false);
  });

  it('opens with a null shot when the render failed, rather than not opening', async () => {
    snapshot.mockResolvedValue(null);
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(null);
      await vi.runAllTimersAsync();
    });
    expect(result.current.state.open).toBe(true);
    expect(result.current.state.shot).toBeNull();
  });

  it('ignores a second begin while one capture is already in flight', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(null);
      result.current.begin(null);
      await vi.runAllTimersAsync();
    });
    expect(snapshot).toHaveBeenCalledTimes(1);
  });

  it('closes', async () => {
    const { result } = renderHook(() => useFrictionCapture());
    await act(async () => {
      result.current.begin(null);
      await vi.runAllTimersAsync();
    });
    act(() => result.current.close());
    expect(result.current.state.open).toBe(false);
  });
});
