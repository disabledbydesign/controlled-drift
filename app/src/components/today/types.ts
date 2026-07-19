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
  /**
   * Work blocks she has checked off, KEYED BY BLOCK ID — v4's `st.chunked` Set.
   *
   * Absent means "the plan row's own `didChunkToday` decides"; an explicit `false` is her
   * un-check, which outranks the plan until the server answers. See `useAppState`'s `chunked`
   * for why the key is the id and not the `bandIndex-itemIndex` slot v4 used.
   */
  chunked: Readonly<Record<string, boolean>>;
  /** Work blocks whose arc is expanded, keyed by block id — v4's `st.blocksOpen` Set. */
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
   * Record (or un-record) a chunk of work on a block — the work-block check, in BOTH views.
   *
   * ⚠ Deliberately NOT `apply(toggleDone(...))`. A block check means "did a chunk today", never
   * "this project is finished" (`docs/display_grain_design.md` §REVISION 2026-07-14 §B), and the
   * server dispatches on that distinction. Fire-and-forget from here: the shell raises the
   * success signal only once the write is confirmed, and reports a failure itself.
   */
  chunk: (id: string, done: boolean) => void;
  /**
   * Ask the server for a new plan — `/api/refresh` or one of the stored `/api/negotiate` presets.
   *
   * ⚠ Declared with its own shape here rather than importing the shell's `GenerationRequest`,
   * following this file's one-way-dependency rule. The two are structurally identical; if they
   * drift, the mount point in `useSurface` stops compiling, which is the intended alarm.
   *
   * `label` is the button's own text, so the row can show which control is working.
   */
  regenerate: (
    req: { kind: 'refresh'; capacity?: string } | { kind: 'preset'; presetId: string },
    label: string,
  ) => void;
  /** Label of the control whose generation is running, or null. See `TodayPanel`'s action row. */
  generating: string | null;
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
