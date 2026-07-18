/**
 * The slice of app state the detail editor reads and writes.
 *
 * Declared HERE rather than imported from `shell/useAppState.ts`, for the same reason
 * `components/rows/types.ts` does it: the dependency runs one way — shell → screens →
 * components — and a component never reaches back up into the shell. `UiState` satisfies
 * `DetailUi` structurally; if the two drift, the mount point stops compiling, which is the
 * intended alarm.
 */

import type { Theme } from '@tokens';
import type { ChipEditTarget } from '../rows/index.ts';
import type {
  DerivedSchema,
  Graph,
  GraphIndex,
  MutationResult,
} from '../../model/index.ts';

export interface DetailUi {
  /** id of the object open in the editor — v4's `st.detail`. */
  detail: string | null;
  /** v4's `st.moveFor` — set when the location block is tapped (picker is Task 6). */
  moveFor: string | null;
  menuFor: string | null;
  chipEdit: ChipEditTarget | null;
  pickerFilter: string;
  /**
   * v4's `st._returnFrom` (set at 1035/1043/1051/1081/1123, read at 587). Which tab sent the
   * user here, so the back button can say "Today" / "Add" instead of "Back". Only Today and
   * Add set it (Tasks 7 and 8); every other route leaves it null and the label is "Back".
   */
  returnFrom: 'today' | 'add' | null;
}

/**
 * What v4's `detail()` had implicitly as `this`.
 *
 * v4's detail methods read `this.C`, `this.st`, `this.OPTS/CTRL/TEXT`, `this.byId` and call
 * `this.setVal` / `this.setTitle` / `this.toggleDone` / `this.setType` / `this.del` directly.
 * Gathered into one object rather than a dozen props so the port reads against the original.
 */
export interface DetailCtx {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  schema: DerivedSchema;
  ui: DetailUi;
  /** v4's `up(patch)`. */
  up: (patch: Partial<DetailUi>) => void;
  /** v4's mutate-then-`bump()`; here, the one seam mutations go through. */
  apply: (result: MutationResult) => void;
  /**
   * v4's `flash(msg)` with NO model mutation behind it. Used at exactly two sites in
   * `detail()`: the title textarea's `onBlur` (587) and each note textarea's `onBlur` (596).
   * Both fire after `setTitle`/`setVal` have already run per keystroke, so there is nothing
   * left to write — the flash is the only effect.
   */
  flash: (msg: string) => void;
  /**
   * v4's `this._wide` — true only inside `deskApp()` (v4:730). It swaps the phone's
   * "‹ Back" affordance for `paneCloseBtn()`. The desktop shell is Task 10, so nothing in
   * the running app passes this yet; the branch is ported and exercised by tests.
   */
  wide?: boolean;
}
