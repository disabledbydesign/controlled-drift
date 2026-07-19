import { useEffect } from 'react';
import type { Theme } from '@tokens';
import { present } from './signals.ts';
import type { Signal } from './signals.ts';

/**
 * v4 `toast()` (383) — which in v4 is `return null;`, a stub.
 *
 * ── what it is now ───────────────────────────────────────────────────────────
 * The visible half of this repo's read-back rule: a write is not confirmed until it has been
 * re-fetched, and this is where the app says what came back. So the message is *what actually
 * persisted* ("Sorted into Build Controlled Drift", "Moved · synced"), never a bare "Saved" with
 * no referent.
 *
 * ── it renders whatever `present()` says, and decides nothing itself ─────────
 * All the policy — quiet on success, loud and persistent on failure, verbose bar for dev — lives
 * in `signals.ts`. This file renders exactly one of the modes that function can name (`bar`) and
 * returns null for the others. That split is the thing June asked for: making success subtler,
 * or removing it, is an edit to `present()`, not a hunt through components.
 *
 * ── the two looks ────────────────────────────────────────────────────────────
 * SUCCESS (dev-verbose only) is v2/v3's green pill, restored: `savedpulse 1.6s ease forwards`,
 * centred, `bottom:26px`, `zIndex:60`, prefixed `✓ `. Transcribed from
 * `design/mockups/review-reorganize-mobile-v3.html:321`, which is the last mockup that actually
 * implemented the toast before v4 stubbed it — so this is a restoration, not an invention.
 *
 * FAILURE is deliberately NOT that pill. It does not animate away, it is wider, it carries the
 * message on its own line with a dismiss control, and it uses `red`. It has to survive being
 * glanced at late.
 *
 * ── no metaphors ─────────────────────────────────────────────────────────────
 * Hard access requirement. The failure copy says what did not happen and what to do; it does not
 * reach for an image.
 */
export function SignalBar({
  T,
  sig,
  onDismiss,
}: {
  T: Theme;
  sig: Signal | null;
  onDismiss: () => void;
}) {
  const p = sig ? present(sig) : null;
  const auto = !!p && p.mode === 'bar' && !p.persist;
  const ms = p ? p.ms : 0;
  // v4's `flash()` (309) clears with a `setTimeout` it re-arms on each call. Same behaviour,
  // keyed on `seq` so two identical messages in a row each get their own full dwell rather than
  // the second inheriting the remains of the first timer.
  const seq = sig ? sig.seq : -1;

  useEffect(() => {
    if (!auto) return;
    const t = setTimeout(onDismiss, ms);
    return () => clearTimeout(t);
  }, [auto, ms, seq, onDismiss]);

  if (!sig || !p || p.mode !== 'bar') return null;
  // ⚠ A notice persists exactly like a failure, so `p.persist` alone cannot tell them apart —
  // dispatch on the KIND. Without this a "you have not put an end date in yet" renders red with
  // `role="alert"`, telling her something broke when nothing did.
  if (sig.kind === 'notice') return <NoticeBar T={T} sig={sig} onDismiss={onDismiss} />;
  return p.persist ? (
    <FailureBar T={T} sig={sig} onDismiss={onDismiss} />
  ) : (
    <SuccessPill T={T} sig={sig} />
  );
}

/** v3:321 verbatim in structure — green pill, centred, fades itself out. Dev-verbose only. */
function SuccessPill({ T, sig }: { T: Theme; sig: Signal }) {
  const C = T.c;
  return (
    <div
      key={sig.seq}
      role="status"
      aria-live="polite"
      data-signal="success"
      style={{
        // `fixed`, not v4's `absolute`. v4's shell is a FIXED-HEIGHT phone frame, so an
        // absolutely-positioned toast sat at the bottom of the visible screen. The real phone
        // shell is `minHeight:100vh` and grows with its content, so `absolute` puts the bar at
        // the bottom of the whole DOCUMENT — off-screen, which is exactly what happened the
        // first time this was driven on the real page. Caught by looking, not by a test.
        position: 'fixed',
        left: '50%',
        bottom: '26px',
        transform: 'translateX(-50%)',
        background: C.green,
        color: '#062012',
        fontSize: '12.5px',
        fontWeight: 700,
        padding: '8px 16px',
        borderRadius: '20px',
        animation: 'savedpulse 1.6s ease forwards',
        zIndex: 60,
        boxShadow: '0 6px 20px rgba(0,0,0,.4)',
        maxWidth: 'calc(100% - 32px)',
        textAlign: 'center',
      }}
    >
      {'✓ ' + sig.msg}
    </div>
  );
}

