import type { ReactNode } from 'react';
import { Switch } from '../components/atoms/index.ts';
import { Row } from '../components/rows/index.ts';
import { CrossTabMatches, PANEL } from '../components/panels/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';
import { isInactive } from '../model/index.ts';
import { StructurePanel } from './StructurePanel.tsx';

/**
 * The Strategies tab — v4 `strategiesBody()` (~651) inside `structurePanel`.
 *
 * Strategy objects sit outside the Goal→Project→Task hierarchy (they live on
 * `graph.strategies`, not `graph.roots`), so this is a flat list with its own filter block.
 *
 * ── two filters, two different controls, and that is v4's ────────────────────
 * "When" is a row of chips over `OPTS.strategyState` with an explicit All; "Active only" is a
 * switch in its own bordered card. The Filter button lights up either when the block is open
 * or when a filter is still narrowing the list, and a Clear link appears only in the latter
 * case — same principle as the funnel in `MapControls`.
 *
 * ⚠ Note this tab has TWO filter surfaces: this one and the shared `FilterMenu` above it,
 * whose "Hide inactive" ALSO removes retired strategies (`st.hideInactive` is the first
 * conjunct of the list filter below). "Active only" and "Hide inactive" therefore overlap
 * here. That redundancy is v4's, ported as-is.
 *
 * The intro paragraph is v4's copy verbatim, including its curly quotes.
 *
 * ── flagged, NOT fixed: this tab under-serves the real data ──────────────────
 * `docs/BUILD_DOC.md` §8 records that June's 12 live Strategy objects lean hardest on `name`,
 * `What for` and `Context` — and `Context` has no home in the mockup at all, while
 * `Applies when` (the `when` chip here) is populated on 1 of 12. This port reproduces the
 * mockup; surfacing `Context` and `Learning notes` is a design change and hers to approve.
 *
 * `bare` — v4's desktop path calls `strategiesBody()` DIRECTLY (v4:756), with no
 * `structurePanel` wrapper around it, because the desktop toolbar already carries the search
 * box and the `+` button that `MapControls` provides on the phone. Everything this tab needs
 * beyond that (its own filter chips) is inside the body, which is why v4 can drop the wrapper
 * without losing a control. Verified by reading v4:756: `tab==='routines'?this.recurringBody():
 * this.strategiesBody()` inside a plain scrolling div.
 *
 * A prop rather than a second component — same library, two layouts.
 */
export function StrategiesScreen({ ctx, bare = false }: { ctx: PanelCtx; bare?: boolean }) {
  const { T, graph, schema, ui, up } = ctx;
  const C = T.c;
  const q = ui.search.trim().toLowerCase();
  const sw = ui.stratWhen || 'all';
  const sst = ui.stratStatus || 'all';
  const filterOpen = !!ui.stratFilterOpen;
  const filterActive = sw !== 'all' || sst === 'active';

  const fchip = (label: string, on: boolean, onClick: () => void) => (
    <button
      key={label}
      onClick={onClick}
      style={{
        flex: '0 0 auto',
        background: on ? C.blue + '22' : C.panel,
        border: '1px solid ' + (on ? C.blue + '66' : C.border),
        borderRadius: T.r.chip,
        color: on ? C.blue : C.dim,
        fontSize: '12px',
        fontWeight: 600,
        padding: '6px 12px',
        cursor: 'pointer',
        fontFamily: 'inherit',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </button>
  );

  const body: ReactNode[] = [];

  body.push(
    <div
      key="sn"
      style={{ fontSize: '11.5px', color: C.dimmer, padding: '12px 14px 6px', lineHeight: 1.5 }}
    >
      Standing disciplines read into every daily plan. “Always” apply every time; the rest fire
      only in a matching state.
    </div>,
  );

  body.push(
    <div
      key="sfbtn"
      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '2px 12px 10px' }}
    >
      <button
        onClick={() => up({ stratFilterOpen: !filterOpen })}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: filterOpen || filterActive ? C.blue + '22' : C.panel,
          border: '1px solid ' + (filterOpen || filterActive ? C.blue + '66' : C.border),
          borderRadius: T.r.chip,
          color: filterOpen || filterActive ? C.blue : C.dim,
          fontSize: '12px',
          fontWeight: 600,
          padding: '6px 12px',
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <svg width={13} height={13} viewBox="0 0 24 24" fill="none">
          <path
            d="M3 5h18l-7 8v6l-4-2v-4z"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinejoin="round"
          />
        </svg>
        Filter
        {filterActive ? (
          <span
            style={{ width: '6px', height: '6px', borderRadius: '50%', background: C.blue }}
          />
        ) : null}
      </button>
      {filterActive ? (
        <button
          onClick={() => up({ stratWhen: 'all', stratStatus: 'all' })}
          style={{
            background: 'none',
            border: 'none',
            color: C.dimmer,
            fontSize: '11.5px',
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'inherit',
            padding: 0,
          }}
        >
          Clear
        </button>
      ) : null}
    </div>,
  );

  if (filterOpen) {
    body.push(
      <div key="sf1" style={{ padding: '0 12px 8px', animation: 'panelin ' + PANEL }}>
        <div
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.08em',
            textTransform: 'uppercase',
            color: C.dimmer,
            marginBottom: '6px',
          }}
        >
          When
        </div>
        <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap' }}>
          {fchip('All', sw === 'all', () => up({ stratWhen: 'all' }))}
          {(schema.OPTS.strategyState ?? []).map((w) =>
            fchip(w, sw === w, () => up({ stratWhen: sw === w ? 'all' : w })),
          )}
        </div>
      </div>,
    );
    body.push(
      <div
        key="sf2"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          margin: '0 12px 12px',
          padding: '10px 12px',
          background: C.panel,
          border: '1px solid ' + C.border,
          borderRadius: T.r.ctl,
          animation: 'panelin ' + PANEL,
        }}
      >
        <div>
          <div
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '.08em',
              textTransform: 'uppercase',
              color: C.dimmer,
              marginBottom: '2px',
            }}
          >
            Status
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: C.text }}>Active only</div>
        </div>
        <button
          onClick={() => up({ stratStatus: sst === 'active' ? 'all' : 'active' })}
          aria-label="toggle active only"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            flex: '0 0 auto',
            display: 'flex',
          }}
        >
          <Switch T={T} on={sst === 'active'} col={C.blue} />
        </button>
      </div>,
    );
  }

  const strat = graph.strategies.filter((s) => {
    if (ui.hideInactive && isInactive(s)) return false;
    if (sst === 'active' && isInactive(s)) return false;
    if (sw !== 'all' && (s.vals.when || 'Always') !== sw) return false;
    if (q && !s.title.toLowerCase().includes(q)) return false;
    return true;
  });

  if (strat.length) {
    strat.forEach((s) =>
      body.push(
        <Row
          key={s.id}
          ctx={ctx}
          n={s}
          depth={0}
          onTap={() => up({ detail: s.id })}
          hideBadge
          flat
          noMenu
        />,
      ),
    );
  } else {
    body.push(
      <div
        key="se"
        style={{ color: C.dimmer, fontSize: '13px', textAlign: 'center', padding: '40px 20px' }}
      >
        No strategies — add one with +
      </div>,
    );
  }

  // Task 11 — matches that live on the Map or Routines, named as such. This is the tab where the
  // gap was most visible: nothing outside `graph.strategies` could ever be found from here.
  body.push(
    <CrossTabMatches key="ctm" ctx={ctx} shownIds={new Set(strat.map((s) => s.id))} />,
  );

  if (bare) return <>{body}</>;
  return <StructurePanel ctx={ctx}>{body}</StructurePanel>;
}
