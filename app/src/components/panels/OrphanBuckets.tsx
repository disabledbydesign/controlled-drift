import type { ReactNode } from 'react';
import type { ModelNode } from '../../model/index.ts';
import type { PanelCtx } from './types.ts';

/**
 * The catch-all sections for objects that hang off nothing (Task 11).
 *
 * ⚠ NOT A PORT. v4 has no equivalent, because every node in its `seed()` has a parent
 * (`docs/api_contract_v2.md:668`). This carries across a capability of the surface being
 * retired — `scripts/review_surface.py:234-247`.
 *
 * ── why it is load-bearing, in one sentence ──────────────────────────────────
 * In a Goal → Project → Task tree an unparented object renders NOWHERE — not misplaced, absent —
 * and June's live space currently holds twelve of them (3 tasks, 9 recurring items, among them
 * Shower, Go on a walk, Therapy, Text friends). Without these sections the new surface would
 * lose all twelve on the day it replaces the old one.
 *
 * ── two rules, both from June ────────────────────────────────────────────────
 * 1. **A bucket renders only when it has something in it.** An empty bucket produces nothing at
 *    all — not a heading, not a "0". A standing empty section is ambient noise about a problem
 *    that does not exist right now.
 * 2. **No count line.** She declined the data-health readout (`api_contract_v2.md:1022`,
 *    declined 2026-07-17) on the grounds that the buckets appearing IS the signal, and a count
 *    restates it as a standing score. So there is no total anywhere here. The per-bucket number
 *    beside each heading is not that: it says how long THIS list is, the same affordance the
 *    Routines group headers already carry, and it disappears with the bucket.
 *
 * ── the labels are the server's ──────────────────────────────────────────────
 * `GET /api/tree` supplies `orphans[].label` (`scripts/api_tree.py:295-310`), kept verbatim from
 * the retiring surface so the wording June already reads does not change. This component renders
 * what arrives and authors nothing.
 *
 * ── `renderRow` is a parameter because the two Map layouts differ ────────────
 * The phone Map and the desktop Finder column build their rows differently (different tap
 * handlers, `dnd` on one and not the other). Passing the row renderer in means one definition of
 * WHICH buckets show and in what order, with each layout keeping its own row — rather than two
 * copies of the bucket logic that have to be kept in step.
 */
export function orphanSections(
  ctx: PanelCtx,
  renderRow: (n: ModelNode) => ReactNode,
): ReactNode[] {
  const { T, graph } = ctx;
  const C = T.c;
  const out: ReactNode[] = [];

  for (const b of graph.orphans ?? []) {
    if (!b.nodes.length) continue; // rule 1 — nothing at all, not an empty heading
    out.push(
      <div
        key={'oh-' + b.key}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          padding: '14px 12px 6px',
        }}
      >
        <span
          style={{
            flex: 1,
            minWidth: 0,
            fontSize: '11.5px',
            fontWeight: 700,
            // `amber`, not `red`: an unfiled object is something to file, not something broken.
            // The heading text already carries its own ⚠ / ⚙ from the endpoint.
            color: C.amber,
          }}
        >
          {b.label}
        </span>
        <span style={{ fontSize: '11px', color: C.dimmer, flex: '0 0 auto' }}>{b.nodes.length}</span>
      </div>,
    );
    b.nodes.forEach((n) => out.push(renderRow(n)));
  }

  if (out.length) {
    out.unshift(
      <div
        key="oh-note"
        style={{
          fontSize: '11.5px',
          color: C.dimmer,
          padding: '18px 12px 0',
          lineHeight: 1.5,
          borderTop: '1px solid ' + C.hair,
          marginTop: '10px',
        }}
      >
        {/* Deliberately does NOT mention dragging: drag-to-reparent exists only on the desktop
            layout, and this same line renders on the phone. "Open one and set where it belongs"
            is true on both. */}
        These are not filed under anything yet. Open one and set where it belongs.
      </div>,
    );
  }

  return out;
}
