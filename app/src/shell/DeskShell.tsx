import { useCallback, useEffect, useLayoutEffect, useRef } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import type { Theme } from '@tokens';
import { appBg, TopAccent, typeColor } from '../components/atoms/index.ts';
import { DetailOverlay } from '../components/detail/index.ts';
import { FocusOverlay } from '../components/focus/index.ts';
import { AddPanel, FilterMenu, orphanSections, PickerPage } from '../components/panels/index.ts';
import { node } from '../model/index.ts';
import type { ModelNode } from '../model/index.ts';
import { Row } from '../components/rows/index.ts';
import { subtreeVis } from '../screens/MapScreen.tsx';
import {
  AddScreen,
  RoutinesScreen,
  SettingsScreen,
  StrategiesScreen,
  TodayScreen,
} from '../screens/index.ts';
import { starfield } from '../theme/starfield.ts';
import { SignalBar } from './SignalBar.tsx';
import type { AppTab } from './tabs.ts';
import type { Surface as SurfaceType } from './useSurface.ts';

export interface DeskShellProps {
  T: Theme;
  /** @see AppShellProps.surface — built once by `Surface`, shared by both shells. */
  surface: SurfaceType;
}

/** v4:733 — `const COL=340, DETAIL=480`. `BODY_H` is deliberately not ported; see below. */
const COL = 340;
const DETAIL = 480;

/** v4:748 — `this.w('deskcol',320)`, the Finder column width. */
const DESKCOL = 320;

/**
 * ⚠ v4 uses 320 in `renderPanel` (748) and **300** in `componentDidUpdate`'s scroll-target
 * arithmetic (715) for the SAME `deskcol` key. One of the two is a typo in v4; which one is
 * unverified. Ported as-is — the number only affects how far the auto-scroll lands when
 * stepping BACK out of a column, so the visible effect is a slightly short scroll, never a
 * wrong column. Flagged rather than silently unified.
 */
const DESKCOL_SCROLL = 300;

/** v4:708 — the resize clamp, `Math.max(220, Math.min(700, …))`. */
const MIN_W = 220;
const MAX_W = 700;

