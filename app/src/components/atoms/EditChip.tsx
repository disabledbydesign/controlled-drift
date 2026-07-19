import type { Theme } from '@tokens';

export interface EditChipProps {
  T: Theme;
  /** v4 dispatched `up({detail:id,_returnFrom:'today'})` here; the caller now owns that. */
  onClick: () => void;
  /**
   * The visible word. Defaults to v4's `edit`, which is what `CheckPage`'s atom gallery still
   * shows. `RowActions` passes `open editor` instead: on a plan row the word `edit` now belongs
   * to the timing trigger (June's ruling), and two controls saying it was the collision this
   * prop exists to end. The SHAPE is the point of reusing this component — the bordered box is
   * already this codebase's way of saying "through to the object editor", as against the
   * underlined text of the controls that write in place.
   */
  label?: string;
}

/**
 * v4 `editChip(id)` (~1043) — the inline edit affordance on a Today row.
 *
 * Transcribed as-is. Two details that look like slips but are v4's and are kept:
 *   · the radius is `r.card`, not `r.chip` — this is a soft rectangle, not a pill, even in
 *     celestial where every other chip is fully rounded
 *   · `fontFamily:'inherit'` — it does NOT take the hardware mono treatment that `Chip` does
 *
 * ── tap-target expansion (2026-07-18, TRIAL — revert if it misbehaves) ───────
 * The visible chip is unchanged. Because it carries a border, padding on the button would have
 * grown the *drawn* box, so the border/radius/padding moved to an inner span and the button
 * became a transparent hit area around it. Same pixels, larger target.
 *
 * Vertical padding is capped at 3px for the reason given in `RoundCheck`: `TaskRow`'s ~26px row
 * pitch means anything taller overlaps the neighbouring row.
 */
export function EditChip({ T, onClick, label = 'edit' }: EditChipProps) {
  const C = T.c;
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      aria-label="open editor"
      style={{
        flex: '0 0 auto',
        alignSelf: 'center',
        background: 'none',
        border: 'none',
        color: C.dimmer,
        fontSize: '10.5px',
        fontFamily: 'inherit',
        padding: '3px 8px',
        margin: '-3px -8px',
        cursor: 'pointer',
        display: 'flex',
      }}
    >
      <span
        style={{
          border: '1px solid ' + C.border,
          borderRadius: T.r.card,
          padding: '2px 9px',
        }}
      >
        {label}
      </span>
    </button>
  );
}
