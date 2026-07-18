import type { Theme } from '@tokens';

export interface PaneCloseBtnProps {
  T: Theme;
  onClose: () => void;
}

/**
 * v4 `paneCloseBtn()` (~540) — the DESKTOP close affordance.
 *
 * v4's detail header forks on `this._wide` (587): the phone gets a "‹ Back" text button in
 * `C.blue`, the desktop gets this bordered "✕ Close" pill. `_wide` is set true only inside
 * `deskApp()` (730) and false in `renderApp()` (697), `renderShell()` (929) and
 * `structurePanel()` (959) — so on the phone this component never renders.
 *
 * The desktop shell is Task 10. Until it lands nothing in the running app passes
 * `wide`, so this renders only under test. Ported now because it belongs to `detail()`.
 */
export function PaneCloseBtn({ T, onClose }: PaneCloseBtnProps) {
  const C = T.c;
  return (
    <button
      onClick={onClose}
      aria-label="close"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        background: 'none',
        border: '1px solid ' + C.border,
        borderRadius: T.r.field,
        color: C.dim,
        fontSize: '12px',
        fontWeight: 600,
        cursor: 'pointer',
        padding: '4px 11px',
        marginBottom: '10px',
        fontFamily: 'inherit',
      }}
    >
      <svg width={13} height={13} viewBox="0 0 24 24" fill="none">
        <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      </svg>
      Close
    </button>
  );
}
