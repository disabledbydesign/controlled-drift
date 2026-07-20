import type { PlanItem } from '../../fixtures/index.ts';
import { node } from '../../model/index.ts';
import { moveOptions } from './moveTargets.ts';
import type { MoveDestination, MoveRefusal, MoveTarget } from './moveTargets.ts';
import type { TodayCtx } from './types.ts';

/**
 * PLACEMENT MODE, as the list containers see it.
 *
 * June: *"move makes me select where things go using text labels. It should be a visual
 * representation of where things go."* So the destinations are no longer a menu inside the row —
 * they are drawn in the plan, in the slots they would land in. This module is what the two list
 * containers (`Band` for a clock day, `PriorityList` for a fragmented one) ask in order to know
 * which slots to draw.
 *
 * Transcribed from the old surface's `renderBlockPlacement` / the priority branch of `renderPlan`
 * (`docs/overlay_daily.html:2797`, `:2454`): the plan re-renders with a landing target at every
 * legal spot and the moving row marked.
 *
 * ⚠ BILATERAL, and that is load-bearing. `plan_store.move_item` was generalised in commit
 * 3940fe7 precisely because June said she needed to move things EARLIER as well as later, so the
 * old surface's `_hasLaterSpot` limit is deliberately NOT reproduced. Slots appear above the
 * moving row as readily as below it, which is also how the direction stays visible without
 * naming it in words. The only part of the old guard that survives is "offer a slot only where a
 * destination genuinely exists" — that one is still right, and it is `moveOptions`' job.
 */
export interface Placement {
  /** The row being moved, or `null` when no placement is in flight. */
  movingId: string | null;
  /** Every legal landing slot, across every band. */
  slots: MoveDestination[];
}

/**
 * How a row NAMES itself in a destination label. Lifted out of `placementFor` so the neighbour
 * lookup below resolves titles the same way rather than growing a second resolver that could
 * disagree with the one the slots are labelled with.
 */
export function titleOfIn(ctx: TodayCtx): (it: PlanItem) => string {
  return (it: PlanItem): string => {
    if ('id' in it && it.id) {
      const n = node(ctx.idx, it.id);
      if (n?.title) return n.title;
    }
    return 'task' in it && it.task ? it.task : 'this row';
  };
}

export function placementFor(ctx: TodayCtx): Placement {
  const movingId = ctx.ui.movePick;
  if (!movingId) return { movingId: null, slots: [] };

  return { movingId, slots: moveOptions(ctx.plan, movingId, titleOfIn(ctx)).destinations };
}

/**
 * Why a one-step nudge has no destination. `MoveRefusal`'s three reasons, plus one this lookup
 * can hit that the destination list cannot: the neighbouring slot exists on screen but is not a
 * position the server would take.
 */
export type NudgeRefusal = MoveRefusal | 'no-slot';

/** Either where the row lands, or the reason it does not move. Never both, never neither. */
export type Nudge = { target: MoveTarget; refusal: null } | { target: null; refusal: NudgeRefusal };

/**
 * ── THE ▲/▼ CONTROLS ON A CLOCK-SHAPE DAY ────────────────────────────────────
 *
 * `POST /api/plan/priority-order` raises `LookupError` for a clock-shape plan — that plan orders
 * its rows under `blocks[]`, and there is no flat ranking for it to store. So on a timed day the
 * Priority view's arrows were posting to an endpoint that structurally could not accept them: the
 * server answered 400, nothing was said, and the ordering reverted on the next load
 * (live-verified 2026-07-20).
 *
 * `POST /api/task/move` is the endpoint a timed day already has for this. It relocates one row in
 * the cached plan in EITHER direction and re-flows the clock times from the existing durations,
 * which is exactly what nudging a row up or down on a timed day means. This function turns "swap
 * with the neighbour above/below" into the position that endpoint expects.
 *
 * ⚠ It does NOT do its own arithmetic. `moveTargets.moveDestinations` owns every index rule here
 * (the folded-in appointments, the item's own removal from its block) and this only PICKS the
 * destination anchored to the neighbouring row. A second copy of that arithmetic is the one thing
 * that must not exist.
 *
 * `anchorId` is the row the moved item should end up immediately BELOW, or `null` for the slot at
 * the top of `anchorBand`. `anchorBand` disambiguates that top slot, which every band has one of.
 */
