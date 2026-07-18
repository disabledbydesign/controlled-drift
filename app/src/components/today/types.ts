/**
 * The slice of app state the Today tab reads and writes.
 *
 * Declared HERE rather than imported from `shell/useAppState.ts`, following the same rule as
 * `components/panels/types.ts` and `components/rows/types.ts`: the dependency runs one way —
 * shell → screens → components — and a component never reaches back up into the shell.
 * `UiState` satisfies `TodayUi` structurally; if the two drift, the mount point stops
 * compiling, which is the intended alarm.
 */

import type { Theme } from '@tokens';
import type { Period, Plan } from '../../fixtures/index.ts';
import type { Graph, GraphIndex, MutationResult, PlanResult } from '../../model/index.ts';
import type { FocusCtx } from '../focus/types.ts';

/** v4:63 — `this.PANEL='.16s ease'`. Duplicated for the same one-way-dependency reason. */
export const PANEL = '.16s ease';

export interface TodayUi {
  /** Which of the two plan shapes is showing — v4's `st.todayShape` (997). */
  todayShape: 'schedule' | 'priority';
  /** Whether the focus-period slot is expanded — v4's `st.focusExpanded`. */
  focusExpanded: boolean;
  /** Plan-entry keys whose held-back list is open — v4's `st.heldOpen` Set. */
  heldOpen: Readonly<Record<string, true>>;
  /** Plan-entry keys of work blocks checked off — v4's `st.chunked` Set. */
  chunked: Readonly<Record<string, true>>;
  /** Plan-entry keys of work blocks whose arc is expanded — v4's `st.blocksOpen` Set. */
  blocksOpen: Readonly<Record<string, true>>;
  /** User reorder of the Priority list, or null for generator order — v4's `st.priOrder`. */
  priOrder: string[] | null;
  /** The "tell me what you need" box — v4's `st.ask`. */
  ask: string;
}

/** What v4's Today methods had implicitly as `this`. */
export interface TodayCtx {
  T: Theme;
  /** Needed by the pure mutations, which take a graph and return a new one. */
  graph: Graph;
  idx: GraphIndex;
  plan: Plan;
  periods: readonly Period[];
  ui: TodayUi;
  /** v4's `up(patch)`, narrowed to the fields Today owns. */
  up: (patch: Partial<TodayUi>) => void;
  /** Graph mutations (checking a task off) — v4's mutate-then-`bump()`. */
  apply: (result: MutationResult) => void;
  /** Plan mutations (advancing an arc step). See `model/plan.ts` on why this is separate. */
  applyPlan: (result: PlanResult) => void;
  /** v4's `flash(msg)` — a toast with no state change behind it. */
  flash: (msg: string) => void;
  /**
   * v4's `up({detail:id,_returnFrom:'today'})`, as one callback.
   *
   * Expressed as a callback rather than through `up` because `detail` and `returnFrom` are
   * shell-wide fields, not Today's — widening `TodayUi` to carry them would let any Today
   * component write shell routing state.
   */
  openDetail: (id: string) => void;
  /** v4's `up({appTab:'map'})` / `up({appTab:'add'})`. Same reasoning as `openDetail`. */
  goTab: (tab: 'map' | 'add') => void;
  /**
   * The focus-period context (Task 9). `FocusSlot`'s expanded body is v4's `focusPanel()`
   * (v4:1021), which needs `periods`, `applyPeriods` and the `__focus__` detail route —
   * none of which belong in `TodayUi`. Nested as its own context rather than flattened, for
   * the same one-way-dependency reason the whole file exists.
   */
  focus: FocusCtx;
}
