import type { CSSProperties, ReactNode } from 'react';
import { alpha } from '@tokens';
import { setVal, toggleMulti } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface RecurrenceCardProps {
  ctx: DetailCtx;
  n: ModelNode;
}

/**
 * v4 `fmtTime(v)` (~401). Exported because `RecurringPlanRow` uses it too.
 * `'14:05'` → `'2:05 PM'`; empty → `'—'`. Midnight maps to 12 AM via `((H+11)%12)+1`.
 */
export function fmtTime(v: unknown): string {
  if (!v) return '—';
  const p = String(v).split(':');
  const H = Number(p[0]) || 0;
  const M = Number(p[1]) || 0;
  const ap = H < 12 ? 'AM' : 'PM';
  const h12 = ((H + 11) % 12) + 1;
  return h12 + ':' + String(M).padStart(2, '0') + ' ' + ap;
}

/**
 * v4 `recurrenceCard(n)` (~414) — the recurrence editor.
 *
 * ── WHY THIS EXISTS ALONGSIDE THE SCHEMA-DRIVEN FORM ─────────────────────────
 * The RECURRING level's schedule is four separate control tuples (`Repeats`, `Day of week`,
 * `Day of month`, `Time of day`) whose relevance depends on each other: day-of-week only
 * means anything for a weekly cadence, day-of-month only for monthly, and neither for
 * `as_needed`. Rendered independently they would all show at once, three of them inert. So
 * `detail()` FILTERS those labels out of the RECURRING control list (v4:548) and renders this
 * card in their place, where the cadence choice drives what appears below it.
 *
 * Its option lists are still schema-derived: `OPTS.unit` for the cadence pills, `OPTS.dow` for
 * the day pills. Nothing here is a hardcoded vocabulary.
 *
 * ── the calendar branch ──────────────────────────────────────────────────────
 * When `vals.source === 'calendar'` the time is READ-ONLY: a clock glyph, the formatted time,
 * a teal "from Calendar" tag and the line "Synced — edit the time in your calendar." The
 * editable `<input type=time>` is not rendered at all, so there is nothing to type into that
 * would be silently overwritten by the next sync.
 *
 * ── conditional rows, exactly as v4 gates them ───────────────────────────────
 *   count row   `u && u !== 'as_needed'`
 *   day row     `u === 'week'` → day-of-week pills · `u === 'month'` → day-of-month number
 *   time row    `u && u !== 'as_needed'`
 * With no unit set, only the cadence pills show.
 */
