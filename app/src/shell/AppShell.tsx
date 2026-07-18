import { useEffect, useMemo, useRef } from 'react';
import type { Theme, ThemeName } from '@tokens';
import { appBg, TopAccent } from '../components/atoms/index.ts';
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
 * The overlays are Tasks 5, 6 and 11. They are deliberately absent rather than stubbed —
 * a stub that renders nothing looks identical to a missing one and hides the gap.
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

  const goTab = (next: AppTab) => {
    if (next === tab) return;
    up({ tab: next });
  };

  const body =
    tab === 'today' ? (
      <TodayScreen T={T} plan={st.plan} />
    ) : tab === 'add' ? (
      <AddScreen T={T} />
    ) : tab === 'map' ? (
      <MapScreen T={T} idx={st.idx} />
    ) : tab === 'routines' ? (
      <RoutinesScreen T={T} idx={st.idx} />
    ) : tab === 'strategies' ? (
      <StrategiesScreen T={T} graph={st.graph} />
    ) : (
      <SettingsScreen T={T} />
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

      {/* Temporary: the theme switch belongs in Settings (Task 8, `themeSection()` ~1144).
          It sits here so both themes are drivable while Settings is still a placeholder. */}
      <div
        style={{
          flex: '0 0 auto',
          display: 'flex',
          gap: '6px',
          justifyContent: 'center',
          padding: '8px 12px 12px',
          borderTop: '1px solid ' + C.hair,
          background: T.chrome,
        }}
      >
        {(['celestial', 'hardware'] as const).map((n) => (
          <button
            key={n}
            onClick={() => setTheme(n)}
            style={{
              cursor: 'pointer',
              padding: '5px 12px',
              fontFamily: T.mode === 'hardware' ? T.mono : T.font,
              fontSize: '11px',
              textTransform: T.mode === 'hardware' ? 'uppercase' : 'none',
              letterSpacing: T.mode === 'hardware' ? '.08em' : 0,
              color: n === name ? C.sig : C.dimmer,
              background: 'none',
              border: '1px solid ' + (n === name ? C.sig : C.border),
              borderRadius: T.r.chip,
            }}
          >
            {n}
          </button>
        ))}
        <a
          href="#/check"
          style={{
            alignSelf: 'center',
            marginLeft: '6px',
            fontFamily: T.mono,
            fontSize: '10px',
            color: C.dimmest,
            textDecoration: 'none',
          }}
        >
          tokens
        </a>
      </div>
    </div>
  );
}
