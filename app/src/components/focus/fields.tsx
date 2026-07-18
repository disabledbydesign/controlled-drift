import type { CSSProperties, ReactNode } from 'react';
import type { Theme } from '@tokens';

/**
 * The four small layout helpers v4 defines for the focus editor form.
 *
 * ── `fRow` (v4:842) IS NOT PORTED ───────────────────────────────────────────
 * It is defined once and has ZERO call sites — `grep -n "fRow"` over the mockup returns the
 * definition line and nothing else. Its only reader of `st.focusEditField` went with it: that
 * field is *written* at v4:79/816/836/888/926 and *read* only inside `fRow` (842, 847), so
 * with `fRow` gone it has no reader at all and is not carried into `UiState` either.
 *
 * Same basis as the already-removed `renderApp`/`header`/`tab`, `typeSection` and `menuStrip`:
 * this repo does not port v4's dead paths.
 *
 * `focusEditor` (887) builds its form out of `fField` + `fSub` + `fEditor` directly — an
 * always-open form, not the tap-to-expand rows `fRow` would have made.
 */

/** v4 `fSub(t)` (838) — a section heading with a rule above it. */
export function FSub({ T, children }: { T: Theme; children: ReactNode }) {
  const C = T.c;
  return (
    <div
      style={{
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '.1em',
        textTransform: 'uppercase',
        color: C.roseDim,
        marginTop: '4px',
        paddingTop: '9px',
        borderTop: '1px solid ' + C.roseBorder,
      }}
    >
      {children}
    </div>
  );
}

/** v4 `fField(label,ctl)` (839) — an uppercase field label above its control. */
export function FField({ T, label, children }: { T: Theme; label: string; children: ReactNode }) {
  const C = T.c;
  return (
    <div>
      <label
        style={{
          display: 'block',
          fontSize: '10px',
          color: C.roseDim,
          textTransform: 'uppercase',
          letterSpacing: '.07em',
          marginBottom: '5px',
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

/** v4 `fSubLabel(t,ctl)` (841) — the smaller sentence-case label used inside a paired row. */
export function FSubLabel({ T, label, children }: { T: Theme; label: string; children: ReactNode }) {
  const C = T.c;
  return (
    <div>
      <div style={{ fontSize: '10px', color: C.roseDim, marginBottom: '4px' }}>{label}</div>
      {children}
    </div>
  );
}

/** v4 `fEditor`'s `two(a,b)` (853) — two equal-width columns. */
export function FTwo({ a, b }: { a: ReactNode; b: ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: '10px' }}>
      <div style={{ flex: 1 }}>{a}</div>
      <div style={{ flex: 1 }}>{b}</div>
    </div>
  );
}

/**
 * v4 `fEditor`'s `inp` (851) — the shared input style, and also `focusEditor`'s own copy
 * (889), which is byte-identical except that it omits `colorScheme:'dark'`. Both are produced
 * here; `colorScheme` is passed by the caller that needs it, so the two stay one definition.
 *
 * ⚠ `colorScheme:'dark'` is v4's, on the `<input type="date">`/`<input type="time">` controls,
 * to force the browser's native picker chrome dark. It is hardcoded in v4 and does NOT fork
 * on theme — kept as-is; whether the hardware theme wants a light picker is unverified.
 */
export function inputStyle(T: Theme, colorScheme?: 'dark'): CSSProperties {
  const C = T.c;
  return {
    width: '100%',
    background: C.surface,
    border: '1px solid ' + C.roseBorder,
    borderRadius: T.r.field,
    color: C.text,
    fontSize: '13px',
    fontFamily: 'inherit',
    padding: '9px 11px',
    outline: 'none',
    boxSizing: 'border-box',
    ...(colorScheme ? { colorScheme } : null),
  };
}
