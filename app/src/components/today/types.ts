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
import type { ArcStepRef, Graph, GraphIndex, MutationResult, PlanResult } from '../../model/index.ts';
import type { FocusCtx } from '../focus/types.ts';
import type { MoveTarget } from '../../api/planRow.ts';

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
  /**
   * Which rows have their action panel open, KEYED BY ITEM ID — v4's declared `st.editOpen`.
   *
   * ⚠ v4 declares `editOpen: new Set()` in its Today state and never reads it anywhere (grepped:
   * one occurrence, the declaration). So the mockup ANTICIPATED a per-row reveal on Today and
   * left it unbuilt — the name is v4's, the rendering is not a transcription of it. What the
   * treatment IS derived from is the old overlay, which put all three of these controls behind
   * one per-row reveal for a recorded reason: June found separate always-visible chips "messy"
   * (`docs/overlay_daily.html`, `editChipHtml` ~2113).
   *
   * Keyed by id, not by slot, for the reason `chunked` and `blocksOpen` already are: a
   * regenerated plan reassigns slots, so a positional key reattaches to the wrong row.
   */
  editOpen: Readonly<Record<string, true>>;
  /**
   * The item whose move-destination list is showing, or null — the Map picker's `moveFor`, which
   * is likewise a node id rather than an index.
   *
   * One at a time, deliberately: the old overlay collapsed every other affordance during
   * placement ("one thing at a time"), and a single nullable field cannot represent two open
   * pickers even by accident.
   */
  movePick: string | null;
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
  /**
   * Plan mutations. See `model/plan.ts` on why this is separate from `apply`.
   *
   * ⚠ LOCAL ONLY — nothing reachable through here writes to the server, and it currently has no
   * caller. The arc step check used to come this way, which is why it saved nothing. Wire a new
   * plan control to its own shell writer (`completeStep` is the model), not to this.
   */
  applyPlan: (result: PlanResult) => void;
  /**
   * Check off (or reopen) one STEP inside a work block's arc, in BOTH views.
   *
   * ⚠ Not the same control as `chunk`, one level up. A step carries a real Anytype task id and
   * completing it completes that task; a block check only records a chunk of work. Fire-and-
   * forget from here for the same reason as `chunk`: the shell raises the success signal only
   * once the write is confirmed, and reports a failure itself.
   */
  completeStep: (ref: ArcStepRef, done: boolean) => void;
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
   *
   * The third variant carries the free text from the "tell me what you need" box —
   * `/api/negotiate` takes either a stored preset or a message, on one endpoint and one wait.
   *
   * ⚠ Resolves `true` ONLY once a new plan has been generated AND read back. The ask box holds
   * words she wrote and clears itself on that answer alone; every `false` has already told her it
   * did not send. A `void` return here is what would make deleting her text on a dropped request
   * possible, so the promise is the point.
   */
  regenerate: (
    req:
      | { kind: 'refresh'; capacity?: string }
      | { kind: 'preset'; presetId: string }
      | { kind: 'message'; message: string },
    label: string,
  ) => Promise<boolean>;
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
   * Take this row off TODAY'S list — `POST /api/task/not-today`.
   *
   * `kind` is what the server dispatches on: `'block'` takes the id as a PROJECT id and drops
   * every row of that block, `'task'` drops the one row.
   *
   * ⚠ CACHE-ONLY BY DESIGN, and it must stay that way. No Anytype write, no status change, no
   * reschedule: the item returns tomorrow with the status it had, and stays off a same-day
   * regenerate for an 8h window. June asked for exactly that — it holds for the day and does not
   * leak into future days. Do not "fix" this into a durable field.
   */
  notToday: (id: string, kind: 'task' | 'block') => void;
  /**
   * Set how long this takes — `POST /api/duration`.
   *
   * ⚠ ONE endpoint, TWO meanings, dispatched SERVER-side on whether the row is a block:
   *   - a BLOCK is a per-project CHUNK LENGTH — "how long I work on this in a sitting"
   *   - a TASK is that task's own duration — "how long this specific thing takes"
   * The difference is June's and is not cosmetic, so the CALLER must label it correctly; the old
   * overlay's chip read "set chunk length" on a block and "set duration" on a task for this
   * reason. Nothing here may collapse the two into one word.
   */
  setDuration: (id: string, minutes: number) => void;
  /**
   * Move this row to another position in today's plan — `POST /api/task/move`.
   *
   * Bidirectional: earlier and later both work, and the server re-flows the clock times. The
   * target comes from `moveDestinations`, which owns the index arithmetic.
   *
   * ⚠ IMPORTED, not redeclared (review finding B6). This was the third structural copy of one
   * wire contract, and three copies is three chances for an importer to take the wrong one.
   * The one-way-dependency rule this file states is about VALUES, not types: a type-only import
   * from `api/planRow` emits nothing and cannot pull the api layer into a component bundle.
   */
  moveItem: (id: string, target: MoveTarget) => void;
  /**
   * The focus-period context (Task 9). `FocusSlot`'s expanded body is v4's `focusPanel()`
   * (v4:1021), which needs `periods`, `applyPeriods` and the `__focus__` detail route —
   * none of which belong in `TodayUi`. Nested as its own context rather than flattened, for
   * the same one-way-dependency reason the whole file exists.
   */
  focus: FocusCtx;
}
