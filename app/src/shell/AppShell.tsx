import { useEffect, useMemo, useRef } from 'react';
import type { Theme, ThemeName } from '@tokens';
import { appBg, TopAccent } from '../components/atoms/index.ts';
import { DetailOverlay } from '../components/detail/index.ts';
import type { DetailCtx } from '../components/detail/index.ts';
import { PickerPage } from '../components/panels/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';
import type { TodayCtx } from '../components/today/index.ts';
import { seedPeriods } from '../fixtures/index.ts';
import { starfield } from '../theme/starfield.ts';
import {
  AddScreen,
  MapScreen,
  RoutinesScreen,
  SettingsScreen,
  StrategiesScreen,
  TodayScreen,
} from '../screens/index.ts';
import type { AddCtx, SettingsCtx } from '../screens/index.ts';
import { AppHeader } from './AppHeader.tsx';
import { AppTabs } from './AppTabs.tsx';
import { navAnimation, navDir, STRUCTURE_TABS } from './tabs.ts';
import type { AppTab } from './tabs.ts';
import { useAppState } from './useAppState.ts';

export interface AppShellProps {
  T: Theme;
  name: ThemeName;
  setTheme: (n: ThemeName) => void;
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
 * `pickerPage()` (Task 6) and `toast()` (Task 11) are still absent, and deliberately absent
 * rather than stubbed — a stub that renders nothing looks identical to a missing one and
 * hides the gap.
 *
 * ── theme ────────────────────────────────────────────────────────────────────
 * `T` arrives as a prop and is passed down. Nothing below this file calls `useTheme()`:
 * that hook owns a `useState`, so a second call would fork the theme and the switcher would
 * only move one copy. Same rule as `components/atoms/index.ts` states for the atoms.
 */
export function AppShell({ T, name, setTheme }: AppShellProps) {
  const C = T.c;
  const st = useAppState();
  const tab = st.ui.tab;

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
  const nav = useRef<{ tab: AppTab; dir: 'fwd' | 'back' }>({ tab, dir: 'fwd' });
  if (nav.current.tab !== tab) {
    nav.current = { tab, dir: navDir(nav.current.tab, tab) };
  }
  const dir = nav.current.dir;

  // v4:954 clears the same transient UI on every tab change, so a menu or panel left open on
  // one tab does not reappear over another. As an effect keyed on `tab` this fires however
  // the tab changed — the clear was previously inside `goTab` and shared the bypass above.
  const { up } = st;
  useEffect(() => {
    up({ detail: null, menuFor: null, chipEdit: null, addOpen: false, filterOpen: false });
  }, [tab, up]);

  /**
   * v4's `detail()` context. `flash` is v4's `flash(msg)` with no model change behind it —
   * the title and note textareas already wrote per keystroke, so the blur has nothing left to
   * persist and the toast is the only effect. Routing it through `apply` with the CURRENT
   * graph reuses the one toast seam without a second state field; the unchanged reference
   * means React skips the re-render of everything below it.
   */
  const detailCtx: DetailCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    schema: st.schema,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
  };

  /**
   * The context the three structure tabs, their panels and every `Row` share — v4's `this`,
   * minus the parts only `detail()` reads. `UiState` satisfies `PanelUi` structurally; if the
   * two drift, this line stops compiling, which is the intended alarm.
   */
  const panelCtx: PanelCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    schema: st.schema,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
  };

  const goTab = (next: AppTab) => {
    if (next === tab) return;
    up({ tab: next });
  };

  /**
   * v4's `this` as the Today methods read it (Task 7). `periods` comes straight from the
   * fixture rather than through `useAppState`, because nothing in Track A writes a period —
   * the Focus editor that does is Task 9, and it will move this into the state bag then.
   *
   * `openDetail` and `goTab` are callbacks rather than `up` fields on purpose: `detail`,
   * `returnFrom` and `tab` are shell-wide routing state, and putting them in `TodayUi` would
   * let any component in the tab write them. See `components/today/types.ts`.
   */
  const todayCtx: TodayCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    plan: st.plan,
    periods: seedPeriods,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    applyPlan: st.applyPlan,
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
    openDetail: (id: string) => st.up({ detail: id, returnFrom: 'today' }),
    goTab: (t) => goTab(t),
  };

  /**
   * v4's `this` as `captureTab()` / `logTab()` read it (Task 8). `openDetail` mirrors Today's:
   * v4 writes `up({detail:r.id,_returnFrom:'add'})` from the receipt's edit button (v4:1121),
   * and `returnFrom` makes the detail pane's back button say "Add".
   */
  const addCtx: AddCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    openDetail: (id: string) => st.up({ detail: id, returnFrom: 'add' }),
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
  };

  /**
   * Settings reads the UI bag for the backend choice and the plan-content toggle, and takes
   * the THEME from this component's props — i.e. from the single `useTheme()` in `App.tsx`.
   * Passing `setTheme` through rather than letting Settings call the hook is what keeps one
   * theme for the whole surface; see `screens/SettingsScreen.tsx`.
   */
  const settingsCtx: SettingsCtx = { T, name, setTheme, ui: st.ui, up: st.up };

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
      <PickerPage ctx={panelCtx} />
    </div>
  );
}
