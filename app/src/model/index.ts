/**
 * The model layer — pure, non-visual functions the whole UI sits on.
 *
 * Ported from design/mockups/review-reorganize-mobile-v4.html. Logic is
 * transcribed; only the mutation MECHANISM changes (in-place + bump() becomes
 * pure state-in/state-out). See mutations.ts for that argument in full.
 */

export type {
  ModelNode,
  Graph,
  GraphIndex,
  DerivedSchema,
  ModelColors,
  Chip,
  EffectiveValue,
  MutationResult,
} from './types.ts';

export {
  index,
  node,
  parentOf,
  pathTo,
  removeNode,
  updateNode,
  appendChild,
  isSelfOrDescendant,
} from './graph.ts';

export { applySchema } from './schema.ts';

export {
  effective,
  isOwnValue,
  hasSchedulableAncestor,
  INHERIT,
  isInactive,
  statusColor,
  sideColor,
  chipsFor,
  typeOptions,
  TYPE_LABEL_FOR_LEVEL,
} from './fields.ts';

export {
  setVal,
  toggleMulti,
  setTitle,
  clearVal,
  del,
  move,
  setType,
  toggleDone,
  toggleActive,
  addChild,
  defaultNewId,
} from './mutations.ts';
