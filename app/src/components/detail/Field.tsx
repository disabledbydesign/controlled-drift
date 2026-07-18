import type { CSSProperties, ReactNode } from 'react';
import { alpha } from '@tokens';
import { Switch } from '../atoms/index.ts';
import {
  hasSchedulableAncestor,
  INHERIT,
  setVal,
  toggleMulti,
} from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { Control } from '../../fixtures/index.ts';
import { InheritRow } from './InheritRow.tsx';
import type { DetailCtx } from './types.ts';

export interface FieldProps {
  ctx: DetailCtx;
  n: ModelNode;
  /** One control tuple out of `CTRL[level]`: `[kind, label, key, rel?, hint?]`. */
  spec: Control;
}

/**
 * v4's `field(spec)`, the closure inside `detail()` (~549-572).
 *
 * ── EVERYTHING HERE IS SCHEMA-GENERATED ──────────────────────────────────────
 * There is no hardcoded form. The control KIND, its LABEL, the value KEY it writes and the
 * option list it offers all come out of the tuple, and the options themselves come out of
 * `schema.OPTS[rel]`. A wrong schema produces an empty control, not a degraded one
 * (api_contract_v2 §3.1). The only literals below are geometry and colour.
 *
 * ── THE INHERITANCE GATE (v4:572, both conjuncts) ────────────────────────────
 *     if (this.INHERIT.has(vk) && this.hasSchedulableAncestor(n))
 *       return this.inheritRow(n, vk, label, hint, () => ctl);
 * Both halves are required. `INHERIT` is `{access, blockMin, affective}`; applying the
 * inheritance display to anything outside that set renders a false story with no signal.
 *
 * ── KINDS PORTED, AND THE THREE NOT PORTED ───────────────────────────────────
 * Ported: `select` `toggle` `date` `time` `number` `recur` `multi` — exactly the seven in the
 * `ControlKind` union, i.e. exactly the kinds the schema can currently express.
 *
 * NOT ported, deliberately:
 *   · `scale` (v4:554) and `slider` (v4:556) — both are the EXCITEMENT PICKER (their labels
 *     read "not excited" / "can't wait"). The field is cut and is gone from the live Project
 *     type; the handoff names it explicitly under "Do NOT port".
 *   · `seg` (v4:558) — a segmented single-select. Not the excitement picker, and not cut; it
 *     is simply unreachable, because no control tuple in the schema fixture has kind `'seg'`
 *     and `'seg'` is not a member of the `ControlKind` union. Reported rather than added:
 *     when `GET /api/schema` lands (Track B) and the union widens, this is where it goes.
 * An unrecognised kind renders nothing rather than throwing — v4's own behaviour, since its
 * if/else chain simply leaves `ctl` undefined.
 */
