import { useEffect, useState } from 'react';
import type { Theme, ThemeName } from '@tokens';
import { AppShell } from './AppShell.tsx';
import { DeskShell } from './DeskShell.tsx';
import { useSurface } from './useSurface.ts';
import { isNative } from './native.ts';
import { present } from './signals.ts';
import { AnnotateOverlay } from '../friction/AnnotateOverlay.tsx';
import { useFrictionCapture } from '../friction/useFrictionCapture.ts';
import { CHROME_ATTR } from '../friction/capture.ts';
import type { DataSource } from './useAppState.ts';

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
  /** See `DataSource` in `useAppState`. Omitted everywhere but the tests. */
  source?: DataSource;
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
export function Surface({ T, name, setTheme, source }: SurfaceProps) {
  // The desktop app (`?native=1`) is definitionally desktop: it drives its own window width per
  // tab (down to 392px for Today), so the viewport breakpoint must NOT be allowed to flip it to
  // the phone shell at those narrow widths. `isNative()` is a synchronous read of the URL, so
  // this is settled on the first render — no phone→desktop flash. In a browser it's false and
  // the 900px breakpoint decides exactly as before. See `native.ts`.
  const wideByViewport = useIsDesktop();
  const wide = isNative() || wideByViewport;
  const surface = useSurface({ T, name, setTheme, wide, source });

  /**
   * ── the friction capture, mounted ONCE above the fork ──────────────────────
   *
   * Same reason `useSurface` is called here rather than inside either shell: this is the only
   * place that is on every screen in BOTH shells. Mounted inside `AppShell` and `DeskShell`
   * separately it would be two implementations drifting apart, and an in-progress capture — her
   * half-written sentence and whatever she drew on the picture — would be thrown away by a
   * window resize across 900px, because crossing the breakpoint unmounts one shell and mounts
   * the other. That is exactly the bug the state placement documented above exists to prevent,
   * and the capture must not reintroduce it.
   */
  const capture = useFrictionCapture();

  /**
   * A failure or notice bar is `position:fixed`, `bottom:22px`, `calc(100% - 28px)` wide and
   * centred (`SignalBar.tsx`), so at the native Today window's 392px it runs under the quiet
   * button — and its DISMISS control is at its right end, directly beneath. That bar is the one
   * signal that deliberately never fades, so covering the only way to dismiss it would be worse
   * than briefly losing a button. The button comes back the moment the bar goes, and the long
   * press and Cmd/Ctrl-Shift-F still reach the capture meanwhile.
   */
  const barShowing = surface.st.toast !== null && present(surface.st.toast).mode === 'bar';

  return (
    <>
      {wide ? <DeskShell T={T} surface={surface} /> : <AppShell T={T} surface={surface} />}

      {/* The quiet always-there way in — "this whole screen is wrong", and the guaranteed path
          when a gesture misfires. Marked as capture chrome so `snapshot()`'s filter drops it;
          without that every picture would have this button burned into its corner. */}
      {!capture.state.open && !capture.state.busy && !barShowing ? (
        <button
          type="button"
          {...{ [CHROME_ATTR]: '' }}
          aria-label="Log what is wrong here"
          title="Log what is wrong here (press and hold, or Cmd-Shift-F)"
          onClick={() => capture.begin(null, 'button')}
          style={{
            position: 'fixed',
            right: 12,
            bottom: 12,
            // Above the signal bars (60) and the picker page (45) so it is never buried, and
            // below the overlay itself (9999), which replaces it rather than sitting under it.
            zIndex: 9998,
            width: 34,
            height: 34,
            borderRadius: 17,
            border: `1px solid ${T.c.border}`,
            background: T.c.surface,
            color: T.c.dim,
            font: 'inherit',
            fontSize: 15,
            lineHeight: '1',
            cursor: 'pointer',
            opacity: 0.55,
          }}
        >
          !
        </button>
      ) : null}

      {capture.state.open ? (
        <AnnotateOverlay
          T={T}
          shot={capture.state.shot}
          target={capture.state.target}
          onCancel={capture.close}
          // `surface.tab` and `surface.st.ui.detail` are the SAME two values `DeskShell` reads for
          // its native window resize (`DeskShell.tsx:167`) — the app has no other record of where
          // she is. `ui.detail` is an object id, or the `'__focus__'` sentinel when the focus
          // editor is open; both are stored verbatim and never interpreted, like the raw text.
          //
          // The answer is returned undiluted, and CLOSING IS NOT DECIDED HERE. `logDay` resolves
          // false having already said what did not happen, and `AnnotateOverlay.send` closes only
          // on a true — so her comment and her drawing survive a failed send. Closing here as well
          // would put that decision in two places, and the overlay's copy is the one that also
          // has to keep her text.
          onSend={(text, shot, marks, size) =>
            surface.st.logDay(text, ['issue'], {
              shot,
              view: { tab: surface.tab, detailId: surface.st.ui.detail },
              target: capture.state.target,
              via: capture.state.via,
              marks,
              size,
            })
          }
        />
      ) : null}
    </>
  );
}
