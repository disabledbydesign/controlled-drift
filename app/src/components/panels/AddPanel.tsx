import type { ReactNode } from 'react';
import { Badge } from '../atoms/index.ts';
import { addChild, node } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import { PANEL } from './types.ts';
import type { PanelCtx } from './types.ts';

/** v4 `validAddParent(type,n)` (~373), verbatim. */
export function validAddParent(type: string, n: ModelNode | null): boolean {
  if (!n) return false;
  if (type === 'Project') return ['GOAL', 'PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(n.level);
  if (type === 'Task' || type === 'Recurring')
    return ['PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(n.level);
  return false;
}

/**
 * v4 `addContextParent()` (~372), phone branch only.
 *
 * v4's own comment: "Where a new child lands by default: whatever you're currently inside."
 * So: the node the Map is drilled into, else the node open in the detail editor — and only if
 * that node can HOLD children (TASK / RECURRING / STRATEGY are leaves and are rejected).
 *
 * v4's full expression is
 *   `this._wide ? (pick(st.deskPath.at(-1)) || pick(st.detail)) : (pick(st.focus) || pick(st.detail))`
 * The `_wide` branch is the desktop shell (Task 10) and is not ported here; this is the phone
 * branch only.
 */
export function addContextParent(ctx: PanelCtx): ModelNode | null {
  const pick = (id: string | null): ModelNode | null => {
    const d = id ? node(ctx.idx, id) : undefined;
    return d && !['TASK', 'RECURRING', 'STRATEGY'].includes(d.level) ? d : null;
  };
  return pick(ctx.ui.focus) || pick(ctx.ui.detail);
}

/**
 * v4 `addPanel()` (~374) — the `+` drop-down.
 *
 * Five buttons, and the branch behind each is the whole point:
 *   · Goal and Strategy need no parent → created immediately at top level.
 *   · Project / Task / Recurring need one. If the place you are standing can hold that type,
 *     it is created there with no further question. If it cannot, the button says "choose…"
 *     and hands off to `PickerPage` by setting `addParentFor` to the TYPE (not an id).
 *
 * The header line names where a child would land — badge plus title — or says "Adding at top
 * level" when nothing qualifies.
 *
 * ⚠ v4 passes `'style-hover':{background:C.panel2}` on the type buttons. That is v4's own
 * hyperscript extension, not a DOM or React property; React has no inline-style hover. Dropped
 * rather than reimplemented — reproducing it needs either a CSS class or a JS hover state, and
 * classes are ruled out by the port's inline-styles constraint. Flagged, not silently lost.
 *
 * Returns v4's two-element array: a full-bleed backdrop that closes on tap, then the menu.
 */
export function AddPanel({ ctx }: { ctx: PanelCtx }) {
  const { T, graph, up, apply } = ctx;
  const C = T.c;
  const context = addContextParent(ctx);

  const btn = (type: string, needsParent: boolean): ReactNode => {
    const auto = needsParent && validAddParent(type, context);
    return (
      <button
        key={type}
        onClick={() => {
          if (!needsParent) {
            apply(addChild(graph, null, type as ModelNode['type']));
            return;
          }
          if (auto && context) {
            apply(addChild(graph, context.id, type as ModelNode['type']));
            return;
          }
          up({ addOpen: false, addParentFor: type, pickerFilter: '' });
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '10px',
          width: '100%',
          textAlign: 'left',
          background: 'none',
          border: 'none',
          color: C.text,
          fontSize: '13.5px',
          fontWeight: 600,
          padding: '9px 12px',
          borderRadius: T.r.field,
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <span>{'+ ' + type}</span>
        {needsParent && !auto ? (
          <span style={{ fontSize: '10px', color: C.dimmer, fontWeight: 600 }}>choose…</span>
        ) : null}
      </button>
    );
  };

  return (
    <>
      <div
        key="bd"
        onClick={() => up({ addOpen: false })}
        style={{ position: 'absolute', inset: 0, zIndex: 34 }}
      />
      <div
        key="menu"
        style={{
          position: 'absolute',
          top: '100px',
          right: '12px',
          zIndex: 35,
          background: C.roseBg,
          border: '1px solid ' + C.roseBorder,
          borderRadius: T.r.card,
          padding: '6px',
          minWidth: '194px',
          boxShadow: '0 14px 34px rgba(0,0,0,.55)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          animation: 'panelin ' + PANEL,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.06em',
            textTransform: 'uppercase',
            color: C.dimmer,
            padding: '6px 10px 5px',
          }}
        >
          {context ? (
            <>
              <span style={{ color: C.dimmer }}>Into</span>
              <Badge T={T} level={context.level} small />
              <span
                style={{
                  color: C.dim,
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {context.title}
              </span>
            </>
          ) : (
            'Adding at top level'
          )}
        </div>
        {btn('Goal', false)}
        {btn('Project', true)}
        {btn('Task', true)}
        {btn('Recurring', true)}
        {btn('Strategy', false)}
      </div>
    </>
  );
}
