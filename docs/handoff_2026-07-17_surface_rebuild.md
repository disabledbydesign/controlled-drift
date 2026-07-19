# Handoff — surface rebuild (updated 2026-07-18, mid-build)

You are continuing a UI rebuild plus a data-model cleanup that grew out of it. **Read this before touching anything.** Branch: `feat/overlay-actionable`.

**Read in this order:** this file → `docs/BUILD_DOC.md` (the project build doc — protocol, autonomy line, definition of done, live hazards) → `docs/superpowers/plans/2026-07-18-track-a-component-port.md` (the Track A plan) → `docs/api_contract_v2.md` (**including its two APPENDED sections, which correct earlier errors in the same file**).

---

## 1. What is being built

The whole Controlled Drift surface, rebuilt from a Claude Design mockup. It replaces **two** live surfaces: `docs/overlay_daily.html` **and** `scripts/surface_template.html` + `scripts/surface_serve.py`.

**June's top requirement is fidelity.** She finetuned this design over a long period. When in doubt, transcribe rather than improve.

### The three-way source of truth — memorise this
| Question | Authority |
|---|---|
| How does it **look**? | `design/mockups/color-system.html` (the gallery). Trusted regions ONLY: `4a`, `4c`, `5a`, `5c`. Sections `1a`–`3c` are superseded explorations. |
| What **data** exists? | `docs/review_reorganize_backend_spec.md` + `docs/spec_deltas_2026-07-16.md` + `AI_LAYER_SPEC.md` |
| How does it **behave / lay out**? | `design/mockups/review-reorganize-mobile-v4.html` (v2 and v3 are byte-identical to each other; **v4 is the single reference**) |

Consequence: v4 still renders an excitement picker, but the field is cut — **do not port it**.

---

## 2. State

**2026-07-18 — the port is integrated, live, and reviewed.** The new surface runs on real Anytype data at `http://localhost:5050/app/`, all six tabs, both themes, 420 and 1440. 995 backend tests, 294 frontend, tsc clean. The cross-family review gate has been run (5 chunks, GPT-4o) and its two real findings are fixed. What remains is **June's own drive of the surface** — the highest-quality signal available, and the thing no agent can substitute for.

### Track A — the port (`app/`, React 19 + Vite 8 + TS, mounts at `/app/`)
Tasks 1–6 **done, each through an independent review gate**: atoms · model layer · shell (the wire-in point) · `row()` · `detail()` · structure tabs + picker + Map drill-in. **Task 7 (Today tab) in flight.** Remaining: 8 Add/Settings · 9 Focus editor · 10 desktop panes · 11 toast + orphan buckets + cross-tab search · **12 integration and live-verify (REQUIRED, not a test)**.

The acceptance/token page is preserved at `#/check`.

### Track B — backend
⚠ **A parallel thread already built spec §2 and §3.** Audit table in `BUILD_DOC.md` §8 — **read it before dispatching, or you will rebuild live work.** Done today: the write-log provenance work (below). In flight: access tags + `Side` rename.

### The data-model side thread (grew out of one question about `Affective`)
- **Field semantics** (`scripts/field_semantics.py`) — 53 fields, every entry **extracted and cited** from the specs, never authored. Two layers: repo defaults + June's overrides, resolved override-if-present, with the default and its citation always surviving. Surfaced at `describe_model.py`, the MCP write tools, `gsdo_objects`, and the drift skill.
- **Provenance** — the weeding gate's `reasoning` no longer lands in `Context`; LLM authorship is stamped in the write log (`corrections_log`, renamed today from `plan_corrections_log`).
- **Focus Period** — design recovered from four sources and migrated into `AI_LAYER_SPEC.md` §2. Nothing was undocumented; it was orphaned.
- **Migrations** — 14 `Affective` values re-filed (7 left alone as genuine affect). Context cleanup in flight.

---

## 3. Load-bearing decisions — do not quietly reverse

1. **Inline style objects stay inline.** Do NOT convert v4's 494 inline styles to CSS classes or variables. That translation is where tuned detail leaks. CSS vars are a safe refactor only AFTER fidelity is locked.
2. **Themes fork on SHAPE, not just colour** (~30 `isHW()` sites).
3. **Object-type colour comes from the gallery legend** (`typeRamp`), never v4's `TYPE` map — which coloured TASK green, colliding with the completion green used for done/steady/saved.
4. **The new app mounts at a SECOND route.** `overlay_daily.html` stays live until June judges the new one better.
5. **Do NOT port v4's dead paths.** Removed on this basis: `renderApp`/`header`/`tab`, `typeSection` (defined once, never called), `menuStrip` (all 18 `menuFor:` assignments are `null`). An unwired component is the built-but-dead shape `BUILD_DOC` §3 exists to prevent.
6. **Provenance and history go in the WRITE LOG, never on objects.** Applies to authorship stamps and to the gate's filing rationale.
7. **The inherit control is TWO states** — inherited, or set here. An empty value on a set field is a normal, valid shape (*"if leaving the house isn't checked, it doesn't involve leaving the house"*), and needs no explanation. v4 renders exactly two branches.
8. **Never write your own reasoning into her fields.** Filing rationale is process output; it belongs in a log.

---

## 4. The failure patterns this build actually hit