/**
 * The DESKTOP render path — v4 `deskApp()` (730), `deskCrumbBar()` (719), `dragHandle()` (718),
 * `w()` (716), `navigateDeskPath()` (717) and the resize wiring in `componentDidMount` (708).
 *
 * ── THIS IS A SECOND LAYOUT, NOT A SECOND APP ───────────────────────────────
 * Every component rendered here is the one the phone renders: `Row`, `DetailOverlay`,
 * `TodayScreen`, `RoutinesScreen`, `StrategiesScreen`, `AddScreen`, `SettingsScreen`,
 * `FilterMenu`, `AddPanel`, `PickerPage`, `FocusOverlay`. Nothing is forked. The three places
 * a component genuinely differs take a `wide` prop, exactly the three v4 reaches through
 * `this._wide` — see `PanelCtx.wide`. State comes from `useSurface`, which is `AppShell`'s
 * state builder verbatim.
 *
 * What differs is arrangement:
 *   · tabs move from a bottom-ish strip into a single top toolbar (v4's `dtab`, 735)
 *   · Map becomes a Finder-style column browser under a breadcrumb bar, with resizable panes
 *   · the detail editor docks as a right-hand PANE instead of covering the screen
 *   · Routines / Strategies render their bodies BARE — the desktop toolbar already carries
 *     the search box and `+` that `MapControls` provides on the phone (v4:756)
 *
 * ── ⚠ DRAG-TO-REPARENT IS LIVE HERE AND ONLY HERE ───────────────────────────
 * v4:747 is the single `dnd:true` call site in the whole mockup — `deskApp`'s Map panel row.
 * `Row` has carried the implementation since Task 4; this is what switches it on. Dragging a
 * row onto a container row re-parents it through the same `move()` mutation the picker uses.
 *
 * ⚠ AN INVALID DROP IS A SILENT NO-OP. Dropping a node onto itself or onto one of its own
 * descendants is refused in two places — `Row`'s own ancestor walk (v4:446) and `move()`'s
 * guard (mutations.ts) — and NEITHER produces a toast or a `ui` patch. The drop-target
 * outline clears (that happens before the guard) and nothing else occurs: no message, no
 * move, no explanation. That is v4's own shape and it is ported as-is, but it is a real gap
 * and it belongs to Task 11's `toast()`.
 *
 * ── two deliberate divergences from v4's frame, both about canvas furniture ──
 * v4 draws a fake macOS window: traffic-light dots, a "Controlled Drift — desktop" caption,
 * a fixed `BODY_H=672px` body and a hard `width:W+'px'` on the outer card. That is the design
 * CANVAS showing a desktop frame next to a phone frame on one page — `renderVals()` returns
 * both. A real app IS the window.
 *
 *   1. The mac titlebar and `BODY_H` are dropped, and the shell fills the viewport, exactly as
 *      the phone port dropped v4's device frame and used `minHeight:100vh`.
 *   2. `W` survives as a `maxWidth`, but only for the NARROW tabs (today / add / settings).
 *      v4's comment at 734 says why it exists — *"narrow tabs match the phone width; open an
 *      editor → dock a second pane"* — and that is a real layout intent: Today is a reading
 *      column and must not stretch to 1440px. For map / routines / strategies the same number
 *      is only the fake window's size; their internals are explicitly a horizontal scroller
 *      and a flexing list, so they fill the viewport instead of being capped at 1024.
 *
 * ── what v4 defines here and never uses ─────────────────────────────────────
 *   · `this._deskOverlay = narrow` (731) — assigned, and read NOWHERE else in v4 (grepped).
 *     Not ported.
 *   · `this._activeColRef` (81, attached at 748) — a ref that is attached to the active column
 *     and whose `.current` is never read (grepped: two hits, the constructor and the
 *     attachment). Not ported.
 */
