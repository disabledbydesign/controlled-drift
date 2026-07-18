import type { ReactNode } from 'react';
import { Badge } from '../atoms/index.ts';
import { addChild, move, node } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import { NAV, PANEL } from './types.ts';
import type { PanelCtx } from './types.ts';

interface PickItem {
  n: ModelNode;
  kids: PickItem[];
  selectable: boolean;
}

/**
 * v4 `pickerPage()` (~603) — the full-screen destination chooser.
 *
 * One component, two jobs, told apart by which state field is set:
 *   · `moveFor` holds an ID  → "Move under…", and picking calls `move()`.
 *   · `addParentFor` holds a TYPE → "Add <Type> under…", and picking calls `addChild()`.
 * Both null → renders nothing.
 *
 * ── ⚠ THE EXCLUSION SET IS LOAD-BEARING (v4:605) ────────────────────────────
 * When moving, the moved node's whole subtree is collected into `exclude` and skipped while
 * the destination list is built. You therefore cannot even SEE your own descendants as
 * destinations, which is what makes the "move a node into its own child" case unreachable from
 * the UI.
 *
 * `move()` in the model layer carries its own guard for the same case, but that guard is a
 * SILENT DEAD END: it returns the graph unchanged with `toast:null` and `ui:null`, so
 * `moveFor` never clears and this picker would sit open with no message and no effect. The
 * exclusion is what keeps that path unreachable — dropping it does not degrade to a nice
 * error, it degrades to a frozen picker. See the comment on `move()` in `model/mutations.ts`.
 *
 * ── who is offered vs. who is shown ─────────────────────────────────────────
 * Two different rules, and v4 keeps them apart. `build` decides what APPEARS: leaves
 * (TASK / RECURRING / STRATEGY) never appear, excluded ids never appear, and a node that does
 * not match the filter still appears if a descendant does — otherwise you could not navigate
 * down to a match. `predicate` decides what is CHOOSABLE: adding a Project can land anywhere,
 * adding a Task or Recurring needs a schedulable container, and a move needs a container or a
 * goal. Non-choosable rows render at 55% opacity and only expand.
 *
 * ── while filtering, everything is open ─────────────────────────────────────
 * `isOpen = q ? true : !!expanded[id]` — a text filter forces every branch open, so matches
 * deep in the tree are visible without hunting. Clearing the filter returns to the manual
 * expansion state.
 *
 * ── two shells over one body (v4:619 + v4:626) ──────────────────────────────
 * `wide` (the desktop path) makes this a CENTRED MODAL: a fixed 480px card, capped at 82% of
 * the height, over a `rgba(0,0,0,.55)` scrim that closes on click, entering with `panelin`.
 * The phone keeps v4's full-bleed slide-in with no scrim. Only the wrapper differs — the
 * header, the filter, the rows and every rule above are shared, as in v4.
 */
