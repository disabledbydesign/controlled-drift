import type { ReactNode } from 'react';
import { Row } from '../rows/Row.tsx';
import type { ModelNode } from '../../model/index.ts';
import type { PanelCtx } from './types.ts';

/**
 * Search that spans Map + Routines + Strategies, saying which tab each hit lives in (Task 11).
 *
 * ⚠ NOT A PORT — genuinely absent from v4, and absent for a structural reason. The surface being
 * retired was ONE tree, so one filter box searched everything in it. v4 splits that tree across
 * three tabs and gives each tab a filter over its own list only, sharing a single `st.search`
 * string between them. The result is a box that looks global and behaves locally: type
 * "therapy" on Strategies and you are told there is nothing, while the recurring item by that
 * name sits one tab away. `docs/api_contract_v2.md:1007` lists this as the one real capability
 * gap between the two surfaces.
 *
 * ── what this adds, and what it deliberately leaves alone ────────────────────
 * Each tab keeps its own filtered list exactly as ported — nothing is removed or re-ordered.
 * Underneath it, this appends the matches that belong to the OTHER two tabs, grouped under a
 * heading naming where each one lives. So the answer is complete from wherever you typed, and
 * the tab you are on still behaves the way v4 designed it.
 *
 * Rendering nothing is the common case: no query, or no matches outside this tab, produces no
 * element at all — not an empty heading.
 *
 * ── which tab "owns" an object ───────────────────────────────────────────────
 * Not a new taxonomy; it is where each tab already looks. Routines lists every RECURRING node
 * (`RoutinesScreen` walks the whole graph for them), Strategies lists `graph.strategies`, and
 * the Map is everything else. So ownership is read off `level`, and a node cannot be in two
 * places.
 *
 * ── tapping a hit opens it where you are ─────────────────────────────────────
 * It does not switch tabs. Switching would fire `useSurface`'s tab-change effect, which clears
 * `detail` — so the tab would change and the editor would not open, which is worse than not
 * moving. The detail editor is reachable from every tab, so opening in place is both simpler and
 * the thing the user asked for; the heading is what answers "where does this actually live".
 */

/** The three lists a structure tab can be showing. */
export type StructureTab = 'map' | 'routines' | 'strategies';

const TAB_LABEL: Record<StructureTab, string> = {
  map: 'Map',
  routines: 'Routines',
  strategies: 'Strategies',
};

/** Which tab an object belongs to — see the header; read off `level`, not a new field. */
export function owningTab(n: ModelNode): StructureTab {
  if (n.level === 'RECURRING') return 'routines';
  if (n.level === 'STRATEGY') return 'strategies';
  return 'map';
}

/**
 * Every object in the graph that matches `q`, paired with the tab it lives in.
 *
 * Walks rooted nodes, orphan-bucket nodes and strategies — the orphan buckets are included
 * deliberately: an unfiled object is exactly the kind of thing you go looking for with the
 * search box, and leaving it out would reintroduce the vanishing this build just fixed.
 */
export function searchAll(ctx: PanelCtx, q: string): Array<{ n: ModelNode; tab: StructureTab }> {
  const hits: Array<{ n: ModelNode; tab: StructureTab }> = [];
  const walk = (nodes: ModelNode[], forced?: StructureTab): void => {
    nodes.forEach((n) => {
      if (n.title.toLowerCase().includes(q)) hits.push({ n, tab: forced ?? owningTab(n) });
      walk(n.children, forced);
    });
  };
  walk(ctx.graph.roots);
  // ⚠ Orphan-bucket nodes are attributed to MAP even when they are recurring items, and that is
  // the honest answer rather than a shortcut. The heading answers "where do I go to find this",
  // and the buckets render on the Map. `RoutinesScreen` groups recurring items under their
  // parent project, so an orphan — which has no parent — is not on that tab at all. Labelling
  // Shower as "In Routines" would send her to a tab that does not list it.
  (ctx.graph.orphans ?? []).forEach((b) => walk(b.nodes, 'map'));
  walk(ctx.graph.strategies);
  return hits;
}

/**
 * The "also matching elsewhere" block.
 *
 * ── why the caller passes IDS and not just its own tab name ──────────────────
 * The obvious signature is `here: StructureTab`, filtering out that tab's own hits. It is wrong,
 * and subtly: v4's Map search walks the WHOLE tree at `depth:0`, so recurring items nested under
 * projects are already in the Map's own flat list even though Routines is the tab that "owns"
 * them. Filtering by owning tab would have listed every one of them a second time under "In
 * Routines", directly beneath itself. The caller is the only thing that knows what it actually
 * rendered, so it says so.
 */
export function CrossTabMatches({ ctx, shownIds }: { ctx: PanelCtx; shownIds: ReadonlySet<string> }) {
  const { T, ui, up } = ctx;
  const C = T.c;
  const q = ui.search.trim().toLowerCase();
  if (!q) return null;

  const elsewhere = searchAll(ctx, q).filter((h) => !shownIds.has(h.n.id));
  if (!elsewhere.length) return null;

  // Grouped so the tab name is said once per group rather than repeated on every row.
  const order: StructureTab[] = ['map', 'routines', 'strategies'];
  const groups = order
    .map((t) => ({ tab: t, hits: elsewhere.filter((h) => h.tab === t) }))
    .filter((g) => g.hits.length);

  const body: ReactNode[] = [];
  groups.forEach((g) => {
    body.push(
      <div
        key={'cth-' + g.tab}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          padding: '14px 12px 6px',
        }}
      >
        <span style={{ flex: 1, minWidth: 0, fontSize: '11.5px', fontWeight: 700, color: C.dim }}>
          {'In ' + TAB_LABEL[g.tab]}
        </span>
        <span style={{ fontSize: '11px', color: C.dimmer, flex: '0 0 auto' }}>{g.hits.length}</span>
      </div>,
    );
    g.hits.forEach((h) =>
      body.push(
        <Row
          key={'ct-' + h.n.id}
          ctx={ctx}
          n={h.n}
          depth={0}
          onTap={() => up({ detail: h.n.id })}
          noMenu
        />,
      ),
    );
  });

  return (
    <div style={{ borderTop: '1px solid ' + C.hair, marginTop: '10px', paddingTop: '8px' }}>
      <div style={{ fontSize: '11.5px', color: C.dimmer, padding: '8px 12px 0', lineHeight: 1.5 }}>
        Also matching on other tabs
      </div>
      {body}
    </div>
  );
}