export function DeskShell({ T, surface }: DeskShellProps) {
  const C = T.c;
  // v4 `isHW()` — the SHAPE fork. Same expression the phone shell uses (`AppTabs`, `Band`).
  const hw = T.mode === 'hardware';
  const { st, tab, detailCtx, panelCtx, focusCtx, todayCtx, addCtx, settingsCtx } = surface;
  const { ui, up, graph, idx } = st;

  const sky = useRef(starfield()).current;

  const isMap = tab === 'map';
  // v4:731 — which tabs stay phone-width. `settings` is in the set but is reachable only
  // through the gear, never through `dtab`.
  const narrow = tab === 'today' || tab === 'add' || tab === 'settings';

  // ── w(key, def) — v4:716 ──────────────────────────────────────────────────
  // An unresized pane has NO entry, so the default lives at the call site rather than being
  // written into state on mount. `|| def` is v4's own expression, which also means a stored
  // width of 0 falls back — unreachable, since the drag clamps at 220.
  const w = (key: string, def: number): number => ui.widths[key] || def;

  // ── the divider drag — v4 `componentDidMount` (708) + `dragHandle` (718) ──
  //
  // The drag is tracked in a REF, not in state, and that is load-bearing: `mousemove` fires
  // dozens of times a second and the only thing that must repaint is the width. v4 keeps it on
  // the instance (`this._drag`) for the same reason.
  //
  // The listeners are on `document`, not on the handle, so the pointer can leave the 7px strip
  // mid-drag without dropping it — which it will, constantly.
  const drag = useRef<{ key: string; startX: number; startW: number } | null>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const d = drag.current;
      if (!d) return;
      // v4:708 — the detail pane is on the RIGHT, so dragging its left-hand handle to the
      // right makes it NARROWER. Every other pane grows in the direction of travel.
      const sign = d.key === 'detail' ? -1 : 1;
      const next = Math.max(MIN_W, Math.min(MAX_W, d.startW + sign * (e.clientX - d.startX)));
      up({ widths: { ...ui.widths, [d.key]: next } });
    };
    const onUp = () => {
      if (drag.current) {
        drag.current = null;
        document.body.style.cursor = '';
      }
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      // v4's `componentWillUnmount` (714) does not restore the cursor; this does, because
      // unmounting mid-drag would otherwise leave the whole document stuck on `col-resize`.
      if (drag.current) document.body.style.cursor = '';
    };
  }, [up, ui.widths]);

  /**
   * v4 `dragHandle(wkey, rkey)` (718) — the 7px column divider.
   *
   * All Finder columns pass the SAME `wkey` ('deskcol'), so dragging any one divider resizes
   * every column together. v4's shape, kept.
   *
   * ⚠ v4 passes `'style-hover':{background:C.blue+'44'}`. `this.h` is plain
   * `React.createElement` (v4:335), so that key reaches the DOM as an unknown attribute and
   * does nothing — the hover highlight does not work in v4 either. Dropped rather than
   * reimplemented, for the same reason `AddPanel` dropped its `style-hover`: reproducing it
   * needs a CSS class or a JS hover state, and classes are ruled out by the port's
   * inline-styles constraint. FLAGGED, not silently lost: the divider is a 7px strip with a
   * 1px border and no hover feedback, which is thin discoverability. June's call.
   */
  const dragHandle = (wkey: string, rkey?: string) => (
    <div
      key={'h' + (rkey || wkey)}
      data-drag-handle={wkey}
      onMouseDown={(e) => {
        e.preventDefault();
        drag.current = {
          key: wkey,
          startX: e.clientX,
          // ⚠ NEITHER of v4's two defaults here matches what the pane actually renders at, so
          // the FIRST drag of an un-resized divider jumps before it starts tracking. Both
          // confirmed live at 1440px:
          //   · `detail` starts from 480 but the Map's pane renders at 400 (v4:743) → +80
          //   · `deskcol` starts from 340 but a column renders at 320 (v4:748)      → +20
          // v4's own numbers (718 vs 743/748); ported as-is and flagged, not reconciled.
          startW: w(wkey, wkey === 'detail' ? DETAIL : COL),
        };
        document.body.style.cursor = 'col-resize';
      }}
      style={{
        width: '7px',
        flex: '0 0 auto',
        cursor: 'col-resize',
        borderRight: '1px solid ' + C.hair,
      }}
    />
  );

  /** v4:717 — every path change also clears the transient editor/menu state. */
  const navigateDeskPath = useCallback(
    (next: readonly string[]) =>
      up({ deskPath: next, detail: null, menuFor: null, chipEdit: null }),
    [up],
  );

  // ── the column scroller's auto-scroll — v4 `componentDidUpdate` (715) ─────
  //
  // Drilling in scrolls the new rightmost column into view; stepping back out scrolls to where
  // the (now) last column sits. `useLayoutEffect` rather than `useEffect` so the measurement
  // happens after the DOM has the new column but before paint, which is when v4's
  // `componentDidUpdate` runs.
  const navRef = useRef<HTMLDivElement | null>(null);
  const prevCols = useRef(0);
  const cols = ui.deskPath.length;
  useLayoutEffect(() => {
    const el = navRef.current;
    if (el && cols !== prevCols.current) {
      const inc = cols > prevCols.current;
      const target = inc
        ? el.scrollWidth
        : Math.max(0, (cols + 1) * w('deskcol', DESKCOL_SCROLL) + cols * 7 - el.clientWidth);
      // jsdom does not implement `Element.scrollTo`. Feature-tested rather than stubbed in the
      // test setup, because an unimplemented scroll is a no-op everywhere it is missing and
      // there is nothing to assert about it — the columns are already in the DOM either way.
      if (typeof el.scrollTo === 'function') el.scrollTo({ left: target, behavior: 'smooth' });
    }
    prevCols.current = cols;
  });

  // ── the toolbar — v4:735-742 ──────────────────────────────────────────────
  const dtab = (id: AppTab, label: string) => {
    const on = tab === id;
    return (
      <button
        key={id}
        onClick={() =>
          // v4:735 assigns the tab AND clears the transient UI in one patch. The clear also
          // runs from `useSurface`'s tab effect; both are the same patch, so this is v4's
          // literal call and the effect is the belt that catches every other route.
          up({
            tab: id,
            detail: null,
            menuFor: null,
            chipEdit: null,
            addOpen: false,
            filterOpen: false,
          })
        }
        style={{
          flex: '0 0 auto',
          background: 'none',
          border: 'none',
          borderBottom: '2px solid ' + (on ? C.sig : 'transparent'),
          color: on ? C.sig : C.dimmer,
          fontSize: '12px',
          fontWeight: on ? 700 : 600,
          padding: '7px 8px 9px',
          cursor: 'pointer',
          // ⚠ the isHW() SHAPE fork. v4's DESKTOP tab is a plain underline in both themes and
          // forks only on TYPEFACE — mono, uppercase, tracked. It is NOT the phone's fork:
          // `appTabs` (v4:951) gives hardware a bordered, glowing PILL. Two different forks on
          // two different paths; both are v4's and neither is copied onto the other.
          fontFamily: hw ? T.mono : 'inherit',
          textTransform: hw ? 'uppercase' : 'none',
          letterSpacing: hw ? '.05em' : 'normal',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </button>
    );
  };

  const pill = (label: string, on: boolean, onClick: () => void) => (
    <button
      onClick={onClick}
      style={{
        flex: '0 0 auto',
        background: on ? C.blue + '22' : C.panel,
        border: '1px solid ' + (on ? C.blue + '66' : C.border),
        borderRadius: T.r.field,
        color: on ? C.blue : C.dim,
        fontSize: '12.5px',
        fontWeight: 600,
        padding: '8px 12px',
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      {label}
    </button>
  );

  const toolbar = (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '8px 10px',
        borderBottom: '1px solid ' + C.hair,
        flex: '0 0 auto',
      }}
    >
      <div style={{ display: 'flex', gap: '1px', minWidth: 0 }}>
        {dtab('today', 'Today')}
        {dtab('add', 'Add/Log')}
        {dtab('map', 'Map')}
        {dtab('routines', 'Routines')}
        {dtab('strategies', 'Strategies')}
      </div>
      <div style={{ flex: 1 }} />
      {/* v4:738-740 — the search box, Filters pill and + New button appear on the MAP TAB
          ONLY. Routines and Strategies carry their own filter chips inside their bodies, and
          Today / Add / Settings have nothing to filter. */}
      {isMap ? (
        <input
          value={ui.search}
          placeholder="Filter by title…"
          onChange={(e) => up({ search: e.target.value })}
          style={{
            width: '180px',
            background: C.panel,
            border: '1px solid ' + C.border,
            borderRadius: T.r.field,
            color: C.text,
            fontSize: '13px',
            padding: '8px 11px',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
      ) : null}
      {isMap
        ? pill(
            'Filters',
            ui.hideInactive || (ui.sideFilter || 'all') !== 'all' || ui.filterOpen,
            () => up({ filterOpen: !ui.filterOpen }),
          )
        : null}
      {isMap ? (
        <button
          onClick={() => up({ addOpen: !ui.addOpen })}
          style={{
            flex: '0 0 auto',
            background: C.blue,
            border: 'none',
            borderRadius: T.r.field,
            color: C.on,
            fontSize: '13px',
            fontWeight: 700,
            padding: '8px 14px',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          + New
        </button>
      ) : null}
      <button
        onClick={() => up({ tab: tab === 'settings' ? 'today' : 'settings', detail: null })}
        aria-label="settings"
        style={{
          flex: '0 0 auto',
          background: 'none',
          border: 'none',
          color: tab === 'settings' ? C.sig : C.dim,
          fontSize: '18px',
          cursor: 'pointer',
          padding: '0 2px',
          lineHeight: 1,
        }}
      >
        ⚙
      </button>
    </div>
  );

  // ── the docked detail pane — v4:743 ───────────────────────────────────────
  //
  // `DetailOverlay` paints `position:absolute; inset:0`, so the pane below is
  // `position:relative; overflow:hidden` and the editor fills it instead of the screen. Same
  // component, same two-phase close, same slide animation — just a smaller box. That is why
  // the phone's full-bleed editor and this docked one need no fork.
  const detailPane = () => {
    const dw = w('detail', isMap ? 400 : DETAIL);
    return (
      <div
        key="dp"
        style={{
          flex: '0 0 ' + dw + 'px',
          width: dw + 'px',
          position: 'relative',
          overflow: 'hidden',
          background: T.pane,
          backdropFilter: T.paneBlur,
          WebkitBackdropFilter: T.paneBlur,
        }}
      >
        {ui.detail ? (
          <>
            <DetailOverlay ctx={detailCtx} />
            <FocusOverlay ctx={focusCtx} open={ui.detail === '__focus__'} />
          </>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: C.dimmer,
              fontSize: '13px',
              padding: '24px',
              textAlign: 'center',
            }}
          >
            Select an item to edit — its full fields open here
          </div>
        )}
      </div>
    );
  };

  // ── the body ──────────────────────────────────────────────────────────────
  let body: ReactNode;

  if (isMap) {
    // v4:746 — one Finder column per level. `k` is the column index, so tapping a row in
    // column k truncates the path to k and appends that row: drilling from a column you have
    // already stepped back into replaces everything to its right rather than appending.
    const panelRow = (n: ModelNode, k: number) => {
      const canDrill = !['TASK', 'RECURRING'].includes(n.level);
      const drilled = ui.deskPath[k] === n.id;
      const go = () =>
        up({
          deskPath: [...ui.deskPath.slice(0, k), n.id],
          detail: null,
          menuFor: null,
          chipEdit: null,
        });
      return (
        <Row
          key={n.id}
          ctx={panelCtx}
          n={n}
          depth={0}
          sel={drilled}
          expandable={canDrill}
          open={false}
          noMenu
          badgeAbove
          onExpand={canDrill ? go : undefined}
          onTap={
            canDrill
              ? go
              : () =>
                  up({
                    detail: n.id,
                    deskPath: ui.deskPath.slice(0, k),
                    menuFor: null,
                    chipEdit: null,
                  })
          }
          // ⚠ v4:747 — THE ONE `dnd:true` IN THE MOCKUP. See the header.
          dnd
        />
      );
    };

    const renderPanel = (items: ModelNode[], k: number) => {
      // Task 11 — the orphan buckets, in COLUMN 0 only, under the goals. Same rule as the phone
      // Map (`MapScreen`): objects with no parent belong beside the roots, and a column showing
      // a project's children must not claim they are unfiled. Column 0 is the desktop's root
      // list, so it is the same place, not a second decision.
      const buckets = k === 0 ? orphanSections(panelCtx, (n) => panelRow(n, 0)) : [];
      return (
        <div
          key={'p' + k}
          data-desk-col={k}
          style={{ width: w('deskcol', DESKCOL) + 'px', flex: '0 0 auto', overflowY: 'auto', padding: '6px 4px' }}
        >
          {items.length || buckets.length ? (
            <>
              {items.map((n) => panelRow(n, k))}
              {buckets}
            </>
          ) : (
            <div style={{ color: C.dimmer, fontSize: '12px', padding: '20px', textAlign: 'center' }}>
              Nothing here
            </div>
          )}
        </div>
      );
    };

    // v4:749 — column 0 is the visible roots; each id on the path contributes its visible
    // children. A dangling id (its node deleted or moved) contributes an EMPTY column rather
    // than collapsing the path, which is v4's behaviour.
    const f = {
      q: ui.search.trim().toLowerCase(),
      hideInactive: ui.hideInactive,
      sideFilter: ui.sideFilter,
    };
    const colItems: ModelNode[][] = [graph.roots.filter((g) => subtreeVis(idx, g, f))];
    ui.deskPath.forEach((id) => {
      const nn = node(idx, id);
      colItems.push(nn ? nn.children.filter((c) => subtreeVis(idx, c, f)) : []);
    });

    const panels: ReactNode[] = [];
    colItems.forEach((items, k) => {
      if (k > 0) panels.push(dragHandle('deskcol', 'col' + k));
      panels.push(renderPanel(items, k));
    });
    panels.push(<div key="endline" style={{ width: '1px', flex: '0 0 auto', background: C.hair }} />);

    body = (
      <div style={{ display: 'flex', flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minWidth: 0,
            overflow: 'hidden',
          }}
        >
          <DeskCrumbBar T={T} deskPath={ui.deskPath} nodeAt={(id) => node(idx, id)} onNavigate={navigateDeskPath} />
          <div
            ref={navRef}
            style={{ flex: 1, minWidth: 0, overflowX: 'auto', display: 'flex' }}
          >
            {panels}
          </div>
        </div>
        {dragHandle('detail')}
        {detailPane()}
      </div>
    );
  } else if (tab === 'routines' || tab === 'strategies') {
    body = (
      <div style={{ display: 'flex', flex: 1, minWidth: 0 }}>
        <div
          style={{
            flex: '1 1 ' + w('list', 360) + 'px',
            minWidth: w('list', 360) + 'px',
            overflowY: 'auto',
          }}
        >
          {tab === 'routines' ? (
            <RoutinesScreen ctx={panelCtx} bare />
          ) : (
            <StrategiesScreen ctx={panelCtx} bare />
          )}
        </div>
        {/* ⚠ v4:756 puts a `dragHandle('detail')` here but the list beside it is
            `flex:1 1 <w('list')>` with NO handle of its own — so `st.widths.list` is never
            written and the list's width is always its 360px default. Dead state in v4;
            ported as-is (the read stays, nothing writes it) rather than removed, because the
            handle it would need is a design decision, not a port decision. */}
        {dragHandle('detail')}
        {detailPane()}
      </div>
    );
  } else {
    const inner =
      tab === 'today' ? (
        <TodayScreen ctx={todayCtx} />
      ) : tab === 'add' ? (
        <AddScreen ctx={addCtx} />
      ) : (
        <SettingsScreen ctx={settingsCtx} />
      );
    // v4:758 — Settings never docks an editor beside itself; it has no rows to open one from.
    body =
      ui.detail && tab !== 'settings' ? (
        <div style={{ display: 'flex', flex: 1, minWidth: 0 }}>
          <div style={{ width: '392px', flex: '0 0 auto', overflowY: 'auto' }}>{inner}</div>
          {dragHandle('detail')}
          {detailPane()}
        </div>
      ) : (
        <div style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}>{inner}</div>
      );
  }

  // v4:734 — the width the fake window animates to. Kept as a maxWidth for the narrow tabs
  // only; see the header for why the wide tabs are uncapped here and are not in v4.
  const maxWidth: CSSProperties['maxWidth'] = narrow
    ? (ui.detail && tab !== 'settings' ? 872 : 392) + 'px'
    : undefined;

  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        background: appBg(T, sky),
        fontFamily: T.font,
        color: C.text,
      }}
    >
      {/* v4:764 — the inner column carries `position:relative`, which is the containing block
          for everything absolutely positioned below: `AddPanel`, `PickerPage`, and (on the
          narrow tabs, where there is no docked pane) the detail editor. */}
      <div
        style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          width: '100%',
          maxWidth,
          margin: '0 auto',
          transition: 'max-width .3s cubic-bezier(.4,0,.2,1)',
        }}
      >
        <TopAccent T={T} />
        {toolbar}
        {isMap && ui.filterOpen ? <FilterMenu ctx={panelCtx} /> : null}
        {isMap && ui.addOpen ? <AddPanel ctx={panelCtx} /> : null}
        <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>{body}</div>

        {/* ⚠ NO frame-level `DetailOverlay` here, and that is deliberate.
            On the desktop path the editor ALWAYS lives inside `detailPane()`: the wide tabs
            dock it beside the list, and the narrow tabs dock a second pane the moment
            `ui.detail` is set (v4:758-760, which is why `W` grows 392 → 872). Settings is the
            only tab with no pane, and it has no row to open one from — the gear also clears
            `detail` on the way in (v4:742).
            A first pass DID render one here as well, guarded on `narrow`, and it mounted the
            editor TWICE on Today and Add: two "✕ Close" buttons, two location blocks, two live
            textareas over one node. Caught by driving the real page at 1440px, not by a test —
            both copies render, so nothing throws. */}
        {/* v4:769 — the picker sits ABOVE everything, including the docked detail pane, because
            `moveFor` is also set from that pane's location block. Its `wide` branch (a centred
            modal over a scrim) comes from `panelCtx.wide`. */}
        <PickerPage ctx={panelCtx} />
        {/* v4:775 — `this.toast()` is the last child on the desktop path too. Same component,
            same policy; the desktop is where the invalid drop is reachable at all, so this is
            the mount that actually carries the refusal message. */}
        <SignalBar T={T} sig={st.toast} onDismiss={st.dismissToast} />
      </div>
    </div>
  );
}

