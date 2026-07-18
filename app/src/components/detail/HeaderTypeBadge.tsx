import { useEffect, useRef, useState } from 'react';
import { alpha } from '@tokens';
import { Badge } from '../atoms/index.ts';
import { setType, typeOptions, TYPE_LABEL_FOR_LEVEL } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface HeaderTypeBadgeProps {
  ctx: DetailCtx;
  n: ModelNode;
}

/**
 * v4 `headerTypeBadge(n)` (~525) — the type badge that is also the type-conversion control.
 *
 * `typeOptions(n)` returning null (GOAL, STRATEGY) means the level cannot be converted at all,
 * and the badge renders as a plain, non-interactive label. Otherwise the badge grows a chevron
 * and opens a dropdown of the convertible types.
 *
 * ── the disabled branch is the leaf guard, shown before it fires ─────────────
 * `Task` and `Recurring` are blocked while the node has children, with a "has sub-items"
 * annotation. `setType` refuses the same conversion in the model layer and toasts
 * "Can't convert — has sub-items, move them first". Here the UI states the constraint instead
 * of letting the user hit it — so the button is `disabled` AND its handler early-returns,
 * both of which are v4's.
 *
 * ── OPEN STATE: local, not in the shared UI bag ──────────────────────────────
 * v4 keeps this in `st.headerTypeOpen` because everything in v4 is one component. It is
 * local state here: nothing outside this control reads it, and it dies with the pane, which
 * is exactly what v4's `closeDetail()` clear (306) achieves by hand.
 *
 * The outside-click dismissal is v4's `_away` handler (712), which ignores clicks inside any
 * element carrying `data-mkeep`. Same rule, scoped to this control's own subtree — the
 * `data-mkeep` attributes are kept so the markup still matches v4 and so a future global
 * handler finds what it expects.
 */
export function HeaderTypeBadge({ ctx, n }: HeaderTypeBadgeProps) {
  const { T, graph, idx, apply } = ctx;
  const C = T.c;
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement | null>(null);

  const opts = typeOptions(idx, n);

  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => {
      const t = e.target as Element | null;
      if (t && wrap.current && wrap.current.contains(t)) return;
      if (t && t.closest && t.closest('[data-mkeep]')) return;
      setOpen(false);
    };
    document.addEventListener('click', away);
    return () => document.removeEventListener('click', away);
  }, [open]);

  if (!opts) {
    return (
      <span style={{ flex: '0 0 auto' }}>
        <Badge T={T} level={n.level} />
      </span>
    );
  }

  const cur = TYPE_LABEL_FOR_LEVEL[n.level];

  return (
    <div ref={wrap} style={{ position: 'relative', flex: '0 0 auto' }}>
      <button
        onClick={() => setOpen(!open)}
        aria-label="change type"
        aria-expanded={open}
        data-mkeep="1"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '2px 0',
          fontFamily: 'inherit',
        }}
      >
        <Badge T={T} level={n.level} />
        <svg width={12} height={12} viewBox="0 0 24 24" fill="none" style={{ color: C.dim }}>
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {open ? (
        <div
          data-mkeep="1"
          style={{
            position: 'absolute',
            top: '26px',
            left: 0,
            zIndex: 41,
            background: C.roseBg,
            border: '1px solid ' + C.roseBorder,
            borderRadius: T.r.ctl,
            padding: '5px',
            minWidth: '150px',
            // v4 literal '0 14px 34px rgba(0,0,0,.55)'; the token module names the same
            // element's shadow per theme (gallery L203 / L285).
            boxShadow: T.effects.paneShadow,
            display: 'flex',
            flexDirection: 'column',
            gap: '1px',
          }}
        >
          {opts.map((t) => {
            const on = cur === t;
            const blocked = (t === 'Task' || t === 'Recurring') && n.children.length > 0;
            return (
              <button
                key={t}
                disabled={blocked}
                onClick={() => {
                  if (blocked) return;
                  if (!on) apply(setType(graph, n.id, t));
                  setOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  textAlign: 'left',
                  // v4: `C.purple+'22'` — .133
                  background: on ? alpha(C.purple, 0.133) : 'none',
                  border: 'none',
                  color: blocked ? C.dimmer : on ? C.purple : C.text,
                  fontSize: '13px',
                  fontWeight: 600,
                  padding: '9px 11px',
                  borderRadius: T.r.ctl,
                  cursor: blocked ? 'not-allowed' : 'pointer',
                  fontFamily: 'inherit',
                  whiteSpace: 'nowrap',
                  opacity: blocked ? 0.5 : 1,
                }}
              >
                {on ? (
                  <span style={{ color: C.purple, width: '12px', flex: '0 0 auto' }}>✓</span>
                ) : (
                  <span style={{ width: '12px', flex: '0 0 auto' }} />
                )}
                <span style={{ flex: 1 }}>{t}</span>
                {blocked ? (
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      fontStyle: 'italic',
                      color: C.dimmer,
                      flex: '0 0 auto',
                    }}
                  >
                    has sub-items
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
