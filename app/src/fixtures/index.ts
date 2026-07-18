/**
 * Fixtures extracted from design/mockups/review-reorganize-mobile-v4.html.
 *
 * These are a CONTRACT with the backend track — the frontend builds against
 * them and the backend builds to the same shapes, so integration is swapping
 * the data source. Values are verbatim; do not rename, normalise or tidy.
 */

export { defaultSchema } from './schema.ts';
export { seed, seedStrategies } from './tree.ts';
export { seedPlan } from './plan.ts';
export { seedPeriods } from './periods.ts';

export type {
  Level,
  NodeType,
  RelationKey,
  Relation,
  ControlKind,
  Control,
  NoteField,
  Schema,
  NodeVals,
  Node,
  Strategy,
  ArcState,
  PlanArcStep,
  PlanBlockItem,
  PlanTaskItem,
  PlanBreakItem,
  PlanItem,
  PlanBlock,
  Plan,
  PeriodWhen,
  Period,
} from './types.ts';
