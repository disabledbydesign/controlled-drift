import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  defaultSchema,
  seed,
  seedOrphans,
  seedPeriods,
  seedPlan,
  seedStrategies,
} from '../fixtures/index.ts';
import type { Period, Plan, Schema } from '../fixtures/index.ts';
import { applySchema, index, toggleArcStep, updateNode } from '../model/index.ts';
import {
  getCaptureSession,
  getStatus,
  rescheduleCaptured,
  setCapturedEngagement,
  startCapture,
  undoCaptured,
} from '../api/capture.ts';
import type { WeedEntry, WhenToken } from '../api/capture.ts';
import { apiGet, apiSend } from '../api/client.ts';
import {
  FOCUS_POLL_MS,
  commitFocus,
  focusResult,
  focusStatus,
  startAuthor,
  updateFocus,
} from '../api/focus.ts';
// Aliased on import: the shell's own intents keep the `...Row` names declared on `AppState`, so
// the endpoint function and the state callback that wraps it stay distinguishable at every use.
import {
  moveItem as moveItemApi,
  notToday as notTodayApi,
  setDuration as setDurationApi,
} from '../api/planRow.ts';
import {
  graphFromTree,
  periodsFromLive,
  planFromLive,
  presetsFromLive,
  schemaFromResponse,
} from '../api/adapt.ts';
import type { ActionsResponse, Preset } from '../api/adapt.ts';
import type { LivePlan, PeriodsResponse, TreeResponse } from '../api/adapt.ts';
import type {
  ArcStepRef,
  DerivedSchema,
  FocusForm,
  Graph,
  GraphIndex,
  ModelNode,
  MutationResult,
  PeriodResult,
  PlanResult,
  WriteIntent,
} from '../model/index.ts';
import { fieldsFromForm, formFromFields } from '../model/index.ts';
import type { PressTarget } from '../friction/capture.ts';
import type { ChipEditTarget } from '../components/rows/index.ts';
import type { FocusView } from '../components/focus/index.ts';
import { logFailure } from './errorLog.ts';
import type { Signal } from './signals.ts';
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

  // ── desktop render path (Task 10) ──────────────────────────────────────────
  // Both are v4's own state fields, declared in its initial bag at v4:78
  // (`focus:null,deskPath:[],widths:{}`).
  /**
   * The ids the DESKTOP Finder browser is drilled into, outermost first — v4's `st.deskPath`.
   * `deskPath.length + 1` columns render: the roots, then one column of children per id.
   *
   * Deliberately SEPARATE from `focus`, which is the phone Map's single-column drill-in. v4
   * keeps both and never syncs them, so switching widths mid-session does not carry a
   * position across. Ported as-is.
   */
  deskPath: readonly string[];
  /**
   * Pane widths in px, keyed by pane — v4's `st.widths`, read through `w(key, default)` so an
   * unresized pane has no entry at all rather than a stored default. Written only by the
   * desktop divider drag; clamped to 220–700 there.
   *
   * ⚠ All Finder columns share the ONE key `deskcol`, so dragging any divider resizes every
   * column together. That is v4's shape (v4:751 passes `'deskcol'` for every handle), not an
   * oversight here.
   */
  widths: Readonly<Record<string, number>>;

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
  /**
   * Which work blocks are checked off, KEYED BY THE BLOCK'S ID — see `WorkBlock` on the naming.
   *
   * ⚠ Two changes from v4, both load-bearing (2026-07-18):
   *
   * · The key was `bandIndex-itemIndex`. A regeneration reassigns those slots, so a check that
   *   outlives one generation reattaches to whatever item now sits in the slot — the wrong row
   *   showing as done. The id travels with the block.
   * · The value is a full boolean, not `true`-or-absent. Absent means "the plan's own
   *   `didChunkToday` decides"; an explicit `false` is her un-check, which has to outrank the
   *   plan row until the server's answer replaces it.
   */
  chunked: Readonly<Record<string, boolean>>;
  /**
   * Which work blocks have their arc expanded. v4's `st.blocksOpen`, keyed by block id for the
   * same slot-reassignment reason as `chunked` — and so a block has ONE expand state across the
   * Schedule/Priority toggle rather than one per view. Client-only: nothing persists it.
   */
  blocksOpen: Readonly<Record<string, true>>;
  /**
   * User-reordered Priority ranking, or null for generator order. v4's `st.priOrder`.
   * ⚠ Spec §14 leaves the backend source-of-truth for this ordering OPEN; this is v4's
   * client-local reorder, unchanged, and nothing persists it.
   */
  priOrder: string[] | null;
  /** Free-text "tell me what you need" box under Today's action row. v4's `st.ask`. */
  ask: string;
  /**
   * Which plan rows have their action panel open ("not today" / duration / move), keyed by ITEM
   * ID — v4's `st.editOpen`, which v4 declares (v4:79) and never reads.
   *
   * Keyed by id and not by slot for the reason `chunked` and `blocksOpen` already are: a
   * regenerated plan reassigns slots, so a positional key reattaches to the wrong row.
   */
  editOpen: Readonly<Record<string, true>>;
  /**
   * The plan row whose move-destination list is showing, or null. The Map picker's `moveFor`
   * applied to Today, and likewise an id rather than an index.
   *
   * A single nullable field rather than a set, deliberately: only one row picks a destination at
   * a time, and this shape cannot represent two even by accident.
   */
  movePick: string | null;

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

  // ── Focus-period editor (Task 9) ────────────────────────────────────────────
  // v4 declares `focusView:'list'`, `focusEditId:null`, `focusReflect:null`, `focusDraft:''`
  // and `focusEditField:null` in its initial bag (v4:79). `focusEditField` is NOT carried
  // here: its only reader was `fRow` (v4:842), which has zero call sites — see
  // `components/focus/fields.tsx`. `focusNewOff` and the two picker search boxes appear in v4
  // only via `up()` (v4 keys them `focusPick_front` / `focusPick_paused`) and are read with
  // `||''` fallbacks; declared here because the bag is strictly typed.
  /** Which focus screen the `__focus__` route shows. v4's `st.focusView`. */
  focusView: FocusView;
  /** id of the period being edited — read by `saveFocus`. v4's `st.focusEditId`. */
  focusEditId: string | null;
  /** The live focus edit form. v4's `st.focusReflect`. */
  focusReflect: FocusForm | null;
  /** The author flow's free-text box. v4's `st.focusDraft`. */
  focusDraft: string;
  /** Un-added date in the days-off editor. v4's `st.focusNewOff`. */
  focusNewOff: string;
  /** Foreground picker's search box. v4's `st['focusPick_front']`. */
  focusPickFront: string;
  /** Paused picker's search box. v4's `st['focusPick_paused']`. */
  focusPickPaused: string;
}

/** v4's two literal log tags (v4:1130). Not schema-driven in v4 — hardcoded in the render. */
export type LogTag = 'The day' | 'Friction';

/**
 * One freehand mark drawn on a snapshot, as geometry rather than only as pixels.
 *
 * `points` are in image coordinates; `box` is `[x, y, w, h]`. The image is meaningless without
 * the size it was drawn against, which is why `LogExtras.size` travels with any `marks`.
 * `closed` records whether the stroke ended near where it began — the cheap difference between
 * "circled this" and "pointed at this", without asking her to declare which she meant.
 */
export interface Mark {
  points: Array<[number, number]>;
  box: [number, number, number, number];
  closed: boolean;
}

/**
 * Which way in she used to open the capture.
 *
 * Recorded so an entry point that turns out to go unused can be FOUND and retired instead of
 * quietly accumulating. It is a record of a mechanism, never of her, and it is never used to
 * prompt or nudge her — retirement is surfaced to June and is her call.
 */
export type CaptureVia = 'longpress' | 'shortcut' | 'rightclick' | 'button';

/**
 * The optional context a snapshot capture attaches to a log entry.
 *
 * ⚠ Every field is optional AND every absent field is omitted from the request body entirely —
 * see `logDay`. The Add tab's Log button has always called `logDay(text, tags)` with two
 * arguments, and that call must keep sending a byte-identical body; there are 45 existing
 * entries written by it. Spreading this object into the payload, or sending `shot: undefined`,
 * would change the shape of the unchanged path.
 */
export interface LogExtras {
  /** A PNG data URL of what she was looking at, or null when the render failed. */
  shot?: string | null;
  view?: { tab: string; detailId: string | null } | null;
  target?: PressTarget | null;
  via?: CaptureVia | null;
  marks?: Mark[] | null;
  /** Image dimensions the marks were drawn against. Mark coords are meaningless without it. */
  size?: { w: number; h: number } | null;
}

/**
 * What the Today action row can ask the server to generate.
 *
 * Two endpoints, because the server has two: `/api/refresh` starts a plain fresh generation,
 * `/api/negotiate` runs one of the stored presets (`plan_store._DEFAULT_ACTIONS['presets']`,
 * merged with `~/.controlled-drift/actions.json`). BOTH answer 202 and generate in a background
 * thread, so the two share one poll — see `regenerate`.
 *
 * `presetId` is never composed here. An id the server does not hold answers 400 (`server.py:927`),
 * so the ids live in the schema and the buttons quote them.
 *
 * `message` is the third: `/api/negotiate` takes EITHER a `preset_id` OR a free-text `message`
 * (`server.py:973`), and answers the same 202 through the same background thread — so it is the
 * same wait, and it belongs on this seam rather than in a second one beside it. No `operation` is
 * sent with it: the server's own default for a free-text negotiate is `reorder` (`server.py:975`),
 * and choosing `generate` here would be this client deciding something the server already decides.
 */
export type GenerationRequest =
  | { kind: 'refresh'; capacity?: string }
  | { kind: 'preset'; presetId: string }
  | { kind: 'message'; message: string };

/** How long between two `/api/status` reads while a generation is in flight. */
const POLL_MS = 1_200;
/**
 * How long to keep polling before saying so.
 *
 * Generation takes tens of seconds against her production backend (mistral is the decided
 * default). Five minutes is well past that, and the point of the cap is that the surface stops
 * waiting SILENTLY — it says the plan has not changed yet rather than waiting forever with a
 * control that looks busy.
 */
const POLL_TIMEOUT_MS = 300_000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * The backend ids the SERVER accepts (`scripts/server.py` `VALID_BACKENDS`).
 *
 * ⚠ CORRECTED 2026-07-19 (Task 10). v4's three (`claude | local | api`, v4:1161-1163) do not
 * match: `api` does not exist on the server and would 400 on contact, and `mistral` — June's
 * decided production default (`backend-model-comparison` memory) — was missing entirely. Because
 * `POST /api/settings` was never wired at all before this task, choosing either failure produced
 * no visible error.
 */
export type BackendId = 'mistral' | 'openrouter' | 'claude' | 'local';

