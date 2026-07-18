# Controlled Drift — build-protocol doc

> **This is the input `writing-plans` step zero looks for.** Its absence was forcing the protocol to
> be re-derived every session. Read this before planning any task; revise it as the build teaches us.
>
> Created 2026-07-18. **First version — unverified in full; the first run through it will teach us.**

`writing-plans` and `subagent-driven-development` are the project-neutral engines. This doc supplies
the project-specific parts they consume: the substrate, where autonomy ends, the sequence, the human
gates, and the launch moves.

---

## 1. The substrate — what we build on and against

| Layer | What it is |
|---|---|
| **Data store** | **Anytype**, local app at `localhost:31009`. Five types: Goal / Project / Task (built-in, extended) / Recurring / Strategy, in the "Get Started" space. Open the app if a call is refused. |
| **Schema tooling** | `scripts/build_*.py` (idempotent create), `scripts/verify_model.py` (expected-property check). `ensure_type` only ever ADDS — removing a property needs an explicit unlink block. |
| **Write layer** | `scripts/gsdo_objects.py` (create/update), `scripts/gsdo_anytype.py` (raw API). ⚠ `create` **dedups by name** and returns an existing id *without writing properties* — see §6. |
| **Server** | `scripts/server.py` — Python **stdlib** `ThreadingHTTPServer`, no Flask/FastAPI, no dependencies. ~34 JSON endpoints, flat if-chain routing, no path params. `CD_BIND`/`CD_PORT` env. |
| **Domain** | `daily_plan.py`, `plan_generate.py`, `plan_store.py`, `capture_generate.py`, `focus_period*.py`, `grain.py`, `datetime_seam.py`, `orient_map.py`. Domain returns data; `server.py` is a thin JSON adapter. |
| **Learning logs** | ~12 append-only `*_log.py` modules. **Never invent a new log** — route new signals through the existing ones. |
| **Frontend (new, 2026-07)** | `app/` — React 19 + Vite 8 + TypeScript. Tokens at `design/tokens/tokens.ts`. Mounts at `/app/`; the old overlay stays at `/`. |
| **LLM backends** | Pluggable: mistral (production default) / openrouter / claude / local. |

**Live self-describe — run these before designing, not after:**
```
python3 scripts/describe_model.py     # the live schema
python3 scripts/whats_open.py         # the live work-stream map
```

---

## 2. The mechanical-vs-situated line — where the agent loop's autonomy ends

Placed by **who bears the cost of an error.**

### The loop may run autonomously (clear objective signal, reversible)
- Editing source, adding/updating tests, running `pytest` / `tsc` / `vite build`.
- Refactors with test coverage; fixing a failing test; typecheck errors.
- Reading Anytype, running `describe_model.py` / `whats_open.py`.
- Committing to a feature branch.
- Writing/updating docs and plans.

### STOP for June — do not proceed
- **Any write to her live Anytype space that changes schema.** Editing `build_*.py` is the agent's
  job; *running* it is not. Same for migrations and property unlinks.
- **Deleting or archiving real objects.** Her data.
- **Design/value decisions** — what a field means, whether a concept earns its place, category names,
  anything affecting what the system *says* to her.
- **Anything the plan didn't anticipate**, plan-conflicts, and genuine ambiguity (SDD local rule 1).
- **Retiring a live surface.** `overlay_daily.html` comes down only when she judges the new one better.
- **Changes to user-facing register/copy** — see §5 access constraints.
- **Pushing to `main`.** Feature branches only unless she asks.

### Judgment calls that look mechanical but are not
- "This field is unused, remove it" — several stored fields are deliberately not-yet-wired. Ask.
- "These two colors are nearly identical, merge them" — she tuned them. Ask.
- "This looks like a typo in her data" — it may be deliberate. Preserve and flag.

---

## 3. Definition of done — the anti-"built-but-dead" rule

This repo's most expensive recurring failure, diagnosed 2026-07-11:

