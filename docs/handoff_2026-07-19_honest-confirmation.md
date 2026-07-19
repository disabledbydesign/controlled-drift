# Handoff — the honest-confirmation build (2026-07-18 → 07-19)

*For the next agent. Read this, then `docs/superpowers/plans/2026-07-18-persistence-seam.md` (the live task list with per-task status), then `docs/BUILD_DOC.md`. Branch: `feat/overlay-actionable`.*

---

## 1. What this thread is fixing

**The surface tells June things happened when they did not.** She is neurodivergent and built this system so her commitments live outside her head; a control that claims success it has not earned is the most damaging thing it can do, because it destroys the trust the whole system runs on.

The root cause, verified rather than assumed: **14 of the 19 write endpoints on the server were built and unreachable from the app.** The buttons existed; nothing called them. So the work is *wiring*, not building.

⚠ **June's correction, 2026-07-18, which reframed the plan:** *"we want those functions to work, not just tell me they aren't working. We really need both sides in the fix."* An earlier draft would have made the broken controls politely refuse. That is the fallback for genuine residue only — **the deliverable is working functions.**

---

## 2. What is DONE (all committed, all mutation-verified)

| Commit | What |
|---|---|
| `3474eef` | Tap targets ~4× larger; her tuned visuals untouched (hit area only) |
| `14c1766` | The Friction button actually writes; toast only after the server confirms |
| `b09cde9` | Focus tab shows her REAL periods — it was rendering invented sample data |
| `fc27805` | 15 tests for `GET /api/periods`, which shipped with none |
| `b37b0fc` | **Three chores she had finished rendered as outstanding** — recurring completions live in `completion_log`, never on the graph node, and every consumer read the graph |
| `d44d214` | `Plan.shape` narrowed; the server's own `header` carried across |
| `b1124e7` | `addressedWorkItems` — items carry the band/item address arc check-off needs |
| `328e455` | A block in the priority list opens to its arc |
| `1df84fe` | The plan's own shape decides how it renders |
| `7485088` | Generation buttons regenerate for real (202 + poll), with an in-progress state |
| `3940fe7` | **Move works in BOTH directions** (backend; `move_item_later` → `move_item`) |
| `b721103` | Work-block checks persist, keyed by real id not slot position |
| `465271e` | The Life admin preset — and the merge bug that kept ANY new preset from reaching an existing install |
| `27c29ca` | **The ask box stops deleting what she wrote**; "Add something" removed; Life admin wired |
| `c20a956` | Failed writes reach a durable log |
| `188107f` | A message in the ask box REGENERATES rather than reshuffles (her decision) |

**Suites:** 417 frontend, 1052 backend, `tsc` clean.

---

## 3. What is LEFT

From the plan, in order:

1. **Task 4 — the row action panel**: not-today, duration, move. All four backends live. The OLD overlay had exactly this per row (`docs/overlay_daily.html:2140-2155`: "move later ›", a duration chip reading *"set chunk length"* on a block and *"set duration"* on a task, and "not today"). ⚠ Touch-friendly, NOT drag — drag does not work on her phone. ⚠ Not-today must log to `corrections`, not `signal_log`: that log is **her own words**, and a machine-recorded deferral does not belong in it. 8 existing `plan_deferral` entries need moving.
2. **Task 9 — the focus editor actually saves.** Currently every field she edits is discarded on reload under a toast reading "Focus period updated". Five endpoints live and unreachable. ⚠ Also delete `formFromDraft`'s hardcoded `start:'2026-07-21'`/`end:'2026-07-27'` and the "Here's what I heard" screen — it claims a comprehension no model performed. ⚠ `commit`/`update` answer a REFUSED write with **HTTP 200 + `{"blocked":[...]}`** (`server.py:1313`, `:1396`); `client.ts` reads any 200 as success. Handle in the focus caller, NOT the generic client. ⚠ A refusal for missing dates is **not a failure** — do not send it down the error channel or log it as breakage.
3. **Task 10 — Settings.** Offers `claude|local|api`; server accepts `mistral|openrouter|claude|local`. So `api` is a guaranteed 400 and `mistral` (her production default) is not offered. Read options from `GET /api/settings`.
4. **Press feedback** — see §5.
5. **Task 6 — honest refusal** for whatever cannot be wired.
6. **Task 7 — live-verify** and **Task 8 — cross-family review**. Both REQUIRED.

