import { typeRamp } from '@tokens';
import type { Theme } from '@tokens';

/** The seven object levels the tree renders. */
export type TypeLevel =
  | 'GOAL'
  | 'PROJECT'
  | 'SUBPROJECT'
  | 'WORKSTREAM'
  | 'TASK'
  | 'RECURRING'
  | 'STRATEGY';

/**
 * Object-type colour.
 *
 * v4 read `this.TYPE[level]`, a map built in `applyTheme()` (~166) as
 * `{GOAL:amber, PROJECT:blue, SUBPROJECT:teal, TASK:green, WORKSTREAM:purple,
 *   RECURRING:orange, STRATEGY:strategy}`.
 *
 * That map is superseded by `typeRamp` in the token module, which is an explicit legend in
 * the gallery: Goal ⊃ Project ⊃ Task get a continuous pale-cyan → cyan → blue ramp because
 * that IS the containment hierarchy, and Recurring/Strategy sit outside it. v4's map also
 * coloured TASK green, colliding with the completion green used for done/steady/saved.
 * Do not reintroduce it.
 */
export function typeColor(T: Theme, level: string): string {
  return typeRamp[T.name][level] ?? T.c.dim;
}
