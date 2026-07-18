import type { MouseEvent } from 'react';
import { chipBorder, chipFill } from '@tokens';
import type { Theme } from '@tokens';

/** v4's chip descriptor: `{unset, color, text}`. */
export interface ChipValue {
  text: string;
  /** Accent colour. Ignored when `unset`. */
  color?: string;
  /** No value set — renders as a transparent, italic, dimmed placeholder. */
  unset?: boolean;
}

export interface ChipProps {
  T: Theme;
  c: ChipValue;
  /** Present ⇒ the chip is a live control (pointer cursor, `data-mkeep`). */
  /**
   * ⚠ Takes the EVENT. v4:452/455 both call `e.stopPropagation()` before `onChip(c)`, because
   * in the `chipsBelow` branch the chip strip is a child of the row's own tap target — without
   * the stop, one tap fires both the chip handler and the row handler. This was typed
   * `() => void`, which made `stopPropagation` untypeable from any caller and silently dropped
   * v4's behaviour. Widened 2026-07-18 (review gate).
   */
  onClick?: ((e: MouseEvent) => void) | undefined;
}

/**
 * v4 `chipEl(c,onClick)` (~338) — the status / value chip.
 *
 * Three branches, transcribed:
 *   · unset     transparent fill, `c.border` stroke, `c.dimmer` italic label — in BOTH themes,
 *               with none of the hardware mono/uppercase treatment (v4 leaves `extra` empty
 *               on this branch, so the fallbacks apply)
 *   · hardware  gradient fill, top bevel highlight, mono, uppercase, .04em tracking, 10.5px
 *   · celestial flat fill, sans, 11.5px
 *
 * Fill and stroke come from `chipFill()` / `chipBorder()`. v4 wrote them as hex-suffix
 * concatenations — `linear-gradient(180deg,color+'24',color+'0d')` / `color+'24'` for the fill
 * and `color+'66'` for the stroke; the helpers are the tokenized form of exactly those, at the
 * gallery's round .14 / .05 / .4.
 *
 * `data-mkeep` is v4's marker for "a click inside this element must not close the open menu".
 */
export function Chip({ T, c, onClick }: ChipProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';

  const unset = !!c.unset;
  const color = c.color ?? C.dim;

  const bg = unset ? 'transparent' : chipFill(color, T.mode);
  // Unset stroke is `disabled` (#4f4a5e celestial), which is where that token actually belongs:
  // RECONCILIATION.md sources it from gallery L153, the unset "Parked" chip. v4 used the much
  // fainter generic `C.border` (rgba(255,255,255,0.09)) here. Corrected 2026-07-18 (review gate).
  const border = unset ? '1px solid ' + C.disabled : chipBorder(color);
  const fg = unset ? C.dimmer : color;

  // v4's `extra`, populated on the hardware branch only.
  const extraFont = !unset && hw ? T.mono : 'inherit';
  const extraTransform = !unset && hw ? ('uppercase' as const) : ('none' as const);
  // .03em, not v4's .04em — gallery 5c chips (L228-231) are `letter-spacing:.03em`.
  const extraTracking = !unset && hw ? '.03em' : 'normal';
  // v4 literal 'inset 0 1px 0 rgba(255,255,255,.08)' — the hardware `bevelHighlight` token.
  const extraShadow = !unset && hw ? T.effects.bevelHighlight : 'none';

  return (
    <button
      onClick={onClick}
      data-mkeep={onClick ? '1' : undefined}
      style={{
        fontSize: hw ? '10.5px' : '11.5px',
        fontWeight: unset ? 600 : hw ? 600 : 700,
        color: fg,
        background: bg,
        border,
        borderRadius: T.r.chip,
        padding: hw ? '3px 9px' : '4px 11px',
        whiteSpace: 'nowrap',
        fontStyle: unset ? 'italic' : 'normal',
        cursor: onClick ? 'pointer' : 'default',
        fontFamily: extraFont,
        lineHeight: 1.3,
        textTransform: extraTransform,
        letterSpacing: extraTracking,
        boxShadow: extraShadow,
      }}
    >
      {c.text}
    </button>
  );
}
