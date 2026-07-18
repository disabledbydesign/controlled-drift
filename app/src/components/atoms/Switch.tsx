import { alpha } from '@tokens';
import type { Theme } from '@tokens';

export interface SwitchProps {
  T: Theme;
  on: boolean;
  /** Accent colour of the "on" state. Defaults to the theme signal colour, as in v4. */
  col?: string;
}

/**
 * v4 `switchEl(on,col)` (~188).
 *
 * v4's own comment: "One switch atom for the whole app: rounded soft-glow pill (Celestial) vs
 * square beveled LED (Hardware). Every on/off toggle routes through this."
 *
 * The two themes are structurally different controls, not one control recoloured:
 *   · hardware  48×24, 3px radius, TWO vertical tick marks flanking a square knob, LED glow
 *   · celestial 48×22, pill, ONE horizontal light bar (rendered only when on), round knob
 * Both branches are transcribed whole, including the greys v4 hardcoded (`#2a3346`, `#242c3d`,
 * `#3d4658`, `#252c3b`) and the knob highlight `#ffe4f0`, none of which are tokenized.
 */
export function Switch({ T, on, col }: SwitchProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';
  const c = col || C.sig;

  if (hw) {
    return (
      <span
        style={{
          width: '48px',
          height: '24px',
          borderRadius: '3px',
          background: on
            ? // v4: 'linear-gradient(180deg,'+c+'47,'+c+'14)'  (0x47 = .278, 0x14 = .078)
              `linear-gradient(180deg,${alpha(c, 0.278)},${alpha(c, 0.078)})`
            : 'rgba(0,0,0,.45)',
          // v4: on ? c+'99' : 'rgba(255,255,255,.12)'  (0x99 = .6)
          border: '1px solid ' + (on ? alpha(c, 0.6) : 'rgba(255,255,255,.12)'),
          position: 'relative',
          display: 'inline-block',
          flex: '0 0 auto',
          overflow: 'hidden',
          boxShadow: on
            ? // v4: '0 0 12px '+c+'73, inset 0 1px 0 rgba(255,255,255,.12)'  (0x73 = .451)
              `0 0 12px ${alpha(c, 0.451)}, inset 0 1px 0 rgba(255,255,255,.12)`
            : // v4's literal, and gallery-correct. ⚠ Briefly replaced with
              // `T.effects.bevelInsetDeep` (alpha .4) on the strength of a token docstring
              // naming this site — but RECONCILIATION cites L119/L280 for that token, which are
              // TEXT-INPUT WELLS. The gallery's actual hardware toggle-off track in 5c reads
              // `inset 0 1px 3px rgba(0,0,0,.5)`. Reverted 2026-07-18 (review gate).
              'inset 0 1px 3px rgba(0,0,0,.5)',
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: on ? '5px' : 'auto',
            right: on ? 'auto' : '5px',
            width: '2px',
            background: on ? c : '#2a3346',
            boxShadow: on ? '0 0 6px ' + c : 'none',
          }}
        />
        <span
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: on ? '9px' : 'auto',
            right: on ? 'auto' : '9px',
            width: '2px',
            // v4: c+'73'  (0x73 = .451)
            background: on ? alpha(c, 0.451) : '#242c3d',
          }}
        />
        <span
          style={{
            position: 'absolute',
            top: '3px',
            left: on ? '29px' : '3px',
            width: '16px',
            height: '16px',
            borderRadius: '2px',
            background: on
              ? `linear-gradient(180deg,rgba(255,255,255,.75),${c})`
              : 'linear-gradient(180deg,#3d4658,#252c3b)',
            boxShadow: on
              ? `0 0 8px ${c}, inset 0 1px 0 rgba(255,255,255,.4)`
              : 'inset 0 1px 0 rgba(255,255,255,.06)',
            transition: 'left .15s',
          }}
        />
      </span>
    );
  }

  return (
    <span
      style={{
        width: '48px',
        height: '22px',
        borderRadius: '999px',
        background: on
          ? // v4: 'linear-gradient(90deg,'+c+'0d,'+c+'52)'  (0x0d = .051, 0x52 = .322)
            `linear-gradient(90deg,${alpha(c, 0.051)},${alpha(c, 0.322)})`
          : 'rgba(255,255,255,.04)',
        // v4: on ? c+'66' : 'rgba(255,255,255,.1)'  (0x66 = .4)
        border: '1px solid ' + (on ? alpha(c, 0.4) : 'rgba(255,255,255,.1)'),
        position: 'relative',
        display: 'inline-block',
        flex: '0 0 auto',
        overflow: 'hidden',
        // v4: '0 0 12px '+c+'40'  (0x40 = .251)
        boxShadow: on ? `0 0 12px ${alpha(c, 0.251)}` : 'none',
      }}
    >
      {on ? (
        <span
          style={{
            position: 'absolute',
            top: '50%',
            left: '6px',
            right: '24px',
            height: '2px',
            transform: 'translateY(-50%)',
            // v4: 'linear-gradient(90deg,transparent,'+c+'b3)'  (0xb3 = .702)
            background: `linear-gradient(90deg,transparent,${alpha(c, 0.702)})`,
            borderRadius: '2px',
          }}
        />
      ) : null}
      <span
        style={{
          position: 'absolute',
          top: '2px',
          left: on ? '27px' : '4px',
          width: '17px',
          height: '17px',
          borderRadius: '50%',
          background: on ? `radial-gradient(circle at 40% 35%,#ffe4f0,${c})` : 'transparent',
          border: on ? 'none' : '1.5px solid ' + C.dimmer,
          boxShadow: on
            ? // v4: '0 0 10px '+c+'e6, 0 0 3px #fff'  (0xe6 = .902)
              `0 0 10px ${alpha(c, 0.902)}, 0 0 3px #fff`
            : // v4 literal 'inset 0 0 4px rgba(0,0,0,.5)'; tokens name this exact site
              // (celestial `bevelInset` — "gallery L180 (toggle-off knob)")
              T.effects.bevelInset,
          transition: 'left .15s',
        }}
      />
    </span>
  );
}
