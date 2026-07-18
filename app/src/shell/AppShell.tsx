import { useMemo, useRef } from 'react';
import type { Theme } from '@tokens';
import { appBg, TopAccent } from '../components/atoms/index.ts';
import { DetailOverlay } from '../components/detail/index.ts';
import { FocusOverlay } from '../components/focus/index.ts';
import { PickerPage } from '../components/panels/index.ts';
import { starfield } from '../theme/starfield.ts';
import {
  AddScreen,
  MapScreen,
  RoutinesScreen,
  SettingsScreen,
  StrategiesScreen,
  TodayScreen,
} from '../screens/index.ts';
import { AppHeader } from './AppHeader.tsx';
import { AppTabs } from './AppTabs.tsx';
import { SignalBar } from './SignalBar.tsx';
import { navAnimation, navDir, STRUCTURE_TABS } from './tabs.ts';
import type { AppTab } from './tabs.ts';
import type { Surface as SurfaceType } from './useSurface.ts';

export interface AppShellProps {
  T: Theme;
  /**
   * The app state and every screen context — built ONCE by `Surface` and handed to whichever
   * shell is mounted. Not built here, so that crossing the desktop breakpoint mid-session
   * swaps the layout without resetting what the user was doing. See `Surface.tsx`.
   */
  surface: SurfaceType;
}

/**
 * v4 `renderShell()` (~929) — the phone frame.
 *
 * Structure is v4's, in order: the app background, `topAccent()`, `appHeader()`, then
 * `appTabs()` UNLESS settings is open, then the tab body, then the three overlays
 * (`detail()`, `pickerPage()`, `toast()`).
 *
 * `detail()` is mounted (Task 5) as `DetailOverlay`, which owns v4's two-phase close. It sits
 * LAST in the tree and paints `position:absolute; inset:0; zIndex:30` over the whole frame —
 * including the tab bar — which is why the shell root is `position:relative`.
 *
 * `pickerPage()` is mounted (Task 6). `toast()` is mounted (Task 11) as `SignalBar` — v4's own
 * `toast()` is `return null;` (v4:383), so what lands here is not a port but the thing that stub
 * was standing in for: the read-back confirmation, and the failure message. What it shows for
 * which case is decided in `shell/signals.ts`, not here.
 *
 * ── the contexts moved out (Task 10) ────────────────────────────────────────
 * The five context objects this file used to build now live in `useSurface`, because the
 * DESKTOP shell needs the identical ones. v4 does not have this problem: `renderShell` and
 * `deskApp` are methods on one component, so they share one `this` and it cannot fork. Two
 * components have to be given that single `this` explicitly or it becomes two copies that
 * drift. Nothing about the phone path changed — the definitions only moved.
 *
 * ── theme ────────────────────────────────────────────────────────────────────
 * `T` arrives as a prop and is passed down. Nothing below this file calls `useTheme()`:
 * that hook owns a `useState`, so a second call would fork the theme and the switcher would
 * only move one copy. Same rule as `components/atoms/index.ts` states for the atoms.
 */
