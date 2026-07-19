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
import type { MoveTarget } from '../../api/planRow.ts';

/**
 * ⚠ `MoveTarget` IS NOT REDECLARED HERE (review finding B6). It was declared in three places —
 * `api/planRow.ts`, this file, and structurally inline in `today/types.ts` — and three copies of
 * one contract is three chances for an importer to take the wrong one. `api/planRow.ts` owns it,
 * because that is where the wire format is written; this file and `types.ts` both import it.
 */
export type { MoveTarget };

export interface MoveDestination {
  /** Stable across a re-render; used as the React key and nothing else. */
  key: string;
  /** June-facing, literal: "first in the list", "after Email Sam". */
  label: string;
  target: MoveTarget;
  /** Which band this destination sits in, as RENDERED. */
  bandIndex: number;
  /**
   * The RENDERED row index this destination sits immediately above, in its band — so the plan
   * itself can draw a "move here" target in the slot rather than describing it in a sentence.
   * This is the rendered index space, NOT `target.position`'s server one; the two differ by the
   * folded-in appointments and by the item's own removal, which is the whole subject of this file.
   */
  beforeIndex: number;
  /**
   * The id of the rendered row this slot sits immediately BELOW, or `null` for the slot at the
   * top of the band.
   *
   * ⚠ Both anchors are carried because the two list containers need different ones, and neither
   * is a substitute for the other. `Band` renders the plan's band verbatim, so `beforeIndex` is
   * exact there — including the break and appointment rows, which occupy slots but are never
   * destinations. `PriorityList` does NOT: it drops breaks and honours June's own local reorder
   * (`ui.priOrder`), so a numeric plan index does not address a row on that screen at all. It
   * places the slot under the named row instead, wherever that row currently sits.
   */
  afterId: string | null;
}

/**
 * Why a move is not on offer. One sentence used to cover all three, and one of the three made
 * that sentence untrue (review finding B5).
 *
 *   `not-found`   — the id is not in the plan at all. The honest words are "I could not find
 *                   this row", not "there is nowhere to put it".
 *   `appointment` — the row is a folded-in appointment. `planFromLive` renders appointments as
 *                   ordinary task rows, but the server keeps them in their own key and never
 *                   indexes them, so every destination offered for one can only 404 (B1).
 *   `nowhere`     — a real, movable row with genuinely no other position to take.
 */
export type MoveRefusal = 'not-found' | 'appointment' | 'nowhere';

export interface MoveOptions {
  destinations: MoveDestination[];
  /** `null` when the move IS on offer. */
  refusal: MoveRefusal | null;
}

interface Located {
  bandIndex: number;
  /** The item's own position in the SERVER's index space. */
  position: number;
  /** The item's own index in the RENDERED band, before any offset is taken off. */
  renderIndex: number;
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
        return { bandIndex: bi, position: j - offsetOf(plan, bi), renderIndex: j };
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
    const add = (
      position: number,
      label: string,
      key: string,
      beforeIndex: number,
      afterId: string | null,
    ) => {
      // The no-op. Only possible within the item's own block, and a 400 if sent.
      if (sameBlock && position === from.position) return;
      out.push({
        key,
        label,
        target: { block: targetBlock, position },
        bandIndex: bi,
        beforeIndex,
        afterId,
      });
    };

    // The first slot sits below any folded-in appointments, never above them: an appointment is
    // a fixed-time anchor and the server does not index it, so a slot above one is not a position.
    add(
      0,
      priority ? 'first in the list' : 'first in ' + (block.label || 'this block'),
      bi + ':first',
      offset,
      null,
    );

    block.items.forEach((it, j) => {
      // An appointment carries no index the server would accept; a break has no name to offer.
      // Both still occupy a slot, which is why `j` is not re-derived from a filtered list.
      if (j < offset) return;
      if (it.kind === 'break') return;
      if ('id' in it && it.id === itemId) return;
      const anchor = j - offset;
      // Its own block lifts the item out first, so a later anchor is the final index itself.
      const position = sameBlock && anchor > from.position ? anchor : anchor + 1;
      add(position, 'after ' + titleOf(it), bi + ':' + j, j + 1, 'id' in it ? (it.id ?? null) : null);
    });
  });

  return out;
}

/**
 * Is this row a folded-in appointment? Derived from GEOMETRY, not from a row-kind flag, because
 * `api/adapt.planFromLive` has already turned appointments into `kind:'task'` rows by the time
 * anything on this surface sees them — the only surviving trace is that they occupy the first
 * `plan.apptCount` rendered slots of band 0.
 */
function isAppointmentRow(plan: Plan, at: Located): boolean {
  return at.bandIndex === 0 && at.renderIndex < (plan.apptCount ?? 0);
}

/**
 * The move offer for one row — the destinations, or the reason there are none.
 *
 * Prefer this over `moveDestinations` at any call site that shows June something. An empty list
 * on its own cannot tell "there is nowhere to put this" from "I could not find this row" from
 * "this is an appointment and the server would refuse it", and the surface said the first of the
 * three for all of them.
 */
export function moveOptions(
  plan: Plan,
  itemId: string,
  titleOf: (item: PlanItem) => string,
): MoveOptions {
  const from = locate(plan, itemId);
  if (!from) return { destinations: [], refusal: 'not-found' };
  if (isAppointmentRow(plan, from)) return { destinations: [], refusal: 'appointment' };
  const destinations = moveDestinations(plan, itemId, titleOf);
  return { destinations, refusal: destinations.length ? null : 'nowhere' };
}