/**
 * One backend Settings can offer, and how it actually resolves.
 *
 * `label`, `mechanism` and `model` are read from the server's `GET /api/settings` — computed by
 * `plan_generate.backend_descriptor`, never hand-written here — because a hardcoded description
 * can drift from what the backend actually does, and June chooses between these based on real
 * differences (speed, where the request goes, whether it trains on what she sends).
 */
export interface BackendOption {
  id: BackendId;
  label: string;
  mechanism: string;
  /** `null` for `claude`: the CLI's own default model is not pinned, so the server has none to report. */
  model: string | null;
}

/** The shape `GET /api/settings` answers — read here, never inferred from the client side. */
interface SettingsResponse {
  backend?: string;
  options?: { id: string; label: string; mechanism: string; model: string | null }[];
  include_hobby_block?: boolean;
}

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
  deskPath: [],
  widths: {},
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
  editOpen: {},
  movePick: null,
  priOrder: null,
  ask: '',
  addText: '',
  logText: '',
  logTag: 'The day',
  backend: 'claude',
  hobby: true,
  receipt: [],
  focusView: 'list',
  focusEditId: null,
  focusReflect: null,
  focusDraft: '',
  focusNewOff: '',
  focusPickFront: '',
  focusPickPaused: '',
};

/**
 * What a toast carries.
 *
 * ⚠ WIDENED IN TASK 11. This used to be `{msg, seq}` — one undifferentiated stream, which
 * silently assumed every message deserves the same presentation. It does not: June's direction
 * of 2026-07-18 is that a success should be quiet and in place while a failure should be loud,
 * textual and persistent. That is a difference in KIND, so the kind is on the value; `signals.ts`
 * decides what each one looks like.
 *
 * `nodeId` is which object the message is about, so an inline success can settle that row
 * instead of painting something generic. Null when there is no single object behind it.
 *
 * The name `Toast` is kept as an ALIAS of `Signal` so no existing import breaks, but the type
 * that matters is `Signal` and new code should say that.
 */
export type Toast = Signal;

export interface AppState {
  graph: Graph;
  /** Always in sync with `graph` — derived, never stored. */
  idx: GraphIndex;
  schema: DerivedSchema;
  plan: Plan;
  /**
   * The focus periods (Task 9). Held in state rather than read straight off the fixture
   * because `saveFocus` writes them — the same reason `plan` is cloned and held here.
   */
  periods: Period[];
  ui: UiState;
  /** The one signal currently outstanding — success or failure. See `signals.ts`. */
  toast: Signal | null;
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
   *
   * ⚠ THIS SEAM DOES NOT WRITE, AND IT IS NOW DEAD PLUMBING. `PlanResult` is `{plan, toast}`:
   * there is no `write` on it and no network call is reachable through here. Its one and only
   * caller was `components/today/ArcStep.tsx`, which is why tapping a step raised "Nice — one
   * down" and saved nothing (2026-07-19). That call site now goes to `completeArcStep`.
   *
   * It is marked rather than silently extended on purpose. Giving `PlanResult` a `write` field
   * would have made every future caller of this seam LOOK like it persists, which is exactly
   * the shape that let a dozen controls claim saves they never performed. If you wire a new
   * plan control, give it its own writer beside `completeArcStep` — do not route it through
   * here, and do not add a `write` to `PlanResult` to make this one work.
   */
  applyPlan: (result: PlanResult) => void;
  /**
   * Check off (or reopen) ONE STEP inside a work block's arc — `POST /api/complete` /
   * `/api/uncomplete` with the STEP's own Anytype task id.
   *
   * ⚠ A separate entry point from `chunkBlock` because the two mean different things to the
   * server and to June: a block check records a chunk of work and never finishes the project,
   * while a step check completes a real task. See the note on the implementation.
   */
  completeArcStep: (ref: ArcStepRef, done: boolean) => Promise<void>;
  /**
   * She has finished editing a field on this object — the object editor's `onBlur`.
   *
   * Flushes any pending debounced write for it, waits for the server, and raises "Saved" ONLY
   * if the write was confirmed. Says nothing when nothing was written, and nothing when the
   * write failed (that has already reported itself). See the implementation.
   */
  finishedEditing: (id: string) => Promise<void>;
  /**
   * Apply a PERIOD mutation (Task 9). Third seam of the same shape as `apply`/`applyPlan`,
   * for the same reason: focus periods are neither graph nodes nor plan entries. See
   * `model/periods.ts`.
   *
   * ⚠ DEAD PLUMBING. Nothing produces a `PeriodResult` any more — the focus-period write goes
   * to the server through `saveFocusPeriod`. Wiring a period change to this seam would
   * reintroduce the local-only write that lost every field on reload; the type will not stop
   * you. Kept only because removing the plumbing was judged out of scope.
   */
  applyPeriods: (result: PeriodResult) => void;
  /**
   * Report that something did NOT happen.
   *
   * The counterpart to `apply`, and deliberately a separate entry point rather than a `kind`
   * argument threaded through it: `apply` takes a `MutationResult`, and a mutation that refused
   * does not produce one — it returns the graph unchanged with `toast:null`. The caller that
   * KNOWS it refused is the only thing that can say so, which is exactly the invalid-drop case.
   *
   * ⚠ This does NOT change the model layer's signature. `move()`'s cycle guard still returns a
   * plain no-op; the drop handler, which knows it refused and knows both titles, raises this.
   *
   * Recording is not optional and not the caller's business: every failure reaches the log
   * (`errorLog.ts`) on the way to the screen, so a dismissed message still leaves a trace.
   */
  fail: (msg: string, opts?: { nodeId?: string | null; before?: unknown; kind?: string }) => void;
  /**
   * Say that a change CANNOT be made, or what she has to do next — visible, autofading, and not
   * written to the error log because nothing went wrong. See the implementation for why this is
   * neither `flash` (which renders nowhere) nor `fail` (which claims a defect).
   */
  refuse: (msg: string, nodeId?: string | null, hold?: boolean) => void;
  /**
   * Append a log entry to the friction log via `POST /api/logday`. Resolves `true` only when the
   * server confirmed the write — callers must not clear her text on `false`.
   *
   * `extras` carries an optional snapshot of what she was looking at, which view she was on,
   * which element she pressed, which way in she used, and anything she drew — see
   * `app/src/friction/`. All of it is optional: the Add tab's Log button still calls this with
   * two arguments and sends a byte-identical body.
   */
  logDay: (text: string, tags: string[], extras?: LogExtras) => Promise<boolean>;
  /**
   * Hand her words to the structure step and get back the form she checks.
   *
   * `null` means no form was produced — busy, failed, or nothing understood. Each has already
   * reported itself; the caller must NOT fall back to building a form locally, which is the
   * fabrication this replaced.
   */
  authorFocus: (text: string) => Promise<FocusForm | null>;
  /**
   * Write a focus period — `commit` for a new one, `update` for an edit in place.
   *
   * Returns whether it LANDED, so the caller only closes the editor on a real write. `false`
   * covers both a refusal (a field still empty) and a failure; each has already reported itself
   * in its own register, and neither should discard what she typed.
   *
   * ⚠ `true` also covers a period that saved while an as-needed task she named did NOT come back
   * on. It landed, so the editor closes — and the partial failure has already reported itself
   * loudly, naming what stayed off.
   */
  saveFocusPeriod: (
    view: 'edit' | 'author',
    editId: string | null,
    form: FocusForm,
  ) => Promise<boolean>;
  /**
   * Record (or un-record) a chunk of work on a block — `POST /api/complete` / `/api/uncomplete`
   * with the block's id, which on the wire is its `project_id`.
   *
   * ⚠ A block check means "did a chunk today", NEVER "this project is finished"
   * (`docs/display_grain_design.md` §REVISION 2026-07-14 §B). This is a separate entry point
   * from `apply(toggleDone(...))` for exactly that reason: the server dispatches on
   * `plan_store.is_block_item` and writes the chunk log, and nothing here touches the project's
   * done state.
   */
  chunkBlock: (id: string, done: boolean) => Promise<void>;
  /**
   * Take one plan row off TODAY'S list — `POST /api/task/not-today`.
   *
   * ⚠ CACHE-ONLY BY DESIGN. No Anytype write, no status change, no reschedule: the item returns
   * tomorrow with the status it had, and an 8h window keeps it off a same-day regenerate. That
   * is what June asked for — it holds for the day and does not leak into future days. Do not
   * turn this into a durable field.
   */
  notTodayRow: (id: string, kind: 'task' | 'block') => Promise<void>;
  /**
   * Set a row's length — `POST /api/duration`.
   *
   * ⚠ The server dispatches on whether the row is a block: a block sets the durable per-project
   * CHUNK LENGTH, a task sets its own duration. The distinction is June's and the LABEL carries
   * it; nothing here decides the kind.
   */
  setRowDuration: (id: string, minutes: number) => Promise<void>;
  /**
   * Move one row to another position in today's plan — `POST /api/task/move`. Bidirectional.
   *
   * ⚠ The move lives ONLY in the plan cache. The next generation rebuilds from Anytype and it is
   * gone, so nothing may tell her it persisted.
   */
  moveRow: (id: string, target: { block: number | null; position: number }) => Promise<void>;
  /**
   * The real backend list — read from `GET /api/settings` on hydration, never hardcoded. Empty
   * until hydration answers, or if it fails; see the hydration effect for why there is no
   * fixture-style fallback list here.
   */
  backendOptions: BackendOption[];
  /**
   * Write a Settings change — `POST /api/settings`. Optimistic like `chunkBlock`: the radio dot
   * or switch moves immediately, and a refusal puts it back. `hobby` is translated to the
   * server's `include_hobby_block` key here, nowhere else.
   */
  saveSettings: (patch: Partial<Pick<UiState, 'backend' | 'hobby'>>) => void;
  /**
   * Ask the server for a new plan, and do not claim anything until it has one.
   *
   * `label` is the June-facing name of the control that started it, so the surface can show
   * WHICH control is working. See `generating`.
   *
   * Resolves `true` ONLY when a new plan was generated and read back. Callers that hold text of
   * hers — the "tell me what you need" box — must clear it on `true` and never otherwise, exactly
   * as `logDay`'s callers do. Every `false` has already reported itself through `fail`.
   */
  regenerate: (req: GenerationRequest, label: string) => Promise<boolean>;

