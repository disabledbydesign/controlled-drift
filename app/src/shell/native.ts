/**
 * The native-window bridge — the desktop app half of the per-tab window resize.
 *
 * In a browser this whole module is inert: `isNative()` is false and every export no-ops, so
 * `localhost:5050` in Safari/Chrome behaves exactly as before. It only comes alive inside the
 * pywebview shell (`scripts/desktop_app.py`), which opens the app with `?native=1` and injects
 * `window.pywebview.api.resize(w, h)`.
 *
 * ── why this exists ─────────────────────────────────────────────────────────
 * v4's `deskApp()` gave every tab its own frame width and animated between them (mockup line
 * 733 computes `W`; line 776 puts a `transition:width .3s` on the frame div). The port dropped
 * it because a real browser cannot resize its own window AND three of the widths sit below the
 * 900px phone/desktop breakpoint, so they'd flip the layout (see `DeskShell.tsx` 83-97). In a
 * native window both problems dissolve: `?native=1` forces the desktop layout (Surface.tsx) and
 * `resize()` drives the real OS window. The easing lives in Python (`desktop_app.py`).
 */

/** True when running inside the pywebview desktop shell (launched with `?native=1`). */
export function isNative(): boolean {
  if (typeof window === 'undefined') return false;
  return new URLSearchParams(window.location.search).has('native');
}

/** Fixed window height — v4 fixed its body height too; only width is per-tab. */
export const NATIVE_HEIGHT = 860;

/**
 * The per-tab window width, ported verbatim from v4 `deskApp()` (mockup line 733):
 *   `W = narrow ? ((detail && tab!=='settings') ? 872 : 392) : (isMap ? 1024 : 832)`
 * where narrow = today | add | settings, and the else branch (routines | strategies) is
 * v4's `DETAIL+COL+12 = 480+340+12 = 832`.
 */
export function nativeWidthFor(tab: string, hasDetail: boolean): number {
  const narrow = tab === 'today' || tab === 'add' || tab === 'settings';
  if (narrow) return hasDetail && tab !== 'settings' ? 872 : 392;
  if (tab === 'map') return 1024;
  return 832; // routines | strategies
}

interface PywebviewApi {
  resize?: (w: number, h: number) => void;
}
function api(): PywebviewApi | undefined {
  return (window as unknown as { pywebview?: { api?: PywebviewApi } }).pywebview?.api;
}

// The bridge is injected asynchronously: `window.pywebview.api` may not exist at first mount.
// A resize requested before then is held and replayed once `pywebviewready` fires, so the very
// first tab still sizes correctly even if its effect runs ahead of the injection.
// `pending` holds only the LATEST requested size, not a queue: if several tab switches happen
// before the bridge is injected, we want the window to land on the FINAL tab's size, not to
// animate through every stale intermediate width on startup. Last-write-wins is deliberate.
let ready = false;
let pending: { w: number; h: number } | null = null;

function flush(x: { w: number; h: number }): void {
  try {
    api()?.resize?.(x.w, x.h);
  } catch {
    // A bridge hiccup must never throw into a React effect — a missed resize is cosmetic.
  }
}

if (typeof window !== 'undefined') {
  if (api()) ready = true;
  window.addEventListener('pywebviewready', () => {
    ready = true;
    if (pending) {
      flush(pending);
      pending = null;
    }
  });
}

/** Drive the native window to the given tab's size. No-op in a browser. */
export function nativeResize(tab: string, hasDetail: boolean): void {
  if (!isNative()) return;
  const x = { w: nativeWidthFor(tab, hasDetail), h: NATIVE_HEIGHT };
  if (ready && api()?.resize) flush(x);
  else pending = x; // replayed on pywebviewready
}
