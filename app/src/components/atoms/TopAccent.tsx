import type { Theme } from '@tokens';

export interface TopAccentProps {
  T: Theme;
}

/**
 * v4 `topAccent()` (~169) — the gradient bar across the top of a panel.
 *
 * v4 built the bar inline:
 *   hardware:  1px, 'linear-gradient(90deg,transparent,'+C.blue+'aa 20%,'+C.blue+'aa 80%,transparent)',
 *              boxShadow '0 0 6px '+C.blue+'66', opacity .7
 *   celestial: 2px, 'linear-gradient(90deg,'+C.rose+','+C.strategy+' 50%,'+C.teal+')',
 *              boxShadow '0 0 12px '+C.rose+'99', opacity .92
 *
 * All three properties are tokenized (`effects.topAccent`, `topAccentHeight`, `topAccentGlow`)
 * and tokens.ts records them as gallery corrections to exactly these v4 values — the gallery
 * gives hardware a 2px rose→sig bar with no glow, and celestial a bar starting from `sig`
 * rather than `rose`. The gallery is the authority on how it looks, so the tokens are used.
 *
 * v4's `opacity` is NOT reapplied: it was part of the same superseded inline recipe, and the
 * token values are the already-tuned rendered colours. Flagged in the port report.
 */
export function TopAccent({ T }: TopAccentProps) {
  return (
    <div
      style={{
        height: T.effects.topAccentHeight,
        flex: '0 0 auto',
        background: T.effects.topAccent,
        boxShadow: T.effects.topAccentGlow,
      }}
    />
  );
}
