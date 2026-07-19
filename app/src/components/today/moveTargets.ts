/**
 * Where one plan row can be moved to — the destination list behind the row's "move" control.
 *
 * ── WHY A LIST OF DESTINATIONS AND NOT A DRAG ────────────────────────────────
 * June raised this directly: drag does not work on her phone. The Map tab's move picker is the
 * established answer here (`components/panels/PickerPage.tsx`) — tap the thing, then tap where it
 * goes, with an explicit Cancel — and this is that grammar applied to the plan. What does NOT
 * carry over is the picker's CONTENT: Map reparents inside a hierarchy, so it lists nodes; a plan
 * move is positional, so this lists positions.
 *
 * ── THE TWO INDEX SPACES ─────────────────────────────────────────────────────
 * `/api/task/move`'s `position` is the FINAL index the item lands at, against the SERVER's list.
 * Two things separate that from what is on screen, and both are silent when wrong because the
 * wrong index is still a valid one:
 *
 *  1. APPOINTMENTS. The server holds them in their own top-level key and does not index them;
 *     `planFromLive` folds them into the front of `blocks[0]` so they render as the fixed-time
 *     anchors they are. `plan.apptCount` is the difference, and it applies to `blocks[0]` only.
 *  2. THE ITEM'S OWN REMOVAL. Within its own block the item is lifted out before being
 *     reinserted, so a later anchor at index `j` is the final index `j` — while in ANY OTHER
 *     block, landing after `j` is `j + 1`. This asymmetry is the old overlay's, verified against
 *     the live server (`docs/overlay_daily.html`, `renderBlockPlacement`), not a derivation.
 *
 * ── WHAT IS DELIBERATELY NOT OFFERED ─────────────────────────────────────────
 * A destination that would not change anything. `plan_store.move_item` answers "already there"
 * with a 400, and inviting a tap that can only produce a visible failure is worse than not
 * offering it. Breaks and appointments are never anchors — a break has no id to name and an
 * appointment has no index the server would take — though a break still OCCUPIES a position,
 * because the server's list contains it.
 *
 * Moving EARLIER is offered as readily as later: the endpoint is bidirectional (commit 3940fe7).
 * The old overlay's later-only limit was its own, and is not reproduced.
 */

import type { Plan, PlanItem } from '../../fixtures/index.ts';

/** Where a move lands. `block` is `null` on a fragmented day, which has no blocks. */
export interface MoveTarget {
  block: number | null;
  /** The FINAL index the item lands at, in the server's index space. */
  position: number;
}

export interface MoveDestination {
  /** Stable across a re-render; used as the React key and nothing else. */
  key: string;
  /** June-facing, literal: "first in the list", "after Email Sam". */
  label: string;
  target: MoveTarget;
}

interface Located {
  bandIndex: number;
  /** The item's own position in the SERVER's index space. */
  position: number;
}

/** Appointments are folded into the FIRST block only; every later block is unshifted. */
function offsetOf(plan: Plan, bandIndex: number): number {
  return bandIndex === 0 ? (plan.apptCount ?? 0) : 0;
}

function locate(plan: Plan, itemId: string): Located | null {
  for (let bi = 0; bi < plan.blocks.length; bi++) {
    const items = plan.blocks[bi]?.items ?? [];
    for (let j = 0; j < items.length; j++) {
      const it = items[j];
      if (it && 'id' in it && it.id === itemId) {
        return { bandIndex: bi, position: j - offsetOf(plan, bi) };
      }
    }
  }
  return null;
}

/**
 * Every position `itemId` can be moved to, in reading order.
 *
 * `titleOf` resolves a row's display name. It is injected rather than read from the graph here
 * so this stays a pure function of plan geometry — which is the part that has to be exactly
 * right, and the part worth testing on its own.
 *
 * Returns an empty list for an id that is not in the plan: there is nothing to move, and a
 * destination list for a row that does not exist would invite a tap that could only 404.
 */
export function moveDestinations(
  plan: Plan,
  itemId: string,
  titleOf: (item: PlanItem) => string,
): MoveDestination[] {
  const from = locate(plan, itemId);
  if (!from) return [];

  const priority = plan.shape === 'priority';
  const out: MoveDestination[] = [];

  plan.blocks.forEach((block, bi) => {
    const offset = offsetOf(plan, bi);
    const sameBlock = bi === from.bandIndex;
    const targetBlock = priority ? null : bi;
    const add = (position: number, label: string, key: string) => {
      // The no-op. Only possible within the item's own block, and a 400 if sent.
      if (sameBlock && position === from.position) return;
      out.push({ key, label, target: { block: targetBlock, position } });
    };

    add(0, priority ? 'first in the list' : 'first in ' + (block.label || 'this block'), bi + ':first');

    block.items.forEach((it, j) => {
      // An appointment carries no index the server would accept; a break has no name to offer.
      // Both still occupy a slot, which is why `j` is not re-derived from a filtered list.
      if (j < offset) return;
      if (it.kind === 'break') return;
      if ('id' in it && it.id === itemId) return;
      const anchor = j - offset;
      // Its own block lifts the item out first, so a later anchor is the final index itself.
      const position = sameBlock && anchor > from.position ? anchor : anchor + 1;
      add(position, 'after ' + titleOf(it), bi + ':' + j);
    });
  });

  return out;
}
