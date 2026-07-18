/**
 * The slice of app state a row reads and writes.
 *
 * Declared HERE rather than imported from `shell/useAppState.ts` so the dependency runs one
 * way — shell → screens → components — and a component never reaches back up into the shell.
 * `UiState` satisfies `RowUi` structurally; if the two ever drift, `MapScreen` (which passes a
 * real `UiState` in) stops compiling, which is the intended alarm.
 */

import type { Theme } from '@tokens';
import type { Graph, GraphIndex, MutationResult } from '../../model/index.ts';

/** v4's `this.st.chipEdit` — WHICH field of WHICH row has its option strip open. */
export interface ChipEditTarget {
  id: string;
  field: string;
}

export interface RowUi {
  /** id of the object open in the detail editor. */
  detail: string | null;
  /** id of the row whose kebab menu is open. */
  menuFor: string | null;
  chipEdit: ChipEditTarget | null;
  /** id of the row a drag is currently hovering over. */
  dragOverId: string | null;
}

/**
 * What `row()` had implicitly as `this`.
 *
 * v4's `row()` is a method, so it reads `this.C`, `this.st`, `this.byId` and calls
 * `this.up` / `this.toggleDone` / `this.move` directly. Those are gathered into one object
 * rather than a dozen props, so the port reads against the original line-for-line.
 */
export interface RowCtx {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  ui: RowUi;
  /** v4's `up(patch)`. */
  up: (patch: Partial<RowUi>) => void;
  /** v4's mutate-then-`bump()`; here, the one seam mutations go through. */
  apply: (result: MutationResult) => void;
}

/**
 * v4:1173 — `this.D = (this.props.density==='Compact') ? {...} : {...}`
 *
 * The app has no density prop yet, so only v4's DEFAULT branch is reproduced. The Compact
 * branch is `{leadH:'42px', padV:'5px', title:'13.5px'}`; when a density setting lands, this
 * becomes a two-branch lookup and nothing else changes.
 */
export const D = {
  leadH: '52px',
  padV: '9px',
  title: '14.5px',
} as const;
