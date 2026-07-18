import { alpha } from '@tokens';
import type { Theme } from '@tokens';

/**
 * Non-component visual primitives ported from
 * `design/mockups/review-reorganize-mobile-v4.html`: `glow()` (~170), `bevel()` (~171),
 * `appBg()` (~172).
 *
 * PORTING RULE used throughout this directory
 * -------------------------------------------
 * v4 derived translucent colours by concatenating a hex alpha suffix onto a hex colour
 * (`col+'66'`). Those are now expressed with the token module's `alpha()` helper, with the
 * v4 original named in a comment.
 *
 * Where `tokens.ts` documents a named token as having been taken FROM this v4 site (or from
 * the gallery's rendering of this same element), the named token wins — the gallery is the
 * authority on how things look. Where there is no such documented link, v4's literal geometry
 * and alpha are kept, because substituting a similar-looking token from a different element
 * would be reinterpretation, not transcription.
 */

/**
 * v4 `glow(col)` — emphasis glow for a lit/active control.
 *
 * v4 hardware:  '0 0 8px '+col+'66, inset 0 1px 0 rgba(255,255,255,.12)'
 * v4 celestial: '0 0 0 3px '+col+'22, 0 0 12px '+col+'66'
 *
 * The inset highlight is `effects.bevelHighlightStrong`; tokens.ts names the celestial value
 * as "v4 glow() literal", i.e. this exact site, so the token is used for it.
 */
export function glow(T: Theme, col: string): string {
  const hw = T.mode === 'hardware';
  return hw
    ? // v4: '0 0 8px '+col+'66'  (0x66 = .4)
      `0 0 8px ${alpha(col, 0.4)}, ${T.effects.bevelHighlightStrong}`
    : // v4: '0 0 0 3px '+col+'22, 0 0 12px '+col+'66'  (0x22 = .133, 0x66 = .4)
      `0 0 0 3px ${alpha(col, 0.133)}, 0 0 12px ${alpha(col, 0.4)}`;
}

/**
 * v4 `bevel()` — raised-surface bevel. Celestial does not bevel at all; that is a SHAPE
 * difference between the themes, not a colour swap.
 *
 * v4 hardware: 'inset 0 1px 0 rgba(255,255,255,.08), inset 0 -1px 0 rgba(0,0,0,.35)'
 *
 * Both halves are named tokens (`bevelHighlight` / `bevelShadow`), mined from the gallery's
 * rendering of the same bevel; the gallery's shadow alpha is .32 where v4 wrote .35.
 */
export function bevel(T: Theme): string {
  return T.mode === 'hardware'
    ? `${T.effects.bevelHighlight}, ${T.effects.bevelShadow}`
    : 'none';
}

/**
 * v4 `appBg()` — the full app background composition.
 *
 * Layer order is v4's. The corner washes and the base colour come from the token module
 * (`effects.ambient`, `c.bg`), which mined them from the gallery — v4's own wash coordinates
 * and alphas differ slightly and the gallery wins.
 *
 * Celestial takes the runtime-generated starfield (`theme/starfield.ts`) as its `sky` layer,
 * matching the composition already accepted in App.tsx.
 *
 * Hardware keeps v4's two `repeating-linear-gradient` anodized hairlines verbatim. tokens.ts
 * carries a hardware `star` (a 26px instrument grid) built from plain `linear-gradient`s,
 * which tiles only if the caller also sets a per-layer `background-size`. v4's repeating form
 * is self-tiling and drops into a single background string, so it is the one transcribed here.
 */
export function appBg(T: Theme, sky?: string): string {
  const C = T.c;
  if (T.mode === 'hardware') {
    // instrument-panel surface: top sheen + faint anodized hairlines (no repeating motif)
    // + theme corner washes  [comment and first three layers verbatim from v4]
    return (
      'linear-gradient(180deg,rgba(255,255,255,.035),transparent 32%),' +
      'repeating-linear-gradient(0deg,rgba(255,255,255,.017) 0 1px,transparent 1px 29px),' +
      'repeating-linear-gradient(90deg,rgba(255,255,255,.013) 0 1px,transparent 1px 29px),' +
      `${T.effects.ambient},${C.bg}`
    );
  }
  return `${sky ? sky + ',' : ''}${T.effects.ambient},${C.bg}`;
}
