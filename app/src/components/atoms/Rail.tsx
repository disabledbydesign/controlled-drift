import type { Theme } from '@tokens';
import { typeColor } from './typeColor';

export interface RailProps {
  T: Theme;
  /** Object level, e.g. 'PROJECT'. Drives the colour. */
  level: string;
}

/**
 * v4 `rail(level)` (~337) — the left rail / indent marker.
 *
 * `alignSelf:'stretch'` is load-bearing: the rail takes its height from the flex row it sits
 * in, so it spans whatever the row grows to. Colour source is the gallery legend, not v4's
 * `TYPE` map — see `typeColor.ts`.
 */
export function Rail({ T, level }: RailProps) {
  return (
    <div
      style={{
        width: '3px',
        alignSelf: 'stretch',
        borderRadius: '3px',
        background: typeColor(T, level),
        flex: '0 0 auto',
      }}
    />
  );
}
