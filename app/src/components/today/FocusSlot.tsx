import { PANEL } from './types.ts';
import type { TodayCtx } from './types.ts';

/**
 * v4 `fmtDate(v)` (~840):
 *   if(!v)return '—'; const s=''+v; const d=new Date(s.length<=10?s+'T00:00':s);
 *   return isNaN(d.getTime())?s:d.toLocaleDateString('en-US',{month:'short',day:'numeric'});
 *
 * The `+'T00:00'` on a bare `YYYY-MM-DD` is load-bearing: without it the string parses as UTC
 * midnight and renders as the previous day for anyone west of Greenwich. Unparseable input
 * falls through to the raw string rather than "Invalid Date".
 */
export function fmtDate(v: string | undefined | null): string {
  if (!v) return '—';
  const s = '' + v;
  const d = new Date(s.length <= 10 ? s + 'T00:00' : s);
  return isNaN(d.getTime()) ? s : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export interface FocusSlotProps {
  ctx: TodayCtx;
}

/**
 * v4 `focusSlot()` (~1013) — the focus-period strip at the very top of Today.
 *
 * Two parts. The header line (period name + date range) renders only when a period is
 * currently running (`when === 'now'`); with no active period the strip is just the
 * disclosure button, and v4 drops the button's top border in that case so there is no
 * hairline hanging under nothing.
 *
 * The `›` rotates 90° on expand. `panelin` is the shared entry animation, already in
 * `index.html`.
 *
 * ⚠ The expanded body is v4's `focusPanel()` (~814), which is **Task 9**, not this task.
 * A visible marker renders in its place rather than nothing at all — a stub that renders
 * nothing is indistinguishable from a missing mount, which is the failure mode
 * `docs/BUILD_DOC.md` §3 is about. It is placeholder chrome and comes out with Task 9.
 */
export function FocusSlot({ ctx }: FocusSlotProps) {
  const C = ctx.T.c;
  const p = ctx.periods.find((x) => x.when === 'now');
  const open = ctx.ui.focusExpanded;

  return (
    <div
      style={{
        background: ctx.T.chrome,
        backdropFilter: ctx.T.blur,
        WebkitBackdropFilter: ctx.T.blur,
        borderBottom: '1px solid ' + C.hair,
      }}
    >
      {p ? (
        <div
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '11px 14px 10px' }}
        >
          <span style={{ fontSize: '12px', color: C.rose, fontWeight: 500, flex: 1, lineHeight: 1.3 }}>
            {p.name}
          </span>
          <span style={{ fontSize: '11px', color: C.roseDim, flex: '0 0 auto' }}>
            {fmtDate(p.start) + ' – ' + fmtDate(p.end)}
          </span>
        </div>
      ) : null}
      <button
        onClick={() => ctx.up({ focusExpanded: !open })}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          width: '100%',
          background: 'none',
          border: 'none',
          borderTop: p ? '1px solid ' + C.roseBorder : 'none',
          color: C.dim,
          fontSize: '12px',
          fontFamily: 'inherit',
          padding: '9px 14px',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        See focus periods
        <span
          style={{
            fontSize: '10px',
            color: C.dimmer,
            marginLeft: 'auto',
            display: 'inline-block',
            transform: open ? 'rotate(90deg)' : 'none',
            transition: 'transform .15s',
          }}
        >
          ›
        </span>
      </button>
      {open ? (
        <div style={{ padding: '0 14px 12px', animation: 'panelin ' + PANEL }}>
          <div style={{ fontFamily: ctx.T.mono, fontSize: '10px', color: C.dimmer }}>
            Focus period editor — not built yet (Task 9).
          </div>
        </div>
      ) : null}
    </div>
  );
}
