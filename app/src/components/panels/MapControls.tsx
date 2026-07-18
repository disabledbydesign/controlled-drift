import type { ReactNode } from 'react';
import type { PanelCtx } from './types.ts';

/**
 * v4 `mapControls()` (~967) — the control bar pinned above every structure list.
 *
 * Three controls in a row: the title filter, a funnel that opens `FilterMenu`, and `+` that
 * opens `AddPanel`. It is `flex:'0 0 auto'` inside `structurePanel`'s column and the list
 * scrolls underneath it, which is the whole reason the structure tabs sit OUTSIDE the shell's
 * scrolling wrapper (see the fork comment in `AppShell`).
 *
 * ── the funnel is lit by STATE, not just by being open ───────────────────────
 * v4: `st.filterOpen || st.hideInactive || (st.sideFilter||'all')!=='all'`. So after you close
 * the filter block, the funnel stays lit while a filter is still narrowing the list. Without
 * that, a hidden branch looks like a missing branch.
 *
 * The `Filter by title…` box is per-tab and per-tab only — it reads and writes the single
 * `search` field, and each body applies it to its own list. Cross-tab search (spanning Map,
 * Routines and Strategies at once) is Task 11 and is deliberately NOT here.
 */
export function MapControls({ ctx }: { ctx: PanelCtx }) {
  const { T, ui, up } = ctx;
  const C = T.c;

  const iconBtn = (child: ReactNode, onClick: () => void, label: string, active: boolean) => (
    <button
      onClick={onClick}
      aria-label={label}
      style={{
        flex: '0 0 auto',
        width: '40px',
        height: '38px',
        background: active ? C.blue + '22' : C.panel,
        border: '1px solid ' + (active ? C.blue + '66' : C.border),
        borderRadius: T.r.field,
        color: active ? C.blue : C.dim,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {child}
    </button>
  );

  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid ' + C.hair,
        flex: '0 0 auto',
        background: T.chrome,
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
      }}
    >
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <input
          value={ui.search}
          placeholder="Filter by title…"
          onChange={(e) => up({ search: e.target.value })}
          style={{
            flex: 1,
            minWidth: 0,
            background: C.panel,
            border: '1px solid ' + C.border,
            borderRadius: T.r.field,
            color: C.text,
            fontSize: '13px',
            padding: '9px 11px',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        {iconBtn(
          <svg width={16} height={16} viewBox="0 0 24 24" fill="none">
            <path
              d="M3 5h18l-7 8v6l-4-2v-4z"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinejoin="round"
            />
          </svg>,
          () => up({ filterOpen: !ui.filterOpen }),
          'filters',
          ui.filterOpen || ui.hideInactive || (ui.sideFilter || 'all') !== 'all',
        )}
        {iconBtn(
          <span style={{ fontSize: '22px', lineHeight: 1 }}>+</span>,
          () => up({ addOpen: !ui.addOpen }),
          'add',
          ui.addOpen,
        )}
      </div>
    </div>
  );
}