> *"The build process defined 'done' as: unit tests pass + a reviewer approves the code. Nothing ever
> checked whether the thing was wired into the running system and actually worked when used. So pieces
> shipped built-but-dead — passing their own tests, marked done, never connected."*

**A task is done only when all four hold:**

1. **Tests pass** — and they test behavior, not that the code exists.
2. **It is WIRED IN** — the plan named the real call site, and the code is called from it. A module
   nothing imports is not done. A component nothing renders is not done.
3. **The FEATURE was driven on the real runtime** — regenerate the real plan, check off a real task,
   load the real page. Use the `verify` skill. **This is not pytest.** A frame can match every word of
   a spec, pass 599 tests, and still break the function — that has happened here and cost a rebuild.
4. **Read-back where a write is involved** — write → re-fetch → confirm the change is actually present
   → only then report success. "The API returned 200" is not confirmation.

**Every plan's final task is an integration-and-live-verify task. REQUIRED, non-negotiable, not a test.**

**Red flag:** *a clean diff is not a working, wired-in feature.*

---

## 4. Human-review gates — June as co-knower, not rubber stamp

| Gate | When | What she is actually deciding |
|---|---|---|
| **Design approval** | Before any build touching design | "Let's do it" on a concept is NOT approval of a specific design. State the plan explicitly first. |
| **Plan review** | After `writing-plans`, before SDD | Whether the decomposition matches intent. Use `critic-swarm` on the plan first for non-trivial builds. |
| **Live-verify** | End of every build | She drives the real feature and reacts to the artifact. Her reaction to real output is the highest-quality signal available — build a thin real thing and show her. |
| **Cross-family review** | Before a thread closes | `~/.claude/skills/requesting-code-review/github_models_review.py` — a NON-Claude family, because a same-family reviewer shares the generator's blind spots. If it errors, fall back to a Claude review **with a visible note that the cross-family pass was skipped and why** — never silently. ⚠ ~8k token cap: chunk per file, and send a file and its tests in the same chunk or the reviewer false-flags "no tests." |

**How to bring things to her:** options she directs, not questions she must generate answers to. She
directs, reviews, approves — she does not generate. Never use the AskUserQuestion UI tool; ask in prose.

---

## 5. Constraints that hold across every build

1. **No silent failures.** Raise, don't `assert`. Exit non-zero. Never proceed as if a failed step
   succeeded, never silently skip a review, never silently mark a task done.
