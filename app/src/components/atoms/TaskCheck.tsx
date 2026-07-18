import { alpha } from '@tokens';
import type { Theme } from '@tokens';

export interface TaskCheckProps {
  T: Theme;
  done: boolean;
  /** Accent colour of the checked state. */
  col: string;
  /** Box edge in px. v4's default is 19; the geometry forks at 17. */
  size?: number;
}

/**
 * v4 `taskCheck(done,col,sz)` (~183).
 *
 * v4's own comment: "One checkbox atom for the whole app: round + soft glow (Celestial) vs
 * square + beveled (Hardware). Every checkable control routes through this."
 *
 * SHAPE FORKS, transcribed exactly:
 *   · radius   hardware → 3px at every size; celestial → 50% at every size
 *   · border   2px at size>=17, 1.5px below (both themes)
 *   · shadow   done+hw → glow + inset top highlight; done+cel → glow only;
 *              undone+hw → inset well; undone+cel → none
 *
 * The empty-box stroke is `c.dimmer` — v4's original, and gallery-correct.
 *
 * ⚠ CORRECTED 2026-07-18 (review gate). This briefly used `c.disabled`, on the strength of a
 * tokens.ts docstring claiming that token covered "empty checkbox". It does not:
 * RECONCILIATION.md sources `disabled` only from a text glyph (L60) and a chip border (L153).
 * The gallery's actual checkbox atoms are `border:2px solid #6f6480` (5a celestial = `dimmer`)
 * and `#5f6a86` (5c hardware = `dimmest`). The wrong token rendered this — the most-repeated
 * control in the app — at #4f4a5e on a #060512 ground, a real contrast loss.
 */
export function TaskCheck({ T, done, col, size }: TaskCheckProps) {
  const C = T.c;
  const s = size || 19;
  const hw = T.mode === 'hardware';
  // Hardware is 3px at every size. v4 used 4px at s>=17; the gallery's 19px hardware checkbox
  // (5c) is `border-radius:3px` — the same 4px→3px hardware correction the reconciliation
  // already applied to `r.chip` and `r.card`, just never carried to the checkbox.
  const rad = hw ? '3px' : '50%';
  const bw = s >= 17 ? '2px' : '1.5px';

  const sh = done
    ? hw
      ? // v4: '0 0 7px '+col+'99, inset 0 1px 0 rgba(255,255,255,.2)'  (0x99 = .6)
        `0 0 7px ${alpha(col, 0.6)}, inset 0 1px 0 rgba(255,255,255,.2)`
      : // v4: '0 0 9px '+col+'77'  (0x77 = .467)
        `0 0 9px ${alpha(col, 0.467)}`
    : hw
      ? 'inset 0 1px 2px rgba(0,0,0,.45)'
      : 'none';

  return (
    <span
      style={{
        width: s + 'px',
        height: s + 'px',
        borderRadius: rad,
        // Empty stroke: celestial `dimmer` #6f6480 (gallery 5a), hardware `dimmest` #5f6a86
        // (gallery 5c). In celestial the two tokens are the same value anyway.
        border: bw + ' solid ' + (done ? col : hw ? C.dimmest : C.dimmer),
        background: done ? col : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: sh,
        flex: '0 0 auto',
      }}
    >
      {done ? (
        <span
          style={{
            color: C.on,
            fontSize: Math.round(s * 0.6) + 'px',
            lineHeight: 1,
            fontWeight: 900,
          }}
        >
          ✓
        </span>
      ) : null}
    </span>
  );
}
