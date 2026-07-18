import type { Theme } from '@tokens';
import type { Period } from '../../fixtures/index.ts';
import { formFromPeriod } from '../../model/index.ts';
import { fmtDate } from './fmtDate.ts';
import type { FocusCtx } from './types.ts';

/**
 * v4 `focusPanel()` (814) — the focus-period LIST, rendered inside the Today slot's
 * expanded body (v4:1021 `this.focusPanel()`).
 *
 * Two sections, "Current focus period" (`when==='now'`) and "coming up"
 * (`when==='upcoming'`), each falling back to a plain line when empty, then a dashed
 * "+ Add a period" button that opens the author flow.
 *
 * ── SHAPE FORKS ─────────────────────────────────────────────────────────────
 * v4 makes NO `this.HW` / `isHW()` branch anywhere in 813-926 — verified by grep over that
 * range. The whole focus surface forks on shape only through the token bundle: `T.r.ctl`
 * (999px pill vs. 4px), `T.r.card` (16px vs. 5px), `T.r.field` (13px vs. 3px) and the two
 * themes' colour slots. Every radius below therefore reads from `T.r`, never a literal.
 */
function PeriodCard({
  T,
  p,
  badge,
  onEdit,
}: {
  T: Theme;
  p: Period;
  badge: string;
  onEdit: () => void;
}) {
  const C = T.c;
  const hasFront = !!(p.front && p.front.length);
  const hasPaused = !!(p.paused && p.paused.length);

  return (
    <div
      style={{
        border: '1px solid ' + C.roseBorder,
        borderRadius: T.r.ctl,
        padding: '12px 13px',
        background: C.roseBg,
        marginBottom: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '7px' }}>
        <span
          style={{
            fontSize: '10px',
            color: C.roseDim,
            textTransform: 'uppercase',
            letterSpacing: '.06em',
            border: '1px solid ' + C.roseBorder,
            borderRadius: '4px',
            padding: '1px 6px',
            flex: '0 0 auto',
          }}
        >
          {badge}
        </span>
        <span style={{ flex: 1, fontSize: '11px', color: C.rose }}>
          {fmtDate(p.start) + ' – ' + fmtDate(p.end)}
        </span>
        <button
          onClick={onEdit}
          style={{
            background: 'none',
            border: '1px solid ' + C.roseBorder,
            borderRadius: T.r.ctl,
            color: C.roseDim,
            fontSize: '11px',
            fontFamily: 'inherit',
            padding: '3px 10px',
            cursor: 'pointer',
          }}
        >
          Edit
        </button>
      </div>

      <div
        style={{
          fontSize: '13px',
          fontWeight: 600,
          color: C.rose,
          marginBottom: '6px',
          lineHeight: 1.35,
        }}
      >
        {p.name}
      </div>

      {/* Intent, verbatim. Spec §14/§17: it is June's own words and is never reworded —
          there is no transform on this value anywhere in the read or the write path. */}
      <div
        style={{
          fontSize: '12px',
          color: C.rose,
          opacity: 0.85,
          lineHeight: 1.5,
          marginBottom: hasFront ? '8px' : 0,
        }}
      >
        {p.intent}
      </div>

      {hasFront ? (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
            alignItems: 'center',
            marginBottom: '8px',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              color: C.roseDim,
              textTransform: 'uppercase',
              letterSpacing: '.06em',
            }}
          >
            front
          </span>
          {p.front.map((f, i) => (
            <span
              key={i}
              style={{
                fontSize: '11px',
                color: C.text,
                background: C.roseDim,
                border: '1px solid ' + C.roseBorder,
                borderRadius: T.r.card,
                padding: '3px 10px',
              }}
            >
              {f}
            </span>
          ))}
        </div>
      ) : null}

      {hasPaused ? (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
            alignItems: 'center',
            marginBottom: p.note ? '8px' : 0,
          }}
        >
          <span
            style={{
              fontSize: '10px',
              color: C.dimmer,
              textTransform: 'uppercase',
              letterSpacing: '.06em',
            }}
          >
            paused
          </span>
          {p.paused.map((f, i) => (
            <span
              key={'pz' + i}
              style={{
                fontSize: '11px',
                color: C.dimmer,
                border: '1px solid ' + C.border,
                borderRadius: T.r.card,
                padding: '3px 10px',
                textDecoration: 'line-through',
              }}
            >
              {f}
            </span>
          ))}
        </div>
      ) : null}

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          rowGap: '4px',
          alignItems: 'center',
          marginBottom: p.note || hasPaused ? '8px' : 0,
        }}
      >
        <span
          style={{
            fontSize: '10px',
            color: C.roseDim,
            background: C.roseBg,
            border: '1px solid ' + C.roseBorder,
            borderRadius: T.r.ctl,
            padding: '2px 8px',
          }}
        >
          {'plan: ' + (p.output || 'Auto')}
        </span>
        {p.availStart && p.availEnd ? (
          <span style={{ fontSize: '10px', color: C.roseDim }}>
            {'free ' + fmtDate(p.availStart) + '–' + fmtDate(p.availEnd)}
          </span>
        ) : null}
        {p.workdayStart || p.workdayEnd ? (
          <span style={{ fontSize: '10px', color: C.roseDim }}>
            {'day ' + (p.workdayStart || '—') + '–' + (p.workdayEnd || '—')}
          </span>
        ) : null}
      </div>

      {p.note ? (
        <div style={{ fontSize: '11px', color: C.roseDim, lineHeight: 1.4 }}>{p.note}</div>
      ) : null}
    </div>
  );
}