/**
 * v4 `deskCrumbBar()` (719) — the Finder path bar above the columns.
 *
 * A back button that steps one level out (disabled at the root), then `root › … › current`,
 * each crumb clickable to truncate the path to that point. The LAST crumb is bold and inert.
 *
 * Crumb colour comes from `typeColor` (the gallery's `typeRamp`), not v4's `this.TYPE` — the
 * same substitution `MapScreen`'s breadcrumb already makes, for the same reason: v4's map
 * coloured TASK green and collided with the completion green.
 *
 * ⚠ v4 renders `'—'` for a crumb whose node is missing, keeping the path intact rather than
 * truncating it. Kept — a dangling id shows an empty column, and silently rewriting the user's
 * path underneath them would be worse.
 */
export function DeskCrumbBar({
  T,
  deskPath,
  nodeAt,
  onNavigate,
}: {
  T: Theme;
  deskPath: readonly string[];
  nodeAt: (id: string) => ModelNode | undefined;
  onNavigate: (next: readonly string[]) => void;
}) {
  const C = T.c;
  const crumbs: Array<{ id: string | null; title: string; level: string | null }> = [
    { id: null, title: 'root', level: null },
    ...deskPath.map((id) => {
      const nn = nodeAt(id);
      return { id, title: nn ? nn.title : '—', level: nn ? nn.level : null };
    }),
  ];
  const canBack = deskPath.length > 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        flexWrap: 'wrap',
        padding: '8px 14px',
        borderBottom: '1px solid ' + C.hair,
        flex: '0 0 auto',
        background: T.chrome,
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
      }}
    >
      <button
        onClick={() => canBack && onNavigate(deskPath.slice(0, -1))}
        aria-label="back one level"
        disabled={!canBack}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '26px',
          height: '26px',
          borderRadius: T.r.ctl,
          border: '1px solid ' + C.border,
          background: canBack ? C.panel : 'transparent',
          color: canBack ? C.text : C.dimmer,
          cursor: canBack ? 'pointer' : 'default',
          flex: '0 0 auto',
        }}
      >
        <svg width={15} height={15} viewBox="0 0 24 24" fill="none">
          <path
            d="M15 6l-6 6 6 6"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {i > 0 ? <span style={{ color: C.dimmer, fontSize: '12px' }}>›</span> : null}
            <button
              onClick={() => onNavigate(deskPath.slice(0, i))}
              style={{
                background: 'none',
                border: 'none',
                color: c.level ? typeColor(T, c.level) : C.text,
                fontWeight: i === crumbs.length - 1 ? 700 : 600,
                fontSize: '13px',
                cursor: i === crumbs.length - 1 ? 'default' : 'pointer',
                padding: 0,
                fontFamily: 'inherit',
              }}
            >
              {c.title}
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
