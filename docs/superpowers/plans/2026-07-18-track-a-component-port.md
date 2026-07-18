# Track A — v4 Component Port Implementation Plan

> **For agentic workers:** implement task-by-task via the build-loop — fresh subagent per task, per-task review, final whole-branch review (`subagent-driven-development`). Steps use checkbox (`- [ ]`) syntax.
>
> **Read `docs/BUILD_DOC.md` first** — it defines where this loop's autonomy ends and what "done" means here.

**Goal:** Port the v4 mockup's UI into working React components against the extracted fixtures, at high fidelity, so the surface runs end-to-end on fixture data before any backend integration.

**Architecture:** One component library over two render paths (phone shell, desktop multi-column), exactly as v4 structures it. Styles are inline style objects reading from `design/tokens/tokens.ts`. Data comes from `app/src/fixtures/` via the model layer; no network calls in this track.

**Tech Stack:** React 19, Vite 8, TypeScript 7 (strict, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`), vitest.

## Global Constraints

Copied from `docs/handoff_2026-07-17_surface_rebuild.md` and `docs/BUILD_DOC.md`. **Every task's requirements implicitly include these.**

- **Styles stay INLINE STYLE OBJECTS.** Do NOT convert to CSS classes, CSS variables, styled-components, or a `css` prop. That translation is where finetuned detail leaks. This is load-bearing, not an oversight.
- **Three-way source of truth:** gallery (`design/mockups/color-system.html`) = how it looks · spec (`docs/review_reorganize_backend_spec.md`) = what data exists · mockup (v4) = behavior and layout.
- **Themes fork on SHAPE, not just color.** v4 branches on `isHW()` at ~30 sites (checkbox geometry, radii, mono-vs-sans, glyph prefixes). Preserve every branch.
- **Object-type color comes from `typeRamp`** in tokens.ts (the gallery legend), never v4's `TYPE` map — which colored TASK green and collided with completion green.
- **Do NOT port:** `renderApp()` (~697), `header()` (~344), `tab()` (~357) — dead legacy path. The excitement picker — field is cut.
- **No metaphors in user-facing text.** Hard access requirement.
- **v4 is large with very long lines** — grep/sed/awk only, never read it whole.
- **Another thread works this branch** (`scripts/server.py`, `scripts/daily_plan.py`). Commit only Track A files.
- Do not run Python scripts or anything touching Anytype.

## File Structure

```
app/src/
  theme/          ✅ tokens re-export, useTheme, starfield        (done)
  fixtures/       ✅ schema, tree, plan, periods, types           (done)
  model/          graph, schema derivation, effective(), mutations
  components/
    atoms/        taskCheck, switchEl, chipEl, badge, rail, glow…
    rows/         row(), taskRow(), recurringPlanRow(), arcStep()
    detail/       detail(), inheritRow(), typeSection(), recurrenceCard()
    panels/       filterMenu, addPanel, chipStrip, menuStrip, pickerPage
  screens/        today, add, map, routines, strategies, settings, focus
  shell/          AppShell (phone), DeskShell (desktop), tab routing
  App.tsx         entry — becomes the real app; token-check page moves to /check
```

---

## Task 1 — Visual atoms  ✅ DONE (gate applied, e05157d)

- [x] Port `topAccent` 169, `glow` 170, `bevel` 171, `appBg` 172, `taskCheck` 183, `switchEl` 188, `badge` 336, `rail` 337, `chipEl` 338, `roundCheck` 1042, `editChip` 1043 to `app/src/components/atoms/`
- [x] **Review gate:** PASS WITH FIXES — 5 gallery-verified corrections applied, incl. a cascade error from the token docstring
- [x] `npx tsc --noEmit && npx vite build` clean

## Task 2 — Model layer  ✅ DONE (gate applied, fde7405)

- [x] Port `index`/`node`/`pathTo`/`removeNode` 277-280, `applySchema` 126, `effective` 486, `isInactive`, `statusColor`, `sideColor`, `chipsFor`, `typeOptions` 291, and all mutations (282-299, 487) to `app/src/model/`
- [x] Mutations converted from in-place `bump()` to pure state→state functions — the ONE place restructuring is expected
- [x] vitest installed; 63 tests incl. tri-state, `isInactive` per level, reparenting, type conversion, delete-with-children, structural sharing, `isOwnValue`
- [x] **Review gate**: PASS WITH FIXES — `INHERIT` was unported, `move()` took a stale-able index, a fabricated symbol in a comment
- [x] ⚠ Report whether v4's `effective()` actually implements spec §4's tri-state (absent = inherit, present-but-empty = intentional none). **ANSWER: v4 implements it CORRECTLY.** No divergence.

## Task 3 — App shell + tab routing  ← THE WIRE-IN POINT

Everything after this renders *into* the shell. Nothing downstream is "done" until it appears here.

- [ ] `shell/AppShell.tsx` — phone frame, `appHeader` 940, `appTabs` 949, six-tab state (`today | add | map | routines | strategies | settings`), gear→settings
- [ ] Nav animation grammar from v4: forward enters right, back enters left (keyframes already in `index.html`)
- [ ] `App.tsx` renders the shell; move the token-check page to a `/check` route so it stays available
- [ ] Each tab renders a visible placeholder naming itself — so the shell is verifiable before the tabs exist
- [ ] **Live check:** load `/app/`, switch all six tabs, toggle both themes, screenshot
- [ ] **Review gate** · commit

## Task 4 — `row()`, the workhorse

`row()` 436 is used by the tree, routines, strategies AND the picker. Getting it right covers four screens.

- [ ] Port `row()` 436 + `lead()` 385, consuming Task-1 atoms and Task-2 `chipsFor`
- [ ] Indentation expresses depth; hue does NOT (gallery: nested children carry status glyph colors only)
- [ ] Expand/collapse via `toggleCollapse` 676
- [ ] Render a real fixture tree inside the Map tab — **wire-in, not a storybook**
- [ ] **Live check:** screenshot both themes against gallery 4a/4c
- [ ] **Review gate** · commit

## Task 5 — `detail()`, the editor

- [ ] Port `detail()` 541 + `headerDone` 521, `headerTypeBadge` 525, `typeSection` 292, `locationBlock` 500, `inheritRow` 488, `recurrenceCard` 414
- [ ] Every field's options derive from the schema (`OPTS`/`CTRL`/`TEXT`) — nothing hardcoded
- [ ] `inheritRow` surfaces the tri-state honestly: inherited-from-ancestor vs. explicitly-set-empty must be distinguishable to the user
- [ ] Edits go through Task-2 pure mutations; state lives in the shell
- [ ] Reachable by tapping a row from Task 4
- [ ] **Live check:** open a task, a project, a recurring, a strategy; change a field; confirm it renders back
- [ ] **Review gate** · commit

## Task 6 — Structure tabs + picker

- [ ] `treeBody` 630 → Map · `recurringBody` 677 → Routines · `strategiesBody` 651 → Strategies
- [ ] `filterMenu` 359, `addPanel` 374, `chipStrip` 464, `menuStrip` 477, `mapControls` 967
- [ ] `pickerPage` 603 — move/re-parent target picker, driven by `moveFor`/`addParentFor`
- [ ] **Live check:** filter each tab, move an object, add a child, convert a type
- [ ] **Review gate** · commit

## Task 7 — Today tab

- [ ] `todayPanel` 977, `focusSlot` 1013, `band` 1053, `planEntry` 1067, `workBlock` 1089, `arcStep` 1099, `interstitial` 1068, `taskRow` 1074, `priorityList` 1024
- [ ] Both shapes: clock `schedule` and flat `priority` (`todayShape` 997)
- [ ] Per spec §14: **no per-item "why" line**, no plan-age line, held-back items expand inline, block chunk-check reads as completion
- [ ] Woven frame always expanded
- [ ] **Live check:** both shapes, check off a task, check off a block, expand held-back
- [ ] **Review gate** · commit

## Task 8 — Add tab + Settings

- [ ] `addLogTab` 1108, `captureTab` 1109, `logTab` 1126, `capture()` 1136 (parses input into a node + receipt)
- [ ] `settingsPanel` 1152, `themeSection` 1144 — theme toggle wires to existing `useTheme`
- [ ] **Live check:** capture text → receipt appears; switch theme from settings and it persists across reload
- [ ] **Review gate** · commit

## Task 9 — Focus period editor

- [ ] `focusPanel` 814, `focusDetail` 813, `focusEditor` 887, `fEditor` 850, `daysOffEditor` 866, `focusFrontPicker` 874, `saveFocus` 920
- [ ] All spec §17 fields incl. **`workday_start`** (new), per-period `days_off`, availability window, plan-shape override, front/paused project lists
- [ ] Paused picker filtered to pausable projects only (not Backburner/Done/Parked/Inactive)
- [ ] ⚠ `docs/ux_consistency_review_2026-07-17.md` #4 notes Back discards the draft silently here while item edits commit as you type. **Port v4's behavior as-is; do not fix.** That is June's call, post-port.
- [ ] **Live check:** author a period, edit fields, save, reopen
- [ ] **Review gate** · commit

## Task 10 — Desktop multi-column

- [ ] `deskApp` 730, `deskCrumbBar` 719, `dragHandle` 718, `w()` 716, resize via mousedown/mousemove (`componentDidMount` 708)
- [ ] Same component library — layout differs, behavior must not
- [ ] **Live check:** resize panes at desktop width; confirm behavior matches phone
- [ ] **Review gate** · commit

## Task 11 — The three genuine additions

Not in v4. Confirmed with June 2026-07-17.

- [ ] **`toast()`** — stubbed in v4 (`return null`; `flash()` 309 sets state, nothing renders it). Becomes the write read-back confirmation. Must say *what actually persisted*, not "Saved."
- [ ] **Orphan buckets** — catch-all sections for unparented objects (tasks/recurrings with no project, workstreams with no parent, projects with no goal; cf. `review_surface.py:234-247`). Render **only when non-empty**. Load-bearing: in a pure Goal→Project→Task tree an unfiled task renders nowhere.
- [ ] **Cross-tab search** spanning Map + Routines + Strategies, showing which tab each hit is in.
- [ ] **Do NOT add** a data-health count line — declined; the buckets' presence is already the signal.
- [ ] **Review gate** · commit

## Task 12 — Integration and live verification  ★ REQUIRED, NOT A TEST

Per `docs/BUILD_DOC.md` §3. **The build is not done without this.** A clean diff is not a working, wired-in feature — this repo has shipped built-but-dead pieces before and it cost a rebuild.

- [ ] Confirm **every** component from Tasks 1–11 is reachable in the running app. Grep for exported components with no importer; a component nothing renders is not done.
- [ ] Serve the built output from `server.py` at `/app/` (static-asset route — currently absent, see `docs/api_contract_v2.md`). The old overlay stays untouched at `/`.
- [ ] Run `/verify`: drive the real running surface — every tab, both themes, phone and desktop widths, check off a task, edit a field, move an object, capture text, author a period.
- [ ] Screenshot each tab in both themes; compare against gallery 4a/4c and 5a/5c.
- [ ] Whole-branch review, then **cross-family review** via `~/.claude/skills/requesting-code-review/github_models_review.py` (~8k cap — chunk per file, file + its tests together). If it errors, fall back to a Claude review **with a visible note that the cross-family pass was skipped and why**.
- [ ] **June's gate:** she drives the running surface and reacts. Her reaction to real output is the highest-quality signal available — do not close the track without it.

---

## Out of scope for Track A

Network calls (Track B + Phase 2), schema writes (human-gated), retiring the old surfaces (Phase 3, June's judgment), acting on the parked UX consistency review (post-port, her call).
