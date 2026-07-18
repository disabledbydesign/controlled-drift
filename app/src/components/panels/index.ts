/**
 * The structure-tab panels, ported from `design/mockups/review-reorganize-mobile-v4.html`.
 *
 * These are the chrome around the three structure lists (Map / Routines / Strategies) plus the
 * two things that drop out of a row. Styles are INLINE STYLE OBJECTS reading from the token
 * module, deliberately; see `components/atoms/index.ts` for that argument in full.
 */
export { MapControls } from './MapControls.tsx';
export { FilterMenu } from './FilterMenu.tsx';
export { AddPanel, addContextParent, validAddParent } from './AddPanel.tsx';
export { ChipStrip, chipOpts } from './ChipStrip.tsx';
export type { ChipStripProps } from './ChipStrip.tsx';
export { PickerPage } from './PickerPage.tsx';
// Task 11 — neither is a port; see each file's header for what it carries across and why.
export { orphanSections } from './OrphanBuckets.tsx';
export { CrossTabMatches, searchAll, owningTab } from './CrossTabMatches.tsx';
export type { StructureTab } from './CrossTabMatches.tsx';
export { FLABEL, NAV, PANEL } from './types.ts';
export type { PanelCtx, PanelUi } from './types.ts';
