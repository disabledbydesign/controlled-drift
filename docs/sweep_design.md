# Controlled Drift — Sweep Workflow Design
*Session design, 2026-06-19. Authoritative for the Mode 2 (additive sweep) implementation.*

---

## What this is

The sweep is **Orient Mode 2** from `AI_LAYER_SPEC.md §8h` — the additive pass that finds work in a repo not yet captured in Anytype and proposes it as structured sub-projects and tasks. It is NOT a general repo audit; it is a targeted pass to close the gap between what exists in the filesystem and what's in the Anytype graph.

The lead agent holds structure and judgment. Haiku subagents do parallel file reading. June sees a grouped proposal with sources and confirms before anything is written.

This document is the spec for the build. A cold executor can build from this + `AI_LAYER_SPEC.md §2` (data model) + the existing scripts.

---

## When the sweep runs

Sweep language is **not user-facing**. June never says "sweep." Triggers are inferred:

1. **Binding creation** — always triggers an initial sweep immediately after the `.gsdot` is written. No separate invocation needed.
2. **Stale `last_sweep`** — when drift is invoked in a bound repo and the `.gsdot`'s `last_sweep` field is absent or ≥ 7 days old, the skill offers a sweep: *"I haven't read through this project in a while — want me to check what's here and what's already in Anytype?"* June can decline.
3. **Natural language** — "what am I missing here," "catch me up on this project," "I've lost the thread of what's in this repo" → infer Mode 2.

The skill distinguishes Mode 1 (read Anytype only, no repo read) from Mode 2 (repo read + Anytype) by whether the trigger implies new discovery vs. showing existing structure.

---

## CLAUDE.md check — every drift open, not just sweeps

Separate from the sweep: every time drift is invoked in a bound repo, check `CLAUDE.md` at the repo root first. Agents leave todos there. This is fast (one file) and happens regardless of whether a sweep runs.

---

## File selection rules

### Always read
- `CLAUDE.md` at repo root
- All non-dot `.md` files at the repo root level (dot-files like `.gsdot-log.md` and `.gsdot` are skipped — they are metadata, read via their own dedicated functions)
- Full contents of: `docs/`, `prompts/`, `plans/`, `planning/`, `specs/` subdirectories (if they exist)

### Scan (extract signals only, not full content ingestion)
- Code files: extract TODO/FIXME comments + stub signals (`raise NotImplementedError`, `pass` in obviously-unfinished functions, `# TODO`, `# FIXME`, `# HACK`)
- Scan at root level + one level of subdirectories only (not recursive into deeply nested dirs)

### Skip entirely
- `node_modules/`, `__pycache__/`, `.git/`, `vendor/`, `dist/`, `distro/`, `build/`
- Any directory with "archive" in the name (case-insensitive)
- Any file with "archive" in the filename (case-insensitive)
- Binary files, generated files, data files
- Files with explicit completion markers at top: `# DONE`, `# COMPLETED`, `# SHIPPED`, `# MERGED`, `status: complete` (case-insensitive, within first 5 lines)
- History and reference genre: files that are clearly past-tense summaries with no open items (agent judgment; when uncertain, read it)

### Special case — job search and non-code repos
If the bound project has no code files (or trivially few), skip the code scan pass entirely. Read: tracker file (any file named `*tracker*`, `*applications*`, `*pipeline*`), planning docs, CLAUDE.md.

### Architecture docs
Read for explicit maintenance TODOs about the map itself (e.g., "TODO: update this diagram when X ships"). Do not scour for implicit todos inside the architecture description. If a file is clearly an architecture reference with no open action items, skip after a quick first-pass check.

---

## Subagent structure

### Skip threshold
If the repo has fewer than ~15 readable files total (after exclusions): lead agent reads directly, no subagents. The overhead isn't worth it for small repos.

### When to use subagents
Split by area — not by count. Spawn Haiku subagents in parallel for:
1. **Planning/root docs agent**: root `.md` files + `docs/`/`plans/`/`prompts/` subdirs
2. **Code signals agent**: code files — extract TODO/FIXME/stubs only
3. **Specs/additional docs agent**: any remaining docs subdirs not covered above

Maximum 4 Haiku subagents. Beyond that, synthesis quality drops.

### What each subagent returns
A structured list per file read. Two channels produce signals with compatible schemas:

**Code-file signals** (`extract_code_signals()` in `scripts/sweep.py`):
```
{
  "source_file": "absolute/path/to/file.py",
  "source_excerpt": "the specific line",
  "signal_type": "todo" | "fixme" | "hack" | "stub",
  "signal_text": "the captured text",
  "line": 42
}
```

**Planning/doc signals** (LLM subagents reading `.md` files):
```
{
  "source_file": "relative/path/to/file.md",
  "source_excerpt": "the specific text or passage",
  "signal_type": "todo" | "stub" | "planned_but_unclear" | "possible_done",
  "signal_text": "plain description of what this is"
}
```

The `line` field is code-channel only. The `planned_but_unclear` and `possible_done` types are LLM-channel only (judgment calls on prose). The lead agent handles both shapes in synthesis.

