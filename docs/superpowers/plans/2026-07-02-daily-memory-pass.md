# Controlled Drift — the daily memory pass

*Plan written 2026-07-02, in response to the open Anytype task "Build a daily pass that moves
memory items into Anytype" (Ready, id `bafyreiaq4hgy33omkmwgafgn63fxppadedxklmixnerkncybsbi2ijdame`).
Build sequenced one slice at a time, verify, then the next — same discipline as
`2026-06-22-overlay-and-backend.md`.*

## Context — the actual task text (verbatim from Anytype, so nothing gets re-derived from the title)

> Stop relying on Claude judging save-location at write-time (it keeps misfiling June-facing
> items into memory). Instead: a DAILY automated pass (launchd, like the morning push). Headless
> claude -p reads the memory files, finds items that belong in Anytype, adapts each to the real
> schema (type, Context field, links), flags anything underspecified. Python then creates them
> with read-back + dedup (same split as the weeding pipeline: model proposes, deterministic layer
> commits). GUARDS: (1) minimal re-summarization — carry the memory words verbatim into Context,
> do not compress; (2) do not overstretch — if a memory entry does not say enough to type or link
> it, create as Needs Clarifying with the verbatim text, never invent; (3) run-twice-safe — mark
> each memory entry once extracted AND check Anytype for an existing match before creating (the
> 3x-duplicate failure). Conceptually = the repo sweep pointed at memory. First real use of
> cd_mcp_server (cold agent operating Anytype). NOTE: GRA will likely want the same pattern — its
> metabolism layer has the same memory-to-structured-store need + the same two guards (keep
> original words, do not overstretch). Open detail: the per-entry extracted-marker.

**Decided 2026-07-02 (June + Claude): no — out of scope, and June's fragility instinct is right.**
"Mark completed tasks as done" is a different data flow with a different source of truth (memory
doesn't reliably record completion — June does, in her head or the overlay). Coupling it to the
extraction pass means a bug in one can wedge the other. If a done-reconciliation pass is wanted,
it's its own small job later, not bolted onto this one.

"Memory items" = Claude's own persistent memory files (YAML frontmatter with `name` /
`description` / `metadata.type` — one of `user`/`feedback`/`project`/`reference` — followed by
markdown body).

**Scope decided 2026-07-02 (June): global, not repo-scoped.** Every Claude Code project gets its
own memory folder at `~/.claude/projects/<project-slug>/memory/*.md` — this misfiling problem
isn't unique to Controlled Drift's own folder, so the pass globs
`~/.claude/projects/*/memory/*.md` across all of them, not just
`-Users-june-Documents-GitHub-cyborg-memory-controlled-drift`. This changes Slice 1 step 2 and
the state-file shape below (each entry now records which project folder it came from, both so
the log is legible and so a name collision across two projects' memory can't be mis-deduped
against the wrong one).

## Why this is a real gap, not already solved by `cd_mcp_server.py`

`scripts/cd_mcp_server.py` (242 lines, live, registered globally) gives a *cold interactive
agent* six verbs (`create_task`, `create_object`, `update_object`, `complete_task`,
`list_tasks`, `get_context`) with read-back-proves-persistence baked in. That solves the **write**
half. It does not touch three things this task explicitly asks for:

1. **No filesystem side at all.** It never reads `~/.claude/projects/.../memory/*.md`, never
   parses YAML frontmatter, never knows a memory file exists. Someone/something else has to read
   the files and decide what's in them.
2. **No dedup against existing Anytype content.** `list_tasks` returns Tasks only; `get_context`
   returns Goals/Projects only. Neither checks "does an object already exist that already
   captures this memory entry" — the exact failure the task names ("the 3x-duplicate failure").
3. **No scheduling.** launchd is mentioned explicitly as the model to copy
   (`~/Library/LaunchAgents/com.june.controlled-drift.morning.plist` +
   `scripts/morning_push.py`), and no plist for this job exists yet.

A fourth thing needs a **design decision**, not just new code — see below.


**Decided 2026-07-02 (June + Claude): the "already extracted" marker is the per-entry state file
(step 2 below), not a marker written into the memory file itself.** June's instinct here (notate
so it isn't re-pulled) is exactly right; the open question was *where* the mark lives. Two options
both solve it: (a) write a marker into the memory file's own frontmatter, or (b) keep a separate
state file keyed by content-hash. June: either is fine. **Chosen: the separate state file** — the
lower-risk of the two, because it never mutates files that Claude Code's own memory system manages
(adding keys to memory frontmatter risks being stripped or confusing memory recall). The state
file is the single authority for "this entry is already handled": delete it to force a clean
re-backfill; it records source_project + content-hash + anytype_id + date, so an entry can be
traced and a reworded entry gets reconsidered.
## Design decision: don't route this through cd_mcp_server's MCP transport

