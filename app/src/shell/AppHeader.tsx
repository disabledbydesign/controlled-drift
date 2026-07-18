import { alpha } from '@tokens';
import type { Theme } from '@tokens';
import { bevel } from '../components/atoms/index.ts';

export interface AppHeaderProps {
  T: Theme;
  /** v4 reads `this.plan.date` for the sub-line. */
  planDate: string;
  onSettings: boolean;
  onToggleSettings: () => void;
}

/**
 * v4 `appHeader()` (~940).
 *
 * The theme fork is structural, not a recolour: hardware renders the header as a floating
 * bevelled CARD (its own margin, border, panel fill, `bevel()`), celestial renders it as flush
 * translucent chrome with no border at all. Title size and letter-spacing fork too, and the
 * sub-line gains a `SYS · ` prefix in hardware.
 *
 * v4 wrote translucency as hex-alpha concatenation (`C.sig+'22'`, `C.sig+'66'`); those are the
 * `alpha()` calls below, with the v4 original in a comment — the porting rule already used in
 * `components/atoms/effects.ts`.
 */
export function AppHeader({ T, planDate, onSettings, onToggleSettings }: AppHeaderProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';

  const gear = (
    <button
      onClick={onToggleSettings}
      aria-label="settings"
      style={{
        flex: '0 0 auto',
        width: '32px',
        height: '32px',
        borderRadius: hw ? '5px' : '50%',
        background: onSettings
          ? alpha(C.sig, 0.133) // v4: C.sig+'22'
          : hw
            ? 'rgba(255,255,255,.05)'
            : 'rgba(255,255,255,.04)',
        border:
          '1px solid ' +
          (onSettings
            ? alpha(C.sig, 0.4) // v4: C.sig+'66'
            : hw
              ? 'rgba(255,255,255,.12)'
              : 'rgba(255,255,255,.09)'),
        boxShadow: hw ? 'inset 0 1px 0 rgba(255,255,255,.08)' : 'none',
        color: onSettings ? C.sig : C.dim,
        fontSize: '15px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      ⚙
    </button>
  );

  const inner = (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '100%',
      }}
    >
      <div>
        <div
          style={{
            fontSize: hw ? '16px' : '18px',
            fontWeight: 700,
            color: C.text,
            letterSpacing: hw ? '.01em' : '-.01em',
          }}
        >
          Controlled Drift
        </div>
        <div
          style={{
            fontFamily: T.mono,
            fontSize: '10px',
            color: C.dimmer,
            letterSpacing: '.07em',
            marginTop: '2px',
          }}
        >
          {(hw ? 'SYS · ' : '') + String(planDate ?? '').toUpperCase()}
        </div>
      </div>
      {gear}
    </div>
  );

  if (hw) {
    return (
      <div
        style={{
          margin: '8px 12px 10px',
          padding: '11px 14px',
          flex: '0 0 auto',
          border: '1px solid ' + C.border,
          borderRadius: T.r.card,
          background: C.panel,
          boxShadow: bevel(T),
          backdropFilter: T.blur,
          WebkitBackdropFilter: T.blur,
        }}
      >
        {inner}
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '13px 16px 11px',
        flex: '0 0 auto',
        background: T.chrome,
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
      }}
    >
      {inner}
    </div>
  );
}
