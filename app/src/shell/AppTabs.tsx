import { alpha } from '@tokens';
import type { CSSProperties } from 'react';
import type { Theme } from '@tokens';
import { TAB_BAR } from './tabs.ts';
import type { AppTab } from './tabs.ts';

export interface AppTabsProps {
  T: Theme;
  current: AppTab;
  onSelect: (id: AppTab) => void;
}

/**
 * v4 `appTabs()` (~949).
 *
 * SHAPE fork, not a recolour — the two themes use different navigation idioms entirely:
 *   hardware  — a lit PILL: sig-tinted fill, sig border, mono uppercase with letter-spacing,
 *               an outer glow plus an inset top highlight, and a 5px/2px margin so the pills
 *               float inside the bar.
 *   celestial — an UNDERLINE: no fill, no border, a 2px sig bottom border pulled up by a
 *               -1px margin so it sits on the bar's own hairline, inherited sans font.
 *
 * The bar itself is the same in both: horizontal scroll, a hairline bottom border, and the
 * translucent chrome fill.
 */
export function AppTabs({ T, current, onSelect }: AppTabsProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';

  const styleFor = (on: boolean): CSSProperties =>
    hw
      ? {
          flex: '0 0 auto',
          background: on ? alpha(C.sig, 0.118) : 'none', // v4: C.sig+'1e'
          border: '1px solid ' + (on ? alpha(C.sig, 0.4) : 'transparent'), // v4: C.sig+'66'
          borderRadius: T.r.ctl,
          color: on ? C.sig : C.dimmer,
          fontSize: '11px',
          fontWeight: on ? 700 : 500,
          padding: '6px 10px',
          margin: '5px 2px',
          cursor: 'pointer',
          fontFamily: T.mono,
          textTransform: 'uppercase',
          letterSpacing: '.06em',
          whiteSpace: 'nowrap',
          boxShadow: on
            ? // v4: '0 0 10px '+C.sig+'33, inset 0 1px 0 rgba(255,255,255,.12)'
              `0 0 10px ${alpha(C.sig, 0.2)}, inset 0 1px 0 rgba(255,255,255,.12)`
            : 'none',
        }
      : {
          flex: '0 0 auto',
          background: 'none',
          border: 'none',
          borderBottom: '2px solid ' + (on ? C.sig : 'transparent'),
          color: on ? C.sig : C.dimmer,
          fontSize: '12.5px',
          fontWeight: on ? 700 : 500,
          padding: '6px 11px 8px',
          cursor: 'pointer',
          fontFamily: 'inherit',
          marginBottom: '-1px',
          whiteSpace: 'nowrap',
        };

  return (
    <div
      style={{
        display: 'flex',
        padding: '0 8px',
        borderBottom: '1px solid ' + C.border,
        flex: '0 0 auto',
        background: T.chrome,
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
        overflowX: 'auto',
      }}
    >
      {TAB_BAR.map(({ id, label }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          aria-current={current === id ? 'page' : undefined}
          style={styleFor(current === id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
