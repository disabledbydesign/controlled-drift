import { useEffect } from 'react';
import type { Theme, ThemeName } from '@tokens';
import type { DetailCtx } from '../components/detail/index.ts';
import type { FocusCtx } from '../components/focus/index.ts';
import type { PanelCtx } from '../components/panels/index.ts';
import type { TodayCtx } from '../components/today/index.ts';
import type { AddCtx, SettingsCtx } from '../screens/index.ts';
import type { AppTab } from './tabs.ts';
import { present } from './signals.ts';
import { useAppState } from './useAppState.ts';
import type { AppState, DataSource } from './useAppState.ts';

/**
 * The five context objects every screen reads — v4's `this`, sliced per consumer — built ONCE
 * and shared by both render paths.
 *
 * ── why this exists (Task 10) ───────────────────────────────────────────────
 * The desktop path is a SECOND LAYOUT OVER THE SAME COMPONENT LIBRARY, not a second app. v4
 * makes that structural: `renderShell()` (929) and `deskApp()` (730) both read `st.appTab` and
 * both call the same `row()`, `detail()`, `todayPanel()`, `recurringBody()` — they are methods
 * on one component, so there is exactly one `this` and it cannot fork.
 *
 * Here the two shells are two components, so that single `this` has to be made explicit or it
 * becomes two copies that drift. Every context below was lifted VERBATIM out of `AppShell`;
 * the phone path is unchanged, it just no longer owns the definitions.
 *
 * `wide` is the only input that differs between the paths, and it reaches exactly the three
 * places v4's `_wide` reaches — see `PanelCtx.wide`. Everything else is identical by
 * construction rather than by matching maintenance.
 */
export interface Surface {
  st: AppState;
  tab: AppTab;
  goTab: (next: AppTab) => void;
  detailCtx: DetailCtx;
  panelCtx: PanelCtx;
  focusCtx: FocusCtx;
  todayCtx: TodayCtx;
  settingsCtx: SettingsCtx;
  addCtx: AddCtx;
}

export interface SurfaceOptions {
  T: Theme;
  name: ThemeName;
  setTheme: (n: ThemeName) => void;
  /** v4's `this._wide` — true for `deskApp()`, false for `renderShell()`. */
  wide: boolean;
  /**
   * Where the data comes from. Defaults to the real endpoints; the component tests pass
   * `'fixtures'` so they keep asserting against known content. See `DataSource`.
   */
  source?: DataSource;
}

