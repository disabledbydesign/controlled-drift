/**
 * Model-layer types. Pure data — no React, no theme, no DOM.
 *
 * Everything here is derived from design/mockups/review-reorganize-mobile-v4.html.
 * The fixture types in `src/fixtures/types.ts` are the contract with the backend;
 * this file only adds what the *runtime* graph needs on top of them.
 */

import type { Node, Level, Control, NoteField, RelationKey } from '../fixtures/index.ts';

/**
 * A node as it exists at runtime.
 *
 * v4 hangs two extra properties on seed nodes that are NOT fixture data:
 *   - `parent` — a back-pointer set by `index()` (~line 277)
 *   - `_new`   — set by `addChild()` (~line 299), read by `maybeDiscardBlank`
 *
 * `parent` is deliberately NOT reproduced here. A back-pointer makes the graph
 * cyclic, and a cyclic structure cannot be structurally shared when copied — it
 * would force a full deep clone on every keystroke. Ancestry lives in
 * `GraphIndex.parentOf` instead, which is derived, not stored.
 */
export interface ModelNode extends Node {
  children: ModelNode[];
  /** v4's `_new:true` marker on a just-created, not-yet-filled node. */
  _new?: boolean;
}

/**
 * The whole object graph.
 *
 * v4 keeps these as two separate instance fields (`this.data`, `this.strategies`)
 * because Strategy is global and non-hierarchical. Same split, one value.
 */
export interface Graph {
  roots: ModelNode[];
  strategies: ModelNode[];
}

/**
 * Derived lookups over a Graph — v4's `this.byId` plus the `parent` pointers it
 * used to write onto the nodes themselves.
 *
 * Rebuild this after every mutation. It is cheap (one walk) and holding a stale
 * index is the one real hazard of moving ancestry off the nodes.
 */
export interface GraphIndex {
  byId: ReadonlyMap<string, ModelNode>;
  parentOf: ReadonlyMap<string, ModelNode | null>;
}

/**
 * The flat lookups `applySchema()` (~line 126) derives from the schema literal.
 * Named exactly as v4 names them so render code ports across unchanged.
 */
export interface DerivedSchema {
  /** relationKey -> option list (a copy, as in v4's `.slice()`). */
  OPTS: Record<RelationKey, string[]>;
  /** level -> control tuples. */
  CTRL: Record<Level, Control[]>;
  /** level -> note fields. */
  TEXT: Record<Level, NoteField[]>;
}

/**
 * The colour slots the model layer needs.
 *
 * Passed in rather than imported so the model stays pure and testable — the
 * theme module owns which hex belongs to which slot, and there are two themes.
 * Structurally satisfied by `design/tokens/tokens.ts`'s palette.
 */
export interface ModelColors {
  dimmer: string;
  blue: string;
  green: string;
  amber: string;
  teal: string;
  purple: string;
  orange: string;
  red: string;
  strategy: string;
  horizon: string;
  side: string;
}

/** One chip on a collapsed row — v4's `chipsFor()` return element (~line 320). */
export interface Chip {
  text: string;
  color: string;
  field: string;
  /** Present only on the chips that can be unset; v4 omits it otherwise. */
  unset?: boolean;
}

/** The result of `effective()` — v4 returns `{val, from}` (~line 486). */
export interface EffectiveValue {
  val: string | string[] | number | boolean;
  /** Title of the ancestor the value came from; null when nothing inherited. */
  from: string | null;
}

/**
 * What a mutation returns.
 *
 * ── THE ONE PLACE THIS PORT RESTRUCTURES RATHER THAN TRANSCRIBES ─────────────
 * v4's mutations are `void`. They mutate `this.data` / node objects in place,
 * then call `bump()` (a no-op state tick that forces a re-render), `flash(msg)`
 * (a transient toast), and sometimes `up({...})` (a patch onto `this.state.s`,
 * the UI-state bag). React with immutable state cannot do any of that.
 *
 * So each mutation is a pure function returning all four effects as data:
 *   - `graph` — the new graph. `bump()` is gone; a changed reference IS the
 *     re-render signal. When a mutation no-ops, the SAME reference comes back.
 *   - `toast` — the exact string v4 passed to `flash()`, or null where v4 did
 *     not flash. The caller decides how to show it. (Per the handoff, `toast()`
 *     is stubbed in v4 and becomes the real read-back confirmation; keeping the
 *     message as data rather than a side effect is what makes that possible.)
 *   - `ui`   — the exact patch v4 passed to `up()`, or null. Untyped bag on
 *     purpose: the UI-state shape belongs to the component, not to the model.
 *   - `node` — the affected node AFTER the mutation, or null when nothing
 *     happened. `addChild` needs it (the caller must know the generated id);
 *     the others make it available for the read-back confirmation.
 *
 * What is preserved exactly: which node changes, which keys change, what is
 * left alone, what is removed, and in what order the guards fire.
 */
export interface MutationResult {
  graph: Graph;
  toast: string | null;
  ui: Record<string, unknown> | null;
  node: ModelNode | null;
}