Subagents do NOT synthesize or group. They read and extract. Synthesis is the lead agent's job.

---

## Lead agent synthesis

### Step 1: Load Anytype context first
Load the bound project's Goal, Projects, sub-projects, and Tasks from Anytype. This is the reference structure — everything gets positioned against it.

### Step 2: Collect subagent findings
Receive raw signal lists from all Haiku subagents. Combine into one flat list.

### Step 3: Code comparison pass
For items in planning docs that look like open todos: quick check — is there code evidence this work was already done? Look for the obvious artifact (a file that should exist, a function that should exist, a commit message signal). This is a light check, not a full audit. The target error: work that's done in code but the planning doc was never updated. Flag uncertain cases as "this might already be complete — worth verifying before adding" rather than either adding or skipping.

### Step 4: Dedup against Anytype
For each finding, ask: **does this map to an existing sub-project or work stream in Anytype?**
- If yes, and the work stream covers it → it may already be captured. Check if a task under that sub-project covers the finding. If yes, skip. If no, add as a task under the existing sub-project.
- If yes, but the finding seems to go beyond what the sub-project covers → note the gap; may need a new task or sub-project extension.
- If no existing work stream covers it → this is a new work stream candidate.

This is structural matching (does this belong to an existing cluster?), not text matching (does this exact phrase appear?). The lead agent uses judgment.

### Step 5: Group into named work streams
Organize all surviving findings into named routes/streams. Use the existing Anytype sub-project structure as the base. Add new work stream names only when the content is genuinely distinct. Subdirectory organization in the repo is a hint (not authoritative — can break down even within one repo). Planning docs' own organization is a stronger hint.

Output is always structured by work stream — never a flat list of todos. A flat list is cognitively inaccessible. Named streams are navigable.

### Step 6: Build the proposal
Format the proposal for June:
```
## Work stream: [name]
[1-sentence description of what this stream is]

Proposed additions:
- [sub-project name] (new) — [why / what it covers]
  - [task] — from [source_file], line/section [ref]
  - [task] — ...
- [existing sub-project name] (adding tasks)
  - [task] — from [source_file]
  ...

Flagged for your judgment:
- "[item]" — marked open in [file] but may already be done (couldn't find obvious code evidence). Check before adding.
```

Show sources for every item. June should be able to trace any proposed task back to where it came from.

---

## Gate — human confirmation before writing

Present the full proposal. June confirms/edits/rejects:
- Entire work streams (accept or reject a route)
- Individual items within a stream
- Re-categorize items across streams

After confirmation: create new sub-projects and tasks via `gsdo_objects.create()`. Read-back each created object. Ding once at the end of the batch (not per item). Update `last_sweep` in `.gsdot`.

---

## Learning loop

### Layer 1 — structural tracking in `.gsdot`
Add two fields to the marker format after each sweep:
```json
"last_sweep": "2026-06-19",
"items_surfaced": ["item name", "item name", ...]
```
Always written. Mechanical.

### Layer 2 — open-text feedback log at `.gsdot-log.md`
Agent writes here **only when there's genuine signal** — something unexpected, something that worked particularly well, a problem and how it was resolved, anything that would change how the next sweep runs.

**This is NOT a required step.** A routine sweep with no surprises needs no log entry. Writing a log entry just because it's suggested creates noise that makes the log useless.

When there IS something worth logging, format is loose — a few sentences is enough:
- What worked (worth protecting in future sweeps)
- What went wrong
- How it was resolved
- What would change next time

The log accumulates across sweeps. Future instances read it before running a sweep in the same repo.

---

## CLAUDE.md write on binding creation

When `init_binding()` creates a new binding, it writes or updates `CLAUDE.md` at the repo root. If a `CLAUDE.md` already exists, append a clearly-delimited Controlled Drift section rather than overwriting. Content:

```markdown
## Controlled Drift binding

This repo is bound to Controlled Drift → Project: [project name] (Goal: [goal name]).
When working here: capture any todo/commitment mentions to Anytype under [project name] by default.
The `drift` skill is active here — June never has to name a function.
Binding: `.gsdot` in this directory.
```

This is loose enforcement (instruction, not a hook) — the tighter version (a hook in `settings.local.json` that auto-loads the binding) is a post-v1 design item.

---

## `.gsdot` format update

Add `last_sweep` to the marker format. Full format after this build:

```json
{
  "system": "Controlled Drift",
  "binds_to": {
    "goal": {"id": "...", "name": "..."},
    "projects": [{"id": "...", "name": "..."}]
  },
  "last_sweep": "2026-06-19",
  "note": "optional human note"
}
```

`last_sweep` is absent until the first sweep completes. `note` is optional, set by the user during binding creation if they want to add context.

---

## What this build does NOT include

- Hooks-based enforcement of default capture (post-v1)
- Orient Mode 3 (reorganization) — parked, see `AI_LAYER_SPEC.md §10`
- Full code-vs-plan audit (the light comparison pass above is not a comprehensive audit)
- Learning loop quality improvements beyond the two layers above (post-v1)
