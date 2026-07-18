import { alpha } from '@tokens';
import { Switch } from '../atoms/index.ts';
import { setVal, toggleActive } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface RecurringPlanRowProps {
  ctx: DetailCtx;
  n: ModelNode;
}

/**
 * v4 `recurringPlanRow(n)` (~402) — the in-plan switch plus duration, for RECURRING only.
 *
 * ⚠ NOT NAMED IN ANY TASK'S PORT LIST. `detail()` calls it at v4:593, directly above
 * `recurrenceCard`, so `detail()` cannot be ported without it. It is absent from Task 4's
 * checklist (which built `row()` and `lead()` only) and from Tasks 6-11. Ported here with
 * `detail()` because that is its only call site in v4; flagged so it is not ported a second
 * time when the Routines tab lands.
 *
 * ── the label pairs are not synonyms ─────────────────────────────────────────
 * A cadence-bearing recurring reads IN PLAN / PAUSED. An `as_needed` one reads OPEN / CLOSED
 * and switches its accent from orange to teal — because "paused" is the wrong word for a
 * thing with no schedule to pause. The underlying value is the same `paused` flag either way.
 *
 * `toggleActive` stores `paused`; the backend endpoint takes its INVERSE, `active`
 * (api_contract_v2 Q3). That inversion belongs at the API seam, not here.
 *
 * Duration lives on this row rather than in the form because `detail()` filters
 * 'Duration (min)' out of the RECURRING control list along with the schedule fields (v4:548).
 */
export function RecurringPlanRow({ ctx, n }: RecurringPlanRowProps) {
  const { T, graph, apply } = ctx;
  const C = T.c;
  const id = n.id;
  const act = !n.vals.paused;
  const asNeeded = n.vals.unit === 'as_needed';
  const col = asNeeded ? C.teal : C.orange;
  const label = asNeeded ? (act ? 'OPEN' : 'CLOSED') : act ? 'IN PLAN' : 'PAUSED';
  const box = C.box;

  return (
    <div
      style={{
        marginBottom: '14px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flexWrap: 'wrap',
        // v4: `col+'14'` — .078 · `col+'66'` — .4
        background: act ? alpha(col, 0.078) : C.panel,
        border: '1px solid ' + (act ? alpha(col, 0.4) : C.border),
        borderRadius: T.r.ctl,
        padding: '9px 12px',
      }}
    >
      <button
        onClick={() => apply(toggleActive(graph, id))}
        aria-label="toggle in plan"
        style={{
          flex: '0 0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '9px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          fontFamily: 'inherit',
        }}
      >
        <Switch T={T} on={act} col={col} />
        <span
          style={{
            fontSize: '11px',
            fontWeight: 800,
            letterSpacing: '.12em',
            fontFamily: T.mono,
            color: act ? col : C.dimmer,
          }}
        >
          {label}
        </span>
      </button>
      <div style={{ flex: 1 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', flex: '0 0 auto' }}>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '.04em',
            textTransform: 'uppercase',
            color: C.dim,
          }}
        >
          Duration
        </span>
        <input
          type="number"
          min={0}
          value={n.vals.duration ? String(n.vals.duration) : ''}
          placeholder="—"
          onChange={(e) => apply(setVal(graph, id, 'duration', e.target.value))}
          style={{
            width: '64px',
            fontSize: '13.5px',
            color: C.text,
            background: box,
            border: '1px solid ' + C.border,
            borderRadius: T.r.field,
            padding: '7px 9px',
            outline: 'none',
            fontFamily: 'inherit',
            colorScheme: 'dark',
          }}
        />
        <span style={{ fontSize: '12px', color: C.dimmer }}>min</span>
      </div>
    </div>
  );
}