export interface FocusPanelProps {
  ctx: FocusCtx;
}

export function FocusPanel({ ctx }: FocusPanelProps) {
  const { T, periods, openEditor } = ctx;
  const C = T.c;
  const now = periods.filter((p) => p.when === 'now');
  const up = periods.filter((p) => p.when === 'upcoming');

  const sectionLabel = {
    fontSize: '10px',
    color: C.dimmer,
    textTransform: 'uppercase' as const,
    letterSpacing: '.08em',
  };
  const emptyLine = { fontSize: '12px', color: C.dimmer, marginBottom: '12px' };

  return (
    <div style={{ padding: '8px 2px 2px' }}>
      <div style={{ ...sectionLabel, marginBottom: '9px' }}>Current focus period</div>
      {now.length ? (
        now.map((p) => (
          <PeriodCard
            key={p.id}
            T={T}
            p={p}
            badge="Now"
            // v4:816 — Edit opens the detail route with a form copied off the period.
            onEdit={() => openEditor('edit', p.id, formFromPeriod(p))}
          />
        ))
      ) : (
        <div style={emptyLine}>No focus period set for today.</div>
      )}

      <div style={{ ...sectionLabel, margin: '14px 0 9px' }}>coming up</div>
      {up.length ? (
        up.map((p) => (
          <PeriodCard
            key={p.id}
            T={T}
            p={p}
            badge="Next"
            onEdit={() => openEditor('edit', p.id, formFromPeriod(p))}
          />
        ))
      ) : (
        <div style={emptyLine}>Nothing scheduled yet.</div>
      )}

      {/* v4:836 — the author flow opens with NO form (`focusReflect:null`), which is what
          `FocusEditor` branches on to show the "say it in your own words" screen. */}
      <button
        onClick={() => openEditor('author', null, null)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          width: '100%',
          background: 'none',
          border: '1px dashed ' + C.roseBorder,
          borderRadius: T.r.field,
          color: C.rose,
          fontSize: '12px',
          fontFamily: 'inherit',
          padding: '11px 12px',
          cursor: 'pointer',
          marginTop: '4px',
        }}
      >
        + Add a period
      </button>
    </div>
  );
}