export function RecurrenceCard({ ctx, n }: RecurrenceCardProps) {
  const { T, graph, schema, apply } = ctx;
  const C = T.c;
  const id = n.id;
  const u = n.vals.unit ? String(n.vals.unit) : '';
  const cnt = n.vals.count ? String(n.vals.count) : '';
  const cal = n.vals.source === 'calendar';
  const box = C.box;

  const sub = (t: string) => (
    <div
      style={{
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '.08em',
        textTransform: 'uppercase',
        color: C.dimmer,
        marginBottom: '7px',
      }}
    >
      {t}
    </div>
  );

  const pill = (label: string, on: boolean, onClick: () => void, small?: boolean) => (
    <button
      key={label}
      onClick={onClick}
      style={{
        fontSize: small ? '12px' : '12.5px',
        fontWeight: 600,
        padding: small ? '6px 10px' : '8px 14px',
        borderRadius: T.r.chip,
        cursor: 'pointer',
        fontFamily: 'inherit',
        border: '1px solid ' + (on ? C.orange : C.border),
        // v4: `C.orange+'26'` — .149
        background: on ? alpha(C.orange, 0.149) : box,
        color: on ? C.orange : C.dim,
        textTransform: 'capitalize',
      }}
    >
      {label}
    </button>
  );

  const inp: CSSProperties = {
    fontSize: '13.5px',
    color: C.text,
    background: box,
    border: '1px solid ' + C.border,
    borderRadius: T.r.field,
    padding: '9px 11px',
    outline: 'none',
    fontFamily: 'inherit',
  };

  const units = (schema.OPTS.unit || []) as string[];
  const dows = (schema.OPTS.dow || []) as string[];

  const pills = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {units.map((o) => pill(o.replace(/_/g, ' '), u === o, () => apply(setVal(graph, id, 'unit', o))))}
    </div>
  );

  const countRow =
    u && u !== 'as_needed' ? (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '13.5px', color: C.dim }}>every</span>
        <input
          type="number"
          min={1}
          value={cnt || '1'}
          onChange={(e) => apply(setVal(graph, id, 'count', e.target.value))}
          style={{ ...inp, width: '70px' }}
        />
        <span style={{ fontSize: '13.5px', color: C.dim }}>
          {(Number(cnt) || 1) > 1 ? u + 's' : u}
        </span>
      </div>
    ) : null;

  let dayRow: ReactNode = null;
  if (u === 'week') {
    // v4: `const cur = n.vals.dow || ''` then `cur.includes(d)`. The fixture stores dow as a
    // comma-joined STRING; `String(...)` keeps the array case sane rather than throwing.
    const cur = n.vals.dow ? String(n.vals.dow) : '';
    dayRow = (
      <div>
        {sub('On')}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {dows.map((d) =>
            pill(d, cur.includes(d), () => apply(toggleMulti(graph, id, 'dow', d)), true),
          )}
        </div>
      </div>
    );
  } else if (u === 'month') {
    dayRow = (
      <div>
        {sub('Day of month')}
        <input
          type="number"
          min={1}
          max={31}
          value={n.vals.dom ? String(n.vals.dom) : ''}
          placeholder="e.g. 1"
          onChange={(e) => apply(setVal(graph, id, 'dom', e.target.value))}
          style={{ ...inp, width: '92px' }}
        />
      </div>
    );
  }

  let timeRow: ReactNode = null;
  if (u && u !== 'as_needed') {
    timeRow = cal ? (
      <div>
        {sub('Time')}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', ...inp }}>
          <svg
            width={15}
            height={15}
            viewBox="0 0 24 24"
            fill="none"
            style={{ color: C.teal, flex: '0 0 auto' }}
          >
            <circle cx={12} cy={12} r={9} stroke="currentColor" strokeWidth={2} />
            <path d="M12 7v5l3 2" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
          </svg>
          <span style={{ flex: 1, color: C.text }}>{fmtTime(n.vals.tod)}</span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '.05em',
              textTransform: 'uppercase',
              color: C.teal,
              // v4: `C.teal+'1c'` — .11 · `C.teal+'55'` — .333
              background: alpha(C.teal, 0.11),
              border: '1px solid ' + alpha(C.teal, 0.333),
              borderRadius: T.r.ctl,
              padding: '2px 7px',
              flex: '0 0 auto',
            }}
          >
            from Calendar
          </span>
        </div>
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '6px' }}>
          Synced — edit the time in your calendar.
        </div>
      </div>
    ) : (
      <div>
        {sub('Time · optional')}
        <input
          type="time"
          value={n.vals.tod ? String(n.vals.tod) : ''}
          onChange={(e) => apply(setVal(graph, id, 'tod', e.target.value))}
          style={{ ...inp, width: '140px', colorScheme: 'dark' }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        marginBottom: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '13px',
        // v4: `linear-gradient(135deg,'+C.orange+'18,'+C.orange+'07)` — .094 / .027
        background: `linear-gradient(135deg,${alpha(C.orange, 0.094)},${alpha(C.orange, 0.027)})`,
        // v4: `C.orange+'55'` — .333
        border: '1px solid ' + alpha(C.orange, 0.333),
        borderRadius: T.r.card,
        padding: '14px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          fontSize: '10.5px',
          fontWeight: 800,
          letterSpacing: '.1em',
          textTransform: 'uppercase',
          color: C.orange,
        }}
      >
        <span
          style={{ width: '6px', height: '6px', borderRadius: '50%', background: C.orange }}
        />
        Recurrence
      </div>
      {pills}
      {countRow}
      {dayRow}
      {timeRow}
    </div>
  );
}
