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
  /**
   * Objects that exist but hang off nothing — see `OrphanBucket`. Optional so every existing
   * `{roots, strategies}` literal (tests, fixtures, the old shape) still typechecks; absent and
   * empty mean the same thing.
   */
  orphans?: OrphanBucket[];
}

/**
 * A catch-all group of unparented objects.
 *
 * ── why this is load-bearing and not a diagnostic ────────────────────────────
 * The tree is Goal → Project → Task. An object with no parent renders NOWHERE in it — it does
 * not show as misplaced, it silently does not exist. Capture and weeding both produce unfiled
 * objects, so this is not an edge case: **twelve objects in June's live space are unparented
 * right now** (3 tasks and 9 recurring items, including Shower, Go on a walk, Therapy, Text
 * friends). Without these buckets the new surface would lose all twelve from view the day it
 * replaces the old one. `scripts/review_surface.py:234-247` is the surface being retired, and
 * this is the capability being carried across.
 *
 * ── the labels come from the server, not from here ───────────────────────────
 * `GET /api/tree` returns `orphans` as four keyed buckets, each `{label, nodes}`
 * (`scripts/api_tree.py:295-310`), and the labels there are kept verbatim from the retiring
 * surface so the wording June already reads does not change. The UI renders whatever labels
 * arrive; it does not author them and must not.
 *
 * ── they are part of the graph, not beside it ────────────────────────────────
 * Bucket nodes go through `index()`, `updateNode()`, `removeNode()` and `appendChild()` exactly
 * like rooted ones. That is deliberate: a row you can see but not open, edit or move is the
 * "uncheckoffable ghost row" failure this repo already paid a rebuild for. Filing an orphan by
 * moving it into a project is the whole point of surfacing it, and that only works if `move()`
 * can find it.
 */
export interface OrphanBucket {
  /** Stable id from the endpoint — `orphan_tasks`, `projects_without_goal`, … */
  key: string;
  /** June-facing heading, supplied by the endpoint. */
  label: string;
  nodes: ModelNode[];
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
  /**
   * THIS `toast` IS A REFUSAL, NOT A RECEIPT — the mutation declined, deliberately, and nothing
   * changed. Absent (falsy) on every ordinary mutation, whose `toast` reports what did happen.
   *
   * It exists because the two cannot share a presentation. A receipt is quiet: the control has
   * already re-rendered with the new value, so the message is a second telling of a visible fact.
   * A refusal has no such fact behind it — nothing on screen moved — so it has to be READ, and
   * the caller must raise it as a notice rather than a success. Raised as a success it renders
   * nowhere at all, because success is presented `inline` and a refusal carries no `node` to
   * settle on. See `shell/signals.ts`.
   */
  refusal?: boolean;
  /**
   * WHAT THIS MUTATION MEANS ON THE WIRE — see `WriteIntent`. Absent on a no-op and on the
   * mutations that have no endpoint yet; present on every mutation that must persist.
   */
  write?: WriteIntent;
}

/**
 * A mutation's network meaning, carried as DATA rather than performed here.
 *
 * ── why the intent travels with the result instead of the call site calling fetch ──
 * There are ~30 mutation call sites across the components (`Field`, `ChipStrip`, `Row`,
 * `Detail`, `RecurrenceCard`, `PickerPage`, `AddPanel`, `Lead`, `HeaderDone`, …) and every one
 * of them already funnels through a single `ctx.apply(result)`. Putting `fetch` at those call
 * sites would mean 30 places that each have to remember to await, roll back and report — which
 * is precisely the shape of rule that gets forgotten, the same argument `useAppState` already
 * makes for deriving the index instead of rebuilding it per call site.
 *
 * So the model layer stays PURE (it still computes the optimistic next graph and nothing else)
 * and simply says what the write was. `useAppState.apply` is the one place that talks to the
 * network, and the one place that can roll back when the server says the write did not land.
 *
 * ⚠ Two `op`s below have NO endpoint on the server today: `clearField`
 * (`POST /api/object/{id}/clear-field`, contract §1) and `setType`
 * (`POST /api/object/{id}/type`, contract §1 · §6 Q2 — it needs a live capability probe first,
 * and `api_write.py` says in its own docstring that the conversion seam is deliberately not
 * built). They are declared so the shape is complete and so `apply` can report them honestly as
 * not-persisted rather than showing a false success. See `unsupported` in `useAppState`.
 */
export type WriteIntent =
  /** `PATCH /api/object/{id}` `{vals}` — setVal, toggleMulti, and the recurrence editor. */
  | { op: 'patchVals'; id: string; vals: Record<string, unknown> }
  /** `PATCH /api/object/{id}` `{title}` — debounced; see `apply`. */
  | { op: 'patchTitle'; id: string; title: string }
  /** `POST /api/object/{id}/move` `{parent_id}`. */
  | { op: 'move'; id: string; parentId: string }
  /** `DELETE /api/object/{id}` — archives, and answers `{ok,id,archived}` with no object. */
  | { op: 'archive'; id: string }
  /** `POST /api/object` `{level,title,parent_id}` — the response id REPLACES the temp id. */
  | { op: 'create'; tempId: string; level: string; title: string; parentId: string | null }
  /** `POST /api/complete` / `POST /api/uncomplete` `{id}`. */
  | { op: 'complete'; id: string; done: boolean }
  /** `POST /api/recurring/active` `{id, active}` — note the UI stores the INVERSE, `paused`. */
  | { op: 'recurringActive'; id: string; active: boolean }
  /**
   * `POST /api/object/{id}/clear-field` `{field}` — REMOVE a property so it inherits again.
   * Deliberately not a `patchVals` with an empty value: key-presence IS the spec §4 tri-state,
   * and an empty write would set an explicit "none" (or, for a multi_select, delete the
   * property while reporting a set). The server refuses formats it cannot actually clear.
   */
  | { op: 'clearField'; id: string; field: string }
  /** No endpoint yet — contract §1. Carries why, so the failure message can say it. */
  | { op: 'unsupported'; id: string; what: string };
