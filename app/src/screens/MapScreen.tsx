import { useRef } from 'react';
import type { ReactNode } from 'react';
import { typeColor } from '../components/atoms/index.ts';
import { Row } from '../components/rows/index.ts';
import { NAV } from '../components/panels/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';
import { isInactive, node, pathTo, sideOf } from '../model/index.ts';
import type { GraphIndex, ModelNode } from '../model/index.ts';
import { StructurePanel } from './StructurePanel.tsx';

/** The filter inputs `subtreeVis` reads, gathered so the callers cannot disagree. */
export interface VisFilters {
  /** Already `.trim().toLowerCase()`d by the caller, as v4 does. */
  q: string;
  hideInactive: boolean;
  sideFilter: string;
}

/**
 * v4 `subtreeVis(n)` (~330), now complete:
 *
 *   sidePass = (st.sideFilter||'all')==='all' || sideOf(n)===st.sideFilter
 *   self     = (!q || title.includes(q)) && !(st.hideInactive && isInactive(n)) && sidePass
 *   return self || n.children.some(subtreeVis)
 *
 * The `||` at the end is the rule that matters: a node stays visible if IT passes **or any
 * descendant does**. Without it, hiding done tasks would also hide the project they live under
 * as soon as the project itself read as inactive, and whole live branches would vanish behind
 * a dead ancestor.
 *
 * Task 4 shipped this with only the `hideInactive` conjunct, because neither of the other two
 * had a control yet and `sideOf` was unported. Both are here now.
 */
export function subtreeVis(idx: GraphIndex, n: ModelNode, f: VisFilters): boolean {
  const sidePass = (f.sideFilter || 'all') === 'all' || sideOf(idx, n) === f.sideFilter;
  const self =
    (!f.q || n.title.toLowerCase().includes(f.q)) && !(f.hideInactive && isInactive(n)) && sidePass;
  return self || n.children.some((c) => subtreeVis(idx, c, f));
}

/**
 * The Map tab — v4 `treeBody()` (~630) inside `structurePanel`.
 *
 * ── ⚠ THIS IS A DRILL-IN, NOT A NESTED TREE ──────────────────────────────────
 * Nothing on this screen indents and nothing expands in place. Every row renders at
 * `depth:0`; tapping a container (or its chevron) sets `st.focus` to that node and the panel
 * REPLACES itself with that node's children, behind a breadcrumb that walks back out. v4's own
 * comment at line 634: *"Drill-in: show only the focused level + a breadcrumb. No inline
 * expand → nothing accumulates, nothing jumps."*
 *
 * Task 4 built an interim nested tree here because an earlier revision of the plan said
 * "expand/collapse", conflating this with the Routines tab's grouping headers
 * (`toggleCollapse` at v4:676, which is real and belongs there). That container is what this
 * replaces. `Row` itself was correct and is unchanged.
 *
 * Leaves (TASK / RECURRING) cannot be drilled into, so they tap through to the detail editor
 * and carry their chips under the title rather than beside it.
 *
 * ── search narrows to a flat list, deliberately ──────────────────────────────
 * With a filter typed, v4 abandons the drill-in entirely: no breadcrumb, no focus, just every
 * matching node in the whole tree at `depth:0`. v4's own comment calls this "intentional
 * narrowing" — while searching you want hits, not structure. Note the search branch applies
 * `hideInactive` but NOT the Side filter; that asymmetry is v4's and is ported as-is.
 *
 * ── the panel's entry direction is derived from DEPTH ────────────────────────
 * Going deeper enters from the right, coming back out from the left, and staying at the same
 * depth reuses the last direction. v4 keeps the previous depth on the instance
 * (`_prevTreeDepth` / `_treeDir`); a ref is the same scope here. It is computed during render
 * from the focus actually in state — the same rule `AppShell` uses for tab direction — so any
 * route that changes `focus` animates correctly, not only the click handler.
 */
