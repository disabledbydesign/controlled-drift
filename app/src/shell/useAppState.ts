import { useCallback, useMemo, useState } from 'react';
import { defaultSchema, seed, seedPlan, seedStrategies } from '../fixtures/index.ts';
import type { Plan } from '../fixtures/index.ts';
import { applySchema, index } from '../model/index.ts';
import type {
  DerivedSchema,
  Graph,
  GraphIndex,
  MutationResult,
  PlanResult,
} from '../model/index.ts';
import type { ChipEditTarget } from '../components/rows/index.ts';
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
  /**
   * WHICH field of WHICH row has its option strip open.
   *
   * ⚠ Type CORRECTED 2026-07-18 (Task 4). This was `string | null`, but v4 stores an object:
   * `up({chipEdit:{id:n.id,field:chip.field}})` at row() 438, read back as
   * `st.chipEdit.id===n.id` (row 437) and `this.st.chipEdit.field` (chipStrip 464). A bare id
   * cannot say WHICH chip on the row was tapped, and a row carries up to two. Every existing
   * assignment in this repo is `chipEdit: null`, so widening the type breaks nothing.
   */
  chipEdit: ChipEditTarget | null;
  addOpen: boolean;
  filterOpen: boolean;
  /**
   * id of the row a drag is currently hovering over — v4's `st.dragOverId`, read by row()'s
   * drop-target branch (440-446). v4 never declares it in the initial state bag; it appears
   * only via `up()`. Declared here because the bag is strictly typed.
   */
  dragOverId: string | null;
  /**
   * Which nodes are COLLAPSED — v4's `st.collapsed` (78), toggled by `toggleCollapse` (676).
   * Absent id = expanded, so the tree opens expanded and the map stays small.
   */
  collapsed: Readonly<Record<string, true>>;

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
  /**
   * Which destination rows are expanded inside the move/add picker — v4's `st.pickerExpanded`
   * (read at v4:609, written at v4:611, cleared by the picker's Cancel at v4:616). Absent id =
   * collapsed, so the picker opens showing only the top level. v4 never declares it in the
   * initial bag; it appears only via `up()`.
   */
  pickerExpanded: Readonly<Record<string, boolean>>;

  // ── per-tab filter state (Task 6) ───────────────────────────────────────────
  // v4 declares `recFilter:'all'` in its initial bag (v4:78) but NOT the three `strat*` keys,
  // which appear only via `up()` and are read with `||` defaults (v4:651). Declared here
  // because the bag is strictly typed; the defaults below are v4's own fallbacks.
  /** Routines cadence filter — v4's `st.recFilter`. */
  recFilter: 'all' | 'asneeded' | 'scheduled';
  /** Strategies "When" filter: 'all' or one of `OPTS.strategyState`. v4's `st.stratWhen`. */
  stratWhen: string;
  /** Strategies status filter: 'all' or 'active'. v4's `st.stratStatus`. */
  stratStatus: string;
  /** Whether the Strategies tab's own filter block is open — v4's `st.stratFilterOpen`. */
  stratFilterOpen: boolean;
  /**
   * Row whose Delete button is armed for a second tap — v4's `st.confirmDelete`, set by
   * `askDelete` (v4:476) and auto-cleared after 3s. Read by `menuStrip` (v4:477) only.
   */
  confirmDelete: string | null;

  /**
   * v4's `st._returnFrom` — which tab sent the user into the detail editor, so its back
   * button can say "Today" / "Add" instead of "Back" (v4 sets it at 1035, 1043, 1051, 1081
   * and 1123; reads it at 587). Added 2026-07-18 with Task 5: the detail pane reads it and
   * there is no other home for cross-tab origin. Today (Task 7) and Add (Task 8) are the only
   * writers; every other route leaves it null and the label falls back to "Back".
   */
  returnFrom: 'today' | 'add' | null;

  // ── Today tab (Task 7) ──────────────────────────────────────────────────────
  // v4 declares `focusExpanded:false`, `todayShape:'schedule'`, `priOrder:null`,
  // `blocksOpen:new Set()` in its initial bag (v4:79); `heldOpen`, `chunked` and `ask` appear
  // only via `up()`/`tset()` and are read with `||new Set()` / `||''` fallbacks. All are
  // declared here because the bag is strictly typed, with v4's own fallbacks as defaults.
  //
  // v4's three membership sets are `Set` objects mutated through `tset(name,key)`. They are
  // readonly records here for the same reason `collapsed` and `pickerExpanded` already are:
  // `up()` merges into immutable state, and a `Set` mutated in place would not change
  // reference, so React would not re-render.
  /** Whether the focus-period slot at the top of Today is expanded. v4's `st.focusExpanded`. */
  focusExpanded: boolean;
  /** Which plan rows have their held-back list expanded, keyed by plan-entry key. */
  heldOpen: Readonly<Record<string, true>>;
  /** Which work blocks are checked off. v4's `st.chunked` — see `WorkBlock` on the naming. */
  chunked: Readonly<Record<string, true>>;
  /** Which work blocks have their arc expanded. v4's `st.blocksOpen`. */
  blocksOpen: Readonly<Record<string, true>>;
  /**
   * User-reordered Priority ranking, or null for generator order. v4's `st.priOrder`.
   * ⚠ Spec §14 leaves the backend source-of-truth for this ordering OPEN; this is v4's
   * client-local reorder, unchanged, and nothing persists it.
   */
  priOrder: string[] | null;
  /** Free-text "tell me what you need" box under Today's action row. v4's `st.ask`. */
  ask: string;

  // ── Add / Log tab + Settings (Task 8) ───────────────────────────────────────
  // None of these six appear in v4's initial bag (v4:79). Every one is written only via
  // `up()` and read with a `||` / `!==false` fallback, exactly like `stratWhen` above.
  // Declared here with v4's own fallbacks as the defaults, because the bag is strictly typed.
  /** The capture textarea. v4's `st.addText`, read by `capture()` (v4:1136). */
  addText: string;
  /** The log textarea. v4's `st.logText`. */
  logText: string;
  /**
   * Which log tag is selected — v4's `st.logTag`, one of the two literal strings v4 hardcodes
   * at 1130. Default 'The day' is v4's `st.logTag||'The day'`.
   */
  logTag: LogTag;
  /** Which model backend writes plans. v4's `st.backend||'claude'` (v4:1152). */
  backend: BackendId;
  /**
   * Whether the daily plan includes creative/hobby work. v4's `st.hobby!==false` (v4:1156) —
   * i.e. ON unless explicitly set false, which is why the default here is `true`.
   */
  hobby: boolean;
  /**
   * "Added this session" — what capture has filed, newest first.
   *
   * ⚠ DIVERGENCE FROM v4, deliberate. v4 holds this on the instance (`this.receipt=[]`,
   * v4:80) rather than in the `up()` bag, because it mutates instance fields freely and calls
   * `bump()`. Immutable React state has no equivalent of that, and the receipt has to survive
   * a tab switch, so it lives in the bag — the one piece of state here that is a LIST rather
   * than a control value. Nothing else about it changes: same entry shape, same newest-first
   * prepend (v4:1140).
   */
  receipt: readonly ReceiptEntry[];
}

