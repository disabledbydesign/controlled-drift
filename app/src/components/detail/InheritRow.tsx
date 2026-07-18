import type { ReactNode } from 'react';
import { alpha } from '@tokens';
import { clearVal, effective, isOwnValue, setVal } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface InheritRowProps {
  ctx: DetailCtx;
  n: ModelNode;
  /** The value key, v4's `vk`. */
  vk: string;
  label: string;
  hint?: string | null;
  /** v4's `buildEditor` — the control to show when the node has its OWN value. */
  editor: ReactNode;
}

/**
 * v4 `inheritRow(n,vk,label,hint,buildEditor)` (~488).
 *
 * ── TWO STATES, not three (June, 2026-07-18) ────────────────────────────────
 * A field is either INHERITED from an ancestor, or SET HERE. That is the whole model, and the
 * `Inherit | Custom` segments already carry it.
 *
 * **An empty value on a SET field is a normal, valid shape — not a special case.** June:
 * "Selecting no options is a valid shape (if leaving the house isn't checked, it doesn't
 * involve leaving the house)." So `Custom` with nothing checked simply means none of the
 * options apply. It needs no explanation and gets none.
 *
 * ⚠ An earlier pass added a line reading "Set here as none — not inherited." under that case,
 * describing it as an honest third state. It was REMOVED: v4 has no such text (its inheritRow
 * renders exactly two branches — the dashed box, or the editor), and it editorialised an
 * ordinary state as if it were unusual.
 *
 * The underlying DATA model still has the distinction that backend spec §4 turns on, and the
 * segments are what express it:
 *   · key ABSENT   → inheriting. `Inherit` lit. Dashed box naming the ancestor, or
 *                    "Nothing to inherit from a parent yet".
 *   · key PRESENT  → set here. `Custom` lit, editor shown — whether the value is empty or not.
 *
 * `Inherit` calls `clearVal`, which DELETES the key. It must never write '' — that would set
 * the field here and silently stop the ancestor walk.
 */
export function InheritRow({ ctx, n, vk, label, hint, editor }: InheritRowProps) {
  const { T, graph, idx, apply } = ctx;
  const C = T.c;
  const id = n.id;

  const inheriting = !isOwnValue(n, vk);
  const eff = effective(idx, n, vk);

  // v4: `disp = v => (v===''||v==null) ? 'none set' : (''+v).replace(/-/g,' ')`
  const disp = (v: unknown): string =>
    v === '' || v === null || v === undefined ? 'none set' : String(v).replace(/-/g, ' ');

  const seg = (txt: string, on: boolean, onClick: () => void) => (
    <button
      key={txt}
      onClick={onClick}
      style={{
        fontSize: '11px',
        fontWeight: 600,
        padding: '4px 11px',
        borderRadius: T.r.ctl,
        cursor: 'pointer',
        fontFamily: 'inherit',
        border: '1px solid ' + (on ? C.blue : C.border),
        // v4: `C.blue+'22'` — 0x22/255 = .133
        background: on ? alpha(C.blue, 0.133) : C.panel,
        color: on ? C.blue : C.dim,
      }}
    >
      {txt}
    </button>
  );

  // v4's `n.vals[vk]` read for the Custom branch.
  const own = n.vals[vk];

  const body = inheriting ? (
    <div
      style={{
        fontSize: '12.5px',
        color: C.dim,
        fontStyle: 'italic',
        padding: '9px 11px',
        background: C.panel,
        border: '1px dashed ' + C.border,
        borderRadius: T.r.field,
      }}
    >
      {eff.from ? 'Inheriting from ' + eff.from + ' — ' + disp(eff.val) : 'Nothing to inherit from a parent yet'}
    </div>
  ) : (
    editor
  );

  return (
    <div style={{ marginBottom: '14px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          marginBottom: '7px',
        }}
      >
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
        <div style={{ display: 'flex', gap: '4px', flex: '0 0 auto' }}>
          {seg('Inherit', inheriting, () => apply(clearVal(graph, id, vk)))}
          {seg('Custom', !inheriting, () =>
            apply(setVal(graph, id, vk, (inheriting ? eff.val : own) || '')),
          )}
        </div>
      </div>
      {body}
      {hint ? (
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '6px' }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}
