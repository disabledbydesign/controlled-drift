import type { Theme } from '@tokens';

export interface EditChipProps {
  T: Theme;
  /** v4 dispatched `up({detail:id,_returnFrom:'today'})` here; the caller now owns that. */
  onClick: () => void;
}

/**
 * v4 `editChip(id)` (~1043) — the inline edit affordance on a Today row.
 *
 * Transcribed as-is. Two details that look like slips but are v4's and are kept:
 *   · the radius is `r.card`, not `r.chip` — this is a soft rectangle, not a pill, even in
 *     celestial where every other chip is fully rounded
 *   · `fontFamily:'inherit'` — it does NOT take the hardware mono treatment that `Chip` does
 */
export function EditChip({ T, onClick }: EditChipProps) {
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
        border: '1px solid ' + C.border,
        borderRadius: T.r.card,
        color: C.dimmer,
        fontSize: '10.5px',
        fontFamily: 'inherit',
        padding: '2px 9px',
        cursor: 'pointer',
      }}
    >
      edit
    </button>
  );
}
