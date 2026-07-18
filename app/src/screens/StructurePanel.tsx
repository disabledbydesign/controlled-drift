import type { ReactNode } from 'react';
import { AddPanel, FilterMenu, MapControls } from '../components/panels/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';

/**
 * v4 `structurePanel(kind)` (~959) — the frame shared by Map, Routines and Strategies.
 *
 * v4 verbatim:
 *   div{position:relative, flex:1, display:flex, flexDirection:column, overflow:hidden}(
 *     mapControls(),
 *     st.filterOpen ? filterMenu() : null,
 *     st.addOpen ? addPanel() : null,
 *     div{flex:1, overflowY:auto, padding:'6px 6px 40px'}(body))
 *
 * Three things this shape does that a plain scrolling page would not:
 *
 * 1. The controls and the filter block are OUTSIDE the scroller, so they stay put while the
 *    list moves. This is why `AppShell` routes these three tabs around its own scrolling
 *    wrapper — nested inside one, `flex:1` here is inert, the height collapses to content, and
 *    the controls scroll away with the list.
 * 2. `position:relative` is the containing block for `AddPanel`, which is absolutely
 *    positioned at `top:100px; right:12px` — i.e. anchored under the `+` button in
 *    `MapControls`, not to the viewport.
 * 3. `padding:'6px 6px 40px'` on the scroller: the 40px tail is what keeps the last row clear
 *    of the tab bar.
 *
 * ⚠ ONE ADDITION to v4's style objects: `minHeight:0` on the scroller. Without it a flex child
 * refuses to shrink below its content height and the list overflows instead of scrolling.
 * v4 gets away with `overflow:hidden` on the parent alone; called out rather than folded in.
 */
export function StructurePanel({ ctx, children }: { ctx: PanelCtx; children: ReactNode }) {
  const { ui } = ctx;
  return (
    <div
      style={{
        position: 'relative',
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <MapControls ctx={ctx} />
      {ui.filterOpen ? <FilterMenu ctx={ctx} /> : null}
      {ui.addOpen ? <AddPanel ctx={ctx} /> : null}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '6px 6px 40px' }}>
        {children}
      </div>
    </div>
  );
}
