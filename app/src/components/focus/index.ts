/**
 * The focus-period editor — v4's `focusPanel` (814), `focusDetail` (813), `focusEditor` (887),
 * `fEditor` (850), `daysOffEditor` (866) and `focusFrontPicker` (874).
 *
 * Two mount points, both wired: `FocusPanel` renders inside the Today tab's focus slot
 * (v4:1021), and `FocusOverlay` paints the editor over the whole phone frame on the
 * `__focus__` detail route (v4:541).
 *
 * Styles are INLINE STYLE OBJECTS reading from the token module, deliberately. See
 * `components/atoms/index.ts` for that argument in full.
 *
 * NOT PORTED, and why: `fRow` (v4:842) — defined once, zero call sites; and with it
 * `st.focusEditField`, whose only reader it was. `daysOffDisp` (v4:895) — computed, never
 * rendered, same dead consumer. Details in `fields.tsx`.
 */
export { FocusPanel } from './FocusPanel.tsx';
export type { FocusPanelProps } from './FocusPanel.tsx';
export { FocusOverlay } from './FocusOverlay.tsx';
export type { FocusOverlayProps } from './FocusOverlay.tsx';
export { FocusEditor } from './FocusEditor.tsx';
export { FEditor } from './FEditor.tsx';
export type { FEditorKey } from './FEditor.tsx';
export { DaysOffEditor } from './DaysOffEditor.tsx';
export { FocusProjectPicker } from './FocusProjectPicker.tsx';
export { FSub, FField, FSubLabel, FTwo, inputStyle } from './fields.tsx';
export { fmtDate } from './fmtDate.ts';
export { NAV } from './types.ts';
export type { FocusCtx, FocusUi, FocusView } from './types.ts';