export function AppShell({ T, surface }: AppShellProps) {
  const C = T.c;
  const { st, tab, goTab, detailCtx, panelCtx, focusCtx, todayCtx, addCtx, settingsCtx } = surface;

  // The starfield is generated once from a fixed seed, so the sky does not re-scatter on
  // every render or every tab change. Celestial only — appBg() ignores it in hardware.
  const sky = useMemo(() => starfield(), []);

  // ── navigation grammar (v4 `treeBody` ~642 / `NAV` ~61) ────────────────────
  // Forward enters from the right, back from the left. v4 derives the direction from tree
  // DEPTH; the same rule is applied here to the tab order (see `navDir`). The keyframes
  // (`navfwd` / `navback`) already live in index.html — this only names them.
  //
  // ⚠ Direction is DERIVED during render from the tab actually in state — it is NOT tracked
  // by the click handler. Corrected 2026-07-18 (review gate): tracking it in `goTab` meant
  // any other route to a tab change bypassed it. `up({tab:'map'})` is public, `tab` is a
  // UiState field, and a future mutation returning `ui:{tab:...}` would flow through
  // `apply()` — all three would have silently inverted the animation.
  //
  // This is the same principle as the stale-index fix in useAppState: make the wrong thing
  // impossible rather than documenting a rule someone has to remember. Whatever changes the
  // tab, the direction is right, because it is computed from the tab itself.
  //
  // This animation is the PHONE grammar and stays here: v4's `deskApp` has no per-tab entry
  // animation at all (verified — no `animation:` on any of its containers), because panes
  // dock and undock rather than sliding a whole screen in.
  const nav = useRef<{ tab: AppTab; dir: 'fwd' | 'back' }>({ tab, dir: 'fwd' });
  if (nav.current.tab !== tab) {
    nav.current = { tab, dir: navDir(nav.current.tab, tab) };
  }
  const dir = nav.current.dir;

  const body =
    tab === 'today' ? (
      <TodayScreen ctx={todayCtx} />
    ) : tab === 'add' ? (
      <AddScreen ctx={addCtx} />
    ) : tab === 'map' ? (
      // Task 6: all three structure tabs take the one panel context and each wraps itself in
      // `StructurePanel` (v4:959), which owns the controls, the filter block and the scroller.
      <MapScreen ctx={panelCtx} />
    ) : tab === 'routines' ? (
      <RoutinesScreen ctx={panelCtx} />
    ) : tab === 'strategies' ? (
      <StrategiesScreen ctx={panelCtx} />
    ) : (
      <SettingsScreen ctx={settingsCtx} />
    );

  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        overflow: 'hidden',
        background: appBg(T, sky),
        fontFamily: T.font,
        color: C.text,
      }}
    >
      <TopAccent T={T} />
      <AppHeader
        T={T}
        planDate={st.plan.date}
        onSettings={tab === 'settings'}
        // v4: the gear toggles — pressing it while in settings returns to Today.
        onToggleSettings={() => goTab(tab === 'settings' ? 'today' : 'settings')}
      />
      {tab !== 'settings' ? <AppTabs T={T} current={tab} onSelect={goTab} /> : null}

      {/* v4:934-935 FORKS here and the fork is load-bearing (review gate, 2026-07-18):
          `today` and `add` get a scrolling wrapper, but `map` / `routines` / `strategies` go
          to `structurePanel(tab)` (v4:959-965) OUTSIDE it. `structurePanel` is its own flex
          column with `overflow:hidden`, holding `mapControls()` / `filterMenu()` / `addPanel()`
          ABOVE its own inner scroller (v4:964) so those controls stay put while the list moves.

          Nested inside a scrolling parent, `structurePanel`'s `flex:1` is inert (the parent is
          not a flex container), its height collapses to content, and the map controls scroll
          away with the list. Invisible today because the structure tabs are placeholders — it
          would surface in Task 6 and read as a Task 6 bug. Forked now so it cannot. */}
      {STRUCTURE_TABS.has(tab) ? (
        <div key={tab} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', animation: navAnimation(dir) }}>
          {body}
        </div>
      ) : (
        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {/* Keyed on the tab so React remounts the panel and the entry animation actually
              replays; without the key it is the same element and the animation runs once. */}
          <div key={tab} style={{ animation: navAnimation(dir) }}>
            {body}
          </div>
        </div>
      )}

      {/* The temporary theme switcher that sat here is GONE (Task 8). It was explicitly marked
          as belonging in `themeSection()` (v4:1144), and it now lives there — reached from the
          header gear → Settings. v4 has no footer strip below the tab bar.

          The `#/check` link went with it: the acceptance/token page is still served at that
          route (see `App.tsx`), it just no longer has a permanent affordance in the phone
          chrome, which v4 does not have either. */}

      {/* v4's overlay slot (renderShell 936-938): detail, then pickerPage, then toast — in
          that order, and the order is the z-order. `toast()` is Task 11.

          ⚠ `PickerPage` is deliberately mounted at SHELL level, not inside `StructurePanel`.
          v4 puts it here, and the reason shows up in use: `moveFor` is also set from the
          detail editor's location block, so the picker has to be able to paint over the
          detail pane (zIndex 45 vs. its 30), not sit behind it inside a tab body. */}
      <DetailOverlay ctx={detailCtx} />
      {/* v4:938 — `this.toast()` is the LAST child of the shell, and that is the z-order.
          v4's own `toast()` (383) is `return null`; `SignalBar` is what it became. It renders
          only when `signals.present()` says `bar` — which by default is failures ONLY. */}
      <SignalBar T={T} sig={st.toast} onDismiss={st.dismissToast} />
      {/* v4 reaches the focus editor from INSIDE `detail(id)` (v4:541,
          `if(id==='__focus__')return this.focusDetail()`). Here it is a sibling instead:
          `DetailCtx` has no `periods` / `applyPeriods` and must not grow them. Same
          `__focus__` route, same z-index, same slide-in. `Detail.tsx` keeps its
          `id==='__focus__' → null` guard so exactly one of the two ever paints. */}
      <FocusOverlay ctx={focusCtx} open={st.ui.detail === '__focus__'} />
      <PickerPage ctx={panelCtx} />
    </div>
  );
}