/**
 * The failure bar. Persistent, prominent, dismissible, and it names what did not happen.
 *
 * `role="alert"` rather than `role="status"`: a screen reader should interrupt for this one.
 */
function FailureBar({ T, sig, onDismiss }: { T: Theme; sig: Signal; onDismiss: () => void }) {
  const C = T.c;
  return (
    <div
      key={sig.seq}
      role="alert"
      data-signal="failure"
      style={{
        // `fixed` for the same reason as the pill above — see that note.
        position: 'fixed',
        left: '50%',
        bottom: '22px',
        transform: 'translateX(-50%)',
        width: 'calc(100% - 28px)',
        maxWidth: '440px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        background: C.panel,
        border: '1px solid ' + C.red,
        boxShadow: '0 8px 26px rgba(0,0,0,.45), inset 3px 0 0 ' + C.red,
        borderRadius: T.r.ctl,
        padding: '11px 12px 11px 14px',
        zIndex: 60,
        animation: 'panelin .16s ease',
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          color: C.red,
          fontSize: '13px',
          fontWeight: 700,
          lineHeight: 1.5,
          flex: '0 0 auto',
        }}
      >
        !
      </span>
      <span style={{ flex: 1, minWidth: 0, fontSize: '12.5px', lineHeight: 1.5, color: C.text }}>
        {sig.msg}
      </span>
      <button
        onClick={onDismiss}
        aria-label="dismiss"
        style={{
          flex: '0 0 auto',
          background: 'none',
          border: 'none',
          color: C.dim,
          fontSize: '13px',
          cursor: 'pointer',
          padding: '0 2px',
          fontFamily: 'inherit',
          lineHeight: 1.5,
        }}
      >
        ✕
      </button>
    </div>
  );
}

/**
 * The notice bar — "you have not filled this in yet".
 *
 * Same shape and same persistence as the failure bar, because it has the same problem: its
 * result is not visible at the control, so a bar that fades leaves her believing a write landed.
 * Everything that says BREAKAGE is dropped: the red rule and glyph become the neutral gold
 * accent, and `role="status"` announces at the next pause instead of `role="alert"` cutting in.
 * Nothing went wrong here — she is being told what is still needed.
 */
function NoticeBar({ T, sig, onDismiss }: { T: Theme; sig: Signal; onDismiss: () => void }) {
  const C = T.c;
  return (
    <div
      key={sig.seq}
      role="status"
      aria-live="polite"
      data-signal="notice"
      style={{
        position: 'fixed',
        left: '50%',
        bottom: '22px',
        transform: 'translateX(-50%)',
        width: 'calc(100% - 28px)',
        maxWidth: '440px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        background: C.panel,
        border: '1px solid ' + C.gold,
        boxShadow: '0 8px 26px rgba(0,0,0,.45), inset 3px 0 0 ' + C.gold,
        borderRadius: T.r.ctl,
        padding: '11px 12px 11px 14px',
        zIndex: 60,
        animation: 'panelin .16s ease',
        backdropFilter: T.blur,
        WebkitBackdropFilter: T.blur,
      }}
    >
      <span style={{ flex: 1, minWidth: 0, fontSize: '12.5px', lineHeight: 1.5, color: C.text }}>
        {sig.msg}
      </span>
      <button
        onClick={onDismiss}
        aria-label="dismiss"
        style={{
          flex: '0 0 auto',
          background: 'none',
          border: 'none',
          color: C.dim,
          fontSize: '13px',
          cursor: 'pointer',
          padding: '0 2px',
          fontFamily: 'inherit',
          lineHeight: 1.5,
        }}
      >
        ✕
      </button>
    </div>
  );
}
