# Session handoff — 2026-07-11: build-protocol fix + self-describe commands

**For the next instance. Orient from the live system first — not this doc:**
- `python3 scripts/whats_open.py` — what's open in this repo (live work-stream map).
- `python3 scripts/describe_model.py` — how the data model works (live schema).
- Full record: `build-protocol-integration-gap.md` in the auto-memory dir: `~/.claude/projects/-Users-june-Documents-GitHub-cyborg-memory-controlled-drift/memory/`.

This doc is narrative context only; the live commands and the Anytype work-stream below are the source of truth.

**Terms this doc uses** (a cold reader won't know these): *Anytype* — a local app where this system's live state lives; the two commands above read from it. *Work-stream* — a unit of tracked work, stored as an Anytype Project, usually nested under a parent Project (here, "Build Controlled Drift"). *`drift` / `verify` / `writing-plans` / `subagent-driven-development`* — named skills available in this environment. *GRA* — June's separate memory/archive system that surfaces relevant prior design when a topic comes up (referenced in the parked section below).

## The problem this session worked on

June named it: work in this system keeps getting *designed and never integrated* — "we keep making flat docs and reinventing designs without ever integrating." The root cause, diagnosed and grounded in the code:

**The build process defined "done" as: unit tests pass + a reviewer approves the code. Nothing ever checked whether the thing was wired into the running system and actually worked when used.** So pieces shipped built-but-dead — passing their own tests, marked done, never connected. (Recurring shape across two same-day diagnoses: "logging built, loops deferred"; "spine built, unwired.")

## What got fixed / built

1. **Build protocol now requires integration + end-to-end verify.** Edited two GLOBAL build skills:
   - `~/.claude/skills/writing-plans/SKILL.md` — every plan must end with an integration-and-verify task (name the real call site the feature wires into; drive the real flow via the `verify` skill, not just pytest).
   - `~/.claude/skills/subagent-driven-development/SKILL.md` — run `verify` end-to-end before finishing; red-flag added: "a clean diff is not a working, wired-in feature."
   - ⚠️ **These edits live in `~/.claude/skills` and are NOT version-controlled.** An Anytype task is captured to fix that (git-backup config/dotfiles). Whole-machine backup was left — it needs hardware.

2. **Two live self-describe commands** (so agents stop re-deriving the system), committed `02d8091`, wired into the `drift` skill + repo `CLAUDE.md`:
   - `scripts/whats_open.py` — cross-repo; the work-stream map for whatever project a repo is bound to.
   - `scripts/describe_model.py` — Drift-specific; the live schema (inert Anytype system fields filtered; `Done`/`Due date`/`Linked Projects` kept because the model uses them).

## What's OPEN — the real next build

Tracked as an Anytype work-stream under "Build Controlled Drift", named **"Keep work-stream statuses current"** (shows `● active` in `whats_open.py`).

The map *shows* status, but nothing keeps it *honest* — statuses drift out of date (e.g. a thread reads "Done" while the capability doesn't work). Two fix-pieces are already known and were NOT assembled this session:
- **Agents close their own tasks in-flight** — decided; June-facing side already built (`task_actions.complete_task`).
- **A "system notices, you confirm" check-in** — designed in `docs/focus_configuration_addendum.md`; `neglect.py` exists as scaffolding but has never been run.

**Decided design (2026-07-11, June):** delivery is a *scheduled checker subagent* (~monthly) that compares each thread's status against evidence — staleness (`neglect.py`), status-vs-tasks mismatch, and reading code/commits to investigate. **Autonomy — lean cautious:** the agent may *auto-fix only cases with concrete positive evidence of the true state* (e.g. work clearly complete in the code but not marked done — "the code is right there"). Anything resting on absence-of-evidence or judgment (looks stale; marked done but the capability can't be found/confirmed) it *flags for June* and does not change — auto-marking from absence would let a wrong guess silently become the record (the map lying a new way). The asymmetry is the safety line.

**Next step:** write a short plan that assembles these two pieces into that checker, then build it through the (now-fixed) loop. Do NOT half-build it — that reproduces the exact pattern this session fixed.

## Known gaps in this session's own work
- `whats_open.py` / `describe_model.py` have no unit tests — they are thin glue over already-tested functions, and were verified by live run (the bar the new build rule sets). Add mocked tests if a reviewer wants belt-and-suspenders.
- The global skill edits are unversioned (see the captured backup task).

## Parked — separate threads, not this one
- **Don't-reinvent-designs** (e.g. the spoons mechanics agents keep rebuilding) → this is GRA's job (relevance-injected memory), not a Drift command. Activates when GRA runs.
- **`docs/structural_diagnosis_2026-07-11.md`** — why the daily plan feels arbitrary/overwhelming. A distinct thread June set aside this session; it has its own direction to set.
