# Honest Confirmation Implementation Plan

> **For agentic workers:** implement task-by-task via the build-loop — fresh subagent per task, per-task review, live-verify, then a NON-Claude cross-family review before the thread closes (`subagent-driven-development`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** The controls WORK. Where one genuinely cannot yet, it says so plainly instead of claiming success — but honest refusal is the fallback for the residue, not the deliverable.

⚠ **REVISED AGAIN 2026-07-18 after June's correction:** *"we want those functions to work, not just tell me they aren't working. We really need both sides in the fix."* She is right, and the evidence backs her: **14 of the 19 write endpoints on the server are built and unreachable from the app.** Every control this plan was going to teach to refuse politely has a working backend already. The work is wiring, not building.

**Architecture:** Wire each dead control to the endpoint that already implements it, one control per commit, each live-verified against her real data. The honest-refusal path is used only where a control genuinely has no endpoint. That path already exists — `WriteIntent`'s `unsupported` variant, handled at `useAppState.ts:583`, rolls back the optimistic change and tells her *"Could not [X] — this surface cannot save that yet, so nothing changed."* This plan routes the controls that currently lie through that existing path, one call site at a time. The type-level hardening that an earlier draft led with is deferred; it is optional once the call sites are honest.

**Tech Stack:** React 19 + Vite 8 + TypeScript (`app/`), vitest.

---

## ⚠ REVISION 2026-07-18 — this plan was rewritten after four reviewers rejected its first draft

The first draft proposed making `write` required on every mutation result, with a new `{op:'local', why}` case, so that "forgot to persist" and "nothing to persist" would stop looking alike. **All four reviewers independently found the same fatal flaw**, and it is recorded here because the current shape only makes sense against it.

**The flaw: it would have certified the lies.** `flash()` is defined three times (`useSurface.ts:102, 177, 195`) as a write-less result, and feeds ~12 call sites whose truth values differ completely. Making `write` required turns those three definitions into compile errors; the draft's instruction was to fix them mechanically with `{op:'local'}`; and the draft's next task exempted `local` from the confirmation gate. Net effect: every lying button — including the one that destroys her text — would emerge type-checked, blessed, and still lying.

**What the draft missed:** `op:'unsupported'` already exists (`types.ts:216`) and already does the honest thing. The draft introduced `local` as a near-twin without ever discussing the relationship, and gave an author no rule for choosing between them.

**The other correction, which is about her and not about types:** the draft's end state left several controls SILENT rather than lying. A reviewer pushed back — for someone who relies on this system to hold her commitments, a save that produces no signal is not clearly better than a false one, because nothing then distinguishes "saved" from "broken." Hence the goal line above: **not silence — a refusal.**

**Three factual errors in the draft's own evidence**, all of which would have misled a builder:
- Its audit table claimed the object editor had "0 falsely claims success". `Detail.tsx:323` fires `flash('Saved')` on blur while the title write is on a 600ms debounce, so the claim can precede the request entirely. At least two sites, in the area the draft scoped out. **The table is deleted; it was inherited, its categories were undefined, and one probed row was wrong.**
- It cited the focus endpoints at `server.py:1228`/`:1314`. They are at **`:1304`** (blocked at `:1313`) and **`:1384`** (blocked at `:1396`).
- It said `errorLog.ts:61` "posts failures to `POST /api/log/correction`". It posts nothing — `sink` is null and line 61 is a comment saying Track B will wire it. Route absent, sink unwired, no requests made.

---

## Global Constraints

- Branch `feat/overlay-actionable`. **Another thread owns**: `app/src/shell/DeskShell.tsx`, `Surface.tsx`, `native.ts`, `native.test.ts`, `scripts/desktop_app.py`, `scripts/desktop/`, `scripts/build_desktop_app.py`, `.gitignore`, `Controlled Drift.command`, and everything under `docs/`. Do not touch, stage, or commit them.
- **No metaphors in any June-facing string.** Literal words. Agent-facing comments exempt.
- No silent failures — raise, never bare `assert`.
- **A test is unverified until you have watched it fail.** Assert POSITIVELY — name what must be true. An assertion that a wrong thing did NOT happen also passes against a control wired to nothing; two reviewers rejected a task on exactly that.
- `vite.config` sets `globals: false` — component tests MUST call `afterEach(cleanup)` explicitly.
- Do NOT restart the server. launchd owns it with `CD_BIND=0.0.0.0`, which is what lets her phone reach it.
- **Before asserting anything is missing, unused, or broken: grep the exact name in the source of truth.** Five false claims were made in one session from unvalidated queries. One `grep` each would have caught them.

## The decision rule every task depends on

When a control does not persist, it is exactly one of three things. **This distinction is the plan.**

| | Means | What to do |
|---|---|---|
| **Has a live endpoint** | The overwhelming majority — 14 of 19 write routes are built and unwired. | **WIRE IT.** This is the deliverable. |
| **Genuinely nothing to save** | View state — a filter, a collapsed row, a pane width. No server meaning by design. | Leave it. It never claimed to save. |
| **Real edit, genuinely no endpoint** | Nothing on the server implements it. | `unsupported` — she is TOLD. Interim only; log it as a backend gap. |
| **Open design question** | Nobody has decided whether it should persist. | `unsupported`, and it stays on the open-questions list. |

### The wiring map — verified live 2026-07-18

| Control that currently lies | Endpoint that already implements it |
|---|---|
| "↻ Fresh plan" | `POST /api/refresh` (202 + poll `/api/status`) |
| "Low energy today", "Quick wins only", "Life admin & household", "I'm stuck" | `POST /api/negotiate` `{preset_id}` |
| The "tell me what you need" box ("Sent", destroys her text) | `POST /api/negotiate` |
| "Move this later" | `POST /api/task/move` ⚠ later-only; earlier needs `plan_store.move_item_later` changed |
| Work-block check ("Done", reverts) | `POST /api/complete` — `plan_store.is_block_item` routes a block to the chunk log |
| Not-today (no control exists yet) | `POST /api/task/not-today` |
| Duration (no control exists yet) | `POST /api/duration` |
| Focus editor ("Focus period updated", sends nothing) | `POST /api/focus/author,reflect,commit,edit,update` |
| Settings backend + hobby toggle | `GET`/`POST /api/settings` ⚠ app offers `api` (invalid); server wants `mistral` (her default) |

⚠ **`priOrder` is the third kind, not the first.** Her manual reordering of the priority list never leaves the client (`PriorityList.tsx` → `ctx.up({priOrder})`, no server reference anywhere), so it is lost on every reload. But `api_contract_v2.md` §6 Q1 records its persistence as **undecided**. Do NOT classify it as "genuinely nothing to save" — that would write a sentence certifying her data loss as intentional and close her open question in the direction of losing her work. Route it to a refusal and leave the question open.

---

### ✅ Task 1 (DONE `7485088`): The generation controls actually regenerate the plan

**Files:** `app/src/components/today/TodayPanel.tsx` (`:241-249`), `app/src/shell/useAppState.ts` (a generation action + poll), tests alongside each.

Six buttons currently call `flash()` and nothing else. Three of their messages — "Regenerating plan…", "Trimmed to one small win", "Showing quick wins" — describe a plan change that does not happen.

- `↻ Fresh plan` → `POST /api/refresh` `{capacity?}`. Answers **202** `{state:'running', started}` and generation is ASYNC — poll `GET /api/status` until it settles, then re-read the plan. A 202 is not a finished write; do not signal success on it.
- The other four → `POST /api/negotiate` `{preset_id}`. Read the handler at `server.py:921` for the real preset ids and the response shape; **do not invent ids** — an unknown one answers 400.

⚠ Generation takes tens of seconds on her production backend (mistral). The button must show that work is in progress, and must not look idle or finished while it runs.

⚠ **June decided 2026-07-18: BUILD the in-progress state, derived from the existing design system — do not report it as a gap and do not invent it ad hoc.** Review first, in this order: `app/src/shell/signals.ts` (the existing signal vocabulary), `design/tokens/tokens.ts` (use existing tokens; introduce no new colour or radius values), `design/mockups/color-system.html` (⚠ trusted regions are ONLY `4a`, `4c`, `5a`, `5c` — `1a`–`3c` are superseded), and `design/mockups/review-reorganize-mobile-v4.html` for any existing pending/loading/disabled treatment. It must work in BOTH themes, which fork on shape and not only colour. If the gallery has no precedent, say so explicitly and describe what the treatment was derived from — do not present an invention as a transcription. Name the ELEMENT the evidence came from, not just a line number.

- [ ] **Step 1:** Write failing tests — POSITIVE. Each button issues the right request; a 202 does NOT raise success; success is raised only once the poll reports the plan settled; a failed request produces a failure she can read.
- [ ] **Step 2:** Run, watch them fail.
- [ ] **Step 3:** Implement. One button per commit where practical.
- [ ] **Step 4:** Run, watch them pass.
- [ ] **Step 5:** Mutation-check — signal success straight off the 202 (the poll test must fail); drop the poll (same); swap two preset ids (the request test must fail). Restore each.
- [ ] **Step 6:** Commit.

---

### 🔄 Task 2 (IN FLIGHT): The "tell me what you need" box sends, and never eats her words

**Files:** `app/src/components/today/TodayPanel.tsx` (~`:293`), tests.

Today: `ctx.flash('Sent')` then `ctx.up({ask:''})`. Nothing reads `ui.ask`. It is a 150px box prompting *"e.g. I only have 30 min and need to stay horizontal"* — it invites a real message, says it sent, and deletes it. **Same shape as the Friction-log bug fixed earlier today, in a box that invites more words.**

Wire it to `POST /api/negotiate` (free text, not a preset — confirm the body key against `server.py:921`).

⚠ **`logDay` (`useAppState.ts:851-871`) is the model to copy**: it raises success only after `res.ok`, and returns whether it landed so the caller clears the box ONLY on a confirmed write. Her text must survive every failure path.

- [ ] **Step 1:** Failing tests — the request carries her text; the box is cleared ONLY on confirmed success; on failure the text is still present AND she is told it did not send.
- [ ] **Step 2–6:** run-fail, implement, run-pass, mutation-check (clear unconditionally → the text-preserved assertion must fail), commit.

---

### ✅ Task 3 (DONE `b721103`): Checking a work block records a chunk that survives a reload

**Files:** `app/src/components/today/WorkBlock.tsx` (`:75`), `app/src/components/today/PriorityList.tsx` (`:223`), tests.

Both say "Done"/"Reopened" over `ctx.ui.chunked`, which is UI state that dies on reload. **They are the same control in two views and must stay identical.**

`POST /api/complete` `{id}` already handles this: `plan_store.is_block_item` routes a block id to the chunk log rather than marking the project done. The block's id is its `project_id` (`adapt.ts:161` documents why).

⚠ **`chunked` is keyed `bandIndex-itemIndex`.** A regenerated plan reassigns those slots, so the key must move to the real id before this can persist. That is part of this task, not a follow-on.

⚠ Per `display_grain_design.md` §REVISION §B a block check means **"did a chunk today"**, never "this project is finished." Nothing here may mark the project done.

- [ ] **Step 1:** Failing tests — checking a block issues `/api/complete` with the project id; success is raised only after confirmation; the state is keyed by id, not slot position.
- [ ] **Step 2–6:** as above. Mutation: key by slot again (the id test must fail); mark the project done (the chunk test must fail).

---

### ⬜ Task 4: The row action panel — not today, duration, move

**Files:** a new panel component under `app/src/components/today/`, `useAppState.ts` write intents, tests.

The OLD overlay had exactly this per row (`docs/overlay_daily.html:2140-2155`): a **"move later ›"** button, a duration chip reading *"set chunk length"* on a block and *"set duration"* on a task, and a **"not today"** button. The new surface has no equivalent — its edit chip opens the object editor instead. All three backends are live:

- `POST /api/task/not-today` `{id, kind:"task"|"block", name?}` — cache-only by design; an 8h session window makes a same-day regenerate honour it, then it expires. **This is exactly what June asked for: holds for the day, does not leak into future days.**
- `POST /api/duration` `{id, minutes}` — dispatches on `is_block_item`: a block sets the durable chunk length, a task sets `Duration min`.
- `POST /api/task/move` `{id, target_block?, position?}` — ⚠ **DECIDED by June 2026-07-18: change the plan store FIRST, then wire the control.** She wants both directions and does not want a later-only control shipped in the interim. **Task 11 therefore runs BEFORE this task** — do not wire a move control against the later-only backend.

⚠ **June's correction on logging:** not-today currently writes to `signal_log`. That log is *her own words* — 44 of its entries are things she typed. A machine-recorded deferral does not belong there. Route it to `corrections` instead, and move the 8 existing `plan_deferral` entries across. `BUILD_DOC` §3 clause 5 applies: update `scripts/field_semantics.py` in the same commit.

⚠ Touch-friendly, not drag — she raised this: drag does not work on her phone.

- [ ] **Step 1–6:** TDD per control, mutation-check each, one commit per control.

---

### 🔄 Task 5 (IN FLIGHT): Failed writes reach a durable log

**Files:** `scripts/server.py` (new route), `app/src/shell/errorLog.ts`, `tests/`.

`logFailure` records to `console.error` and a 50-entry in-memory array that dies on reload. `setFailureSink` has no production caller. June: *"what matters more is error logging if something fails."*

⚠ **Do NOT add a new log file** — `scripts/data/` already holds 13 `.jsonl` files. Route through `corrections_log` (`kind, before, after`).

⚠ **The sink is called synchronously and unguarded** (`errorLog.ts:86`, `if (sink) sink(rec);`). A throwing poster would throw out of `logFailure` → `fail()` → `rollback()` and reject the unawaited `performWrite` promise — turning a *reported* failure into an unhandled rejection. A poster that reported its own failure through `fail()` would recurse infinitely. **Fire-and-forget, try/caught, console-only on its own failure.**

⚠ `BUILD_DOC` §3 clause 5: update `scripts/field_semantics.py` in the same commit.

- [ ] **Step 1–6:** TDD both sides; mutation — make the sink call unguarded, the propagation test must fail.

---

### ⬜ Task 6: Honest refusal for whatever is left

**Files:** whatever Task 1–5 could not wire.

After the wiring, list what still cannot save. For each, route through the existing `unsupported` intent (`types.ts:216`, handled `useAppState.ts:583`) so she is TOLD rather than misled — and record each as a backend gap.

⚠ **Silence is not an acceptable outcome.** A control that stops lying and says nothing has not been fixed.

⚠ **`priOrder` belongs here, not in "nothing to save."** Her reordering is lost on every reload, and `api_contract_v2.md` §6 Q1 records its persistence as UNDECIDED. Refuse honestly and leave the question open — do not write a rationale certifying the loss as intentional.

- [ ] **Step 1–6:** as above.

---

### ⬜ Task 7: Live-verify — REQUIRED, not a test

- [ ] **Step 1:** `cd app && npx vite build`. `app/dist` is gitignored; port 5050 serves the built bundle, so source changes are invisible until this runs.
- [ ] **Step 2:** Press "↻ Fresh plan" on her real plan. Confirm work-in-progress is visible, that success appears only when generation finishes, and that the plan on screen actually changes.
- [ ] **Step 3:** Type into the ask box, press Send. Confirm it sends, and that on a forced failure **her text is still there.**
- [ ] **Step 4:** Check a work block. **Reload.** Confirm it is still checked.
- [ ] **Step 5:** Use not-today on one real item; confirm it leaves today's list. Regenerate; confirm it stays gone today. **Do not verify the next-day expiry by waiting** — read the session-window code and say it is unverified.
- [ ] **Step 6:** Set a duration; reload; confirm it held.
- [ ] **Step 7:** Every remaining unwired control refuses out loud. No silent controls.
- [ ] **Step 8:** Force a failure via the devtools offline toggle, NOT by stopping the server. Confirm she is told, and that the entry reaches `corrections`.
- [ ] **Step 9:** The arc still works — expand a block, tap a step, watch the "here" marker move. `toggleArcStep` answers a bad address with silence, so a rendered checkbox proves nothing.
- [ ] **Step 10:** Report honestly, including anything unverified. Do NOT mark done on a green suite.

⚠ `agent-browser screenshot` HANGS INDEFINITELY — do not call it. Use DOM/text reads or `cd app && node scripts/shot.mjs "today" celestial`.

---

### ⬜ Task 8: Cross-family review — REQUIRED before this thread closes

`~/.claude/skills/requesting-code-review/github_models_review.py`. A NON-Claude family — a same-family reviewer shares the generator's blind spots. ⚠ ~8k cap: chunk per file, a file and its tests in the SAME chunk or the reviewer false-flags "no tests." **If it errors — it returned 429 rate-limits earlier today — fall back to a Claude review with a VISIBLE note that the cross-family pass was skipped and why. Never silently.**

---

### ⬜ Task 9: The focus editor actually saves

**Files:** `app/src/components/focus/FocusEditor.tsx`, `app/src/model/periods.ts`, `app/src/shell/useAppState.ts`, `app/src/api/client.ts` or a focus-specific caller, tests.

`saveFocus` is a pure local state change — every field she edits (name, dates, intent, availability window, note, plan shape, workday hours, days off, foreground and paused projects) is gone on reload, under a toast reading "Focus period updated". Five endpoints are live and unreachable: `/api/focus/author`, `reflect`, `commit`, `edit`, `update`.

⚠ **Delete the fabricated reflect-back.** `formFromDraft` (`model/periods.ts:77-95`) hardcodes `start:'2026-07-21'` and `end:'2026-07-27'` and cuts her text at the first comma for a name. The next screen is headed **"Here's what I heard"** and says *"It reads back what it heard for you to check — it won't reword your intent."* No model ran. That is the invented-content bug in its most direct form: the surface claiming a comprehension that did not happen. `/api/focus/author` is what actually structures her words.

⚠ **`commit` and `update` answer a REFUSED write with HTTP 200** and a body of `{"blocked":[...]}` (`server.py:1313`, `:1396`). `client.ts:62` treats any 200 without `ok:false` as success, so a refusal would raise a success toast. **Handle this in the focus caller, NOT in the generic `request()`** — teaching the shared client one endpoint family's private convention would impose it on all traffic.

⚠ **A refusal is not a failure.** A period blocked for missing dates means "you haven't filled the dates in yet" — it must NOT go down the error channel, must NOT be logged as breakage, and must NOT address her in the register of something having gone wrong. Name the missing field.

⚠ `‹ Back` (`FocusEditor.tsx:45-64`) silently discards the whole in-progress form. Once saving works this becomes the remaining way to lose it. Flag to June; do not fix silently.

- [ ] **Step 1–6:** TDD per endpoint, mutation-check each, one commit per endpoint where practical.

---

### ⬜ Task 10: Settings works, against the real backend vocabulary

**Files:** `app/src/screens/SettingsScreen.tsx`, `app/src/shell/useAppState.ts`, tests.

Neither control reaches the server — `grep` for `/api/settings` across `app/src` returns nothing. Both endpoints are live.

⚠ **The vocabulary is wrong and would 400 on contact.** The app offers `claude | local | api` (`useAppState.ts:244`); the server accepts `mistral | openrouter | claude | local` (`server.py:73`). So `api` is a guaranteed failure, and **`mistral` — her decided production default — is not offered at all.** `GET /api/settings` returns the real option list with a descriptor per backend, computed from what the backend actually does. **Read the options from the server; do not hardcode them.**

⚠ The hobby toggle's client key is `hobby`; the server's is `include_hobby_block`. Map it.

- [ ] **Step 1–6:** TDD, mutation-check (hardcode the old three → the options test must fail), commit.

---

### ✅ Task 11 (DONE `3940fe7`) — ran before Task 4 (June's decision, 2026-07-18): Move works in both directions

**Files:** `scripts/plan_store.py`, `scripts/server.py`, the move control from Task 4, `tests/`.

`move_item_later` raises `ValueError` unless the destination is strictly later, and its priority-shape sibling is the same. June wants both directions — *"I should be able to move things earlier as well as later."*

This is a genuine backend change, not a relabel. Generalise the move to accept any destination, keeping the re-flow of clock times that the later-only path already does, and keep the honest failure for a destination that is out of range or identical.

⚠ Touch-friendly, not drag — drag does not work on her phone. The Map tab's existing move picker (tap the item, tap where it goes) is the pattern to reuse.

- [ ] **Step 1–6:** backend TDD in `tests/` first, then the control, then live-verify a real move in both directions.

---

## Sequencing — why this order, since all of it is being built

1–3 are her daily surface and include the control that destroys her words. 4 adds back the row actions the old overlay had and she lost. 5 is the failure logging she named as mattering more than success messaging. 6 catches the residue. 7–8 are the gates. 9 is the largest single win after the Today tab — the focus editor currently discards every edit she makes. 10 is small and independent. 11 was going to land last, but June decided 2026-07-18 to **change the plan store before wiring any move control** rather than ship a later-only one — so it runs before Task 4.

**Nothing here is optional or cut.** The only thing genuinely left out is making `write` required at the type level — that is hardening, it is worth doing after the call sites are honest, and it must not be attempted before `flash` is split by call site (an earlier draft of this plan would have used it to certify every lie).

---

## Added mid-build at June's request (not in the original task list)

- **✅ The Life admin preset** (`465271e`). The button existed with no instruction behind it. Her words: *"prioritize household chores and life admin tasks."* Written as a `reorder` preset in the register of her existing two. ⚠ The real bug was that a NEW preset could never reach an existing install — `load_actions` backfilled missing FIELDS but never missing presets — so the merge was fixed rather than her file hand-edited. Live-verified: 202 from `/api/negotiate`, generation ran, plan led with chores, stamped `source: preset:life-admin`.
- **🔄 Remove "Add something" from the action row.** Navigation, not a plan action; the Add tab is on the tab bar. In flight with Task 2.
- **⬜ Press feedback on buttons.** June, 2026-07-19: *"clicking the button gives no ui signal — right now it feels like its just a flat surface with no action on it."* ⚠ Verified: there is NO press/active treatment anywhere in `app/src`, and **none in the v4 mockup either** — the three `:active` grep hits are variables named `active` (a selected state), not press rules. So this is genuinely absent from the original design, NOT lost in the port. New design work: derive from existing tokens, must work in both themes (which fork on shape, not only colour), and show June before it settles.
- **⬜ Preset label drift.** Her stored preset reads *"Quick wins first"*; the button says *"Quick wins only"*. Harmless, but they have diverged.

## Verification standard applied throughout this plan

Every task: fresh implementer, main-session QC, and **the main session independently re-runs the load-bearing mutation** rather than trusting the implementer's report. That has already caught: an implementer whose mutation sweep ran against reverted code, a wiring error where absent state defaulted to `false` instead of deferring to the server's record, and an untested precedence rule where an un-check would spring back to checked.

⚠ **Mutations must be confirmed to have APPLIED before their run is trusted.** Two mutations in this session silently failed to match their anchor and produced green runs that proved nothing. Assert the anchor matches exactly once before writing.