The task text says "First real use of cd_mcp_server (cold agent operating Anytype)" — implying a
headless `claude -p` run that calls the MCP tools itself. But the codebase already has an
established, *proven* pattern for exactly this "model proposes / Python commits" split, used by
`scripts/capture_generate.py` (the Add tab's engine) and `scripts/plan_generate.py` (the morning
push): a **single-shot** headless `claude -p` call via `plan_generate.generate(prompt)` — prompt
in, JSON out over stdout, no tool-calling — and a plain Python layer (`gsdo_objects.create`, read-
back, dedup) that does the actual write.

Routing through cd_mcp_server's live MCP transport instead would mean running `claude -p` with
tool-calling enabled and unattended (no human to approve each tool call), which needs a
permission-bypass flag under launchd — a new risk surface with no precedent in this repo. The
plain-JSON pattern has zero new risk, is what `capture_generate.py` already does, and the
"deterministic layer" cd_mcp_server wraps (`gsdo_objects.create` + read-back) is the *same*
underlying code either way. **Recommendation: build this the `capture_generate.py` way, not
through cd_mcp_server.** This is a real divergence from what the task text names — flagging it
for June rather than silently picking one, since it changes what "uses cd_mcp_server" means for
this task (the write layer underneath is shared; the MCP transport is not used).

**Decided 2026-07-02 (June, confirming the above): yes, the `capture_generate.py`/`claude -p`
pattern is right.** Three follow-on questions this raised, answered here so a cold builder
doesn't have to re-derive them:

- **Pluggable backend?** Yes, and no new work needed — `plan_generate.generate(prompt)` (the
  seam this plan already calls in step 6 of the architecture below) is *already* the
  pluggable-backend layer used by every other headless job in this repo (`CD_BACKEND` env var:
  `claude` / `mistral` / `openrouter` / `local`). This job is not Claude-Code-specific except at
  the *trigger* (the memory files only exist because Claude Code's own memory system wrote
  them) — interpreting plain markdown + YAML frontmatter has no dependency on which model reads
  it, so there's no reason to hand-roll a separate one-off `claude -p` subprocess call here. Use
  `generate()`, not a bespoke call.
- **Does this mean migrating `capture_generate.py`/`plan_generate.py` to use `cd_mcp_server`
  instead?** No. These are two different callers of the *same* underlying deterministic write
  code (`gsdo_objects.create` + read-back), suited to two different contexts: `cd_mcp_server` is
  the transport for a *live, interactive* agent session (a cold Claude Code instance calling
  tools in real time); the headless scripts call the same underlying functions directly in
  Python because they're not running inside an MCP client context — there's no live agent
  issuing tool calls, just a scheduled script. Older-vs-newer is the wrong frame; it's
  interactive-vs-headless, and this job is headless, so it follows the headless precedent.
- **Single JSON blob, Python auto-consumes it — confirmed fine**, exactly as architected below
  (steps 6–9): the model returns one fenced JSON array, `memory_pass.py` parses it and calls
  `gsdo_objects.create` per candidate with no manual step in between.

## Architecture

