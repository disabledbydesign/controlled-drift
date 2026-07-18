/**
 * Row components ported from `design/mockups/review-reorganize-mobile-v4.html`.
 *
 * `Row` is the single most reused component in the app — the Map tree, Routines, Strategies
 * and the move picker all render through it. Styles are INLINE STYLE OBJECTS reading from the
 * token module, deliberately; see `components/atoms/index.ts` for that argument in full.
 */
export { Row } from './Row';
export type { RowOptions, RowProps } from './Row';
export { Lead } from './Lead';
export type { LeadProps } from './Lead';
export { D } from './types';
export type { ChipEditTarget, RowCtx, RowUi } from './types';