Read these; each cost real time and all recurred.

1. **A wrong doc becomes wrong code.** A token docstring claimed `disabled` covered "empty checkbox". It didn't — the audit trail sourced it from a text glyph and a chip border. An implementer trusted the docstring and rendered the most-repeated control visibly fainter than the gallery. Two steps, each internally consistent, only caught by checking the gallery.
2. **Confident false assertions in durable comments.** Twice: a cited function (`filterMoveTree`) that does not exist in v4, and a claim that a code path was unreachable when v4 reaches it at line 747. Neither is typechecked or tested. **If you cannot verify a claim about v4, write "unverified".**
3. **Negative results from unverified queries are not evidence.** `POST /spaces/{sid}/search` **silently returns a broken subset** — 99 objects from a space of 296. It produced two false claims to June (that she had no Strategy objects; that Focus Period was not a type). **Always use `gsdo_anytype.fetch_all_objects(sid)`.**
4. **A filtered view read as a complete one.** `describe_model.py` showed only five types, hiding Focus Period, Page, Note and Bookmark. Three errors from that one omission. **Now fixed** — it discovers types.
5. **Stale docs relayed as current.** Four of eight "built-but-dead" field claims from 2026-07-11 were stale by 2026-07-18. Re-verify before repeating.
6. **Machine formats handed to a human.** A migration log shipped as JSONL for June to review; she cannot read it. **If a human is the audience, write a human format** — see `scripts/migration_report.py` and `scripts/semantics_report.py`.

7. **A passing test proved nothing — twice.** A test written to catch the rollback bug passed against the broken code, because its helper compared `id` and `title` while the edit under test wrote `vals.done`. Only the mutation check (break the fix, watch the test fail) caught it. **A test is unverified until you have watched it fail.** Separately, a `/api/complete` mock returning `{}` made the success path uncheck the box itself, so the test measured its own mock.
8. **The external reviewer praised the code that was broken.** The `as_needed` default had no read-back covering it — the verification loop walks fields present *before* the write, and that field is absent by definition. GPT-4o called it exemplary read-back discipline. The finding came from checking its claim against the source. **The gate's value is what it makes you re-read, not only what it flags.**
9. **A blank tab that was not blank.** "Strategies renders blank for ~0.5s, reproduced 3/3" was a measurement artifact — one probe timed its own cross-process polling (identical poll counts, different wall-clock), another matched the outgoing tab's animated element. Screenshots at 80/200/400ms show the ordinary 0.26s entry slide. **No long tasks, no fetch, no defect.** Not reproducible; do not chase it.

**The rule that keeps paying out:** *make the wrong thing impossible rather than documenting a rule someone must remember.* The index is derived from the graph so no call site can use a stale one; nav direction is derived during render so nothing can bypass it.

---

## 5. Do NOT do these

- **Do not run anything that writes to her live Anytype space** without explicit authorisation for that specific change. Editing `build_*.py` is the agent's job; running it is not.
- **Do not add a thirteenth log.** Route new signals through an existing one (`corrections_log` takes `kind, before, after`).
- **Do not invent field rationale.** Undesigned stays undesigned — a fabricated rationale beside genuine cited ones is worse than an obvious gap.
- **Do not over-explain absence.** A field awaiting design is not a defect.
- **Do not use one concrete example in an LLM-facing field description** — June's observation: the model will replicate your example into her real data.
- **Do not act on `docs/ux_consistency_review_2026-07-17.md`.** Parked candidates; every item is her call, after the port.

---

## 6. Needs June

- **Two review sheets await her notes:** `docs/field_semantics_review.md` (she has annotated it — **do not overwrite**) and `docs/affective_migration_2026-07-18_review.md`.
- **Design-vs-practice divergences on Focus Period**, hers to judge: the "a period can be MORE, not just less" reframe she asked for has no live use (all 4 availability notes describe reductions; `Workday end` is empty on all 7); and the design assumes week-long stretches while 4 of 7 live periods span a single day, including one named "Week of Jul 14".
- **Accessibility:** the round checkbox is a 15px target, the edit chip ~18px. Faithful to v4, well under the 44px guideline. She likes more accessibility but is wary of redesign scope — decide deliberately, after the port, on the running app.
- **Hardware detail pane** sits at 96% opacity so Map text reads through faintly. The gallery's own token value.

---

## 7. Environment gotchas that cost real time

- `agent-browser screenshot` **hangs indefinitely** — reproduced at the raw CDP layer on a blank page. Environmental. **Do not debug it.** Use `cd app && node scripts/shot.mjs "map,today" celestial,hardware`. agent-browser's DOM reads, clicks and computed-style reads all work.
- A Vite dev server started as a **tracked** background command gets killed between turns. Start it detached: `cd app && nohup npx vite --port 5173 > /tmp/vite.log 2>&1 & disown`.
- `vite.config` sets `globals: false`, so Testing Library's auto-cleanup never registers — call `afterEach(cleanup)` explicitly or renders accumulate and every `getByText` fails.
- `~/.claude/skills/drift/SKILL.md` is **not version-controlled**; today's field-routing addition lives on one machine.
- `import cd_mcp_server` fails (no `mcp` module) in agent environments — the MCP `field_meaning` tool is **unverified by execution**.