---

## 4. ⚠ WHAT IS UNVERIFIED — read before claiming anything works

**Almost nothing built on 2026-07-19 has been driven on her real data.** Tests and `tsc` are green; that is not evidence the features work. This repo lost a full rebuild to code that matched its spec and passed 599 tests while being functionally broken.

Specifically unverified:
- The ask box sending a real message end to end (and that the plan CHANGES CONTENT, not just order)
- The work-block check surviving a real reload
- Bidirectional move through any UI (no control exists yet)
- The failure log receiving a record from a real browser
- The in-progress treatment on her phone

**Verified live:** the Life admin preset (202 → generation → plan led with chores, stamped `source: preset:life-admin`), and the done-state fix (all six completed items render checked).

⚠ **Her plan was REGENERATED TWICE as a side effect of testing** (2026-07-18 and 07-19). Legitimate — it is what the buttons do — but it was not something she asked for. Tell her before doing it again.

---

## 5. June's open decisions — do NOT decide these

- **Press feedback on buttons.** Her words: *"clicking the button gives no ui signal — right now it feels like its just a flat surface with no action on it."* ⚠ **This is NEW DESIGN WORK, not a port regression.** There is no press/active treatment anywhere in `app/src` **and none in the v4 mockup either** — the three `:active` grep hits are variables *named* `active` (a selected state). Derive from existing tokens; must work in both themes, which fork on SHAPE not only colour; show her before it settles.
- **The "Regenerating…" treatment** (`7485088`). Also derived, not transcribed — the gallery has no pending state anywhere in its trusted sections (`4a`, `4c`, `5a`, `5c`) and contains zero keyframes. v4's only live-state animation is broken (`box-shadow:0 0 0 3px currentColor22` is not a valid colour, and the keyframe is absent from `app/index.html`).
- **The gold block-row colour** in the priority list — chosen to distinguish "did a chunk of ongoing work" from a rose "task finished".
- **Label drift**: her stored preset reads *"Quick wins first"*; the button says *"Quick wins only"*.

---

## 6. Process rules that actually caught things

**Every task: fresh implementer → main-session QC → the main session independently re-runs the load-bearing mutation.** Do not trust an implementer's mutation report. That caught: an implementer whose entire sweep ran against reverted code, a wiring error where absent state defaulted to `false` instead of deferring to the server's record, and an untested precedence rule where un-checking a block would spring it back to checked.

⚠ **A mutation must be confirmed to have APPLIED before its run is trusted.** This fired **four times** in one session — including a regex that matched a *comment* instead of the code, producing five green tests that proved nothing. Assert the anchor matches exactly once and that the file changed, before running.

⚠ **Before asserting anything is missing, unused, or broken: grep the exact name in the source of truth.** Five false claims were made to June in this session from unvalidated queries — a wrong field name (`kind` vs the wire's `block`), a DOM never measured, and a relayed claim never checked (`str()` is a local helper, not Python). Each cost real work; one grew an entire seven-task plan on a false premise.

⚠ **Tests can assert the bug.** Two previously-passing tests certified the ask box's unconditional clear — they were tests *for* the deletion. A green suite over a data-losing control is exactly what this plan exists to stop.

---

## 7. Two corrections to inherited instructions

- **The server CAN be restarted, safely** — `CLAUDE.md` now carries the protocol (launchd kickstart, confirm the PID changed AND the bind reads `*:5050`, never `127.0.0.1`). The blanket "do NOT restart" in the seam plan is **superseded** and was blocking real backend live-verify.
- **`BUILD_DOC` §3 clause 5** (update `field_semantics.py`) is scoped to changes that alter what reads or writes an **Anytype field**. A JSONL log append is not one. An implementer correctly refused this instruction; `DOES` is keyed by Anytype field display name and its test validates field entries.

---

## 8. Parallel thread

Another agent worked this same tree and is **paused**. Its territory: the native macOS app (`scripts/desktop*`, `Controlled Drift.command`, `app/src/shell/DeskShell.tsx`, `Surface.tsx`, `native.ts`), the Add-tab weeder wiring, and the inherit/override fix. All committed. Its work interleaved with this thread's twice — check `git status` before assuming an uncommitted file is yours.

⚠ It also landed `8e90625`, which **promoted the new surface to `/`** and changed network exposure. June was trying to reach the server from a hotel at the time; her phone access should be re-confirmed rather than assumed.
