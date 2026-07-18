/**
 * The slice of app state the focus-period editor reads and writes.
 *
 * Declared HERE rather than imported from `shell/useAppState.ts`, following the same rule as
 * `components/today/types.ts` and `components/panels/types.ts`: the dependency runs one way —
 * shell → screens → components — and a component never reaches back up into the shell.
 * `UiState` satisfies `FocusUi` structurally; if the two drift, the mount point in `AppShell`
 * stops compiling, which is the intended alarm.
 */

import type { Theme } from '@tokens';
import type { Period } from '../../fixtures/index.ts';
import type { FocusForm, Graph, PeriodResult } from '../../model/index.ts';

/** v4:61 — `this.NAV`. Duplicated for the same one-way-dependency reason. */
export const NAV = '.26s cubic-bezier(.4,0,.2,1)';

/**
 * v4's `st.focusView` (79). Only ONE site reads it — `focusDetail` (813), as
 * `st.focusView==='author'?'author':'edit'` — so 'list' means "the editor is not open" and
 * the value the slot shows is `focusPanel`, which renders regardless of this field.
 */
export type FocusView = 'list' | 'edit' | 'author';

export interface FocusUi {
  focusView: FocusView;
  /** id of the period being edited — v4's `st.focusEditId`, read by `saveFocus` (924). */
  focusEditId: string | null;
  /** The live edit form — v4's `st.focusReflect`. null = the author flow's first screen. */
  focusReflect: FocusForm | null;
  /** The author flow's free-text box — v4's `st.focusDraft`. */
  focusDraft: string;
  /** The un-added date in the days-off editor — v4's `st.focusNewOff` (869-870). */
  focusNewOff: string;
  /** Search box of the Foreground picker — v4's `st['focusPick_front']` (877). */
  focusPickFront: string;
  /** Search box of the Paused picker — v4's `st['focusPick_paused']` (877). */
  focusPickPaused: string;
}

/** What v4's focus methods had implicitly as `this`. */
export interface FocusCtx {
  T: Theme;
  /** v4's `this.data` — the goal roots the project pickers group by (876-878). */
  graph: Graph;
  periods: readonly Period[];
  ui: FocusUi;
  /** v4's `up(patch)`, narrowed to the fields the focus editor owns. */
  up: (patch: Partial<FocusUi>) => void;
  /** Period mutations — v4's in-place write + `bump()`. See `model/periods.ts`. */
  applyPeriods: (result: PeriodResult) => void;
  /**
   * v4's `up({detail:'__focus__', focusView:…, focusEditId:…, focusReflect:…})` (816, 836).
   *
   * A callback rather than a `FocusUi` field because `detail` is shell-wide routing state;
   * widening `FocusUi` to carry it would let any component in here write the detail route.
   * Same reasoning as `TodayCtx.openDetail`.
   */
  openEditor: (view: 'edit' | 'author', editId: string | null, reflect: FocusForm | null) => void;
  /**
   * v4's Back / post-save reset (888, 926):
   * `up({detail:null,focusView:'list',focusEditId:null,focusReflect:null,focusDraft:'',focusEditField:null})`.
   *
   * ⚠ PORTED AS-IS AND FLAGGED, NOT FIXED. `docs/ux_consistency_review_2026-07-17.md`
   * finding #4: Back DISCARDS the whole focus draft silently, while every other editor in
   * this surface (the item detail pane) commits per keystroke. That inconsistency is real and
   * it is June's call post-port — the plan's Task 9 says "port v4's behavior as-is; do not
   * fix." Nothing here warns, confirms, or saves on the way out, exactly as v4 does not.
   */
  closeEditor: () => void;
}
