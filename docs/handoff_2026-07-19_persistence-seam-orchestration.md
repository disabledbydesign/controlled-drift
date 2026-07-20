# Handoff — the honest-confirmation build, orchestration session (2026-07-19)

*For the next agent. Read this, then `.git/sdd/progress.md` (the full per-task ledger with every verification), then `docs/superpowers/plans/2026-07-18-persistence-seam.md`. Branch: `feat/overlay-actionable`.*

---

## 1. What this thread is

**The surface told June things happened when they had not.** She is neurodivergent and built this system so her commitments live outside her head; a control that claims a success it has not earned destroys the trust the whole system runs on.

Root cause, verified rather than assumed: **14 of 19 server write endpoints were built and unreachable from the app.** The buttons existed; nothing called them. So the work was wiring, not building.

**Then June used the result and found a defect class every code review had missed.** Her words, and the governing lesson of the whole session:

> *"the agent perhaps followed instructions but in a way that resulted in a build that still doesn't do what the old UI was able to do, or plug into the backend mechanisms we already built for that UI."*

Every review asked *does the button send the right request*. All passed. None asked *does this control know what is already there, is it pleasant to use, does it invite a tap that can only fail*. **Passing the brief is not the bar. Working the way the old surface worked is the bar.**

---

## 2. What landed (~20 commits)

Each one's load-bearing mutation was **independently re-run by the controller**, not trusted from the implementer's report. That caught real problems more than once.

| Commit | What |
|---|---|
| `42ad47b` | Arc step check-off saves. Its second half was in `plan_store._iter_items`, which never descended into `arc` — a frontend-only fix would not have worked |
| `a4a2d8e` | The object editor's "Saved" follows the write; a pending write is no longer dropped on unmount |
| `fe41ffa` `c6dbac1` `35bef92` | Row actions reworked to June's rulings — inline non-reflowing panel, move as visual destinations in the plan itself, desktop drag, `edit` not "when" |
| `135c8fa` | One `edit` per row; the detail view became a panel item |
| `84d22b9` | Fields she never filled in stop claiming values |
| `73ac5cf` | The plan says how old it is, so yesterday's stops reading as today's |
| `3b13992` | Preset buttons read her `actions.json` instead of hardcoded labels |
| `1e029d9` `5b454e5` `e4a09ea` | Her priority ordering persists, keyed by object id, and survives a regeneration by merging on id |
| `e7871dd` | The verification surface — she sees what the model made of her words and corrects each line |
| `c862f8d` `898286a` | Field meanings reach the planner; `Engagement`'s eight hand-copied glosses collapse to one |
| `f73a554` | The duration she already gave it reaches the row |
| `3f2fb35` | `Side` semantics unstaled — was telling models to write `Obligation`, which no longer exists |
| `70d8d55` | Drift skill merged from two diverged copies and **symlinked** — `~/.claude/skills/drift` → `skills/drift` |
| `eaffb1e` | `/api/focus/edit` retirement documented at the endpoint and in the contract |
| `7cea434` | The flaky frontend suite fixed at the cause |

---

## 3. What is LEFT, in priority order

1. **⚠ LIVE-VERIFY (seam Task 7) — do this FIRST, not as a closing formality.** June approved it. Today made the case twice: a green 762-test suite shipped a feature that crashed the instant it touched her real plan, and her durations were silently dropping on exactly the row types nobody spot-checked. **There is NO dev regenerate** — `--dry-context` prints the assembled context with no LLM call; everything else writes her real plan. **First check whether `CD_DATA_DIR` redirects the plan cache and not merely the learning logs** (`scripts/cd_paths.py:25`). If it does, a full real generation can land in a scratch directory and every future build gets to prove itself without rewriting her day. If it does not, go back to June and let her pick the moment.
2. **Finish move-by-id-order.** `docs/wip/2026-07-19-move-by-id-order.patch` (commit `e431e63`) holds a complete, tested server-side migration that was reverted because the client half was never done. Applying it without finishing the client ships a broken contract. The client half is bigger than it looks: `moveTargets.ts` is built entirely around position arithmetic, so it means reworking that module, `MoveTarget`, every `moveItem` caller (Map picker + Today row panel), and their tests — **all in one commit**.
3. **A route to log per-field corrections on the read-back.** June: *"that is exactly the signal we want to keep."* The existing route hardcodes a null "after", which would misstate what she changed, so the last agent left it unlogged rather than false.
4. **The focus period's NAME as a read-back item**, so she can correct it there. Server-side (`focus_period_adapter.reflect_back`), not a client-invented row.
5. **Desktop shell says "click", not "tap"** (the plan-staleness line). June approved.
6. **Strategies default to Active AT CREATION** — stored in Anytype, not painted on at render. June approved.
7. **Block length consults her Strategy.** She created *"Give deep or involved work a two-hour block"* (2026-07-19). `get_chunk_min` still returns a flat `BLOCK_DEFAULT_MIN = 90` and consults nothing. She also wants **the LLM to estimate when nothing is stored**. ⚠ The 90 was traced to its origin: the only mention in any design doc is `review_reorganize_backend_spec.md:57`, where *"work on GRA for 90 min"* is an **illustration of plan grain, not a decision**. An example became a hardcoded rule.
8. **Honest refusal for the residue (seam Task 6)** — see the inventory in the ledger.
9. **Cross-family review (seam Task 8)** — `~/.claude/skills/requesting-code-review/github_models_review.py`, ~8k cap so chunk per file, a file and its tests in the same chunk.