/** v4's two literal log tags (v4:1130). Not schema-driven in v4 — hardcoded in the render. */
export type LogTag = 'The day' | 'Friction';

/** v4's three backend option ids (v4:1161-1163). */
export type BackendId = 'claude' | 'local' | 'api';

/** One "added this session" row — v4's `{id,text,project}` (v4:1140). */
export interface ReceiptEntry {
  /** id of the created task, so the row's "edit" button can open it in the detail editor. */
  id: string;
  /** The captured text, verbatim. */
  text: string;
  /** Title of the project it was filed under. */
  project: string;
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
  dragOverId: null,
  collapsed: {},
  moveFor: null,
  addParentFor: null,
  pickerFilter: '',
  pickerExpanded: {},
  recFilter: 'all',
  stratWhen: 'all',
  stratStatus: 'all',
  stratFilterOpen: false,
  confirmDelete: null,
  returnFrom: null,
  focusExpanded: false,
  heldOpen: {},
  chunked: {},
  blocksOpen: {},
  priOrder: null,
  ask: '',
  addText: '',
  logText: '',
  logTag: 'The day',
  backend: 'claude',
  hobby: true,
  receipt: [],
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
  /**
   * Apply a PLAN mutation (Task 7). The plan is not part of the graph — it references graph
   * nodes by id — so it gets its own seam rather than being forced through `apply`. Same
   * shape: new value in, toast raised the same way. See `model/plan.ts`.
   */
  applyPlan: (result: PlanResult) => void;
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

/**
 * The plan is cloned for the same reason the graph is: Task 7 edits the plan document
 * directly (advance an arc step), and holding the module-level `seedPlan` by reference would
 * let the running app mutate the fixture other tests import.
 */
function initialPlan(): Plan {
  return structuredClone(seedPlan) as Plan;
}

export function useAppState(): AppState {
  const [graph, setGraph] = useState<Graph>(initialGraph);
  const [plan, setPlan] = useState<Plan>(initialPlan);
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

  const applyPlan = useCallback((result: PlanResult) => {
    setPlan(result.plan);
    if (result.toast) {
      const msg = result.toast;
      setToast((prev) => ({ msg, seq: (prev?.seq ?? 0) + 1 }));
    }
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  return { graph, idx, schema, plan, ui, toast, up, apply, applyPlan, dismissToast };
}