export function Field({ ctx, n, spec }: FieldProps) {
  const { T, graph, idx, schema, apply } = ctx;
  const C = T.c;
  const id = n.id;

  const kind = spec[0];
  const label = spec[1];
  const vk = spec[2];
  const ok = spec[3];
  const hint = spec[4];

  // v4: `const v = n.vals[vk] || ''`. `vals` is an open bag, so the coercion is explicit
  // here; falsy in, '' out — identical inputs collapse identically.
  const raw = n.vals[vk];
  const v = raw ? String(raw) : '';

  const base: CSSProperties = {
    fontSize: '13.5px',
    color: C.text,
    background: C.panel,
    border: '1px solid ' + C.border,
    borderRadius: T.r.field,
    padding: '9px 11px',
    fontFamily: 'inherit',
    outline: 'none',
    maxWidth: '100%',
  };

  const opts = (ok ? schema.OPTS[ok as keyof typeof schema.OPTS] : undefined) || [];

  let ctl: ReactNode = null;

  if (kind === 'select') {
    ctl = (
      <select
        value={v}
        onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
        style={{ ...base, width: '100%', appearance: 'none' }}
      >
        <option value="">—</option>
        {opts.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  } else if (kind === 'toggle') {
    const on = !!v;
    ctl = (
      <button
        onClick={() => apply(setVal(graph, id, vk, !on))}
        aria-pressed={on}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          flex: '0 0 auto',
          display: 'flex',
        }}
      >
        <Switch T={T} on={on} col={C.green} />
      </button>
    );
  } else if (kind === 'date') {
    ctl = (
      <input
        type="date"
        value={v}
        onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
        style={{ ...base, width: '100%', colorScheme: 'dark' }}
      />
    );
  } else if (kind === 'time') {
    ctl = (
      <input
        type="time"
        value={v}
        onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
        style={{ ...base, width: '140px', colorScheme: 'dark' }}
      />
    );
  } else if (kind === 'number') {
    ctl = (
      <input
        type="number"
        value={v}
        onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
        style={{ ...base, width: '110px' }}
      />
    );
  } else if (kind === 'recur') {
    // v4:559. NOTE this is NOT `recurrenceCard` — it is the generic inline recurrence editor
    // the schema-driven form would produce for a `recur` tuple. `detail()` filters 'Repeats'
    // out of the RECURRING control list (v4:548) and renders `recurrenceCard` instead, so on
    // RECURRING this branch does not run. It stays because the gate is a LABEL filter, not a
    // kind filter: any other level given a `recur` tuple would reach it.
    const uk = ok || 'unit';
    const uRaw = n.vals[uk];
    const u = uRaw ? String(uRaw) : '';
    const cnt = v;
    const units = (schema.OPTS[uk as keyof typeof schema.OPTS] || []) as string[];
    ctl = (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
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
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: C.orange,
              flex: '0 0 auto',
            }}
          />
          Recurrence
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {units.map((o) => {
            const on = u === o;
            return (
              <button
                key={o}
                onClick={() => apply(setVal(graph, id, uk, o))}
                style={{
                  fontSize: '12.5px',
                  fontWeight: 600,
                  padding: '8px 14px',
                  borderRadius: T.r.chip,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  border: '1px solid ' + (on ? C.orange : C.border),
                  // v4: `C.orange+'26'` — .149
                  background: on ? alpha(C.orange, 0.149) : C.box,
                  color: on ? C.orange : C.dim,
                  textTransform: 'capitalize',
                }}
              >
                {o.replace(/_/g, ' ')}
              </button>
            );
          })}
        </div>
        {u === 'as_needed' ? null : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13.5px', color: C.dim }}>every</span>
            <input
              type="number"
              min={1}
              value={cnt || '1'}
              onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
              style={{ ...base, width: '70px' }}
            />
            <span style={{ fontSize: '13.5px', color: C.dim }}>
              {(Number(cnt) || 1) > 1 ? u + 's' : u || '—'}
            </span>
          </div>
        )}
      </div>
    );
  } else if (kind === 'multi') {
    ctl = (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {opts.map((o) => {
          const on = v.includes(o);
          return (
            <button
              key={o}
              onClick={() => apply(toggleMulti(graph, id, vk, o))}
              style={{
                fontSize: '11.5px',
                fontWeight: 600,
                padding: '6px 10px',
                borderRadius: T.r.field,
                cursor: 'pointer',
                fontFamily: 'inherit',
                border: '1px solid ' + (on ? C.blue : C.border),
                // v4: `C.blue+'22'` — .133
                background: on ? alpha(C.blue, 0.133) : C.panel,
                color: on ? C.blue : C.dim,
                textAlign: 'left',
              }}
            >
              {o.replace(/-/g, ' ')}
            </button>
          );
        })}
      </div>
    );
  }

  // v4:571 — only a toggle sits on the same line as its label.
  const inline = kind === 'toggle';

  // ── the inheritance gate, v4:572 — BOTH conjuncts ──────────────────────────
  if (INHERIT.has(vk) && hasSchedulableAncestor(idx, n)) {
    return <InheritRow ctx={ctx} n={n} vk={vk} label={label} hint={hint} editor={ctl} />;
  }

  const lab = (
    <label
      style={{
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '.04em',
        textTransform: 'uppercase',
        color: C.dim,
      }}
    >
      {label}
    </label>
  );
  const hintEl = hint ? (
    <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '4px' }}>
      {hint}
    </div>
  ) : null;

  if (inline) {
    return (
      <div style={{ marginBottom: '14px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {lab}
          {ctl}
        </div>
        {hintEl}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        gap: '8px',
        marginBottom: '14px',
      }}
    >
      {lab}
      {ctl}
      {hintEl}
    </div>
  );
}
