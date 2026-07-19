/**
 * The Today tab — v4's execution surface (`todayPanel` ~977 and everything under it).
 *
 * Styles are INLINE STYLE OBJECTS reading from the token module, deliberately. See
 * `components/atoms/index.ts` for that argument in full.
 *
 * Two render paths over one plan payload: the clock `schedule` (bands of timed entries) and
 * the flat `priority` list (ranked, no clock). `TodayPanel` switches between them on
 * `ui.todayShape`; everything below `Band` / `PriorityList` is shared.
 */
export { TodayPanel } from './TodayPanel.tsx';
export type { TodayPanelProps } from './TodayPanel.tsx';
export { FocusSlot, fmtDate } from './FocusSlot.tsx';
export { Band } from './Band.tsx';
export { PlanEntry } from './PlanEntry.tsx';
export { WorkBlock } from './WorkBlock.tsx';
export { ArcStep } from './ArcStep.tsx';
export { Interstitial } from './Interstitial.tsx';
export { TaskRow } from './TaskRow.tsx';
export { PriorityList } from './PriorityList.tsx';
export { RowActions } from './RowActions.tsx';
export type { RowActionsProps } from './RowActions.tsx';
export { moveDestinations } from './moveTargets.ts';
export type { MoveDestination, MoveTarget } from './moveTargets.ts';
export { toggleKey } from './util.ts';
export { PANEL } from './types.ts';
export type { TodayCtx, TodayUi } from './types.ts';
