import { FocusPanel } from '../focus/index.ts';
import { PANEL } from './types.ts';
import type { TodayCtx } from './types.ts';

/**
 * `fmtDate` moved to `components/focus/fmtDate.ts` with Task 9 — the whole focus editor
 * formats dates with it, and it was never Today-specific. Re-exported here so this module's
 * existing import surface (`today/index.ts`) is unchanged.
 */
export { fmtDate } from '../focus/fmtDate.ts';
import { fmtDate } from '../focus/fmtDate.ts';

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
 * The expanded body is v4's `focusPanel()` (~814), mounted here as `FocusPanel` (Task 9).
 * The visible "not built yet" marker that stood in for it is gone.
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
          <FocusPanel ctx={ctx.focus} />
        </div>
      ) : null}
    </div>
  );
}
