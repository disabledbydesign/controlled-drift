import { useEffect, useState } from 'react';
import type { Theme, ThemeName } from '@tokens';
import { AppShell } from './AppShell.tsx';
import { DeskShell } from './DeskShell.tsx';
import { useSurface } from './useSurface.ts';

/**
 * The width at or above which the DESKTOP shell is used.
 *
 * ── why a width breakpoint at all ───────────────────────────────────────────
 * v4 renders BOTH shells at once — `renderVals()` returns `{app: renderShell(), desk:
 * deskApp()}` — because v4 is a design canvas putting a phone frame and a desktop frame side
 * by side on one page for comparison. A real app is on exactly one of those. Nothing else in
 * the state says which: there is no device flag, no user setting, and the two layouts differ
 * in nothing but how much room they need. Available width IS the question being asked.
 *
 * ── why 900 ─────────────────────────────────────────────────────────────────
 * Two independent floors, and 900 clears both.
 *
 * 1. GEOMETRY. The desktop Map is a Finder column browser with a docked editor: one 320px
 *    column + a 7px divider + a 400px detail pane needs 727px before any chrome, and the
 *    layout only starts paying for itself with a second column visible. Below ~900 it is a
 *    cramped single column beside a pane — strictly worse than the phone shell, which is
 *    designed for exactly that width.
 *
 * 2. INPUT. The desktop path is the ONLY place drag-to-reparent and the pane dividers exist,
 *    and both are mouse-only: HTML5 drag events do not fire from touch, and the dividers are
 *    `mousedown`/`mousemove`. A tablet held in portrait (768 or 834 CSS px on iPad) would get
 *    a layout whose two distinguishing interactions it cannot perform. 900 sits above both
 *    common portrait widths, so tablets in portrait get the touch-shaped phone shell and only
 *    landscape/desktop viewports get the pointer-shaped one.
 *
 * Not a device sniff: a narrow window on a large screen gets the phone shell, which is the
 * correct answer — the constraint is room, not hardware.
 */
export const DESKTOP_MIN_WIDTH = 900;

/** `(min-width: 900px)`, as a media query string. Exported so tests can stub `matchMedia`. */
export const DESKTOP_QUERY = `(min-width: ${DESKTOP_MIN_WIDTH}px)`;

/**
 * Live-tracked answer to "is this viewport wide enough for the desktop shell?".
 *
 * `matchMedia` rather than a resize listener on `innerWidth`: the browser only notifies on the
 * threshold being crossed, so dragging a window edge does not fire a state update per pixel.
 *
 * Guarded for a missing `matchMedia` because jsdom did not implement it until recently and a
 * component test that never touches width should not have to stub it. Absent → phone, which is
 * the same default the app has had.
 */
function useIsDesktop(): boolean {
  const [wide, setWide] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia(DESKTOP_QUERY).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia(DESKTOP_QUERY);
    const onChange = (e: MediaQueryListEvent) => setWide(e.matches);
    mq.addEventListener('change', onChange);
    // Re-read on mount in case the viewport changed between the initial render and the effect.
    setWide(mq.matches);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  return wide;
}

export interface SurfaceProps {
  T: Theme;
  name: ThemeName;
  setTheme: (n: ThemeName) => void;
}

/**
 * The app's single state owner, and the phone/desktop switch.
 *
 * ── why the state lives HERE and not in either shell ────────────────────────
 * `useSurface` is called ONCE, above the branch, so crossing the breakpoint swaps the LAYOUT
 * and nothing else: the drilled path, the open editor, an in-progress capture and every
 * unsaved edit survive a window resize. Had each shell called the hook itself, crossing 900px
 * would unmount one and mount the other, and `useAppState` would re-seed from the fixtures —
 * i.e. resizing the window would silently throw the session away.
 *
 * This also matches v4's actual structure, where `renderShell` and `deskApp` are two methods
 * on one component reading one `this.state`.
 *
 * `wide` still has to reach the components that fork on it (`PanelCtx.wide`, `DetailCtx.wide`),
 * so it is an input to `useSurface` — it just is not what decides who owns the state.
 */
export function Surface({ T, name, setTheme }: SurfaceProps) {
  const wide = useIsDesktop();
  const surface = useSurface({ T, name, setTheme, wide });
  return wide ? <DeskShell T={T} surface={surface} /> : <AppShell T={T} surface={surface} />;
}