export function neighbourSlot(
  ctx: TodayCtx,
  movingId: string,
  anchorId: string | null,
  anchorBand: number,
): Nudge {
  const offer = moveOptions(ctx.plan, movingId, titleOfIn(ctx));
  if (offer.refusal) return { target: null, refusal: offer.refusal };
  const bandFirst = () =>
    offer.destinations.find((d) => d.afterId === null && d.bandIndex === anchorBand);
  const afterAnchor =
    anchorId === null ? undefined : offer.destinations.find((d) => d.afterId === anchorId);
  /*
   * ⚠ AN APPOINTMENT ANCHOR HAS NO `after` SLOT, AND THAT IS NOT THE SAME AS HAVING NOWHERE TO GO.
   *
   * `addressedWorkItems` keeps appointment rows, so on a band ordered [Appointment, T1, T2] a
   * legal up-nudge of T2 anchors on the APPOINTMENT — and `moveDestinations` emits no `after`
   * destination for any row above `offset` (`moveTargets.ts:177`), because the server does not
   * index appointments. The lookup missed and she was told "There is no other place in today's
   * plan for that row", which was untrue: the band-first slot is deliberately positioned BELOW the
   * folded-in appointments (`moveTargets.ts:166`) and is exactly where that row should land.
   *
   * June's real plan has a 14:00 appointment, so this fired in ordinary use.
   *
   * ⚠ THE FALLBACK IS DIRECTIONAL. Band-first is only the right answer when she pushed the row
   * UPWARD — falling back to it on a downward nudge would send the row to the top of the band,
   * the opposite of what she asked for. So it applies only when the anchor currently sits ABOVE
   * the moving row. That test is a comparison of rendered positions and computes no server
   * positions of its own; `moveDestinations` remains the only place index arithmetic lives.
   */
  const dest = afterAnchor ?? (anchorAbove(ctx, movingId, anchorId) ? bandFirst() : undefined);
  // No destination at all means the server has no position there to give. Answering with a refusal
  // rather than a nearby guess is the point: a row that quietly lands somewhere other than where
  // she pushed it is the same broken promise as one that does not move at all.
  return dest ? { target: dest.target, refusal: null } : { target: null, refusal: 'no-slot' };
}

/**
 * Does `anchorId` render ABOVE `movingId` in the plan? `null` counts as above — it names the slot
 * at the top of a band, which is the upward direction by definition.
 *
 * Deliberately reads only the rendered order (band index, then index within the band) and returns
 * no position: the offset arithmetic that separates rendered order from the server's index space
 * belongs to `moveTargets` and must not be copied here.
 */
function anchorAbove(ctx: TodayCtx, movingId: string, anchorId: string | null): boolean {
  if (anchorId === null) return true;
  const at = (id: string): number => {
    let n = 0;
    for (const band of ctx.plan.blocks) {
      for (const it of band.items) {
        if ('id' in it && it.id === id) return n;
        n += 1;
      }
    }
    return -1;
  };
  const a = at(anchorId);
  const m = at(movingId);
  return a >= 0 && m >= 0 && a < m;
}

/** The slots belonging to one band, in the order they are rendered. */
export function slotsInBand(p: Placement, bandIndex: number): MoveDestination[] {
  return p.slots
    .filter((d) => d.bandIndex === bandIndex)
    .sort((a, b) => a.beforeIndex - b.beforeIndex);
}

/**
 * The outline on the row currently being moved — the old surface's `.placing-item`, translated
 * into this codebase's grammar. The old rule was `outline: 1px solid var(--gold)` with a fixed
 * 8px radius; here the colour is the theme's own `gold` and the radius is `T.r.card`, so no new
 * value is introduced and the hardware theme's harder corner is preserved.
 */
export function movingRowStyle(ctx: TodayCtx, isMoving: boolean) {
  if (!isMoving) return null;
  return {
    outline: '1px solid ' + ctx.T.c.gold,
    outlineOffset: '2px',
    borderRadius: ctx.T.r.card,
  } as const;
}

/**
 * ── THE DESKTOP DRAG (A3) ────────────────────────────────────────────────────
 * June: *"on the desktop, i should be able to click and drag — the move menu becomes higher
 * friction than needed in that context."* This does NOT reverse her no-drag rule, which was
 * about her PHONE, where drag does not work. Both paths exist and the 900px breakpoint chooses:
 * the phone taps a row and then taps a slot, the desktop drags a row onto the same slot.
 *
 * ⚠ DERIVED, not transcribed — the old surface has no drag path at all, so there was nothing to
 * port. What it is derived from is `components/rows/Row.tsx`, this codebase's one existing drag
 * (the Map tab's drag-to-reparent, v4's single `dnd:true` call site): a module-level id holder
 * rather than a state field, `dataTransfer.effectAllowed='move'`, the `setData` try/catch, and —
 * the part that matters most — a move that cannot legally happen REFUSES IN WORDS rather than
 * snapping silently back.
 *
 * Dragging enters the SAME placement mode tapping does. That is the point: one set of legal
 * destinations, one arithmetic, one set of slots, two ways in. A drag that could only go one
 * direction would be the same defect as a later-only menu, and it cannot be — the slots are
 * whatever `moveOptions` says, above and below alike.
 *
 * A module-level holder, exactly as `Row.tsx` explains: `dataTransfer` cannot be read during
 * `dragover` in every browser, and this value must be readable while the drag is in flight.
 */
export const planDrag: { id: string | null } = { id: null };
