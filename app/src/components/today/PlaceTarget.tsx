import { chipBorder, chipFill } from '@tokens';
import type { DragEvent } from 'react';
import type { MoveDestination } from './moveTargets.ts';
import type { TodayCtx } from './types.ts';

export interface PlaceTargetProps {
  ctx: TodayCtx;
  dest: MoveDestination;
  onPick: (dest: MoveDestination) => void;
  /** True while a desktop drag is in flight — the slot is a drop zone, not just a tap target. */
  dropping?: boolean;
}

/**
 * ONE LANDING SLOT, DRAWN IN THE PLAN ITSELF.
 *
 * ── WHAT THIS IS RECOVERING ──────────────────────────────────────────────────
 * June: *"move makes me select where things go using text labels. It should be a visual
 * representation of where things go."* The old overlay already worked that way and the rebuild
 * lost it: `startPlacing(id, bandIndex)` put the plan into a placement mode where every valid
 * destination became a tap target *between the rows*, the moving row was outlined, and every
 * other edit affordance collapsed (`docs/overlay_daily.html:2062-2129`, `_placeTargetHtml` :2077,
 * `renderBlockPlacement` :2797). That MECHANISM is transcribed. Its APPEARANCE is not.
 *
 * ── TRANSCRIBED vs DERIVED, stated plainly ───────────────────────────────────
 * TRANSCRIBED from the old surface:
 *   · the interaction — tap the row, the plan fills with slots, tap a slot
 *   · the words "move here" (`_placeTargetHtml`)
 *   · the full-width, centred, between-the-rows placement of the slot
 *   · the outline on the row being moved (`.placing-item`)
 *
 * DERIVED, because the old CSS has no v4 equivalent and June asked for the v4 grammar rather
 * than the old appearance:
 *   · fill and stroke come from `chipFill(C.gold, mode)` / `chipBorder(C.gold)` — the same two
 *     helpers `components/atoms/Chip.tsx` uses, at the same alphas. The old `.place-target` used
 *     `var(--gold-dim)` + a flat `1px solid var(--gold)`, which have no token here.
 *   · the DASHED stroke is kept from the old rule and is the one thing carrying "this is an
 *     empty slot, not a thing" — a shape signal, so it survives both themes intact.
 *   · radius is `T.r.chip`, which is where the celestial/hardware soft-vs-hard fork already
 *     lives; no new radius value is introduced.
 *   · the hardware branch takes `Chip`'s own fork — mono, uppercase, .03em tracking and the
 *     `bevelHighlight` inset — rather than a colour swap. Themes fork on SHAPE here as they do
 *     everywhere else.
 * No new colour and no new radius were added for this.
 *
 * ── WHY THE LABEL DOES NOT SAY "EARLIER" OR "LATER" ──────────────────────────
 * Movement is bilateral and must be visibly so, and it is: the slots appear both ABOVE and BELOW
 * the row being moved, so the direction is the slot's own position in her plan. That is the
 * "visual representation of where things go" she asked for. Naming the direction in words as
 * well would put the answer back into text, which is the thing being removed. The destination's
 * own sentence ("first in the list", "after Email Sam") is carried in `aria-label`, so nothing
 * is lost to a screen reader.
 */
export function PlaceTarget({ ctx, dest, onPick, dropping = false }: PlaceTargetProps) {
  const C = ctx.T.c;
  const hw = ctx.T.mode === 'hardware';

  const drop = (e: DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    onPick(dest);
  };

  return (
    <button
      type="button"
      // Read as one sentence: what tapping it does, then where it lands.
      aria-label={'move here: ' + dest.label}
      data-place-target={dest.key}
      onClick={(e) => {
        e.stopPropagation();
        onPick(dest);
      }}
      {...(dropping
        ? {
            onDragOver: (e: DragEvent<HTMLButtonElement>) => {
              // Accepting the dragover is what makes the slot a legal drop; without it the
              // browser cancels the drag and the row snaps back with nothing said.
              e.preventDefault();
              e.dataTransfer.dropEffect = 'move';
            },
            onDrop: drop,
          }
        : null)}
      style={{
        display: 'block',
        width: '100%',
        // 9px vertical on an 11.5px line clears the 38px tap target her phone needs, and the
        // 4px margins keep the slot legible as a gap between rows rather than a row itself.
        padding: '9px 0',
        margin: '4px 0',
        textAlign: 'center',
        background: chipFill(C.gold, ctx.T.mode),
        // Dashed: an empty slot, not a thing. The one rule kept from the old stylesheet.
        border: chipBorder(C.gold).replace('solid', 'dashed'),
        borderRadius: ctx.T.r.chip,
        color: C.gold,
        cursor: 'pointer',
        fontFamily: hw ? ctx.T.mono : 'inherit',
        fontSize: hw ? '10.5px' : '11.5px',
        fontWeight: 600,
        letterSpacing: hw ? '.03em' : 'normal',
        textTransform: hw ? 'uppercase' : 'none',
        boxShadow: hw ? ctx.T.effects.bevelHighlight : 'none',
      }}
    >
      move here
    </button>
  );
}
