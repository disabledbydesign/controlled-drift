import type { PlanItem } from '../../fixtures/index.ts';
import { node } from '../../model/index.ts';
import { moveOptions } from './moveTargets.ts';
import type { MoveDestination } from './moveTargets.ts';
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

export function placementFor(ctx: TodayCtx): Placement {
  const movingId = ctx.ui.movePick;
  if (!movingId) return { movingId: null, slots: [] };

  const titleOf = (it: PlanItem): string => {
    if ('id' in it && it.id) {
      const n = node(ctx.idx, it.id);
      if (n?.title) return n.title;
    }
    return 'task' in it && it.task ? it.task : 'this row';
  };

  return { movingId, slots: moveOptions(ctx.plan, movingId, titleOf).destinations };
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
