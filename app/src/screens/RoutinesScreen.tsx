import type { ReactNode } from 'react';
import { Rail } from '../components/atoms/index.ts';
import { Row } from '../components/rows/index.ts';
import { CrossTabMatches } from '../components/panels/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';
import { pathTo } from '../model/index.ts';
import type { ModelNode } from '../model/index.ts';
import { StructurePanel } from './StructurePanel.tsx';

/** v4:685 — days-per-unit, used only for sorting. `quarter` and `year` are not in `OPTS.unit`. */
const U_DAYS: Record<string, number> = { day: 1, week: 7, month: 30, quarter: 91, year: 365 };

/**
 * The Routines tab — v4 `recurringBody()` (~677) inside `structurePanel`.
 *
 * Every RECURRING object in the graph, grouped under the project it belongs to, with the
 * project's full ancestor path as the header. This is the one place `toggleCollapse` (v4:676)
 * belongs: the GROUP HEADERS collapse, not the tree. (The Map is a drill-in and collapses
 * nothing — an earlier revision of the plan conflated the two.)
 *
 * ── ordering says something ──────────────────────────────────────────────────
 * Within a group, `rank` sorts by how often the thing comes round: as-needed first (rank −1,
 * it has no cadence at all), then daily, weekly, monthly. So the shape of a routine group is
 * legible before any label is read.
 *
 * ── the filters here are the tab's own ───────────────────────────────────────
 * The All / As needed / Scheduled chips are `st.recFilter`, separate from the shared filter
 * block. ⚠ Note what `match` (v4:684) does NOT consult: neither `hideInactive` nor the Side
 * filter reaches this list, so a paused routine still shows with "Hide inactive" on. That is
 * v4's behaviour, ported as-is and flagged rather than corrected — it is arguably right (a
 * paused routine is exactly what you come here to un-pause) but it is not a decision this port
 * gets to make.
 *
 * Rows use `hideBadge` (the whole tab is one type, so the badge would be noise) and `noMenu`.
 * `flat:true` is passed by v4 and is a dead parameter there — see `RowOptions`.
 *
 * `bare` — v4's desktop path calls `recurringBody()` DIRECTLY (v4:756), with no
 * `structurePanel` wrapper around it, because the desktop toolbar already carries the search
 * box and the `+` button that `MapControls` provides on the phone. Everything this tab needs
 * beyond that (its own filter chips) is inside the body, which is why v4 can drop the wrapper
 * without losing a control. Verified by reading v4:756: `tab==='routines'?this.recurringBody():
 * this.strategiesBody()` inside a plain scrolling div.
 *
 * A prop rather than a second component — same library, two layouts.
 */
