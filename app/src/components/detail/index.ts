/**
 * The detail editor — v4's `detail()` (~541) and everything it is made of.
 *
 * Styles are INLINE STYLE OBJECTS reading from the token module, deliberately; see
 * `components/atoms/index.ts` for that argument in full. Every field in the form is generated
 * from the schema (`OPTS` / `CTRL` / `TEXT`), with two documented exceptions, both flagged in
 * the files that make them: the Strategy note relabelling (`strategyFields.ts`) and the
 * RECURRING schedule block (`RecurrenceCard` / `RecurringPlanRow`).
 *
 * `DetailOverlay` is the mount point — `AppShell` renders that, not `Detail`.
 */
export { DetailOverlay } from './DetailOverlay.tsx';
export type { DetailOverlayProps } from './DetailOverlay.tsx';
export { Detail } from './Detail.tsx';
export type { DetailProps } from './Detail.tsx';
export { Field } from './Field.tsx';
export type { FieldProps } from './Field.tsx';
export { InheritRow } from './InheritRow.tsx';
export type { InheritRowProps } from './InheritRow.tsx';
export { HeaderDone } from './HeaderDone.tsx';
export type { HeaderDoneProps } from './HeaderDone.tsx';
export { HeaderTypeBadge } from './HeaderTypeBadge.tsx';
export type { HeaderTypeBadgeProps } from './HeaderTypeBadge.tsx';
export { PaneCloseBtn } from './PaneCloseBtn.tsx';
export type { PaneCloseBtnProps } from './PaneCloseBtn.tsx';
export { LocationBlock } from './LocationBlock.tsx';
export type { LocationBlockProps } from './LocationBlock.tsx';
export { RecurrenceCard, fmtTime } from './RecurrenceCard.tsx';
export type { RecurrenceCardProps } from './RecurrenceCard.tsx';
export { RecurringPlanRow } from './RecurringPlanRow.tsx';
export type { RecurringPlanRowProps } from './RecurringPlanRow.tsx';
/**
 * ⚠ `TypeSection` has NO call site — not here, and not in v4 either (grep finds only its
 * definition at v4:292). See the header comment in `TypeSection.tsx`.
 */
export { strategyNotes } from './strategyFields.ts';
export type { DetailCtx, DetailUi } from './types.ts';