2. **Idempotent Anytype writes**, always with read-back.
3. **Never scalar-flatten affect fields** (guard #3). `affective`, access conditions and capacity
   signals stay text/tags — never a 1–5 number.
4. **Tests self-clean.** Never leave artifacts in June's real space. `tests/conftest.py`
   sandbox-redirects `CD_CONFIG_DIR`/`CD_DATA_DIR`.
5. **No metaphors in any June-facing text** — hard access requirement. "Runway", "stream",
   "sandcastles" block her parsing. Literal words. Agent-facing text is exempt.
6. **Explain the concept before the label.** A name is a reference key; it only works if the reader
   already holds the concept. Plain words first, name after.
7. **Make ONLY the changes requested.** Don't expand scope or rewrite adjacent content.
8. **Commit only your own files** when threads run in parallel on one branch.

---

## 6. Known live hazards — check before assuming

- **`gsdo_objects.create` dedups by name** and returns an existing object's id *without writing
  properties*. Creating something whose name matches an existing object silently no-ops the fields.
  Tracked in `docs/create_vs_update_design.md`.
- **Anytype schema tag/property DELETE is async** — poll until gone; `find_property` caches.
- **⚠ `POST /spaces/{sid}/search` RETURNS A BROKEN SUBSET.** A `query:""` search returned 99 Tasks
  and 1 Page from a space that actually holds **296 objects across 9 types** — no Goals, no
  Projects, no Strategies. It silently under-reports rather than erroring, so "0 results" from it
  means nothing. **Always use `gsdo_anytype.fetch_all_objects(sid)`**, which pages
  `GET /spaces/{sid}/objects`. This cost two wrong claims to June in one session (that she had no
  Strategy objects, and that Focus Period was not a type).
- **Frontend dev-loop gotchas (2026-07-18).**
  - `agent-browser screenshot` **hangs indefinitely** — reproduced at the raw CDP layer on a blank
    page in fresh headless Chrome, so it is environmental, not app-related. **Do not debug it.**
    Use `cd app && node scripts/shot.mjs "map,today" celestial,hardware`. agent-browser's DOM
    reads, clicks and computed-style reads all work fine; only screenshots are affected.
  - A Vite dev server started as a *tracked* background command gets **killed between turns**.
    Start it detached instead: `cd app && nohup npx vite --port 5173 > /tmp/vite.log 2>&1 & disown`.
  - Component tests: `vite.config` sets `globals: false`, so Testing Library's automatic cleanup
    never registers. Call `afterEach(cleanup)` explicitly or renders accumulate and every
    `getByText` fails with "found multiple elements".
- **`describe_model.py` shows only the five core types.** It is the right tool for the GSDO schema
  and the wrong tool for "does this type exist" — Focus Period, Page, Note and Bookmark are all
  live and absent from its output.
- **Objects-relations read back as bare id STRINGS**, under `"objects"` not `"object"`. This caused a
  load-bearing bug where task→project links always read empty.
- **Anytype normalizes datetimes** — compare dates parsed, not as strings.
- **`archive_object` re-fetch behavior after DELETE is UNCONFIRMED** against the live API (2026-07-17).
  Needs one live undo.

---

## 7. Launch sequence — the literal first moves

Fresh session, new build:

1. **Orient from the live system**, not from docs: `describe_model.py`, `whats_open.py`, plus the
   auto-memory index and this doc. Do not jump to building.
2. **Fire archaeology** — read the real code/spec/data before designing. A cold instance can invoke the
   disposition and still skip the dig, because context-free production is cheaper in the moment. The
   documented template is: early abstract-design failure → forced archaeology → recovery.
3. **Spec**, if the shape isn't settled: `/workshop`, June driving.
4. **Plan**: `/writing-plans` → `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`. Non-trivial plans get
   `/critic-swarm`, then June's reuse-or-reinvent filter on the findings (swarms find frame problems,
   but some suggestions reinvent already-built or deliberately-deferred surfaces).
5. **Build**: `/subagent-driven-development` — fresh implementer per task, fresh reviewer after each,
   ledger at `$(git rev-parse --git-path sdd)/progress.md`.
6. **Verify**: `/verify` — drive the real runtime. Then June reacts to the artifact.
7. **Close**: cross-family review → triage → apply what's real → update memory + this doc.

**Where June drives:** steps 3, 4 (review), 6 (reacting to real output). **Where the agent runs:**
1, 2, 5, and the mechanical half of 7.

---

## 8. Current build sequence (2026-07-18)

Surface rebuild — replaces `overlay_daily.html` AND `surface_template.html`/`surface_serve.py`.
Controlling doc: `docs/handoff_2026-07-17_surface_rebuild.md`. Contract: `docs/api_contract_v2.md`.

- ✅ Phase 0 — tokens reconciled, API contract, app scaffolded, fixtures extracted
- 🔄 Track A — Tasks 1 (atoms) ✅, 2 (model) ✅, 3 (shell/wire-in) ✅ — each through a review gate
- 🔄 Track B — see the live audit below
- ⬜ Phase 2 — integrate, live-verify on real Anytype data
- ⬜ Phase 3 — laptop app (PWA first), retire old surfaces **only on June's judgment**

### Track B — live schema audit, 2026-07-18

Run `python3 scripts/describe_model.py` before building any of this; a **parallel thread has
already landed several sections**, and re-deriving from the spec alone would duplicate work.