```
scripts/memory_pass.py  (new, headless, run by launchd)
  │
  ├─ 1. glob ~/.claude/projects/*/memory/*.md across ALL projects (global — see scope note
  │       above), parse frontmatter (name/description/metadata.type) + body per file
  ├─ 2. load per-entry state (~/.controlled-drift/memory_pass_state.json) — content-hash →
  │       {status, anytype_id, source_project} — source_project recorded so two different
  │       projects' memory can't collide in the dedup-by-name check or the log
  ├─ 3. skip entries whose content hash is already marked extracted
  ├─ 4. fetch the live schema (types + properties) to inject into the prompt so it tracks
  │       datatype changes as they evolve — NOT a dedup-by-name list (dedup is delegated to
  │       gsdo_objects.create's existing path, see step 8)
  ├─ 5. build ONE prompt (prompts/daily_memory_pass.md) covering ALL unextracted entries (the model
  │       judges "is this June-facing?" from the content; metadata.type is a prior it's told about,
  │       NOT a pre-filter — a misfiled item may be mis-typed too, so filtering by type would skip
  │       the exact items this pass exists to catch), tagged with which project each came from, with
  │       the live schema from step 4 injected (so the prompt tracks type/property changes, not hardcode)
  ├─ 6. plan_generate.generate(prompt)  ← reused pluggable-backend seam (CD_BACKEND), headless,
  │       prompt in/JSON out — same seam every other headless job in this repo already uses
  ├─ 7. parse JSON: [{source_entry, source_project, verbatim_excerpt, proposed_type,
  │                    proposed_name, context_verbatim, link_to, needs_clarifying, reasoning}, ...]
  ├─ 8. for each candidate: gsdo_objects.create(type, name, properties={...Context: verbatim...})
  │        — the existing create path handles dedup (no bespoke dedup-by-name; one source of truth)
  │        read-back to confirm (same discipline as cd_mcp_server / capture_generate)
  │        mark content hash extracted in state file with the resulting object id
  ├─ 9. anything candidate flags needs_clarifying=True → force Task, status "Needs Clarifying",
  │        Context = verbatim text, never invent a project/goal link
  └─ 10. log every decision (created / skipped-dedup / skipped-unextracted / needs-clarifying)
           to scripts/data/memory_pass_log.jsonl (new, mirrors generation_log.py's shape)
```

**Answered 2026-07-02 (three questions June raised here):**
- *Is this using `generate()` to make a daily plan?* No — the naming is misleading.
  `plan_generate.generate()` is just the generic "prompt in → JSON out" headless model call that
  every job in this repo shares. The morning push uses it to build a to-do plan; this pass uses
  the *same function* with a *different prompt* to read memory. Nothing plan-shaped happens here.
- *How does it adapt as our datatypes evolve?* The prompt must NOT hardcode the current 5 types.
  Before building the prompt, the pass fetches the *live* schema (types + their properties) from
  Anytype and injects it — same idea as fetching live objects. Add or rename a type/field and the
  pass picks it up with no code change. (This is step 4/5 above: fetch live schema, not a hardcode.)
- *How does it know which entries are already extracted?* The content-hash state file (step 2) —
  see the decided note above.