export function PickerPage({ ctx }: { ctx: PanelCtx }) {
  const { T, graph, idx, ui, up, apply, wide } = ctx;
  const C = T.c;
  if (!ui.moveFor && !ui.addParentFor) return null;

  const adding = !!ui.addParentFor;
  const selfId = ui.moveFor;

  // v4:605 — collect the moved node and every descendant. DO NOT REMOVE; see above.
  const exclude = new Set<string>();
  if (selfId) {
    const collect = (n: ModelNode | undefined): void => {
      if (!n) return;
      exclude.add(n.id);
      n.children.forEach(collect);
    };
    collect(node(idx, selfId));
  }

  const predicate: (n: ModelNode) => boolean = adding
    ? ui.addParentFor === 'Project'
      ? () => true
      : (n) => ['PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(n.level)
    : (n) => ['GOAL', 'PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(n.level);

  const q = ui.pickerFilter.trim().toLowerCase();

  const build = (nodes: ModelNode[]): PickItem[] => {
    const out: PickItem[] = [];
    for (const n of nodes) {
      if (['TASK', 'RECURRING', 'STRATEGY'].includes(n.level)) continue;
      if (exclude.has(n.id)) continue;
      const kids = build(n.children);
      if (q && !n.title.toLowerCase().includes(q) && !kids.length) continue;
      out.push({ n, kids, selectable: predicate(n) });
    }
    return out;
  };

  const tree = build(graph.roots);
  const onPick = (n: ModelNode) => {
    if (adding && ui.addParentFor) {
      apply(addChild(graph, n.id, ui.addParentFor as ModelNode['type']));
    } else if (selfId) {
      apply(move(graph, selfId, n.id));
    }
  };

  const expanded = ui.pickerExpanded || {};
  const rows: ReactNode[] = [];
  const render = (list: PickItem[], d: number): void => {
    for (const it of list) {
      const hasKids = it.kids.length > 0;
      const isOpen = q ? true : !!expanded[it.n.id];
      rows.push(
        <div
          key={it.n.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            paddingLeft: 12 + d * 15 + 'px',
            borderBottom: '1px solid ' + C.hair,
          }}
        >
          {hasKids ? (
            <button
              onClick={() => up({ pickerExpanded: { ...expanded, [it.n.id]: !isOpen } })}
              aria-label={isOpen ? 'collapse' : 'expand'}
              style={{
                width: '22px',
                height: '40px',
                flex: '0 0 auto',
                border: 'none',
                background: 'none',
                color: C.dim,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0,
              }}
            >
              <svg
                width={13}
                height={13}
                viewBox="0 0 24 24"
                fill="none"
                style={{
                  transform: isOpen ? 'rotate(90deg)' : 'none',
                  transition: 'transform .15s',
                }}
              >
                <path
                  d="M9 6l6 6-6 6"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          ) : (
            <span style={{ width: '22px', flex: '0 0 auto' }} />
          )}
          <div
            onClick={it.selectable ? () => onPick(it.n) : undefined}
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '11px 12px 11px 0',
              cursor: it.selectable ? 'pointer' : 'default',
              opacity: it.selectable ? 1 : 0.55,
            }}
          >
            <Badge T={T} level={it.n.level} small />
            <span style={{ fontSize: '13.5px', color: C.text, wordBreak: 'break-word', flex: 1 }}>
              {it.n.title}
            </span>
            {it.selectable ? (
              <span style={{ color: C.blue, fontSize: '12px', fontWeight: 600, flex: '0 0 auto' }}>
                choose
              </span>
            ) : null}
          </div>
        </div>,
      );
      if (isOpen) render(it.kids, d + 1);
    }
  };
  render(tree, 0);

  const close = () =>
    up({ moveFor: null, addParentFor: null, pickerFilter: '', pickerExpanded: {} });

  // v4:619 — the card itself. `wide` is a fixed-width centred sheet; the phone is full-bleed.
  const panel = (
    <div
      style={
        wide
          ? {
              position: 'relative',
              width: '480px',
              maxHeight: '82%',
              background: T.pane,
              backdropFilter: T.paneBlur,
              WebkitBackdropFilter: T.paneBlur,
              border: '1px solid ' + C.border,
              borderRadius: T.r.card,
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 24px 60px rgba(0,0,0,.55)',
              overflow: 'hidden',
              animation: 'panelin ' + PANEL,
            }
          : {
              position: 'absolute',
              inset: 0,
              background: T.pane,
              backdropFilter: T.paneBlur,
              WebkitBackdropFilter: T.paneBlur,
              display: 'flex',
              flexDirection: 'column',
              animation: 'slidein ' + NAV,
            }
      }
    >
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid ' + C.hair,
            flex: '0 0 auto',
          }}
        >
          <button
            onClick={close}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'none',
              border: 'none',
              color: C.blue,
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              padding: 0,
              marginBottom: '10px',
              fontFamily: 'inherit',
            }}
          >
            <svg width={18} height={18} viewBox="0 0 24 24" fill="none">
              <path
                d="M15 6l-6 6 6 6"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Cancel
          </button>
          <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '10px' }}>
            {adding ? 'Add ' + ui.addParentFor + ' under…' : 'Move under…'}
          </div>
          <input
            value={ui.pickerFilter}
            placeholder="Filter destinations…"
            onChange={(e) => up({ pickerFilter: e.target.value })}
            style={{
              width: '100%',
              background: C.panel,
              border: '1px solid ' + C.border,
              borderRadius: T.r.field,
              color: C.text,
              fontSize: '13px',
              padding: '9px 11px',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
          {/* v4:619 — a Project is the only type that can exist with no parent at all, so it
              is the only one offered an escape from the destination list. */}
          {adding && ui.addParentFor === 'Project' ? (
            <button
              onClick={() => apply(addChild(graph, null, 'Project'))}
              style={{
                marginTop: '9px',
                width: '100%',
                background: C.panel2,
                border: '1px dashed ' + C.border,
                borderRadius: T.r.field,
                color: C.blue,
                fontSize: '13px',
                fontWeight: 600,
                padding: '9px',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              + At top level (no goal yet)
            </button>
          ) : null}
        </div>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
          {rows.length ? (
            rows
          ) : (
            <div
              style={{
                color: C.dimmer,
                fontSize: '13px',
                textAlign: 'center',
                padding: '40px 20px',
              }}
            >
              No destinations
            </div>
          )}
      </div>
    </div>
  );

  // v4:626 — the wrapper. Both are `position:absolute; inset:0; zIndex:45`; only the desktop
  // one centres the card and lays a click-to-close scrim underneath it.
  return wide ? (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 45,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        onClick={close}
        style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,.55)' }}
      />
      {panel}
    </div>
  ) : (
    <div style={{ position: 'absolute', inset: 0, zIndex: 45 }}>{panel}</div>
  );
}
