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
 * ── WHAT THE THREE STATES ARE (backend spec §4) ──────────────────────────────
 * The key's PRESENCE on the node, not its truthiness, is what carries meaning:
 *
 *   1. key ABSENT           → inherit from the nearest ancestor that has the key
 *   2. key PRESENT, empty   → an intentional "none set HERE". Not inheritance.
 *   3. key PRESENT, a value → the node's own value
 *
 * `isOwnValue(n,vk)` distinguishes 1 from 2-and-3 (`hasOwnProperty`). `effective(idx,n,vk)`
 * answers "what would I inherit" — it starts at the PARENT, never at `n`, and stops at the
 * first ancestor that HAS the key, so an ancestor whose value is an intentional empty returns
 * `{val:'', from:<that ancestor>}` — a different answer from "nothing inherited",
 * `{val:'', from:null}`. All four resulting renders are visually distinct:
 *
 *   absent + ancestor has a value  → dashed italic box, "Inheriting from Crafts — …"
 *   absent + ancestor set it empty → dashed italic box, "Inheriting from Crafts — none set"
 *   absent + no ancestor has it    → dashed italic box, "Nothing to inherit from a parent yet"
 *   present but empty              → the EDITOR, `Custom` segment lit, + "Set here as none"
 *   present with a value           → the EDITOR, `Custom` segment lit
 *
 * ── THE ONE ADDITION TO v4 ───────────────────────────────────────────────────
 * v4 distinguishes present-but-empty from inheriting only by which segment button is lit and
 * whether the editor or the dashed box is showing. That is real, but it is a difference the
 * eye has to reconstruct from two weak signals. The plan (Task 5) requires the two be
 * "distinguishable to the user", so the non-inheriting branch adds ONE line of text when the
 * node's own value is empty: `Set here as none — not inherited.` Nothing else is added, and
 * the styling matches v4's own `hint` line so it reads as part of the same control.
 *
 * ── WHERE THIS MAY BE USED ───────────────────────────────────────────────────
 * ⚠ Only for keys in `INHERIT` (`access`, `blockMin`, `affective`) AND only when
 * `hasSchedulableAncestor(n)`. v4:572 pairs the two conditions and `Field` reproduces that
 * gate. Rendering this for any other field shows an inheritance story that is not true, with
 * no visual signal that it is not true.
 *
 * ── the two segment buttons ──────────────────────────────────────────────────
 * `Inherit` → `clearVal(id,vk)`, which DELETES the key (state 1).
 * `Custom`  → `setVal(id,vk, (inheriting ? eff.val : n.vals[vk]) || '')` — v4's expression
 * verbatim. Pressing Custom while inheriting COPIES the inherited value down onto the node,
 * so the switch does not lose what was showing; pressing it with an own value is a no-op
 * write. `|| ''` is what makes "Custom with nothing inherited" land in state 2.
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

  // v4's `n.vals[vk]` read for the Custom branch, and for the added empty-note below.
  const own = n.vals[vk];
  const ownIsEmpty = !inheriting && (own === '' || own === null || own === undefined);

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
      {/* THE ADDITION described in the header comment — the honest third state. */}
      {ownIsEmpty ? (
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '6px' }}>
          Set here as none — not inherited.
        </div>
      ) : null}
      {hint ? (
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '6px' }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}
