/**
 * The slice of app state a row reads and writes.
 *
 * ── CHANGED IN TASK 6 ────────────────────────────────────────────────────────
 * `RowUi` and `RowCtx` used to be their own declarations, structurally satisfied by the
 * shell's `UiState`. They are now ALIASES of the panel types, because Task 6 makes `Row`
 * render `ChipStrip` — so a row genuinely needs the panel context, including
 * `schema` (the chip strip's option lists are schema-derived) and the picker/filter fields.
 *
 * Two separate declarations that have to stay identical is exactly the drift trap this
 * codebase keeps closing structurally elsewhere (see the stale-index note in
 * `shell/useAppState.ts`). One declaration under two names cannot drift.
 *
 * The dependency still runs one way — shell → screens → components, and inside components
 * `rows` → `panels`, never back. `UiState` satisfies `PanelUi` structurally; if the two drift,
 * `AppShell` stops compiling, which is the intended alarm.
 */

import type { PanelCtx, PanelUi } from '../panels/types.ts';

export type { ChipEditTarget } from '../panels/types.ts';

/** @see PanelUi — one declaration, two names, so they cannot fall out of step. */
export type RowUi = PanelUi;

/**
 * What `row()` had implicitly as `this`.
 *
 * v4's `row()` is a method, so it reads `this.C`, `this.st`, `this.byId` and calls
 * `this.up` / `this.toggleDone` / `this.move` directly. Those are gathered into one object
 * rather than a dozen props, so the port reads against the original line-for-line.
 */
export type RowCtx = PanelCtx;

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
