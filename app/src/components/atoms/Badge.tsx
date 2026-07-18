import type { Theme } from '@tokens';
import { typeColor } from './typeColor';

export interface BadgeProps {
  T: Theme;
  /** Object level, e.g. 'PROJECT'. Drives both the abbreviation and the colour. */
  level: string;
  /** v4's `small` flag: 8.5px instead of 9.5px. */
  small?: boolean;
}

/** v4's abbreviation map, verbatim; every other level prints its own name. */
const TXT: Record<string, string> = {
  SUBPROJECT: 'SUB',
  STRATEGY: 'STRAT',
  WORKSTREAM: 'STREAM',
};

/**
 * v4 `badge(level,small)` (~336) — the type badge.
 *
 * Transcribed as-is except for the colour source: v4 read `this.TYPE[level]`, which the
 * gallery legend supersedes. See `typeColor.ts`.
 */
export function Badge({ T, level, small }: BadgeProps) {
  const txt = TXT[level] ?? level;
  return (
    <span
      style={{
        fontSize: small ? '8.5px' : '9.5px',
        fontWeight: 800,
        letterSpacing: '.05em',
        textTransform: 'uppercase',
        color: typeColor(T, level),
        flex: '0 0 auto',
        whiteSpace: 'nowrap',
      }}
    >
      {txt}
    </span>
  );
}
