import type { ReactNode } from 'react';
import type { Theme } from '@tokens';
import { Row } from '../components/rows/index.ts';
import type { RowCtx } from '../components/rows/index.ts';
import { isInactive } from '../model/index.ts';
import type { Graph, GraphIndex, ModelNode, MutationResult } from '../model/index.ts';
import type { UiState } from '../shell/useAppState.ts';

export interface MapScreenProps {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  ui: UiState;
  up: (patch: Partial<UiState>) => void;
  apply: (result: MutationResult) => void;
}

/**
 * v4 `subtreeVis(n)` (~330), narrowed to the part Task 4 owns.
 *
 * The rule that matters: a node stays visible if IT passes the filter **or any descendant
 * does**. Without that, hiding a done task would also hide the project it lives under as soon
 * as the project itself read as inactive, and whole live branches would vanish behind a dead
 * ancestor.
 *
 * v4's full predicate also ANDs in the title search and the Side filter. Both are omitted
 * here, not forgotten: neither has a control yet (Task 6 brings `filterMenu` / `mapControls`),
 * and the Side half needs v4's `sideOf(n)` (~329), which walks ancestors for an inherited
 * `side` and is **not ported into `model/`**. Reported rather than added — `model/` is outside
 * this task's file scope.
 */
function subtreeVis(n: ModelNode, hideInactive: boolean): boolean {
  const self = !(hideInactive && isInactive(n));
  return self || n.children.some((c) => subtreeVis(c, hideInactive));
}

/**
 * The Map tab — the object tree.
 *
 * ── WHAT THIS IS AND IS NOT ──────────────────────────────────────────────────
 * This renders `Row` recursively with real indentation and expand/collapse. **v4's Map does
 * not navigate this way.** v4's `treeBody` (~630) is a DRILL-IN: every row is `depth:0`, the
 * chevron sets `st.focus` and the panel swaps to that node's children behind a breadcrumb —
 * so nothing ever nests and `depth` is never exercised on that path. `toggleCollapse` (~676)
 * is real v4 code, but it belongs to the Routines tab, where it collapses the grouping
 * headers, not the tree.
 *
 * Porting `treeBody` — breadcrumb, focus, drill animation, `mapControls` — is Task 6, which
 * names it explicitly. This screen is Task 4's wire-in: it puts `Row` in front of real fixture
 * data on the real page, and it is the one place the depth-indentation rule is actually
 * visible, because the drill-in path never indents anything. Task 6 replaces the body below
 * the controls; `Row` itself does not change.
 *
 * ── layout ───────────────────────────────────────────────────────────────────
 * Its own flex column with `overflow:hidden`, holding the controls ABOVE an inner scroller —
 * matching v4's `structurePanel` (959-965), which is why `AppShell` renders the structure tabs
 * outside its scrolling wrapper. Nested in a scroller instead, `flex:1` would be inert and the
 * controls would scroll away with the list.
 */
export function MapScreen({ T, graph, idx, ui, up, apply }: MapScreenProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';

  const ctx: RowCtx = { T, graph, idx, ui, up, apply };

  /** v4:676 — `toggleCollapse(id)`, verbatim: present = collapsed, delete to expand. */
  const toggleCollapse = (id: string) => {
    const c: Record<string, true> = { ...ui.collapsed };
    if (c[id]) delete c[id];
    else c[id] = true;
    up({ collapsed: c });
  };

  const render = (nodes: ModelNode[], depth: number): ReactNode[] =>
    nodes
      .filter((n) => subtreeVis(n, ui.hideInactive))
      .flatMap((n) => {
        const kids = n.children.filter((c) => subtreeVis(c, ui.hideInactive));
        const expandable = kids.length > 0;
        const open = expandable && !ui.collapsed[n.id];
        // v4's treeBody rule: TASK and RECURRING put their chips under the title, because
        // those two rows are the ones that carry a status the eye needs to land on.
        const chipsBelow = n.level === 'TASK' || n.level === 'RECURRING';
        return [
          <Row
            key={n.id}
            ctx={ctx}
            n={n}
            depth={depth}
            expandable={expandable}
            open={open}
            chipsBelow={chipsBelow}
            onExpand={expandable ? () => toggleCollapse(n.id) : undefined}
            onTap={
              expandable ? () => toggleCollapse(n.id) : () => up({ detail: n.id, menuFor: null })
            }
          />,
          ...(open ? render(kids, depth + 1) : []),
        ];
      });

  const rows = render(graph.roots, 0);

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Interim stand-in for v4's `mapControls` (~967) — Task 6 replaces this whole strip with
          the real search field, Side filter and add button. It exists now because Task 4 has to
          be DRIVEN: `hideInactive` is already in UI state and wired through the tree, and with
          no control there is no way to observe that on the running page. */}
      <div
        style={{
          flex: '0 0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 12px',
          borderBottom: '1px solid ' + C.hair,
          background: T.chrome,
        }}
      >
        <button
          onClick={() => up({ hideInactive: !ui.hideInactive })}
          style={{
            cursor: 'pointer',
            padding: '5px 12px',
            fontFamily: hw ? T.mono : T.font,
            fontSize: '11px',
            fontWeight: 600,
            textTransform: hw ? 'uppercase' : 'none',
            letterSpacing: hw ? '.08em' : 0,
            color: ui.hideInactive ? C.blue : C.dim,
            background: ui.hideInactive ? C.blue + '22' : 'none',
            border: '1px solid ' + (ui.hideInactive ? C.blue + '66' : C.border),
            borderRadius: T.r.chip,
          }}
        >
          Hide inactive
        </button>
        <span
          style={{ marginLeft: 'auto', fontFamily: T.mono, fontSize: '10px', color: C.dimmest }}
        >
          {rows.length} rows
        </span>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
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
            Nothing matches
          </div>
        )}
      </div>
    </div>
  );
}