  // ── the Add tab's real capture flow ────────────────────────────────────────
  /**
   * What capture has filed, as the SERVER records it (`GET /api/session?stream=capture`).
   * Each `weed` entry holds the objects one turn created; `undo` entries mark ids as undone.
   * Server-truth rather than a locally-built list: only the weeder knows how many objects a
   * sentence became, and this survives a reload.
   */
  captureEntries: readonly WeedEntry[];
  /**
   * The last turn's `result_summary` — the ONLY channel by which a skipped or failed item
   * reaches her, since `failed[]`/`skipped[]` are not in the receipt.
   */
  captureSummary: string | null;
  /** Re-read the receipt from the server (on tab open, and after any change to it). */
  loadCapture: () => Promise<void>;
  /** Weed one piece of text end to end. True only once a completed run has been read back. */
  runCapture: (text: string) => Promise<boolean>;
  /** Archive one just-captured object; the row then dims from server truth, not a local splice. */
  undoCapture: (id: string) => Promise<void>;
  /** Re-anchor when a captured task is for. Sends a TOKEN; the server resolves the date. */
  setCapturedWhen: (id: string, when: WhenToken) => Promise<void>;
  /** Correct the engagement the weeder proposed for a captured Project. */
  setCapturedEngagement: (id: string, from: string, to: string) => Promise<void>;
  /**
   * The label of the control whose generation is in flight, or null when nothing is running.
   *
   * ⚠ A generation takes tens of seconds against the production backend. This is what stops the
   * action row looking idle — or finished — during that wait.
   */
  generating: string | null;
  /**
   * Her plan-action buttons, read from `GET /api/actions` (her own
   * `~/.controlled-drift/actions.json`). EMPTY means her file could not be read — the action
   * row then offers only what needs no file, rather than a remembered set of labels that may
   * no longer be hers. See `TodayCtx.presets`.
   */
  presets: readonly Preset[];
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
    // Track A's stand-in for `GET /api/tree`'s `orphans`. See `fixtures/orphans.ts` — the
    // endpoint is the real source and this exists so the buckets are visible before Track B.
    orphans: structuredClone(seedOrphans) as Graph['orphans'],
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

/** Cloned for the same reason the graph and the plan are — `saveFocus` writes periods. */
function initialPeriods(): Period[] {
  return structuredClone(seedPeriods) as Period[];
}

/**
 * No periods — what `live` starts from, and where a live read FAILURE leaves the Focus tab.
 *
 * The seed periods are plausible-looking invented commitments ("Job-search sprint · caregiving
 * from Sat"). Showing them in live mode is the same fabrication the tree read refuses: an empty
 * Focus tab plus a loud failure is honest, a fake week she might plan around is not.
 */
function emptyPeriods(): Period[] {
  return [];
}

/**
 * Where the app's data comes from.
 *
 * `live` — the real endpoints, against June's Anytype space. The only value production uses.
 * `fixtures` — the extracted v4 fixtures, no network. Kept because the component tests are
 *   written against known fixture content, and because contract §5 explicitly RETAINS an
 *   offline path ("the export-diff fallback, which spec §1 explicitly keeps"). It is not a
 *   demo mode: nothing in the running app can select it.
 */
export type DataSource = 'live' | 'fixtures';

/** An empty graph — what `live` starts from, so no fixture content is ever shown as hers. */
function emptyGraph(): Graph {
  return { roots: [], strategies: [], orphans: [] };
}

/** An empty plan, for the same reason. */
function emptyPlan(): Plan {
  return { date: '', generated: '', shape: 'schedule', header: '', woven: '', blocks: [] };
}

/**
 * The writes that change exactly one node and nothing about the shape of the forest — so a
 * failure can be undone by putting that one node back, leaving every other edit alone.
 *
 * `move`, `create` and `archive` are deliberately absent: undoing those means re-parenting,
 * removing, or re-inserting at a remembered position, which the snapshot path still handles.
 */
const PER_NODE_OPS = new Set(['patchVals', 'patchTitle', 'complete', 'recurringActive', 'unsupported', 'clearField']);

export function useAppState(source: DataSource = 'live'): AppState {
  const live = source === 'live';
  const [graph, setGraph] = useState<Graph>(live ? emptyGraph : initialGraph);
  const [plan, setPlan] = useState<Plan>(live ? emptyPlan : initialPlan);
  const [periods, setPeriods] = useState<Period[]>(live ? emptyPeriods : initialPeriods);
  const [ui, setUi] = useState<UiState>(INITIAL_UI);
  const [toast, setToast] = useState<Signal | null>(null);
  /**
   * The live vocabularies. `null` until the fetch settles; `defaultSchema` is the FALLBACK the
   * contract asks for (§3.1: "ship `defaultSchema()` as the client-side fallback so a schema
   * fetch failure degrades to the last-known vocabulary rather than a blank form"), never the
   * first thing rendered when a live read is on its way.
   */
  const [liveSchema, setLiveSchema] = useState<Schema | null>(null);
  /**
   * The real backend list, from `GET /api/settings`. Empty until hydration answers — never a
   * hardcoded fallback list, for the same reason `periods`' live-read failure leaves `[]` rather
   * than showing invented content: an offered choice that does not match what the server holds
   * is worse than an empty picker, because she would never learn a selection did nothing.
   */
  const [backendOptions, setBackendOptions] = useState<BackendOption[]>([]);
  /*
   * Her plan-action presets, read from `GET /api/actions`. Starts EMPTY, not seeded with a
   * remembered list: an empty action row is honest before the fetch lands, and a remembered one
   * would show labels that may not be hers.
   */
  const [presets, setPresets] = useState<Preset[]>([]);

  /** Raise a SUCCESS signal. The three `apply*` seams all land here so the shape is identical. */
  const succeed = useCallback((msg: string, nodeId: string | null) => {
    setToast((prev) => ({ kind: 'success', msg, nodeId, seq: (prev?.seq ?? 0) + 1 }));
  }, []);

  const idx = useMemo(() => index(graph), [graph]);
  /**
   * The derived form vocabulary.
   *
   * ⚠ TWO VOCABULARIES IN `defaultSchema` ARE NOW WRONG AGAINST THE LIVE SPACE, which is why
   * this is fetched and not a literal: Project engagement lost `Sprint` and `Hyperfixation`
   * (retired from the data structure — those tags no longer exist), and `Applies when` never
   * gained `Overwhelmed` / `Sprint` / `Stuck`. Offering a value the space cannot store does not
   * degrade gracefully; it produces a failed write at the moment she taps it. See `api/adapt.ts`.
   */
  const schema = useMemo(
    () => applySchema(liveSchema ?? defaultSchema),
    [liveSchema],
  );

  const up = useCallback((patch: Partial<UiState>) => {
    setUi((prev) => ({ ...prev, ...patch }));
  }, []);

  const fail = useCallback<AppState['fail']>((msg, opts = {}) => {
    // Logged BEFORE it is shown, and unconditionally: a failure she dismisses without reading
    // must still be diagnosable afterwards. See `errorLog.ts` for which log and why.
    logFailure(msg, {
      objectId: opts.nodeId ?? null,
      before: opts.before ?? null,
      ...(opts.kind ? { kind: opts.kind } : null),
    });
    setToast((prev) => ({
      kind: 'failure',
      msg,
      nodeId: opts.nodeId ?? null,
      seq: (prev?.seq ?? 0) + 1,
    }));
  }, []);

  /**
   * SAY THAT A CHANGE CANNOT BE MADE — a refusal, or an instruction about what to do next.
   *
   * ⚠ NOT `flash`. `flash` raises a SUCCESS-kind signal with no node behind it, and `present()`
   * gives success `inline`, which needs a node to settle on. So a `flash` refusal renders
   * NOWHERE AT ALL: it cannot go inline (no node) and it is not a failure so it never reaches
   * the bar. That is how "That needs to be a number of minutes above zero." became silence while
   * the box went on displaying a number that was never stored (June, 2026-07-20 live check).
   *
   * ⚠ NOT `fail` either. Nothing broke — the system declined, correctly, and nothing was written
   * that should have been. Routing it through `fail` addresses her as if there were a defect and
   * fills `errorLog` with non-defects, which is what stops that log being useful for real ones.
   * So this deliberately does not log.
   *
   * It FADES (5s) BY DEFAULT, and that is only sound because of the other half of the rule: the
   * control the refusal came from must revert to the stored value, so the screen is truthful with
   * or without the sentence. Do not use the fading form from a control that goes on displaying the
   * rejected input.
   *
   * ⚠ `hold` IS FOR THE SITE WHERE NOTHING REVERTS, because there is nothing to revert. An
   * INSTRUCTION ("Pick an item to move") changes nothing on screen at all — she has to act on the
   * sentence, by finding the `edit` panel on a row, and a sentence that disappears after five
   * seconds while the screen is unchanged leaves her with no way back to it. That is the same
   * defect as a fading notice about an invisible write, which is why `Signal.hold` already exists.
   * A refusal WITH a revert must keep the default and fade — the screen carries it by then.
   */
  const refuse = useCallback((msg: string, nodeId: string | null = null, hold = false) => {
    setToast((prev) => ({ kind: 'notice', msg, nodeId, seq: (prev?.seq ?? 0) + 1, hold }));
  }, []);

  /**
   * The graph as it is RIGHT NOW, for the async write path.
   *
   * A write resolves hundreds of milliseconds after `apply` returned, by which time the `graph`
   * captured in that closure is stale — she may have edited two more fields since. The ref
   * always holds the current value, which is what lets a rollback edit the live graph instead of
   * replacing it wholesale.
   *
   * ⚠ Corrected 2026-07-18 (cross-family review gate). This comment previously claimed the
   * rollback already worked that way. It did not — `rollback` called `setGraph(before)` with a
   * whole-graph snapshot, so any edit she made while a write was in flight was wiped from the
   * screen when that write failed, while its own write succeeded on the server. The comment
   * describing the safe behaviour was the reason nobody looked. See `revertOne` below for what
   * the code now actually does, and which cases it still does not cover.
   */
  const graphRef = useRef(graph);
  graphRef.current = graph;

  /** The plan as it is RIGHT NOW, for the same reason as `graphRef` — see `completeArcStep`. */
  const planRef = useRef(plan);
  planRef.current = plan;

/**
   * Per-object debounce timers for the title field, which fires per keystroke.
   *
   * ⚠ EACH ENTRY CARRIES ITS OWN `flush`, not just a handle. A handle can only be CANCELLED, and
   * cancelling is what the unmount cleanup used to do: `clearTimeout(t)` on every pending timer
   * without firing it, so closing the app within 600ms of the last keystroke silently discarded a
   * write June had already been told had saved. `flush` runs the write NOW and clears the timer,
   * which is what both the unmount and `finishedEditing` actually need.
   */
  const titleTimers = useRef(new Map<string, { timer: ReturnType<typeof setTimeout>; flush: () => void }>());
  useEffect(() => {
    const timers = titleTimers.current;
    return () => {
      // FIRE the pending writes, do not drop them. Her words outrank a tidy teardown.
      for (const t of [...timers.values()]) t.flush();
    };
  }, []);

  /**
   * The most recent field write per object, as the promise that says whether it was CONFIRMED.
   *
   * This is what lets blur wait for an answer instead of guessing one. An entry is CONSUMED when
   * it is read, so a second blur with no edit in between claims nothing — the old unconditional
   * `flash('Saved')` said "Saved" for merely tabbing through an untouched field.
   */
  const fieldWrites = useRef(new Map<string, Promise<boolean>>());

  /**
   * Put the SERVER's object into the graph, replacing whatever the optimistic mutation guessed.
   *
   * This is the read-back discipline arriving in the UI. `api_write` re-fetches from Anytype
   * after every write and returns that read (never the request echoed back), so what lands here
   * is observed state — including any normalisation Anytype applied that the client did not
   * predict (dates, multi-selects, a select stored as a tag id).
   *
   * Children are taken from the server node too: `node_for` finds the object inside the freshly
   * built tree payload, so its subtree is current.
   */
  const acceptServerNode = useCallback((serverNode: ModelNode, replacingId?: string) => {
    const targetId = replacingId ?? serverNode.id;
    setGraph((cur) => updateNode(cur, targetId, () => serverNode).graph);
  }, []);

  /**
   * Perform one write and reconcile local state with what actually persisted.
   *
   * Optimism + rollback rather than a spinner: every mutation here is a single field on a row
   * she is looking at, the round trip is short, and blocking the UI on each one would make the
   * surface feel like a form rather than a list. The cost of optimism is that a failure must be
   * UNDONE visibly, which is what the rollback and the persistent failure bar do together.
   */
  /**
   * Send one write, and say WHETHER THE SERVER CONFIRMED IT.
   *
   * ⚠ The boolean is the point, not a convenience. Every `false` here has already reverted the
   * optimistic change and told her what did not save, so no caller needs to report a failure —
   * but a caller that wants to CONFIRM a save has no other honest source for the answer.
   * `finishedEditing` is that caller: the editor used to say "Saved" on blur with nothing behind
   * it, because there was nothing to ask.
   */
  const performWrite = useCallback(
    async (intent: WriteIntent, before: Graph, beforeNode: ModelNode | null): Promise<boolean> => {
      /**
       * Undo one failed write.
       *
       * Two paths, because the two kinds of write fail differently:
       *
       * · A FIELD write touched exactly one node, so only that node is put back — into the graph
       *   as it is NOW, not as it was when the write started. Anything she changed in the
       *   meantime survives. This is the case the 600ms title debounce widens, and the one that
       *   happens most, so it is the one that must not lose her work.
       *
       * · A STRUCTURAL write (move, create, archive) reshapes the forest, and undoing it means
       *   re-parenting, removing or re-inserting at a remembered position. Reverting those
       *   against a graph that has since changed is a genuinely harder problem than it looks, so
       *   they still restore the snapshot. The exposure is real but much smaller: none of them
       *   is debounced, each is one deliberate action rather than a keystroke burst, so the
       *   window is a single round trip rather than 600ms plus one.
       *
       * NOT a general undo stack, and deliberately not — this only ever reverts the one write
       * that just failed.
       */
      const revertOne = (msg: string, id: string | null) => {
        if (beforeNode && id) {
          setGraph((cur) => updateNode(cur, id, () => beforeNode).graph);
        } else {
          setGraph(before);
        }
        fail(msg, { nodeId: id, before: intent });
      };
      const rollback = revertOne;

      if (intent.op === 'unsupported') {
        // Never a silent success. The optimistic change is reverted and she is told which
        // action has no endpoint, rather than seeing a change that will vanish on reload.
        rollback(
          `Could not ${intent.what} — this surface cannot save that yet, so nothing changed.`,
          intent.id,
        );
        return false;
      }

      if (intent.op === 'complete') {
        const path = intent.done ? '/api/complete' : '/api/uncomplete';
        const res = await apiSend<{
          completed?: Record<string, unknown>;
          uncompleted?: Record<string, unknown>;
          plan?: LivePlan;
        }>('POST', path, { id: intent.id });
        if (!res.ok) {
          rollback(
            `Could not ${intent.done ? 'check off' : 'reopen'} that — it is NOT saved. ${res.error}`,
            intent.id,
          );
          return false;
        }
        // ⚠ `/api/complete` does NOT answer the contract's `{ok, object}` envelope — it returns
        // `{completed: {...partial}, plan}` (contract §4 lists it as CHANGE, unbuilt). So the
        // confirmed fields are MERGED into the node rather than replacing it; replacing would
        // blank every field the partial does not carry.
        const confirmed = (res.data.completed ?? res.data.uncompleted ?? {}) as Record<
          string,
          unknown
        >;
        setGraph((cur) => {
          const r = updateNode(cur, intent.id, (n) => ({
            ...n,
            vals: {
              ...n.vals,
              done: Boolean(confirmed['done']),
              ...(typeof confirmed['status'] === 'string' ? { status: confirmed['status'] } : null),
            },
          }));
          return r.graph;
        });
        // The check-off also re-writes today's plan cache, and the response carries it. An
        // `{empty:true}` body means the id was not in today's plan — not a plan to render.
        if (res.data.plan && !res.data.plan.empty) setPlan(planFromLive(res.data.plan));
        return true;
      }

      if (intent.op === 'recurringActive') {
        const res = await apiSend<{ object?: ModelNode; warning?: string }>(
          'POST',
          '/api/recurring/active',
          { id: intent.id, active: intent.active },
        );
        if (!res.ok) {
          rollback(`Could not change whether that is in the plan — it is NOT saved. ${res.error}`, intent.id);
          return false;
        }
        if (res.data.object) acceptServerNode(res.data.object);
        // A saved write whose read-back could not be assembled is reported, not swallowed —
        // the toggle itself was already proven inside `set_recurring_active`.
        else if (res.data.warning) fail(res.data.warning, { nodeId: intent.id, kind: 'read_back' });
        return true;
      }

      if (intent.op === 'clearField') {
        // Removes the property so the field inherits again (contract §4). A 400 here is the
        // server refusing a format it has no verified way to clear — that is a real not-saved
        // and must roll back, exactly like any other failed write. `already_inheriting` is a
        // success with no write behind it; the optimistic change was already correct.
        const res = await apiSend<{ object?: ModelNode; already_inheriting?: boolean }>(
          'POST',
          `/api/object/${intent.id}/clear-field`,
          { field: intent.field },
        );
        if (!res.ok) {
          rollback(`Could not go back to inheriting ${intent.field} — it is NOT saved. ${res.error}`, intent.id);
          return false;
        }
        if (res.data.object) acceptServerNode(res.data.object);
        return true;
      }

      if (intent.op === 'archive') {
        const res = await apiSend<{ archived?: boolean }>('DELETE', `/api/object/${intent.id}`);
        if (!res.ok) {
          rollback(`Could not delete that — it is still there. ${res.error}`, intent.id);
          return false;
        }
        return true; // nothing to accept: the object is gone, and the optimistic removal was right
      }

      if (intent.op === 'create') {
        const res = await apiSend<{ object?: ModelNode }>('POST', '/api/object', {
          level: intent.level,
          title: intent.title,
          ...(intent.parentId ? { parent_id: intent.parentId } : null),
        });
        if (!res.ok) {
          rollback(`Could not create that — nothing was saved. ${res.error}`, intent.tempId);
          return false;
        }
        if (res.data.object) {
          // THE TEMP ID IS REPLACED BY THE REAL ONE (contract §4). The detail pane was opened on
          // the temp id, so it is re-pointed in the same tick or the editor would be looking at
          // a node that no longer exists.
          acceptServerNode(res.data.object, intent.tempId);
          setUi((prev) =>
            prev.detail === intent.tempId ? { ...prev, detail: res.data.object!.id } : prev,
          );
        }
        return true;
      }

      const path = `/api/object/${intent.id}`;
      const body =
        intent.op === 'patchTitle'
          ? { title: intent.title }
          : intent.op === 'move'
            ? { parent_id: intent.parentId }
            : { vals: intent.vals };
      const url = intent.op === 'move' ? `${path}/move` : path;
      const res = await apiSend<{ object?: ModelNode }>(
        intent.op === 'move' ? 'POST' : 'PATCH',
        url,
        body,
      );
      if (!res.ok) {
        const what =
          intent.op === 'patchTitle'
            ? 'rename that'
            : intent.op === 'move'
              ? 'move that'
              : `save ${Object.keys(intent.vals).join(', ')}`;
        rollback(`Could not ${what} — it is NOT saved. ${res.error}`, intent.id);
        return false;
      }
      if (res.data.object) acceptServerNode(res.data.object);
      return true;
    },
    [acceptServerNode, fail],
  );

  const apply = useCallback(
    (result: MutationResult) => {
      const before = graphRef.current;
      // The node as it was, for the precise revert. Captured BEFORE the optimistic change is
      // applied, and only for the writes that touch exactly one node — `move`, `create` and
      // `archive` reshape the forest, so putting one node back would not undo them. `node()`
      // returns null for an id that is not in the graph (a `create`'s tempId), which lands on
      // the snapshot path on its own without a second condition to keep in sync.
      // `updateNode` with an identity function is a lookup that returns the node and the SAME
      // graph back — so this reads the node without building a whole index on every write.
      const beforeNode = PER_NODE_OPS.has(result.write?.op ?? '')
        ? updateNode(before, (result.write as { id?: string } | undefined)?.id ?? '', (n) => n).node
        : null;
      setGraph(result.graph);
      graphRef.current = result.graph;
      if (result.ui) setUi((prev) => ({ ...prev, ...result.ui }));
      // `result.node` is the object the write was about — that is what makes an INLINE success
      // possible at all, because it is the only thing that says which row to settle.
      // A REFUSAL AND A RECEIPT ARE NOT THE SAME MESSAGE. A refusal has nothing visible behind
      // it, so it has to be read; raised as a success it would be presented `inline` and — with
      // no `node` to settle on — would render nowhere at all. See `MutationResult.refusal`.
      if (result.toast && result.refusal) refuse(result.toast, result.node ? result.node.id : null);
      else if (result.toast) succeed(result.toast, result.node ? result.node.id : null);

      // THE ONE PLACE THE SURFACE WRITES. Every mutation call site in the app funnels through
      // `apply`, so there is no second route to the network and none to forget.
      if (!live || !result.write) return;
      const intent = result.write;
      if (intent.op === 'patchTitle') {
        // Debounced: v4's title textarea writes per keystroke (contract §4 asks for exactly
        // this). The LAST title wins, and the rollback target is the graph as it was before the
        // first keystroke of the burst — which is why `before` is captured out here.
        const prev = titleTimers.current.get(intent.id);
        if (prev) clearTimeout(prev.timer);
        // The write, as a thunk that can be run by the timer OR pulled forward. It records its
        // own promise in `fieldWrites` so a blur arriving later can ask how it went.
        const run = () => {
          titleTimers.current.delete(intent.id);
          fieldWrites.current.set(intent.id, performWrite(intent, before, beforeNode));
        };
        titleTimers.current.set(intent.id, {
          timer: setTimeout(run, 600),
          flush: () => {
            const held = titleTimers.current.get(intent.id);
            if (held) clearTimeout(held.timer);
            run();
          },
        });
        return;
      }
      // Not debounced, but still recorded: a note field writes per keystroke, and blur must be
      // able to wait on the LAST of those rather than announce a save over one still in flight.
      const p = performWrite(intent, before, beforeNode);
      if (intent.op === 'patchVals') fieldWrites.current.set(intent.id, p);
      else void p;
    },
    [live, performWrite, succeed, refuse],
  );

  /**
   * SHE HAS LEFT A FIELD — flush whatever is pending, then say "Saved" ONLY if it saved.
   *
   * ⚠ This replaces `onBlur={() => flash('Saved')}` in the object editor, which was wrong twice
   * over. The title write is on a 600ms debounce, so that claim could precede the REQUEST, not
   * merely the response; and it was unconditional, so it also fired for a field she merely
   * tabbed through. `DetailCtx.flash`'s own doc-comment asserted there was "nothing left to
   * write", which is how it survived review.
   *
   * ⚠ WHY THE CONFIRMATION IS RAISED HERE AND NOT BY EVERY SUCCESSFUL WRITE. `succeed` sets a
   * TOAST, and `patchVals` fires per keystroke — confirming inside `performWrite` would flicker
   * "Saved" on every character she typed. Blur is the right moment to speak. The defect was that
   * blur was not waiting for anything.
   *
   * Silence is correct when nothing was written. A failure has already reported itself through
   * `performWrite`'s rollback, so this must not speak again — she would get two messages about
   * one event, the second contradicting the first.
   */
  const finishedEditing = useCallback(
    async (id: string): Promise<void> => {
      titleTimers.current.get(id)?.flush();
      const pending = fieldWrites.current.get(id);
      if (!pending) return;
      // CONSUMED, so a second blur with no edit in between describes nothing and says nothing.
      fieldWrites.current.delete(id);
      if (await pending) succeed('Saved', id);
    },
    [succeed],
  );

  /**
   * HYDRATION — the schema, the tree, today's plan and the focus periods, read from the running
   * server on mount.
   *
   * Separate awaits rather than one `Promise.all` result: they fail independently and a
   * schema outage must not blank the tree. Each failure is reported on its own terms.
   */
  useEffect(() => {
    if (!live) return;
    let cancelled = false;

    void (async () => {
      const [schemaRes, treeRes, planRes, periodsRes, settingsRes, actionsRes] = await Promise.all([
        apiGet<unknown>('/api/schema'),
        apiGet<TreeResponse>('/api/tree'),
        apiGet<LivePlan>('/api/plan'),
        apiGet<PeriodsResponse>('/api/periods'),
        apiGet<SettingsResponse>('/api/settings'),
        apiGet<ActionsResponse>('/api/actions'),
      ]);
      if (cancelled) return;

      if (schemaRes.ok) {
        setLiveSchema(schemaFromResponse(schemaRes.data));
      } else {
        // Contract §3.1's fallback. It is a REAL degradation, not a quiet default: the built-in
        // vocabulary is a stale snapshot, so she is told rather than left to discover it when a
        // write is refused.
        fail(
          `Could not read the field options from Anytype, so the pickers are showing the last known list — some options may no longer save. ${schemaRes.error}`,
          { kind: 'schema_read' },
        );
      }

      if (treeRes.ok) {
        setGraph(graphFromTree(treeRes.data));
      } else {
        // NO FIXTURE FALLBACK HERE, deliberately, and this is the one place the contract's
        // "fixtures are the fallback" does NOT apply. A stale vocabulary is still June's
        // vocabulary; fixture OBJECTS are not her objects, and rendering "Renew library card"
        // as though it were in her space would be a fabricated record of her own life. Empty
        // plus a loud failure is the honest state.
        fail(`Could not read your objects from Anytype — nothing is shown. ${treeRes.error}`, {
          kind: 'tree_read',
        });
      }

      if (planRes.ok && !planRes.data.empty) setPlan(planFromLive(planRes.data));
      else if (!planRes.ok) {
        fail(`Could not read today's plan. ${planRes.error}`, { kind: 'plan_read' });
      }

      if (periodsRes.ok) {
        setPeriods(periodsFromLive(periodsRes.data));
      } else {
        // Same rule as the tree, for the same reason: NO FIXTURE FALLBACK. `seedPeriods` are
        // invented weeks that read as real commitments, and a Focus tab quietly showing them
        // after a failed read is worse than a blank one — she could plan around a week nobody
        // wrote. Empty plus a loud failure.
        setPeriods([]);
        fail(`Could not read your focus periods — none are shown. ${periodsRes.error}`, {
          kind: 'periods_read',
        });
      }

      /*
       * HER PLAN-ACTION BUTTONS, from her own `~/.controlled-drift/actions.json`.
       *
       * Same rule as the tree, the periods and the settings: NO FALLBACK TO A REMEMBERED SET.
       * The four labels used to be hardcoded in `TodayPanel` and had already drifted from her
       * file — hers reads "Quick wins first", the button read "Quick wins only". Showing a
       * remembered label after a failed read would be the same defect wearing a different hat:
       * a button claiming to be hers, standing for a preset the server may no longer hold.
       *
       * Empty plus a loud failure is the honest state. The row still offers "↻ Fresh plan" and
       * "Move this later", which need no file.
       */
      if (actionsRes.ok) {
        setPresets(presetsFromLive(actionsRes.data));
      } else {
        setPresets([]);
        fail(
          `Could not read your plan buttons, so only Fresh plan is shown. ${actionsRes.error}`,
          { kind: 'actions_read' },
        );
      }

      if (settingsRes.ok) {
        setBackendOptions((settingsRes.data.options ?? []) as BackendOption[]);
        setUi((prev) => ({
          ...prev,
          ...(settingsRes.data.backend ? { backend: settingsRes.data.backend as BackendId } : null),
          ...(typeof settingsRes.data.include_hobby_block === 'boolean'
            ? { hobby: settingsRes.data.include_hobby_block }
            : null),
        }));
      } else {
        // Same rule as the tree and the periods: NO FIXTURE FALLBACK. Offering the old hardcoded
        // three here would let her pick one that either 400s (`api`, gone from the server) or
        // silently is not her production backend — an empty list plus a loud failure is honest.
        fail(`Could not read your settings — no backend choices are shown. ${settingsRes.error}`, {
          kind: 'settings_read',
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [live, fail]);

  const applyPlan = useCallback(
    (result: PlanResult) => {
      setPlan(result.plan);
      // A plan mutation is about a plan entry, not a graph node, so there is no row to settle.
      if (result.toast) succeed(result.toast, null);
    },
    [succeed],
  );

  // ⚠ DEAD PLUMBING — nothing produces a `PeriodResult`. See the note on `AppState.applyPeriods`.
  const applyPeriods = useCallback(
    (result: PeriodResult) => {
      setPeriods(result.periods);
      if (result.toast) succeed(result.toast, null);
    },
    [succeed],
  );

  /**
   * Say that something is still needed — NOT that something went wrong.
   *
   * Deliberately not `fail`: `fail` writes the error log, and a period she has not finished
   * filling in is not a defect. Filling that log with non-defects is how it stops being useful
   * for finding real ones. See `signals.ts` on why `notice` is a third kind rather than a
   * politer failure.
   */
  const notify = useCallback((msg: string) => {
    // `hold` — nothing on screen changed, so this one must not fade. See `Signal.hold`.
    setToast((prev) => ({
      kind: 'notice',
      msg,
      nodeId: null,
      seq: (prev?.seq ?? 0) + 1,
      hold: true,
    }));
  }, []);

  /**
   * Which fields she still has to fill in, as one plain sentence.
   *
   * The server sends ready-to-read labels (`missing_required` → `['start date','end date']`), so
   * this joins them and says what to do. No metaphor, no error register, no blame — the period
   * is not broken, it is unfinished.
   *
   * ⚠ The labels arrive bare ('end date'), and reading them out bare produced "needs start date
   * and end date" — machine output, at the one moment the sentence most needs to sound like a
   * person saying what is left. Each label gets its article here rather than on the server,
   * because the article belongs to this sentence, not to the label.
   */
  const article = (label: string): string => ('aeiou'.includes(label[0]?.toLowerCase() ?? '') ? 'an' : 'a');

  const missingSentence = (missing: string[]): string => {
    const withArticles = missing.map((m) => `${article(m)} ${m}`);
    const names =
      withArticles.length > 1
        ? withArticles.slice(0, -1).join(', ') + ' and ' + withArticles[withArticles.length - 1]
        : (withArticles[0] ?? 'a required field');
    return `That focus period needs ${names} before it can be saved. Nothing else you typed was lost.`;
  };

  /**
   * STRUCTURE HER WORDS — `POST /api/focus/author`, then poll, then read the result.
   *
   * ⚠ WHAT THIS REPLACED, AND WHY IT WAS THE WORST BUG ON THIS SCREEN. "Structure this →" ran
   * `formFromDraft`, a client-side stand-in that hardcoded `start:'2026-07-21'`,
   * `end:'2026-07-27'` and named the period by cutting her sentence at the first comma. The next
   * screen is headed "Here's what I heard" and tells her it "reads back what it heard for you to
   * check". No model had run. The surface claimed a comprehension that never happened and showed
   * her two constants as the dates it had understood.
   *
   * ⚠ ASYNCHRONOUS. The POST answers 202 and the structure step (an LLM call, ~30s) runs on a
   * thread. The answer never comes back from the POST: poll `/api/focus/status` — focus has its
   * OWN status route, not the shared `/api/status` — and then read `/api/focus/result`.
   *
   * Returns the form for her to check, or `null`. It returns null rather than a form of blanks
   * whenever the step did not produce one: a blank form under the heading "Here's what I heard"
   * is the same fabrication in a quieter voice.
   */
  const authorFocus = useCallback(
    async (text: string): Promise<FocusForm | null> => {
      const body = text.trim();
      if (!body) return null;
      if (!live) {
        fail('Not connected to the server — those words were NOT structured.');
        return null;
      }
      if (generatingRef.current) {
        notify('Something else is still running. Your words are still here — try again in a moment.');
        return null;
      }
      generatingRef.current = 'focus-author';
      setGenerating('Reading what you wrote');
      try {
        const start = await startAuthor(body);
        // Busy is ORDINARY, not breakage — one LLM job at a time, shared with plan generation.
        if (start.kind === 'busy') {
          notify('Something else was already running. Your words are still here — try again in a moment.');
          return null;
        }
        if (start.kind === 'failed') {
          fail(`Those words were NOT structured. ${start.error}`);
          return null;
        }

        const deadline = Date.now() + POLL_TIMEOUT_MS;
        let lastReadError = '';
        for (;;) {
          // Status is checked BEFORE the first sleep: a job that finished quickly should not
          // cost a fixed wait, and the first read is what tells us it is running at all.
          const st = await focusStatus();
          if (st.ok && st.data.state === 'error') {
            fail(`Reading what you wrote failed. ${st.data.error ?? ''}`.trim());
            return null;
          }
          if (st.ok && st.data.state !== 'running') break;
          if (!st.ok) lastReadError = st.error;
          if (Date.now() >= deadline) {
            // Deliberately not "it failed": the run may still be going. What is true is that we
            // stopped waiting.
            fail(
              lastReadError
                ? `Still reading what you wrote, and the server stopped answering. ${lastReadError}`
                : 'Still reading what you wrote after five minutes. Nothing was saved.',
            );
            return null;
          }
          await sleep(FOCUS_POLL_MS);
        }

        const res = await focusResult();
        if (!res.ok) {
          fail(`Those words were structured, but the answer could not be read. ${res.error}`);
          return null;
        }
        const fields = res.data.fields;
        if (res.data.empty || !fields) {
          // No fields means nothing was understood. Saying so beats a form of blanks presented
          // as what it heard.
          notify('Nothing came back for that. Your words are still here — try saying it again.');
          return null;
        }
        // The sentence she typed, kept for the commit that follows. See `authoredRawRef`.
        authoredRawRef.current = typeof res.data.raw_text === 'string' ? res.data.raw_text : body;
        return formFromFields(fields);
      } finally {
        generatingRef.current = null;
        setGenerating(null);
      }
    },
    [live, fail, notify],
  );

  /**
   * THE ONE SENTENCE SHE ACTUALLY TYPED, held between authoring and the commit that follows.
   *
   * ⚠ WHY THIS EXISTS. `raw_text` is not metadata: both write routes hand it to
   * `signal_log.log_signal(...)`, and `signal_log.jsonl` is documented and read as JUNE'S OWN
   * TYPED WORDS. `saveFocusPeriod` used to send `form.intent` — so changing only a workday end
   * time on an existing period wrote a "correction" signal whose text was the period's
   * pre-existing intent sentence, attributed to her, which she did not say on that action.
   * Commit `1522ad5` removed a machine-written record from that same log for the same reason.
   *
   * Set only by `authorFocus` (preferring the server's own record of what it received), read only
   * on the author path, and cleared once committed — so it can never be re-attributed to a later
   * action she did not type into. The per-field edit path has no sentence of hers at all and
   * sends none.
   */
  const authoredRawRef = useRef<string>('');

  /**
   * THE FOCUS PERIOD WRITE — `POST /api/focus/commit` for a new one, `POST /api/focus/update`
   * for an edit in place.
   *
   * It used to be `saveFocus`, a pure local state change: every field she edited was gone on
   * reload, under a toast reading "Focus period updated". Both endpoints were already live and
   * nothing called them.
   *
   * ⚠ THREE OUTCOMES, NOT TWO. `api/focus.ts` translates the routes' `{"blocked":[...]}`-on-a-200
   * refusal into its own variant, and it lands here as a NOTICE naming the field — never as a
   * success (which would claim a save the server declined) and never as a failure (which would
   * tell her something broke when she has simply not put an end date in yet).
   *
   * ⚠ The success signal comes only after the server confirms, and the period list is then
   * RE-READ rather than patched from the form: what the Focus tab shows is what persisted. Both
   * routes already re-fetch and verify every written field before answering ok, so their
   * confirmation is worth waiting for.
   */
  const saveFocusPeriod = useCallback(
    async (view: 'edit' | 'author', editId: string | null, form: FocusForm): Promise<boolean> => {
      if (!live) {
        fail('Not connected to the server — that focus period was NOT saved.');
        return false;
      }
      // An edit route with nothing to edit cannot be carried out. Falling through to `commit`
      // here would create a SECOND period while she believed she was changing the one in front
      // of her — proceeding as if a failed step had succeeded, which the house rule forbids.
      // Unreachable today (every edit route sets the id); it says so rather than assuming.
      if (view === 'edit' && !editId) {
        fail('That focus period has no id on it, so the change was NOT saved.');
        return false;
      }

      const fields = fieldsFromForm(form);
      // ⚠ ONLY WORDS SHE TYPED. See `authoredRawRef` — sending the form's intent here wrote her
      // own pre-existing sentence into her own-words log as something she had just said.
      const raw = view === 'edit' ? '' : authoredRawRef.current;
      const res =
        view === 'edit'
          ? await updateFocus(editId!, fields, raw)
          : await commitFocus(fields, raw);

      if (res.kind === 'needs') {
        notify(missingSentence(res.missing));
        return false;
      }
      if (res.kind === 'failed') {
        fail(`That focus period was NOT saved. ${res.error}`);
        return false;
      }

      // Read back, so the list shows the server's period rather than the form's hopes.
      const after = await apiGet<PeriodsResponse>('/api/periods');
      if (after.ok) {
        setPeriods(periodsFromLive(after.data));
      } else {
        // The WRITE succeeded — both routes proved it before answering. Saying "not saved" here
        // would be a false claim about her data; what failed is the re-read.
        fail(`That focus period was saved, but the list could not be re-read. ${after.error}`);
        return true;
      }

      /**
       * ⚠ THE PERIOD SAVED AND PART OF IT DID NOT — both facts, in one sentence.
       *
       * The server reactivates the as-needed tasks she named AFTER the period is written and
       * proved, and deliberately does not roll the period back if that step goes wrong; it
       * reports what could not be turned back on alongside the success rather than dropping it.
       * Saying only "Focus period saved" here would put a success message over a partly
       * discarded instruction — she asked for the dishes back and they would stay off with
       * nothing anywhere saying so.
       *
       * It goes through `fail`, not `succeed`: `fail` is what reaches `errorLog`, and a task that
       * silently stayed off has to leave a trace. The sentence leads with the save so she is
       * never told her period was lost when it was not, and the return value stays `true` —
       * the period IS written, so the editor closes rather than inviting a duplicate write.
       */
      const stillOff = [
        ...res.unresolved,
        ...res.notReactivated.map((f) => (f.id ? `${f.id} (${f.error})` : f.error)),
      ];
      if (stillOff.length > 0) {
        const saved = view === 'edit' ? 'That focus period was updated' : 'That focus period was saved';
        const what = stillOff.length > 1 ? 'these did not' : 'this did not';
        fail(`${saved}, but you asked for something to start again and ${what}: ${stillOff.join(', ')}.`);
        return true;
      }

      succeed(view === 'edit' ? 'Focus period updated' : 'Focus period saved', null);
      // Committed — her sentence is on the record now and must not be attached to a later action.
      authoredRawRef.current = '';
      return true;
    },
    [live, fail, succeed, notify],
  );

  const dismissToast = useCallback(() => setToast(null), []);

  /**
   * The Log button's write — `POST /api/logday`, which appends to `scripts/data/signal_log.jsonl`
   * through `signal_log.log_signal(source="log_day")`.
   *
   * The endpoint was already live; the port left the button dropping her text on the floor
   * (documented at `AddScreen`'s `LogTab`). This is that wire-in.
   *
   * ⚠ The toast is raised ONLY after the server confirms. The old behaviour flashed "Logged"
   * unconditionally, which is the worse half of the bug: a silent drop still looks like a save.
   * Returns whether it landed, so the caller only clears the box on a real write.
   */
  const logDay = useCallback(
    async (text: string, tags: string[], extras?: LogExtras): Promise<boolean> => {
      const body = text.trim();
      if (!body) return false;
      if (!live) {
        fail('Not connected to the server — that was NOT logged. Nothing was saved.');
        return false;
      }
      // ⚠ ONLY PRESENT KEYS ARE SENT, key by key, deliberately. An entry with no snapshot must
      // produce exactly the body the Add tab's Log button has always sent — 45 entries were
      // written by that path. Spreading `extras` in, or assigning `shot: extras?.shot`, would
      // put `shot: undefined` (or nothing at all, but via a different code path) into the
      // object and change the shape of the unchanged path. `marks` is sent only when something
      // was actually drawn: an empty array is not a mark.
      const payload: Record<string, unknown> = { text: body, tags };
      if (extras?.shot) payload['shot'] = extras.shot;
      if (extras?.view) payload['view'] = extras.view;
      if (extras?.target) payload['target'] = extras.target;
      if (extras?.via) payload['via'] = extras.via;
      if (extras?.marks?.length) payload['marks'] = extras.marks;
      if (extras?.size) payload['size'] = extras.size;

      const res = await apiSend<{ ok?: boolean; tags?: string[]; shot?: string | null }>(
        'POST',
        '/api/logday',
        payload,
      );
      if (!res.ok) {
        fail(`That was NOT logged, so nothing was saved. ${res.error}`);
        return false;
      }
      succeed('Logged', null);
      return true;
    },
    [live, fail, succeed],
  );

  /**
   * THE WORK-BLOCK CHECK — one control, two views (`WorkBlock` in the schedule, the block row in
   * `PriorityList`), one write.
   *
   * It used to write `ui.chunked` and flash "Done". `ui.chunked` is in-memory state: she checked
   * a chunk of work off, read the confirmation, reloaded, and it was gone. `POST /api/complete`
   * already did the right thing and nothing called it.
   *
   * ⚠ WHAT THE SERVER DOES WITH THIS, AND WHY IT IS NOT A DONE-WRITE. `complete_task_row`
   * dispatches on `plan_store.is_block_item` (`server.py:187`): a block id goes to
   * `chunk_log.log_chunk` plus `plan_store.mark_block_chunked`, and NEVER to
   * `task_actions.complete_task`. A block must not finish the project underneath it — it comes
   * back tomorrow (`display_grain_design.md` §REVISION 2026-07-14 §B). That is why this does not
   * route through `apply(toggleDone(...))` like every other check on the surface.
   *
   * ⚠ THE ORDER OF THE TWO EFFECTS IS THE POINT. The box checks immediately, because a checkbox
   * that waits on a round trip reads as broken; the SUCCESS SIGNAL waits for `res.ok`, because
   * that is the only moment anything is known to have been saved. `logDay` is the model. A
   * failure puts the box back and says so — the optimistic change is never left standing.
   */
  const chunkBlock = useCallback(
    async (id: string, done: boolean): Promise<void> => {
      if (!id) {
        // A block row with no id cannot be addressed on the server, so there is nothing to
        // write and nothing to claim. Silence here would look exactly like a save.
        fail('That work block has no id on it, so the time on it was NOT saved.');
        return;
      }
      // Optimistic VISUAL state, keyed by the block's id. Explicitly `false` on an un-check
      // rather than deleted, so it outranks the plan row's own `didChunkToday` until the
      // server's answer arrives.
      setUi((prev) => ({ ...prev, chunked: { ...prev.chunked, [id]: done } }));
      const undo = () => {
        setUi((prev) => ({ ...prev, chunked: { ...prev.chunked, [id]: !done } }));
      };

      if (!live) {
        undo();
        fail('Not connected to the server — the time on this was NOT saved.');
        return;
      }

      const res = await apiSend<{
        completed?: Record<string, unknown>;
        uncompleted?: Record<string, unknown>;
        plan?: LivePlan;
      }>('POST', done ? '/api/complete' : '/api/uncomplete', { id });

      if (!res.ok) {
        undo();
        fail(
          `Could not ${done ? 'record time on that' : 'reopen that'} — it is NOT saved. ${res.error}`,
          { nodeId: id },
        );
        return;
      }
      // The response carries today's rewritten plan cache, whose block row now holds
      // `did_chunk_today`. Taking it is what makes the check survive a reload rather than
      // depending on `ui.chunked` staying alive.
      if (res.data.plan && !res.data.plan.empty) setPlan(planFromLive(res.data.plan));
      succeed(done ? 'Done' : 'Reopened', null);
    },
    [live, fail, succeed],
  );

  /**
   * THE ARC STEP CHECK — `chunkBlock` one level deeper, and a DIFFERENT kind of write.
   *
   * It used to be `applyPlan(toggleArcStep(...))`. `PlanResult` is `{plan, toast}` — it has no
   * `write`, so no network call was reachable through that path at all. June tapped a step, read
   * "Nice — one down", and it was gone on reload.
   *
   * ⚠ A STEP IS NOT A BLOCK, AND THE DIFFERENCE IS THE WHOLE POINT. The block header's check
   * means "I did a chunk today" and must never finish the project underneath it. An arc step
   * carries a REAL Anytype task id (verified on her live plan 2026-07-19 — every step of all
   * three arc-carrying items, including "Cancel food stamps"), so checking it completes THAT
   * TASK and nothing else. `complete_task_row` (`server.py:163`) dispatches as-needed →
   * recurring → `is_block_item` → real task; a step id is none of the first three, so it lands
   * on `task_actions.complete_task` and the parent project is never touched. Sending the
   * BLOCK's id here instead would be the right-looking wrong write: a logged work chunk in
   * place of her finished task.
   *
   * ⚠ THE ID IS WHAT TRAVELS; THE ADDRESS ONLY LOCATES THE PIXELS. `toggleArcStep` addresses a
   * step as `plan.blocks[b].items[i].arc[s]`, and a regeneration reassigns those slots — which
   * is why `chunkBlock` moved its state off slot keys. Nothing slot-keyed is persisted here
   * either: the address is used once, synchronously, to compute the optimistic redraw, and the
   * server write is keyed by `ref.id` alone.
   *
   * ⚠ ROLLBACK RESTORES THE WHOLE PLAN, NOT THE TAPPED STEP. `toggleArcStep` is not its own
   * inverse: checking the current step also promotes the next `ahead` step to `here`, and
   * re-toggling does not demote it. Re-toggling as an undo would leave the wrong step
   * highlighted as the one she is on.
   *
   * Effect order follows `chunkBlock` exactly: the box checks immediately, and the success
   * signal waits for `res.ok`, because that is the only moment anything is known to be saved.
   */
  const completeArcStep = useCallback(
    async (ref: ArcStepRef, done: boolean): Promise<void> => {
      if (!ref.id) {
        // A step with no id cannot be addressed on the server. Toggling it locally anyway would
        // look exactly like a save, which is the failure this whole seam exists to end.
        fail('That step has no id on it, so it was NOT saved.');
        return;
      }
      // Read through a ref, not the closure, for the reason `graphRef` records: a callback held
      // by a rendered row can outlive the render it closed over, and a stale plan here would
      // resolve the address against a document that is no longer on screen. It also keeps this
      // callback's identity stable across every plan change.
      const before = planRef.current;
      const next = toggleArcStep(before, ref.bandIndex, ref.itemIndex, ref.stepIndex);
      // ⚠ `toggleArcStep` answers an address that resolves to nothing with a SILENT no-op — the
      // same plan object back, no toast. Left alone that is a checkbox that is tapped and does
      // nothing, forever. Identity comparison is exact here because the function returns the
      // input reference unchanged on a miss.
      if (next.plan === before) {
        fail('Could not find that step in today’s plan, so it was NOT saved.', { nodeId: ref.id });
        return;
      }
      setPlan(next.plan);

      if (!live) {
        setPlan(before);
        fail('Not connected to the server — that step was NOT saved.', { nodeId: ref.id });
        return;
      }

      const res = await apiSend<{
        completed?: Record<string, unknown>;
        uncompleted?: Record<string, unknown>;
        plan?: LivePlan;
      }>('POST', done ? '/api/complete' : '/api/uncomplete', { id: ref.id });

      if (!res.ok) {
        setPlan(before);
        fail(
          `Could not ${done ? 'check that step off' : 'reopen that step'} — it is NOT saved. ${res.error}`,
          { nodeId: ref.id },
        );
        return;
      }
      // The response carries today's rewritten plan cache. `plan_store._mark_arc_step` flips the
      // step's state there using the same rule as `toggleArcStep`, so adopting the server's
      // answer confirms the optimistic redraw rather than undoing it — and THAT is what makes
      // the check survive a reload.
      if (res.data.plan && !res.data.plan.empty) setPlan(planFromLive(res.data.plan));
      // The pure function's own wording, so the surface and the model cannot drift apart.
      if (next.toast) succeed(next.toast, null);
    },
    [live, fail, succeed],
  );

  /**
   * ── THE THREE PER-ROW PLAN WRITES ────────────────────────────────────────────
   *
   * All three take the same shape, and it is NOT `chunkBlock`'s. There is no optimistic step
   * here: what changes on screen IS the rewritten plan the server sends back, so there is
   * nothing to show early and nothing to roll back. The row does not move until the write is
   * known to have landed — which for a control that rearranges her day is the honest order.
   *
   * Each closes the panel it was invoked from on success, so the surface returns to rest without
   * a second tap; a FAILURE leaves it open, because she may well want to try again.
   */
  const rowWriteGuard = useCallback(
    (id: string, whatFailed: string): boolean => {
      if (!id) {
        fail(`That row has no id on it, so ${whatFailed} was NOT saved.`);
        return false;
      }
      if (!live) {
        fail(`Not connected to the server — ${whatFailed} was NOT saved.`);
        return false;
      }
      return true;
    },
    [live, fail],
  );

  const notTodayRow = useCallback(
    async (id: string, kind: 'task' | 'block'): Promise<void> => {
      if (!rowWriteGuard(id, 'that')) return;
      const res = await notTodayApi(id, kind);
      if (res.kind === 'failed') {
        fail(`That is still on today's list — it was NOT removed. ${res.error}`, { nodeId: id });
        return;
      }
      if (res.plan) setPlan(planFromLive(res.plan));
      setUi((prev) => {
        const editOpen = { ...prev.editOpen };
        delete editOpen[id];
        return { ...prev, editOpen, movePick: prev.movePick === id ? null : prev.movePick };
      });
      /**
       * The removal HAPPENED even when a log write did not — so the outcome leads, and the
       * caveat follows it IN THE SAME SIGNAL.
       *
       * ⚠ REVIEW FINDING B4, and the comment here used to describe behaviour the code did not
       * have. `setToast` is a SINGLE SLOT: raising the outcome and then raising the caveat
       * replaced the first with the second, so the only thing she ever saw was the caveat —
       * exactly the inversion this comment forbids. Two calls cannot say two things here.
       *
       * The durable record is kept separately and deliberately. A partial write that exists only
       * in a toast she dismissed is not diagnosable afterwards, which is what `errorLog` is for;
       * but a failure-kind toast would have told her the removal did not happen, and it did.
       */
      if (res.warning) {
        logFailure(res.warning, { objectId: id, before: null });
        succeed(`Taken off today. ${res.warning}`, null);
      } else {
        succeed('Taken off today', null);
      }
    },
    [rowWriteGuard, fail, succeed],
  );

  const setRowDuration = useCallback(
    async (id: string, minutes: number): Promise<void> => {
      if (!rowWriteGuard(id, 'that length')) return;
      const res = await setDurationApi(id, minutes);
      if (res.kind === 'failed') {
        fail(`That length was NOT saved. ${res.error}`, { nodeId: id });
        return;
      }
      if (res.plan) setPlan(planFromLive(res.plan));
      setUi((prev) => {
        const editOpen = { ...prev.editOpen };
        delete editOpen[id];
        return { ...prev, editOpen };
      });
      // The minutes the SERVER confirmed, not the ones that were asked for.
      succeed(`Set to ${res.minutes} minutes`, null);
    },
    [rowWriteGuard, fail, succeed],
  );

  const moveRow = useCallback(
    async (id: string, target: { block: number | null; position: number }): Promise<void> => {
      if (!rowWriteGuard(id, 'that move')) return;
      const res = await moveItemApi(id, target);
      if (res.kind === 'failed') {
        fail(`That did not move — it is where it was. ${res.error}`, { nodeId: id });
        return;
      }
      if (res.plan) setPlan(planFromLive(res.plan));
      setUi((prev) => {
        const editOpen = { ...prev.editOpen };
        delete editOpen[id];
        return { ...prev, editOpen, movePick: null };
      });
      succeed('Moved', null);
    },
    [rowWriteGuard, fail, succeed],
  );

  /**
   * Settings (Task 10) — `POST /api/settings`, wiring the backend radio and the hobby switch.
   *
   * ⚠ THE KEY TRANSLATION. The client's `hobby` and the server's `include_hobby_block` are the
   * same value under two different names — `SettingsScreen` and `UiState` never learn the
   * server's name; the mapping happens once, here.
   *
   * Same optimistic-then-confirm shape as `chunkBlock`, for the same reason: a radio dot or a
   * switch that waits on a round trip before moving reads as broken. The snapshot for rollback is
   * taken from `setUi`'s own `prev`, not from a `ui.backend`/`ui.hobby` closure — a closure over
   * the outer `ui` would go stale if she taps twice before the first request settles, and the
   * second rollback would restore the FIRST tap's value instead of what was on screen before it.
   */
  const saveSettings = useCallback(
    (patch: Partial<Pick<UiState, 'backend' | 'hobby'>>): void => {
      let before: Pick<UiState, 'backend' | 'hobby'> | null = null;
      setUi((prev) => {
        before = { backend: prev.backend, hobby: prev.hobby };
        return { ...prev, ...patch };
      });
      const revert = () => {
        const snapshot = before;
        if (snapshot) setUi((prev) => ({ ...prev, ...snapshot }));
      };

      if (!live) {
        revert();
        fail('Not connected to the server — that choice was NOT saved.');
        return;
      }

      const body: Record<string, unknown> = {};
      if (patch.backend !== undefined) body.backend = patch.backend;
      if (patch.hobby !== undefined) body.include_hobby_block = patch.hobby;

      void (async () => {
        const res = await apiSend<{ backend?: string; include_hobby_block?: boolean }>(
          'POST',
          '/api/settings',
          body,
        );
        if (!res.ok) {
          revert();
          fail(`That choice was NOT saved. ${res.error}`);
          return;
        }
        succeed('Saved', null);
      })();
    },
    [live, fail, succeed],
  );

  /**
   * THE GENERATION SEAM — the action row's six buttons, wired to the two endpoints that already
   * implement them.
   *
   * ⚠ THE THING THIS EXISTS TO GET RIGHT: **202 IS NOT A FINISHED WRITE.** Both `/api/refresh`
   * (`server.py:910`) and `/api/negotiate` (`:921`) hand the work to a background thread and
   * answer 202 `{state:'running', started}` immediately. Raising a success there would say the
   * plan changed while generation had not begun to run — the same "told her it happened when it
   * did not" bug class this whole thread is closing. So: start it, poll `/api/status` until the
   * generation settles, re-read `/api/plan`, and only then say anything.
   *
   * The polling loop tolerates a FAILED status read rather than reporting failure on the first
   * one. A dropped request mid-generation does not mean the generation failed, and saying it did
   * would be its own false claim; the deadline is what ends the wait, and it ends it by saying
   * the plan has not changed YET, which is true.
   */
  const generatingRef = useRef<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  const regenerate = useCallback<AppState['regenerate']>(
    async (req, label) => {
      if (!live) {
        fail('Not connected to the server — the plan was NOT changed.');
        return false;
      }
      if (generatingRef.current) {
        fail(
          `A new plan is already being made, so "${label}" did not start. The plan on screen has not changed.`,
        );
        return false;
      }
      generatingRef.current = label;
      setGenerating(label);
      try {
        // Three request shapes, two endpoints. `preset_id` and `message` are the two halves of
        // `/api/negotiate`'s own body (`server.py:934` / `:973`); sending neither is the 400 it
        // answers at `:1000`, which is why the message variant carries her text and not a flag.
        const start =
          req.kind === 'refresh'
            ? await apiSend<{ state?: string; started?: boolean }>(
                'POST',
                '/api/refresh',
                req.capacity ? { capacity: req.capacity } : {},
              )
            : await apiSend<{ state?: string; started?: boolean }>(
                'POST',
                '/api/negotiate',
                req.kind === 'preset'
                  ? { preset_id: req.presetId }
                  : // ⚠ `operation:'generate'` is REQUIRED here — June's decision 2026-07-19.
                    // The server defaults a free-text message to `reorder` (`server.py:978`),
                    // which only reshuffles what is already on screen. But the box asks
                    // "e.g. I only have 30 min and need to stay horizontal" — that is a
                    // statement about her capacity, and answering it needs the model to
                    // RESELECT from the whole task list, not shuffle a plan built for a
                    // different day. `generate` routes to `generate_plan(extra=message)`, which
                    // is the path that actually carries her words into the prompt.
                    { message: req.message, operation: 'generate' },
              );
        if (!start.ok) {
          fail(`Could not start a new plan, so the plan on screen has not changed. ${start.error}`);
          return false;
        }
        // `_start_generation` answers `started:false` when another generation holds the lock —
        // still a 202. Nothing of hers was started, so she is told that and not left waiting on
        // a result that belongs to someone else's request.
        if (start.data.started === false) {
          fail(
            'A new plan was already being made, so this one did not start. The plan on screen has not changed.',
          );
          return false;
        }

        const deadline = Date.now() + POLL_TIMEOUT_MS;
        let lastReadError = '';
        for (;;) {
          await sleep(POLL_MS);
          const st = await apiGet<{ state?: string; error?: string }>('/api/status');
          if (st.ok && st.data.state === 'error') {
            fail(
              `Making a new plan failed, so the plan on screen has not changed. ${st.data.error ?? ''}`.trim(),
            );
            return false;
          }
          if (st.ok && st.data.state !== 'running') break;
          if (!st.ok) lastReadError = st.error;
          if (Date.now() >= deadline) {
            fail(
              lastReadError
                ? `Still making a new plan, and the server stopped answering. The plan on screen has not changed. ${lastReadError}`
                : 'Still making a new plan after five minutes. The plan on screen has not changed.',
            );
            return false;
          }
        }

        const planRes = await apiGet<LivePlan>('/api/plan');
        if (!planRes.ok) {
          fail(`A new plan was made, but it could not be read. ${planRes.error}`);
          return false;
        }
        if (planRes.data.empty) {
          fail('The new plan came back with nothing in it, so nothing is shown.');
          return false;
        }
        setPlan(planFromLive(planRes.data));
        succeed('Your plan is updated', null);
        return true;
      } finally {
        generatingRef.current = null;
        setGenerating(null);
      }
    },
    [live, fail, succeed],
  );


  /**
   * ── THE ADD TAB'S REAL WRITE PATH ─────────────────────────────────────────
   * The receipt of what capture has actually filed, read from the server rather than built as
   * she types. `capture()` in `model/mutations.ts` is the v4 MOCK — it fabricates one local Task
   * under a hardcoded project and weeds nothing. This is the real one.
   *
   * Server-truth rather than local: the weeder decides how many objects a sentence becomes and
   * what they are, so only the server knows what landed. It also means a reload no longer loses
   * the receipt, and that an undo can dim a row from what the server says rather than from a
   * local splice that could disagree with storage.
   */
  const [captureEntries, setCaptureEntries] = useState<readonly WeedEntry[]>([]);
  /**
   * The last turn's `result_summary` ("added 3, skipped 1"). Held because `failed[]` and
   * `skipped[]` are NOT in the receipt — this string is the only channel by which a skipped or
   * failed item ever reaches her. Dropping it would rebuild the silent-failure path.
   */
  const [captureSummary, setCaptureSummary] = useState<string | null>(null);

  const loadCapture = useCallback(async () => {
    if (!live) return;
    const res = await getCaptureSession();
    if (!res.ok) {
      fail(`Could not read what was added. ${res.error}`);
      return;
    }
    setCaptureEntries(res.data.entries ?? []);
  }, [live, fail]);

  /**
   * Run one weed, end to end: start it, wait for the shared generation to finish, then read what
   * landed. Resolves true only when the receipt has been refreshed from a completed run, so the
   * caller clears her text on a proven capture and never on a dropped one.
   *
   * Shares `generatingRef` with `regenerate` on purpose: the SERVER holds one generation lock for
   * both, so letting the client start a capture while a plan is generating would just earn a
   * `started:false` and a confusing wait.
   */
  const runCapture = useCallback(
    async (text: string): Promise<boolean> => {
      const body = text.trim();
      if (!body) return false;
      if (!live) {
        fail('Not connected to the server — that was NOT added. Nothing was saved.');
        return false;
      }
      if (generatingRef.current) {
        fail(`Something else is still running, so that was NOT added. Nothing was saved.`);
        return false;
      }
      generatingRef.current = 'capture';
      setGenerating('Sorting what you wrote');
      try {
        const start = await startCapture(body);
        // Busy is an ORDINARY outcome, not breakage (contract §:414 — "must not surface it as a
        // failure"), so it is said plainly and without the register of something going wrong.
        if (start.kind === 'busy') {
          fail('Something else was already running, so that was NOT added. Your text is still here.');
          return false;
        }
        if (start.kind === 'failed') {
          fail(`That was NOT added, so nothing was saved. ${start.error}`);
          return false;
        }

        const deadline = Date.now() + POLL_TIMEOUT_MS;
        let lastReadError = '';
        for (;;) {
          await sleep(POLL_MS);
          const st = await getStatus();
          if (st.ok && st.data.state === 'error') {
            fail(`Sorting what you wrote failed, so nothing was saved. ${st.data.error ?? ''}`.trim());
            return false;
          }
          if (st.ok && st.data.state !== 'running') break;
          if (!st.ok) lastReadError = st.error;
          if (Date.now() >= deadline) {
            // Deliberately NOT "it failed": the run may still be going. What is true is that we
            // stopped waiting, and that anything it filed will be in the list once it finishes.
            fail(
              lastReadError
                ? `Still sorting, and the server stopped answering. Check the list in a moment. ${lastReadError}`
                : 'Still sorting after five minutes. Check the list in a moment.',
            );
            return false;
          }
        }

        const res = await getCaptureSession();
        if (!res.ok) {
          // The weed itself finished — saying "not added" here would be a false claim about her
          // data. What failed is the READ.
          fail(`That was added, but the list could not be read. ${res.error}`);
          return true;
        }
        const entries = res.data.entries ?? [];
        setCaptureEntries(entries);
        const lastWeed = [...entries].reverse().find((e) => e.intent === 'weed');
        setCaptureSummary(lastWeed?.result_summary ?? null);
        succeed(lastWeed?.result_summary || 'Added', null);
        return true;
      } finally {
        generatingRef.current = null;
        setGenerating(null);
      }
    },
    [live, fail, succeed],
  );

  /** Archive one just-captured object, then re-read so the row dims from server truth. */
  const undoCapture = useCallback(
    async (id: string) => {
      if (!live) {
        fail('Not connected to the server — nothing was undone.');
        return;
      }
      const res = await undoCaptured(id);
      if (!res.ok) {
        fail(`Could not undo that — it is still there. ${res.error}`);
        return;
      }
      await loadCapture();
      succeed('Undone', null);
    },
    [live, fail, succeed, loadCapture],
  );

  /**
   * The when-chip. Sends a TOKEN and lets the server re-anchor it to a date; a rendered label
   * would put date arithmetic in the browser. Non-optimistic, like the old surface: on failure
   * the chip is left showing what is actually stored.
   */
  const setCapturedWhen = useCallback(
    async (id: string, when: WhenToken) => {
      if (!live) {
        fail('Not connected to the server — that was NOT changed.');
        return;
      }
      const res = await rescheduleCaptured(id, when);
      if (!res.ok) {
        fail(`Could not change when that is for — it is NOT saved. ${res.error}`);
        return;
      }
      await loadCapture();
      succeed(res.data.when_label ? `Set to ${res.data.when_label}` : 'Saved', null);
    },
    [live, fail, succeed, loadCapture],
  );

  /** The engagement chip on a captured Project — correcting what the weeder proposed. */
  const setCapturedEngagementFor = useCallback(
    async (id: string, from: string, to: string) => {
      if (!live) {
        fail('Not connected to the server — that was NOT changed.');
        return;
      }
      const res = await setCapturedEngagement(id, from, to);
      if (!res.ok) {
        fail(`Could not change how that project is engaged — it is NOT saved. ${res.error}`);
        return;
      }
      await loadCapture();
      succeed(`Set to ${res.data.engagement ?? to}`, null);
    },
    [live, fail, succeed, loadCapture],
  );

  return {
    graph,
    idx,
    schema,
    plan,
    periods,
    ui,
    toast,
    up,
    apply,
    applyPlan,
    applyPeriods,
    fail,
    refuse,
    logDay,
    authorFocus,
    saveFocusPeriod,
    chunkBlock,
    completeArcStep,
    finishedEditing,
    notTodayRow,
    setRowDuration,
    moveRow,
    backendOptions,
    saveSettings,
    regenerate,
    generating,
    presets,
    dismissToast,
    captureEntries,
    captureSummary,
    loadCapture,
    runCapture,
    undoCapture,
    setCapturedWhen,
    setCapturedEngagement: setCapturedEngagementFor,
  };
}