---

## 4. ⚠ THREE CLAIMS THE LAST CONTROLLER GOT WRONG — do not re-inherit them

1. **"`desk.test.tsx` is flaky but passes 18/18 in isolation."** FALSE, and it was relayed to three agents as fact before one checked. It was CPU starvation against a 5s timeout: every failure a timeout, never an assertion; the first-failing test fully synchronous, so it could not race, only be denied CPU. `desk.test.tsx` merely held the test with the least headroom. Fixed in `7cea434`.
2. **`neglect.py`'s docstring was quoted to June as evidence.** June: *"neglect.py was written to do a specific thing, which was a misunderstanding — so we want to check that."* The docstring CLAIMS the backwards logic was fixed 2026-07-13. **Treat that as unverified — read what the code computes.** Two in-code comments were found this week asserting the opposite of what the server does.
3. **"The detail pane is a read-only field display."** June: *"the details page was designed so i could edit it."* A recommendation was built on that false premise and withdrawn.

**The pattern:** a document or comment was trusted instead of the code. `BUILD_DOC` §9.1 already names this.

---

## 5. Open decisions that are JUNE'S — do not resolve these

- **Dread detection (PARKED by her).** Her signals, in her words: dread lives in the **affective fields**; `Access conditions` is *"a good call but honestly its a bit more subtle than that"*; and *"a clear signal is also if I keep not doing it."* Two data sources exist: `neglect.active_untouched` (project grain, completion-based, wired) and every "not today" deferral, which now lands in `corrections_log` (`1522ad5`) and **nothing reads**. The affective field is the only signal carrying a *why*.
- **`Horizon`** lists three values in the drift skill; six exist live. `field_semantics` marks it undesigned.
- **Goal engagement still offers `Sprint`** in her live space, retired 2026-07-16.
- **`Backburner` means two different things** in one assembled context — "note but de-emphasize" for goals, "excluded before you see this" for projects.
- **`field_semantics` contradicts itself on `Goal engagement`** — `FIELDS.usage` says "not yet consumed by code"; `DOES.read_by` correctly says it is. A one-line factual fix to her data-model text.
- **Legacy `Frequency` values** disagree with live `Interval unit` on three routines (Clean the toilet, Take out recycling, Do the dishes). `Frequency` is marked LEGACY and nothing reads it; the stale values still sit in her data.
- **"Anthropic coding-prep study session — Tue/Thu firm"** cannot express its own schedule: the model has only "every N days/weeks/months", so specific weekdays live in the title. A schema gap, not a missing value.

---

## 6. Hazards that cost real time today

- **Fixtures that are too clean hide real bugs.** A green 762-test suite shipped a feature that threw instantly on her real plan: **a work block row has NO `id` — its id is in `project_id`**, and every fixture gave each row an `id`. Three of seven rows on her real fragmented day are blocks. Build at least one fixture from a real payload (`curl -s localhost:5050/api/plan`, read-only).
- **Mutations that silently fail to apply.** Bit three times. `diff` the file after mutating; never trust a match count. One anchor reported a match while the file was unchanged (escaped backslashes inside a regex quote block).
- **Tests that pass against the bug they were written to catch.** Several. A test naming the *mechanism* keeps passing when the mechanism is the bug; it has to name the *outcome*.
- **The shared git index.** Another session's agent left files staged twice; one nearly landed `scripts/` files into an unrelated commit. **Check `git diff --cached` immediately before every commit and use explicit pathspecs.**
- **Vitest 4 silently ignores `poolOptions.forks.maxForks`** — an agent proof-ran a whole suite with no pool cap before `tsc` caught it. Use top-level `maxWorkers`.
- **A load generator invoked by script path is unkillable by `pkill -f`** and orphans onto init. Check `uptime` before trusting any "idle" measurement.
- **`agent-browser screenshot` hangs indefinitely.** Use DOM reads or `cd app && node scripts/shot.mjs "today" celestial`.
- **Server restart:** `launchctl kickstart -k gui/$(id -u)/com.june.controlled-drift.server`, then confirm the PID CHANGED **and** the bind reads `*:5050`. Never hand-start — `server.py` defaults to loopback and silently kills her phone access.

---

## 7. Orchestration notes

- **Serialize `app/` and `scripts/` work.** Two of the controller's own agents collided today; both recovered it, but by luck and careful agents, not design. Another session of June's was also active — ask before assuming a red suite is yours.
- **Every implementer's load-bearing mutation gets independently re-run by the controller.** That caught an implementer whose sweep ran against reverted code, a wiring error defaulting to `false` instead of deferring to the server, and a precedence rule where un-checking sprang back to checked.
- **Two agents died mid-task** (one stalled, one hit a session limit). Both had been told to write their report file **incrementally**; the one that batched it lost all its evidence. Keep that instruction in every brief.

Baselines at handoff: **762 frontend / 1175 backend**, `tsc` clean.