export function useSurface({ T, name, setTheme, wide, source }: SurfaceOptions): Surface {
  const st = useAppState(source);
  const tab = st.ui.tab;
  const { up } = st;

  // v4:954 (phone) and v4:735 (desktop `dtab`) clear the SAME transient UI on every tab
  // change, so a menu or panel left open on one tab does not reappear over another. As an
  // effect keyed on `tab` it fires however the tab changed — and it now covers both paths,
  // which is why it lives here rather than in either shell.
  useEffect(() => {
    up({ detail: null, menuFor: null, chipEdit: null, addOpen: false, filterOpen: false });
  }, [tab, up]);

  const goTab = (next: AppTab) => {
    if (next === tab) return;
    up({ tab: next });
  };

  /**
   * THE ONE PLACE the presentation policy is consulted for the in-place success signal.
   *
   * `present()` (shell/signals.ts) decides whether a success shows anything and in what form.
   * If it says `inline`, the affected row is named here and `Row` settles it; if it says
   * anything else, this is null and no component below ever learns a success occurred. So
   * changing or removing success feedback is an edit to `present()` — not a change here, and
   * not a hunt through components.
   */
  const confirmed =
    st.toast && st.toast.kind === 'success' && st.toast.nodeId && present(st.toast).mode === 'inline'
      ? { id: st.toast.nodeId, seq: st.toast.seq }
      : null;

  /**
   * v4's `detail()` context.
   *
   * ⚠ `flash` is v4's `flash(msg)` with no model change behind it, and the claim that used to
   * sit beside it here — "the blur has nothing left to persist" — was FALSE for the title. That
   * write is on a 600ms debounce, so blur could arrive before the request. Blur now goes to
   * `finishedEditing`, which flushes the pending write and speaks only once the server answers.
   * `flash` remains for messages with genuinely nothing behind them.
   */
  const detailCtx: DetailCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    schema: st.schema,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
    finishedEditing: (id: string) => st.finishedEditing(id),
    // v4:587 — the desktop detail pane closes with a bordered "✕ Close" pill, the phone with
    // a "‹ Back" text button.
    wide,
  };

  /**
   * The context the three structure tabs, their panels and every `Row` share — v4's `this`,
   * minus the parts only `detail()` reads. `UiState` satisfies `PanelUi` structurally; if the
   * two drift, this line stops compiling, which is the intended alarm.
   */
  const panelCtx: PanelCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    schema: st.schema,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    fail: st.fail,
    confirmed,
    wide,
  };

  /**
   * v4's `this` as the focus-period methods read it.
   *
   * ⚠ `closeEditor` is v4's Back (888) and v4's post-save reset (926), which are the SAME
   * patch. It discards `focusReflect` without saving. That is `ux_consistency_review` #4 and
   * it is preserved deliberately — see `components/focus/types.ts`.
   */
  const focusCtx: FocusCtx = {
    T,
    graph: st.graph,
    periods: st.periods,
    ui: st.ui,
    up: st.up,
    // ⚠ DEAD PLUMBING — nothing produces a `PeriodResult`; the period write goes through
    // `saveFocusPeriod`. See the note on `AppState.applyPeriods`.
    applyPeriods: st.applyPeriods,
    authorFocus: st.authorFocus,
    saveFocusPeriod: st.saveFocusPeriod,
    openEditor: (view, editId, reflect) =>
      st.up({
        detail: '__focus__',
        focusView: view,
        focusEditId: editId,
        focusReflect: reflect,
        // v4:836 clears the draft when opening the author flow and leaves it alone on edit.
        ...(view === 'author' ? { focusDraft: '' } : null),
      }),
    closeEditor: () =>
      st.up({
        detail: null,
        focusView: 'list',
        focusEditId: null,
        focusReflect: null,
        focusDraft: '',
      }),
  };

  /**
   * v4's `this` as the Today methods read it.
   *
   * `openDetail` and `goTab` are callbacks rather than `up` fields on purpose: `detail`,
   * `returnFrom` and `tab` are shell-wide routing state, and putting them in `TodayUi` would
   * let any component in the tab write them. See `components/today/types.ts`.
   */
  const todayCtx: TodayCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    plan: st.plan,
    periods: st.periods,
    focus: focusCtx,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    applyPlan: st.applyPlan,
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
    // The work-block check. `void` for the same reason as `regenerate`: every outcome reports
    // itself through `succeed`/`fail` inside `chunkBlock`, so the row has nothing to await.
    chunk: (id, done) => void st.chunkBlock(id, done),
    // The arc STEP check, one level inside a block. Same fire-and-forget reasoning as `chunk`,
    // and deliberately a different writer: a step completes a real task, a block records a chunk.
    completeStep: (ref, done) => void st.completeArcStep(ref, done),
    // The action row's generation controls. The ROW's handlers are still fire-and-forget —
    // every outcome reports itself through `succeed`/`fail` inside `regenerate`. The promise is
    // passed through undiluted for the ONE caller that needs the answer: the ask box, which holds
    // text she wrote and may only clear it on a generation that actually happened.
    regenerate: (req, label) => st.regenerate(req, label),
    generating: st.generating,
    // Her plan-action buttons, from her own actions.json — see TodayCtx.presets.
    presets: st.presets,
    openDetail: (id: string) => st.up({ detail: id, returnFrom: 'today' }),
    goTab: (t) => goTab(t),
    // The three per-row plan writes. Fire-and-forget for the same reason as `chunk`: each one
    // reports every outcome through `succeed`/`fail` itself, so the row has nothing to await and
    // no second place to get the reporting wrong.
    wide,
    notToday: (id, kind) => void st.notTodayRow(id, kind),
    setDuration: (id, minutes) => void st.setRowDuration(id, minutes),
    moveItem: (id, target) => void st.moveRow(id, target),
  };

  /**
   * v4's `this` as `captureTab()` / `logTab()` read it. `openDetail` mirrors Today's: v4 writes
   * `up({detail:r.id,_returnFrom:'add'})` from the receipt's edit button (v4:1121), and
   * `returnFrom` makes the detail pane's back button say "Add".
   */
  const addCtx: AddCtx = {
    T,
    graph: st.graph,
    idx: st.idx,
    ui: st.ui,
    up: st.up,
    apply: st.apply,
    openDetail: (id: string) => st.up({ detail: id, returnFrom: 'add' }),
    flash: (msg: string) => st.apply({ graph: st.graph, toast: msg, ui: null, node: null }),
    logDay: st.logDay,
    // The real weeder, replacing the v4 mock the tab shipped with.
    captureEntries: st.captureEntries,
    captureSummary: st.captureSummary,
    loadCapture: st.loadCapture,
    runCapture: st.runCapture,
    undoCapture: st.undoCapture,
    setCapturedWhen: st.setCapturedWhen,
    setCapturedEngagement: st.setCapturedEngagement,
    // The Add tab's "Regenerate today" holds no text of hers, so it has nothing to decide from
    // the answer — the result is dropped here rather than widening `AddCtx` for a value that tab
    // does not read. The generation still reports itself through `succeed`/`fail`.
    regenerate: async (req, label) => {
      await st.regenerate(req, label);
    },
    busy: st.generating,
  };

  /**
   * Settings reads the UI bag for the backend choice and the plan-content toggle, takes the real
   * backend LIST from the server (`st.backendOptions` — never hardcoded, see `SettingsScreen`),
   * writes through `st.saveSettings` rather than the plain `up` (a Settings change must reach
   * `POST /api/settings`, not just the in-memory bag), and takes the THEME from the single
   * `useTheme()` in `App.tsx`, passed down as props. That one call site is what keeps one theme
   * for the whole surface.
   */
  const settingsCtx: SettingsCtx = {
    T,
    name,
    setTheme,
    ui: st.ui,
    options: st.backendOptions,
    save: st.saveSettings,
  };

  return { st, tab, goTab, detailCtx, panelCtx, focusCtx, todayCtx, settingsCtx, addCtx };
}
