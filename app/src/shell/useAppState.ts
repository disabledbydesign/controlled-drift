import { useCallback, useMemo, useState } from 'react';
import { defaultSchema, seed, seedPlan, seedStrategies } from '../fixtures/index.ts';
import type { Plan } from '../fixtures/index.ts';
import { applySchema, index } from '../model/index.ts';
import type { DerivedSchema, Graph, GraphIndex, MutationResult } from '../model/index.ts';
import type { AppTab } from './tabs.ts';

/**
 * The application state — v4's instance fields (`this.data`, `this.strategies`, `this.byId`,
 * `this.OPTS/CTRL/TEXT`, `this.plan`, `this.state.s`) as one React hook.
 *
 * ── THE STALE-INDEX HAZARD, CLOSED STRUCTURALLY ─────────────────────────────
 * `model/types.ts` and the `mutations.ts` header both warn that the index must be rebuilt
 * after every mutation: the model layer has no `parent` back-pointers on purpose (they would
 * make the graph cyclic and kill structural sharing), so ancestry lives only in the derived
 * `GraphIndex`. A stale index does not throw — it silently answers the wrong ancestor.
 *
 * Rather than call `index(result.graph)` at each mutation call site — which is a rule someone
 * eventually forgets — the index is DERIVED from the graph here:
 *
 *     const idx = useMemo(() => index(graph), [graph]);
 *
 * Mutations return a new graph reference (or the same one when they no-op), so the index is
 * recomputed exactly when, and only when, the graph actually changed. There is no call site
 * that *can* forget, because there is no call site that rebuilds it.
 */

/** UI-state bag — v4's `this.state.s`, the thing `up(patch)` merges into. */
export interface UiState {
  tab: AppTab;
  /** id of the object open in the detail editor (Task 5). */
  detail: string | null;
  /** id of the tree node drilled into (Task 6). */
  focus: string | null;
  search: string;
  hideInactive: boolean;
  sideFilter: string;
  todayShape: 'schedule' | 'priority';
  menuFor: string | null;
  chipEdit: string | null;
  addOpen: boolean;
  filterOpen: boolean;

  // These three are emitted by mutations that ALREADY SHIP (mutations.ts:145 `move`,
  // :201 `move`, :406 `addChild`). They were missing here, and the `as Partial<UiState>`
  // cast in `apply()` suppressed the error — so the keys would have landed in the bag at
  // runtime as untyped extras and TypeScript would never have told Task 6 they were absent.
  // The cast is now gone; adding a mutation that returns an unknown `ui` key is a compile
  // error, which is the point. Added 2026-07-18 (review gate).
  /** id of the node being re-parented; drives `pickerPage` (Task 6). */
  moveFor: string | null;
  /** id of the node a new child is being added under (Task 6). */
  addParentFor: string | null;
  /** free-text filter inside the move/add picker (Task 6). */
  pickerFilter: string;
}

const INITIAL_UI: UiState = {
  tab: 'today',
  detail: null,
  focus: null,
  search: '',
  hideInactive: false,
  sideFilter: 'all',
  todayShape: 'schedule',
  menuFor: null,
  chipEdit: null,
  addOpen: false,
  filterOpen: false,
  moveFor: null,
  addParentFor: null,
  pickerFilter: '',
};

/** What a toast carries. `seq` makes two identical messages in a row distinguishable. */
export interface Toast {
  msg: string;
  seq: number;
}

export interface AppState {
  graph: Graph;
  /** Always in sync with `graph` — derived, never stored. */
  idx: GraphIndex;
  schema: DerivedSchema;
  plan: Plan;
  ui: UiState;
  toast: Toast | null;
  /** v4's `up(patch)` — merge a patch into the UI bag. */
  up: (patch: Partial<UiState>) => void;
  /**
   * Apply a model-layer mutation result: new graph, v4's `flash()` message, and v4's `up()`
   * patch. The index rebuild is implicit in the graph swap (see the note above).
   */
  apply: (result: MutationResult) => void;
  dismissToast: () => void;
}

/**
 * Fixtures are deep-cloned so the running app never mutates the module-level fixture objects —
 * the same reason `model.test.ts` clones them (`freshGraph()`).
 */
function initialGraph(): Graph {
  return {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
  };
}

export function useAppState(): AppState {
  const [graph, setGraph] = useState<Graph>(initialGraph);
  const [ui, setUi] = useState<UiState>(INITIAL_UI);
  const [toast, setToast] = useState<Toast | null>(null);

  const idx = useMemo(() => index(graph), [graph]);
  // The schema literal is constant for now; the backend will make it fetched (Track B).
  const schema = useMemo(() => applySchema(defaultSchema), []);

  const up = useCallback((patch: Partial<UiState>) => {
    setUi((prev) => ({ ...prev, ...patch }));
  }, []);

  const apply = useCallback((result: MutationResult) => {
    setGraph(result.graph);
    if (result.ui) setUi((prev) => ({ ...prev, ...result.ui }));
    if (result.toast) {
      const msg = result.toast;
      setToast((prev) => ({ msg, seq: (prev?.seq ?? 0) + 1 }));
    }
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  // `plan` is cloned for the same reason the graph is: Task 7 edits plan blocks directly
  // (check off an item, advance an arc step), and returning the module-level `seedPlan` by
  // reference would let the running app mutate the fixture other tests import.
  const plan = useMemo(() => structuredClone(seedPlan) as Plan, []);

  return { graph, idx, schema, plan, ui, toast, up, apply, dismissToast };
}