export function MapScreen({ ctx }: { ctx: PanelCtx }) {
  const { T, graph, idx, ui, up } = ctx;
  const C = T.c;
  const q = ui.search.trim().toLowerCase();
  const f: VisFilters = { q, hideInactive: ui.hideInactive, sideFilter: ui.sideFilter };

  const nav = useRef<{ depth: number; dir: 'fwd' | 'back' }>({ depth: 0, dir: 'fwd' });

  // ── search: flat matches across the whole tree ────────────────────────────
  if (q) {
    const flat: ReactNode[] = [];
    const walkFlat = (nodes: ModelNode[]): void => {
      nodes.forEach((n) => {
        if (!(ui.hideInactive && isInactive(n)) && n.title.toLowerCase().includes(q)) {
          flat.push(<Row key={n.id} ctx={ctx} n={n} depth={0} onTap={() => up({ detail: n.id })} />);
        }
        walkFlat(n.children);
      });
    };
    walkFlat(graph.roots);
    return (
      <StructurePanel ctx={ctx}>
        {flat.length ? (
          flat
        ) : (
          <div
            style={{ color: C.dimmer, fontSize: '13px', textAlign: 'center', padding: '40px 20px' }}
          >
            Nothing matches
          </div>
        )}
      </StructurePanel>
    );
  }

  // ── drill-in ──────────────────────────────────────────────────────────────
  const focus = ui.focus ? (node(idx, ui.focus) ?? null) : null;
  const path = focus ? pathTo(idx, focus.id) : [];

  const crumbs: Array<{ id: string | null; title: string; level: string | null }> = [
    { id: null, title: 'root', level: null },
    ...path.map((x) => ({ id: x.id, title: x.title, level: x.level as string })),
  ];

  const items = focus
    ? focus.children.filter((c) => subtreeVis(idx, c, f))
    : graph.roots.filter((g) => subtreeVis(idx, g, f));

  const depth = path.length;
  const dir: 'fwd' | 'back' =
    depth > nav.current.depth ? 'fwd' : depth < nav.current.depth ? 'back' : nav.current.dir;
  nav.current = { depth, dir };

  const rows: ReactNode[] = [];
  if (!items.length) {
    rows.push(
      <div
        key="e"
        style={{ color: C.dimmer, fontSize: '13px', textAlign: 'center', padding: '30px 20px' }}
      >
        {focus ? 'Nothing here yet — add with +' : 'Nothing matches'}
      </div>,
    );
  }
  items.forEach((n) => {
    const canDrill = !['TASK', 'RECURRING'].includes(n.level);
    const drill = () => up({ focus: n.id, menuFor: null, chipEdit: null });
    rows.push(
      <Row
        key={n.id}
        ctx={ctx}
        n={n}
        depth={0}
        expandable={canDrill}
        open={false}
        chipsBelow={['TASK', 'RECURRING'].includes(n.level)}
        onExpand={canDrill ? drill : undefined}
        onTap={canDrill ? drill : () => up({ detail: n.id })}
      />,
    );
  });

  return (
    <StructurePanel ctx={ctx}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 8px 10px 12px',
          position: 'sticky',
          top: 0,
          zIndex: 5,
          background: T.chrome,
          backdropFilter: T.blur,
          WebkitBackdropFilter: T.blur,
          borderBottom: '1px solid ' + C.hair,
        }}
      >
        <div
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '4px',
          }}
        >
          {crumbs.map((c, i) => (
            <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {i > 0 ? <span style={{ color: C.dimmer, fontSize: '12px' }}>›</span> : null}
              <button
                onClick={() => up({ focus: c.id, menuFor: null, chipEdit: null })}
                style={{
                  background: 'none',
                  border: 'none',
                  // v4 reads `this.TYPE[c.level]`. That map is superseded by the gallery's
                  // `typeRamp` via `typeColor` — v4's coloured TASK green, colliding with the
                  // completion green.
                  color: c.level ? typeColor(T, c.level) : C.text,
                  fontWeight: i === crumbs.length - 1 ? 700 : 500,
                  fontSize: '13px',
                  cursor: 'pointer',
                  padding: 0,
                  fontFamily: 'inherit',
                }}
              >
                {c.title}
              </button>
            </span>
          ))}
        </div>
        {focus ? (
          <button
            onClick={() => up({ detail: focus.id, menuFor: null, chipEdit: null })}
            aria-label="edit"
            style={{
              flex: '0 0 auto',
              width: '32px',
              height: '32px',
              border: 'none',
              background: 'none',
              color: C.dim,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: T.r.field,
            }}
          >
            <svg width={16} height={16} viewBox="0 0 24 24" fill="none">
              <path d="M12 20h9" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
              <path
                d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        ) : null}
      </div>
      <div
        key={'panel-' + (focus ? focus.id : 'root')}
        style={{ animation: (dir === 'back' ? 'navback' : 'navfwd') + ' ' + NAV }}
      >
        {rows}
      </div>
    </StructurePanel>
  );
}
