/**
 * The slice of app state the structure panels read and write.
 *
 * Declared HERE rather than imported from `shell/useAppState.ts`, for the same reason
 * `components/rows/types.ts` and `components/detail/types.ts` do it: the dependency runs one
 * way — shell → screens → components — and a component never reaches back up into the shell.
 * `UiState` satisfies `PanelUi` structurally; if the two drift, the mount points stop
 * compiling, which is the intended alarm.
 */

import type { Theme } from '@tokens';
import type { DerivedSchema, Graph, GraphIndex, MutationResult } from '../../model/index.ts';

/**
 * v4's `this.st.chipEdit` — WHICH field of WHICH row has its option strip open.
 *
 * Defined here rather than in `rows/types.ts` (where it used to live) so the dependency runs
 * one way: `rows` → `panels`. `Row` renders `ChipStrip`, so it needs the panel
 * context; if `panels` also reached back into `rows` the two type modules would import each
 * other. `rows/types.ts` re-exports this name, so no import elsewhere changes.
 */
export interface ChipEditTarget {
  id: string;
  field: string;
}

/** v4:63 — `this.PANEL='.16s ease'`. The entry timing for every drop-down / filter block. */
export const PANEL = '.16s ease';

/** v4:61 — `this.NAV`. Duplicated from `shell/tabs.ts` so the panels do not import the shell. */
export const NAV = '.26s cubic-bezier(.4,0,.2,1)';

/**
 * v4:73 — `this.FLABEL`. The heading shown above a chip's option list.
 * Note `when` reads "Applies when", not "When": the chip says `when: Always`, the strip
 * has room for the full field name.
 */
export const FLABEL: Readonly<Record<string, string>> = {
  engagement: 'Engagement',
  status: 'Status',
  side: 'Side',
  horizon: 'Horizon',
  when: 'Applies when',
  unit: 'Frequency',
};

export interface PanelUi {
  /** v4's `st.search` — the per-tab `Filter by title…` box in `mapControls`. */
  search: string;
  hideInactive: boolean;
  /** 'all' or one of `OPTS.side`. */
  sideFilter: string;
  filterOpen: boolean;
  addOpen: boolean;
  /** Which node the Map is drilled into — v4's `st.focus`. */
  focus: string | null;
  detail: string | null;
  menuFor: string | null;
  chipEdit: ChipEditTarget | null;
  /** id of the node being re-parented. */
  moveFor: string | null;
  /** The TYPE being added ('Goal' | 'Project' | …), not an id — v4 stores the type here. */
  addParentFor: string | null;
  pickerFilter: string;
  pickerExpanded: Readonly<Record<string, boolean>>;
  confirmDelete: string | null;
  /** id of the row a drag is currently hovering over — read by `Row`'s drop-target branch. */
  dragOverId: string | null;
  /**
   * Which GROUPING HEADERS are collapsed on the Routines tab — v4's `st.collapsed` (78),
   * toggled by `toggleCollapse` (676). Absent id = expanded.
   *
   * ⚠ Not the Map. v4's Map is a drill-in and never collapses anything; the ids in here are
   * the parent projects `recurringBody` groups under.
   */
  collapsed: Readonly<Record<string, true>>;
  /**
   * Which ids the DESKTOP Finder browser is drilled into — v4's `st.deskPath` (Task 10).
   *
   * The panels read it in exactly one place: `addContextParent` (v4:372), whose `_wide` branch
   * asks "what am I currently inside?" of the desktop column path instead of the phone's
   * `focus`. It is on `PanelUi` rather than passed to that one function so the wide and phone
   * branches read from the same bag, as they do in v4.
   */
  deskPath: readonly string[];
  /** Routines cadence filter — v4's `st.recFilter`. */
  recFilter: 'all' | 'asneeded' | 'scheduled';
  /** Strategies "When" filter: 'all' or one of `OPTS.strategyState`. v4's `st.stratWhen`. */
  stratWhen: string;
  /** Strategies status filter: 'all' or 'active'. v4's `st.stratStatus`. */
  stratStatus: string;
  /** Whether the Strategies tab's own filter block is open — v4's `st.stratFilterOpen`. */
  stratFilterOpen: boolean;
}

/** What v4's panel methods had implicitly as `this`. */
export interface PanelCtx {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  schema: DerivedSchema;
  ui: PanelUi;
  /** v4's `up(patch)`. */
  up: (patch: Partial<PanelUi>) => void;
  /** v4's mutate-then-`bump()`; here, the one seam mutations go through. */
  apply: (result: MutationResult) => void;
  /**
   * v4's `this._wide` — true only inside `deskApp()` (v4:730), false in `renderShell()` (929)
   * and `structurePanel()` (959).
   *
   * v4 reads it in three places, all of them LAYOUT, never behaviour: `addContextParent` (372)
   * picks its default parent from `deskPath` instead of `focus`, `detail()` (587) swaps the
   * "‹ Back" text button for the bordered "✕ Close" pill, and `pickerPage()` (626) becomes a
   * centred modal over a scrim instead of a full-bleed slide-in.
   *
   * It is a prop, not a fork: the same components render on both paths. `DetailCtx` already
   * carries the same flag for the same reason.
   */
  wide?: boolean;
}