**Why one call per run is enough — no fan-out, no subagents, nothing to "clear."** Every
`generate()` call is already stateless (a fresh process each time — this is exactly why
`capture_generate.py` can call it per-turn with no session to manage). Because step 3 filters
to *only unextracted* entries before building the prompt, a steady-state daily run only ever
sees what's new since yesterday — typically a handful of entries total across every project,
not the full memory history — so one prompt covering everything new is normally small enough
for a single call regardless of how many projects exist. The one case this could grow large is
a first-ever backfill run scanning years of pre-existing memory across many projects at once;
if that ever produces a prompt too big for the token budget, the fallback is to chunk by
project (one `generate()` call per project's unextracted entries, same as `session_store`
already chunks by token budget elsewhere in this repo) — not a redesign, just a loop added
around step 5–6 if and when it's actually needed. Don't build the chunking pre-emptively;
confirm the single-call size first against real backfill data (Slice 1's dry-run, below).

**Answered 2026-07-02 (three concerns June raised here):**
- *Context overwhelming one agent + "first run: nothing extracted, most stale."* The dangerous
  case is the FIRST run — it scans years of memory across every project at once. **Decided: the
  first run is a *reviewed backfill*, not the unattended 3am job** — dry-run, June eyeballs what it
  proposes, then commits. The 3am launchd job only ever runs the safe steady-state delta
  (new/reworded entries since yesterday) afterward. This separates the scary once-only backfill
  from the boring daily near-no-op.
- *"Most are stale."* Most memory genuinely belongs in memory — `feedback` / `user` / `reference`
  entries describe how Claude should behave. BUT type is a *prior, not a gate*: the whole reason
  this pass exists is that June-facing items get *misfiled* into memory, and a misfiled item was
  probably *mis-typed* by the same bad judgment — so a real task of June's can be sitting there
  typed `feedback`. If the pass pre-filtered by type it would skip exactly the most-misfiled items.
  So the model reads every unextracted entry and judges "is this June-facing?" from the content,
  using type as one signal, not a filter. Steady-state volume stays low anyway (only new/reworded
  entries per run); the one-time first run is the reviewed backfill, which absorbs the larger read.
- *"What if todos are entered somewhere besides memory.md — is that scope too big?"* Yes, too big
  for this build, and yes it's a real gap. This pass is scoped to memory files. Other capture
  surfaces are a separate concern — logged as a follow-up gap in the open items below, not folded
  in here.

## Slice 1 — the prompt + the read/parse layer (no writes yet)

1. **`prompts/daily_memory_pass.md`** (new) — instructs the model: given a list of memory
   entries (file name, frontmatter, body) and a list of existing Anytype object names by type,
   propose which entries belong in Anytype. Hard rules baked into the prompt itself (guards 1+2
   from the task): *carry the memory text verbatim into `context_verbatim` — do not paraphrase or
   compress*; *if type or link can't be determined from the text, set `needs_clarifying: true` and
   still carry the verbatim text — never invent a type, project, or goal*. Output: fenced JSON
   array only (same convention as `daily_list.md`'s JSON block).
2. **`scripts/memory_pass.py`** — write steps 1–4 only: glob `~/.claude/projects/*/memory/*.md`
   (global, not one hardcoded project path — see scope note above), parse frontmatter with a
   small regex/`yaml.safe_load` split on the `---` delimiters (PyYAML is already importable in
   this env, confirmed), load/save the state file, fetch the live schema for the prompt. No Anytype
   writes yet. State file shape: `{"<content_sha256>": {"source_file": "...", "source_project":
   "...", "status": "extracted", "anytype_id": "...", "extracted_at": "..."}}` — `source_project`
   is the project-slug directory name, so the log and any future dedup-by-name check can tell
   two projects' memory apart. Hash the entry's body text (not the whole file) so editing
   unrelated parts of a memory file doesn't force re-processing of already-extracted entries,
   and so an entry's wording changing *does* get re-considered (matches guard 3's "run-twice-
   safe" intent without conflating it with "never re-look-at").
3. **Verify:** `python3 scripts/memory_pass.py --dry-run` prints the parsed entries, which are
   already-extracted (skipped), and which are new — against every real project memory folder
   under `~/.claude/projects/*/memory/`, with zero writes. Confirm by eye that frontmatter
   (`name`, `description`, `metadata.type`) parses correctly for a few files across at least two
   different projects (e.g. this repo's `project_gsdo.md` + one file from another project's
   memory folder, to prove the glob actually crosses project boundaries and not just this one).
   This run is also where the "is one call enough" question above gets answered for real: note
   the total unextracted-entry count found — if it's small (expected in steady state), Slice 2
   proceeds with a single `generate()` call; if a first-run backfill turns up an unexpectedly
   large number, revisit the per-project chunking fallback before Slice 2, not after.

## Slice 2 — generation + the deterministic write layer — **BUILT 2026-07-02**

4. **`scripts/memory_pass.py`** — added steps 5–9: `plan_generate.generate(prompt)`, parse the
   JSON response (malformed candidates dropped into a separate list, never crash the batch —
   mirrors `capture_generate.py`), then `gsdo_objects.create(...)` + read-back exactly as
   `cd_mcp_server._read_back` / `capture_generate.py` already do it. State file entry marked
   extracted only *after* a successful read-back — never before.

   **Correction to this plan's own premise, found while building (2026-07-02):** the line above
   originally said `gsdo_objects.create` "handles dedup via the existing create path" — that was
   false. Checked three ways before touching anything: `gsdo_objects.py`'s full git history (dedup
   logic never existed there), every call site in the repo (none pre-check a name), and the live
   Anytype API directly (created two same-named objects back to back — two distinct ids, no
   server-side dedup either). The state file was the *only* real guard; losing it would have
   reproduced the exact Strategy-triplication incident this system already hit once. Fixed at the
   source: `gsdo_objects.create_object()` now checks for an existing object of the same type +
   normalized name before creating, returning its id instead (see `find_existing()` /
   `_norm_name()` in `gsdo_objects.py`) — every caller (`capture_generate.py`, `cd_mcp_server.py`,
   this pass) gets the backstop for free. Regression test: `test_create_dedups_on_exact_name_same_type`
   in `tests/test_gsdo_objects.py`. `memory_pass.py`'s `apply_candidate()` also does an *explicit*
   pre-check (`gsdo_objects.find_existing`) before calling `create`, purely so the decision log can
   tell "already existed" apart from "created just now" — the actual guard lives in `create()`
   itself either way.

   Incidental finding, not fixed (out of scope): Anytype's `note` layout stores the `name` passed
   at creation into body content (`snippet`/`markdown`), leaving the real `name` field blank — a
   pre-existing gap in `create("Note", ...)`, unrelated to dedup.
5. **`scripts/memory_pass_log.py`** — built as a sibling module (not extending `generation_log.py`)
   since it logs per-entry decisions, not per-generation-attempts. One line per candidate:
   `created` / `skipped-dedup` / `skipped-not-anytype` / `rejected-malformed` / `failed`.
6. **Verified** — against a scratch test set (3 files: the real
   `feedback-where-to-save-anytype-vs-memory.md` unmodified, plus two fabricated entries — a task
   misfiled as `feedback`, and a deliberately underspecified item), never against June's live
   memory directory:
   - The model judged all three correctly: the real feedback entry → `skipped-not-anytype`; the
     misfiled task → created as `Task`/`Ready` with `Context` holding a genuine verbatim quote
     from the body (not a paraphrase); the underspecified item → created as `Task`/`Needs
     Clarifying`, no invented link. Read back live and confirmed by hand.
   - Ran a second time unchanged: zero LLM calls, zero writes (state-file gate short-circuits to a
     no-op — `processed: 0` across the board).
   - Deleted the state file and ran a third time: both previously-created objects came back as
     `skipped-dedup` (matched by id, not recreated) — confirms the write-time backstop actually
     works standalone, not just the state file.
   - Cleaned up: both live test objects deleted, scratch directory removed. Full test suite
     (282 tests, up from 226) still green.

**QC pass, 2026-07-02 (June asked for a genuine re-check, not a re-assertion):** re-read every
file fresh. Found one real bug: `apply_candidate()` validated `proposed_type` against
`ALLOWED_TYPES` *before* the `needs_clarifying` override ran — so a candidate with
`needs_clarifying: true` and `proposed_type: null` (exactly the case guard 2 exists to permit)
would raise and get logged as `failed` instead of correctly creating a Task/Needs-Clarifying. Was
masked in the first verification run because the model happened to still supply a type guess for
the ambiguous test item. Fixed by moving the override before the validation; reproduced the exact
failing input directly (`needs_clarifying=True, proposed_type=None`) and confirmed it now creates
correctly, live. Also double-checked the `MEMORY.md`-is-the-only-index-file assumption against
all 21 real project folders (held, no exceptions) and re-ran the full scratch-set functional test
+ full suite (282 passed) after the fix. No other defects found on this pass.

**Closed 2026-07-03: `--preview` mode built.** `memory_pass.py --preview` calls the LLM
(`preview_pass()`) and prints every candidate (`format_preview()` — full, untruncated
`context_verbatim` so June can confirm guard 1 held), grouped into would-create /
would-stay-in-memory / malformed — but never calls `apply_candidate()`, `mark_extracted()`, or
`save_state()`. Verified against a throwaway scratch fixture (2 fake entries, one real-feedback-
shaped, one misfiled-task-shaped): the model judged both correctly, and running `--preview` twice
in a row produced identical output both times (proves no state was written — a later `--run` will
still see every entry as new). Full suite still green (282 passed). Scratch fixture deleted after.
This closes the review gap: the first-ever backfill is now `--preview` (June reviews the real
proposals) → `--run` (commits), not `--run` blind + after-the-fact log reading.

**Two real bugs found and fixed running `--preview` against the actual corpus (2026-07-03), not
hypothetical:**
- `plan_batches()` split entries by project when the *combined* prompt was too big, but never
  checked whether an individual project's own batch was still over `SINGLE_CALL_TOKEN_BUDGET`.
  The Job-Search project alone has 99 unextracted entries (~65k estimated tokens against the 40k
  budget) and was sent as one oversized call — timed out at the API's 300s ceiling. Fixed:
  `_chunk_to_budget()` greedily splits any project whose own batch still exceeds budget into
  smaller chunks (never drops an entry). Confirmed against the real corpus: all 25 resulting
  batches now sit at or under budget (worst case ~39.7k tokens).
- Separately, a single batch failing (whether over-budget or a transient API stall — evidence
  pointed to the latter: two calls timed out at exactly 300.2s while a *larger* neighboring batch
  succeeded in 197s) aborted the entire pass and discarded every candidate already gathered from
  prior batches, in both `preview_pass()` and `run_pass()`. Fixed two ways: (1) `generate_candidates()`
  now retries once (`GEN_ATTEMPTS = 2`) before raising — both attempts still logged to
  `generation_log.jsonl` either way, so a persistent failure stays visible; (2) both `preview_pass()`
  and `run_pass()` now catch a batch that fails even after retry, record it, and continue to the
  next batch instead of aborting — `preview_pass()` surfaces this as a "FAILED — not previewed"
  section in `format_preview()`; `run_pass()` logs a `failed` decision per entry in that batch and
  leaves them unmarked so the next `--run` retries exactly those. Verified with a monkeypatched
  `plan_generate.generate()` (one batch always raises `TimeoutError`): confirmed 4 calls made
  (1 ok + 2 retries-on-fail + 1 ok) and both good batches' candidates survived.

**First real backfill preview run completed 2026-07-03** (25 batches, all succeeded, zero
failures after the fixes above): 422 unextracted entries considered across every project folder —
199 would be created (8 of those flagged `needs_clarifying`), 225 correctly judged as already-
belongs-in-memory, 0 malformed. Rendered as a reviewable page (grouped by project, full verbatim
text on expand, searchable, filterable to needs-clarifying-only) since 424 items is too much to
review as scrolling terminal text — sent to June for review. **Next step: June reviews, then
`--run` commits.** Nothing has been written to Anytype yet; the state file
(`~/.controlled-drift/memory_pass_state.json`) still does not exist.

## Slice 3 — scheduling

7. **`~/Library/LaunchAgents/com.june.controlled-drift.memory-pass.plist`** (new) — copy
   `com.june.controlled-drift.morning.plist`'s structure exactly: same `PATH` fix
   (`/Users/june/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin` — launchd's bare PATH
   is why `claude` silently isn't found otherwise, per the existing plist's comment),
   `StandardOutPath`/`StandardErrorPath` to `~/.controlled-drift/memory_pass.log` /
   `.err.log`. **Decided: 3am daily** (see decided note below) — staggered from the 9 AM morning
   push so any Needs-Clarifying items are already sitting in Anytype when June opens the overlay.
   NOTE: the launchd job runs only the steady-state delta; the first-ever run is the reviewed
   backfill (dry-run → June eyeballs → commit), done by hand, not by this plist.
8. **Verify:** `launchctl load` the plist, `launchctl start com.june.controlled-drift.memory-pass`
   manually, confirm the log files show a real run (auth + PATH resolve correctly under launchd —
   the same gotcha morning_push.py already hit and documented).

## Open items — mostly resolved 2026-07-02

- ~~Skip cd_mcp_server's MCP transport~~ — **decided**: build it the `capture_generate.py`/plain-JSON way.
- ~~Global vs. this-repo-only scope~~ — **decided**: global, across every project's memory folder.
- ~~Run time~~ — **decided**: 3am daily. Not too often — the extracted-marker means a normal day
  sees zero-to-a-handful of new entries, so the run is a near-no-op and cheap. It would only be
  "too often" if it reprocessed everything nightly, which the marker prevents.
- ~~Dedup approach~~ — **decided (June), then corrected while building**: one source of truth in
  `gsdo_objects.create`, no bespoke dedup-by-name list — that decision held. What was wrong was the
  premise that this dedup *already existed*: it didn't, checked three ways (see Slice 2 above), so
  it was built rather than assumed. The content-hash state file is the "already extracted" guard;
  `gsdo_objects.create`'s new exact-name-match check is the real write-time backstop, confirmed live.
- ~~Mark-completed-tasks-done in this pass~~ — **decided**: no, out of scope (fragility — different
  data flow, different source of truth). See decided note near the top.
- ~~GRA reuse~~ — **removed (June)**: not a reuse; it's a separate GRA task and belongs tracked in
  GRA, not here.
- **Still open — todos entered outside memory files.** This pass only reads
  `~/.claude/projects/*/memory/*.md`. If June-facing items get captured in other surfaces
  (freetext notes, other files), they're not covered here. Real gap, deliberately out of scope for
  this build — worth its own task if it turns out to matter.
- **Still open — the first-run backfill is human-gated.** By design: the one-time run over years
  of accumulated memory is dry-run → June eyeballs → commit, not the 3am job. Flagging that this is
  a deliberate human step, not automation missing.

## Discipline
Idempotent; no silent failures (raise, don't `assert`); read-back on every write; dev/test runs
never touch June's live memory directory or leave artifacts in her real Anytype space; build one
slice at a time, verify, then the next.