export function RoutinesScreen({ ctx, bare = false }: { ctx: PanelCtx; bare?: boolean }) {
  const { T, graph, idx, ui, up } = ctx;
  const C = T.c;
  const q = ui.search.trim().toLowerCase();
  const rf = ui.recFilter || 'all';

  const fchip = (label: string, val: 'all' | 'asneeded' | 'scheduled') => (
    <button
      key={val}
      onClick={() => up({ recFilter: val })}
      style={{
        flex: '0 0 auto',
        background: rf === val ? C.blue + '22' : C.panel,
        border: '1px solid ' + (rf === val ? C.blue + '66' : C.border),
        borderRadius: T.r.chip,
        color: rf === val ? C.blue : C.dim,
        fontSize: '12px',
        fontWeight: 600,
        padding: '6px 13px',
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      {label}
    </button>
  );

  const match = (r: ModelNode): boolean =>
    (!q || r.title.toLowerCase().includes(q)) &&
    (rf === 'all' ||
      (rf === 'asneeded' ? r.vals.unit === 'as_needed' : r.vals.unit !== 'as_needed'));

  const rank = (r: ModelNode): number =>
    r.vals.unit === 'as_needed'
      ? -1
      : (Number(r.vals.count) || 1) * (U_DAYS[String(r.vals.unit)] ?? 7);

  const groups: Array<{ parent: ModelNode | null; label?: string; recs: ModelNode[] }> = [];
  const walk = (n: ModelNode): void => {
    const recs = n.children.filter((c) => c.level === 'RECURRING');
    if (recs.length) groups.push({ parent: n, recs });
    n.children.forEach(walk);
  };
  graph.roots.forEach(walk);

  /**
   * UNPARENTED recurrings get their own group, so they appear on THIS tab too.
   *
   * June, 2026-07-18: "Don't recurring tasks show in both map and routines tabs?" They do — Map
   * renders RECURRING as a leaf of its parent, and this tab groups them by that same parent. But
   * `walk` above only ever finds recurrings that are a CHILD of something, so an orphan appeared
   * in NEITHER tab, and after Task 11 only in Map's bucket. That asymmetry was a bug, not a
   * design decision: a parented routine is on two tabs, an unparented one was on one.
   *
   * This is the existing grouping shape reused, not a new pattern — the group header is the
   * bucket's own label from the endpoint, and like every other bucket it renders only when
   * non-empty. Filing one out of here is the same move affordance as everywhere else, which is
   * the point: the bucket is a staging area for things needing a home, not a home.
   */
  const orphanRecs = (graph.orphans ?? [])
    .filter((b) => b.key === 'orphan_recurring')
    .flatMap((b) => b.nodes.filter((n) => n.level === 'RECURRING'));
  if (orphanRecs.length) {
    groups.push({
      parent: null,
      label:
        (graph.orphans ?? []).find((b) => b.key === 'orphan_recurring')?.label ?? 'No project',
      recs: orphanRecs,
    });
  }

  /** v4:676 `toggleCollapse(id)`, verbatim: present = collapsed, delete to expand. */
  const toggleCollapse = (id: string) => {
    const c: Record<string, true> = { ...ui.collapsed };
    if (c[id]) delete c[id];
    else c[id] = true;
    up({ collapsed: c });
  };

  const body: ReactNode[] = [];
  body.push(
    <div key="rf" style={{ display: 'flex', gap: '7px', padding: '12px 12px 4px', flexWrap: 'wrap' }}>
      {fchip('All', 'all')}
      {fchip('As needed', 'asneeded')}
      {fchip('Scheduled', 'scheduled')}
    </div>,
  );

  let any = false;
  /** Task 11 — what this tab actually listed, so the cross-tab block does not repeat it. */
  const shown = new Set<string>();
  groups.forEach((g) => {
    const recs = g.recs.filter(match).sort((a, b) => rank(a) - rank(b));
    if (!recs.length) return;
    any = true;
    recs.forEach((r) => shown.add(r.id));
    // An unparented group has no ancestry to render and no node id to key collapse on, so it
    // uses the bucket's own label and a stable synthetic key.
    const path = g.parent
      ? pathTo(idx, g.parent.id)
          .map((p) => p.title)
          .join(' › ')
      : (g.label ?? 'No project');
    const gid = g.parent ? g.parent.id : '__orphan_recurring__';
    const col = !!ui.collapsed[gid];
    body.push(
      <div
        key={'gh' + gid}
        onClick={() => toggleCollapse(gid)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          padding: '14px 12px 6px',
          cursor: 'pointer',
        }}
      >
        <span
          style={{
            color: C.dimmer,
            fontSize: '9px',
            flex: '0 0 auto',
            display: 'inline-block',
            transform: col ? 'rotate(-90deg)' : 'none',
            transition: 'transform .15s',
          }}
        >
          ▼
        </span>
        {g.parent ? <Rail T={T} level={g.parent.level} /> : null}
        <span style={{ flex: 1, minWidth: 0, fontSize: '11.5px', fontWeight: 700, color: C.dim }}>
          {path}
        </span>
        <span style={{ fontSize: '11px', color: C.dimmer, flex: '0 0 auto' }}>{recs.length}</span>
      </div>,
    );
    if (!col) {
      recs.forEach((r) =>
        body.push(
          <Row
            key={r.id}
            ctx={ctx}
            n={r}
            depth={1}
            onTap={() => up({ detail: r.id })}
            hideBadge
            flat
            noMenu
          />,
        ),
      );
    }
  });

  if (!any) {
    body.push(
      <div
        key="re"
        style={{ color: C.dimmer, fontSize: '13px', textAlign: 'center', padding: '40px 20px' }}
      >
        No recurring items
      </div>,
    );
  }

  body.push(
    <div
      key="rn"
      style={{
        fontSize: '11.5px',
        color: C.dimmer,
        textAlign: 'center',
        padding: '16px 24px',
        lineHeight: 1.5,
      }}
    >
      Tap the circle to mark an item not-done so it re-enters the daily plan.
    </div>,
  );

  // Task 11 — matches that live on the Map or Strategies, named as such. Renders nothing when
  // the filter box is empty or every match is already in the list above.
  body.push(<CrossTabMatches key="ctm" ctx={ctx} shownIds={shown} />);

  if (bare) return <>{body}</>;
  return <StructurePanel ctx={ctx}>{body}</StructurePanel>;
}
