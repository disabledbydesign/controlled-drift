import { useCallback, useEffect, useRef, useState } from 'react';
import { describeTarget, snapshot, type PressTarget } from './capture.ts';
import { isNative } from '../shell/native.ts';
import type { CaptureVia } from '../shell/useAppState.ts';

/**
 * Long enough not to fire on a tap or the start of a scroll, short enough that she is not holding
 * her thumb down wondering whether it registered. Matches the platform's own press-and-hold feel.
 */
export const LONG_PRESS_MS = 550;
/** Past this much movement it was a scroll, not a press. */
const MOVE_TOLERANCE_PX = 10;

export interface CaptureState {
  open: boolean;
  /** A capture is being rendered. Guards against a second trigger mid-flight. */
  busy: boolean;
  shot: string | null;
  target: PressTarget | null;
  /** Which way in was used. Recorded so an unused entry point can be found and retired. */
  via: CaptureVia | null;
}

const CLOSED: CaptureState = { open: false, busy: false, shot: null, target: null, via: null };

/**
 * The element under a given point, or null.
 *
 * `document.elementFromPoint` is not universally present — jsdom has no layout engine and does
 * not define it at all. We check that the function exists AND that what came back is really an
 * Element, rather than wrapping the call in a try/catch: a stub that returns `undefined` sails
 * straight past a catch and would put a non-Element into `describeTarget`. A missing target only
 * costs the entry its "which control" detail; it must never cost her the capture.
 */
function elementAt(x: number, y: number): Element | null {
  const fn = (document as Document & { elementFromPoint?: (x: number, y: number) => Element | null })
    .elementFromPoint;
  if (typeof fn !== 'function') return null;
  const found = fn.call(document, x, y);
  return found instanceof Element ? found : null;
}

/**
 * When and how June summons the capture.
 *
 * ── four ways in, one flow ──────────────────────────────────────────────────
 * They answer different kinds of friction. Long-press / right-click / shortcut say "THIS THING
 * is wrong" and carry what she pressed, which is what turns a vague report into one pointing at
 * a specific row or control. The quiet always-present button says "this whole screen is wrong"
 * and needs no target. The button is also the guaranteed path: a gesture can misfire or be
 * swallowed by the platform, and there must always be a way in that cannot.
 *
 * ── why touch only for the long press ───────────────────────────────────────
 * A mouse press-and-hold is already meaningful in this app (the desktop shell has drag-to-
 * reparent — `DeskShell.tsx:126` — and the pane dividers are mousedown/mousemove, see
 * `Surface.tsx:30`). Claiming hold on a mouse would break both. Desktop gets right-click and the
 * keyboard shortcut instead; the shortcut reads the last pointer position so it still knows what
 * she was looking at.
 *
 * ── why right-click is confined to the native window ────────────────────────
 * On desktop it beats a gesture: exact targeting, discoverable, no collision with drag. Its one
 * real cost is that claiming `contextmenu` removes the browser's own menu — inspect, copy, open
 * in new tab. In the pywebview window there is no browser menu to lose, so the cost is zero
 * there and real in a browser tab. `isNative()` is a synchronous URL read (`?native=1`), so the
 * handler settles the question on every event with no async gap; in a browser it returns
 * immediately and the browser's own menu is untouched.
 *
 * ⚠ RISK, to check on the real phone: iOS Safari raises its own callout and text selection on a
 * long press. The overlay opening over the top should make that moot, but if the callout wins,
 * the fix is `-webkit-touch-callout: none` plus preventDefault on `contextmenu` in the app
 * shell. The quiet button is unaffected either way, which is the point of having it.
 */
export function useFrictionCapture() {
  const [state, setState] = useState<CaptureState>(CLOSED);
  const busyRef = useRef(false);
  const timer = useRef<number | null>(null);
  const origin = useRef<{ x: number; y: number; el: Element | null } | null>(null);
  const lastPointer = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const begin = useCallback((el?: Element | null, via: CaptureVia = 'button') => {
    // A second trigger while one is rendering would race two snapshots into one state slot.
    if (busyRef.current) return;
    busyRef.current = true;
    const target = describeTarget(el ?? null);
    setState({ open: false, busy: true, shot: null, target, via });
    void snapshot(document.body).then((shot) => {
      busyRef.current = false;
      // Opens even when `shot` is null. A failed render must not swallow the whole capture —
      // the overlay says so plainly and she can still write the entry.
      setState({ open: true, busy: false, shot, target, via });
    });
  }, []);

  const close = useCallback(() => {
    busyRef.current = false;
    setState(CLOSED);
  }, []);

  const cancelPress = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    origin.current = null;
  }, []);

  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      lastPointer.current = { x: e.clientX, y: e.clientY };
      if (e.pointerType !== 'touch') return;
      cancelPress();
      const el = e.target instanceof Element ? e.target : null;
      origin.current = { x: e.clientX, y: e.clientY, el };
      timer.current = window.setTimeout(() => {
        timer.current = null;
        const o = origin.current;
        origin.current = null;
        if (o) begin(o.el, 'longpress');
      }, LONG_PRESS_MS);
    };

    // Right click, in the native window only — see the note above on why the split exists.
    const onContextMenu = (e: MouseEvent) => {
      if (!isNative()) return;
      e.preventDefault();
      begin(e.target instanceof Element ? e.target : null, 'rightclick');
    };

    const onMove = (e: PointerEvent) => {
      lastPointer.current = { x: e.clientX, y: e.clientY };
      const o = origin.current;
      if (!o) return;
      if (
        Math.abs(e.clientX - o.x) > MOVE_TOLERANCE_PX ||
        Math.abs(e.clientY - o.y) > MOVE_TOLERANCE_PX
      ) {
        cancelPress();
      }
    };

    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        const { x, y } = lastPointer.current;
        begin(elementAt(x, y), 'shortcut');
      }
    };

    window.addEventListener('pointerdown', onDown, true);
    window.addEventListener('pointermove', onMove, true);
    window.addEventListener('pointerup', cancelPress, true);
    window.addEventListener('pointercancel', cancelPress, true);
    window.addEventListener('keydown', onKey);
    window.addEventListener('contextmenu', onContextMenu);
    return () => {
      cancelPress();
      window.removeEventListener('pointerdown', onDown, true);
      window.removeEventListener('pointermove', onMove, true);
      window.removeEventListener('pointerup', cancelPress, true);
      window.removeEventListener('pointercancel', cancelPress, true);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('contextmenu', onContextMenu);
    };
  }, [begin, cancelPress]);

  return { state, begin, close };
}