| Spec | State | Notes |
|---|---|---|
| §2 Recurring mirrors Task | ✅ **LIVE** | Recurring has all 7 mirrored fields; `Has target`/`Target` gone. Built by the parallel thread (c0850ad). |
| §3 `Active` flag | ✅ schema live | Plus a `Fixed appointment` checkbox the parallel thread added. Scheduler wiring not audited. |
| §4 block-level attrs | 🔶 **PARTIAL** | Project has `Affective` + `Block chunk min`. **`Access conditions` is MISSING on Project.** The shared `effective()` resolver on the Python side is unaudited (the TypeScript one exists in `app/src/model/fields.ts`). |
| §6 access-condition options | ❌ **NOT DONE** | Live tags are only the original three. Missing `Requires-deep-thinking`, `Involves-bureaucracy`, `Induces-pain`. |
| §9 Strategy | ✅ **DECIDED 2026-07-18 — no schema change** | See "Strategy decision" below. |
| §17 Focus Period | ⬜ likely a real schema change | ⚠ **CORRECTION 2026-07-18:** Focus Period IS an Anytype type with **7 live objects**. An earlier note here said it was not — that came from reading `describe_model.py`, which reports only the five core types. `workday_start` is probably a genuine schema addition. Verify with `fetch_all_objects`, not `describe_model.py`. |
| §1 write layer · §5 type conversion · §14 Today deltas · §11 logging | ⬜ not started | The bulk of Track B. |
| Four API gaps | ⬜ not started | `GET /api/schema` (load-bearing), structured map endpoint, static-asset route, CORS. |
| Authorship stamping | ⬜ not started | June's call: do it NOW, not later — the log is worthless retroactively. |

### Strategy — DECIDED 2026-07-18 (June: "use the existing strategy data structure")

**Do NOT add a `Directive` field. The mockup drifted from the data model; the data model wins.**

June has **12 real Strategy objects**. What they actually use:

| Live field | Real usage across the 12 |
|---|---|
| `name` | The rule, in her words. Always present. |
| `What for` | **Carries BOTH the trigger AND the instruction** — e.g. *"When planning days that involve leaving the house. Weigh the cumulative spoon-cost of errands, not just count."* Used on essentially all of them. |
| `Context` | Elaboration, origin, distinctions from neighbouring strategies. Heavily used (~10 of 12). |
| `Strategy status` | Set to `Active` throughout. |
| `Applies when` | **Barely used — 1 of 12.** |
| `Learning notes` | Appears unused. |

Mapping the mockup onto this:
- mockup `title` → `name`
- mockup `directive` → **`What for`** (that is empirically where her instructions live)
- mockup `when` → `Applies when` (exists, rarely populated)
- mockup has **no place for `Context`**, which she uses more than anything except `name`

⚠ **So the mockup UNDER-SERVES Strategy**: it shows three fields where her real data works in four-to-five, and omits the one she writes in most. The Strategies tab (Task 6) must surface `Context` and `Learning notes` as well, or the port would hide data she has already written.

Not a blocker, noted: `Applies when` (select) and `What for` (text) both nominally answer "when does this apply". The redundancy predates the mockup. Cutting one is a separate, later question.

### ✅ DONE — `Excitement level` retired live (2026-07-18)

June authorised it; `build_project.py` was run and the unlink **confirmed by read-back**. The live
Project type no longer carries it. Historical note below for why it was pending.

**⚠ WAS HUMAN-GATED: `Excitement level` on Project.** The source edit
landed 2026-07-17 (`build_project.py` no longer creates it, and has a retire block that unlinks
it), but the script was deliberately **not run** — schema writes against June's space are hers to
approve. Until she runs it, the live type and the builder disagree. This is the expected state,
not a defect; it just needs her go-ahead.

**Deferred, do not build:** data-health count line (declined), global capture hotkey (declined),
calendar sync (parked post-v1), Needs-Clarifying collapse (§13, revisit when a real use appears).
