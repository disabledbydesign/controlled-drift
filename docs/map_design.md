# The map — authoritative design spec

*This is the single source of truth for how the Orient map renders. **Read this before changing `orient_map.py` or how the map is shown. Update this when June settles a new decision — do not carry map-design decisions only in session memory.** The reason this file exists: the map kept getting re-derived from scratch each session and drifting from decisions already made. That drift is the exact failure Controlled Drift prevents; this file applies the fix to the build itself.*

## What the map is

A **deterministic read of stored fields** that lets June see the whole picture at once and know she's still in the arc. It renders identically every time; no instance re-improvises it. Calm and scannable — never a wall of text.

## Settled decisions (each was learned the hard way — do not revert)

1. **Keep "What it is."** Every stream shows a one-short-line `what it is`, read deterministically from the field. Without it June can't tell what a stream is about. (Removing it is a regression.)
2. **Never "held."** The not-active label is **"later"**, never "held" — "held" is confusing for June and has been rejected many times.
3. **Detail is sized to the work, and to engagement.** A tiny thing gets a tiny line. The map does not give the most detail to the thing being avoided.
4. **Active = what June is actually *in*** — driven by the Engagement field, not by an instance deciding. No session re-spotlights an avoided item.
5. **The map shows `what it is` for every stream; the ARC only for the active stream.** Later streams stay calm (name + one line). Full detail shows when a stream is opened.
6. **No separate "next step" field.** The arc's `→` already points to where we are / what's next.
7. **Finished must scale.** It is never a growing flat list on the map (see below).

## Layout

```
GOAL:  <goal name>  (<horizon>)
       <goal description, wrapped>

  <project name>

  ✓ <done stream> · <done stream>        (compact trajectory — what's behind you)

  ● active   <stream name>
             What it is:  <one short line>
             The arc:
                ✓ <done step>
                → <the step we're on>        (this is the "next" — no separate field)
                ☐ <future step>

  ○ later    <stream name>
             What it is:  <one short line>

  ● active   <grouping / phase name>         (grouping = stream with its own children)

    ● active   <child stream>
               What it is:  <one short line>
               The arc: ...

    ○ later    <child stream>
               What it is:  <one short line>

  — running alongside —
  ○ later    <stream name>
             What it is:  <one short line>
```

The whole map is one ordered list — the project arc (see "the meta-arc" below).

## The arc (replaces the flat task list)

The arc is the stream's **ordered steps**, shown as a progression so June can see forward motion vs. drift. Uniform marker on every step:

- `✓` done
- `→` where we are now (also serves as "next" — no separate next-step line)
- `☐` future step (not started)

Steps **are** the stream's tasks, ordered. "Where we are" = the first not-done step (no separate current-marker stored). Start here; if "step" needs to be broader than a task later, revisit then — don't over-build now.

The arc shows on the map **only for the active stream** (what June is in). For other streams it shows when the stream is opened.

## Finished — trajectory line, not a section (settled 2026-06-20 + 2026-06-20)

Done streams appear as a **single compact trajectory line** near the top of the map — names joined with `·`, prefixed `✓`. This is a progress marker ("what's behind you"), not a listing.

```
  ✓ Foundation work · Data model build
```

This is **not** a "Finished" section. There is no heading, no detail, no count. Do not expand it into a section or add structure to it. It stays one line no matter how many streams are done.

The real home for finished work is the **project wins mirror** (see `map_and_arc.md`) — a proper surface to be designed later, where finished streams are celebrated and held. Until the wins mirror is built, the compact trajectory line is the only reference to done work on the live map.

## Groupings (phase sections)

A **grouping** is a sub-project that itself contains streams. It acts as a phase or category header on the map; its children are the actual work streams.

When the map detects at least one direct child of the project has its own children, it switches to grouping layout. The grouping renders its header line (circle + label + name), then its children are shown indented below it. Leaf streams (no children) at the top level continue to render normally alongside grouping sections.

Detection is automatic: a sub-project with children = a grouping. No flag needed.

`missing_descriptions()` and `gap_streams()` check the **full subtree** — groupings and their children — not just direct children of the root project.

## The meta-arc — the whole map is one ordered arc (settled 2026-06-20)

Just as a stream breaks into ordered steps, the **project breaks into ordered streams.** The map *is* the project arc: one ordered list of streams, in trajectory order, with the active stream opening to show its own internal arc. Same shape at both levels.

- **It keeps the chunk format already settled** — every stream still shows its circle + name + `What it is` (this is NOT a redesign of the chunk; only its *order* changes). Never drop `What it is`.
- **`Stream order` field** (a number, exactly like `Step order` on tasks) sets each stream's place in the project arc. Deterministic, June-editable, no instance guesses.
- **The circle is a separate axis from order.** Order = where a stream *sits* in the plan (trajectory). The circle (`●` active / `○` later) = what June is *in* vs. what's ahead. They differ on purpose — working out of sequence is honest ADHD behavior, not error, and the map shows it rather than flattening it.
- **Parallel vs. sequential (current/interim):** streams that **share the same `Stream order` number are parallel** (same phase, run alongside each other); different numbers are sequential. A parallel group is marked with a plain `— running alongside —` line, no cryptic symbols.
- The active stream expands to its step-arc; later streams show name + `What it is` only. (Open a stream for its full detail.)

### Refinement: hard dependency vs. soft sequence vs. parallel-default (designed 2026-06-20, NOT yet built — its own focused piece)

The interim mechanism above has a real flaw June named: a single manual `Stream order` number (a) forces her to generate the order cold — backwards for a system meant to hold and propose — and (b) conflates two genuinely different kinds of ordering. The refined model:

- **Parallel is the default.** Two streams with no stated relationship are parallel. Most streams are. June numbers nothing cold; doing nothing leaves everything alongside everything else, which is honest — most real work is parallel. Sequence is added only where there's a reason.
- **Hard dependency** — Stream X genuinely *can't* start until Y is done. Factual, structural, no value judgment (e.g. the wins mirror can't exist before the visual layer it lives in). Held as an explicit link the system **enforces** — it won't order X before Y. The AI can spot candidate dependencies and propose them; many are derivable.
- **Soft sequence** — "it *makes sense* to do X before Y." A value judgment, fully June's to override. The AI **proposes** it with reasoning; June refines. This is where human-AI collaboration belongs — not pure automation, not blank-page generation.

Principle: **the AI proposes the order; June adjusts — she never assigns it cold.** Hold what's factual (dependencies), collaborate on what's situated (sequence preference). When built, this replaces "shared number = parallel" with "no relationship = parallel, dependencies enforced, soft order proposed." Until then, the interim `Stream order` mechanism stands.

## Determinism contract

The renderer reads fields and formats them — it never composes or paraphrases content. Content is written once (following `work_stream_register.md`) and shown verbatim. Wrap at a fixed conservative width so the TUI never re-breaks lines. Show the map inside a code block.

## Workstreams are never rendered as projects/subprojects (decided 2026-07-13)

A **workstream** is an internal dev/research thread inside a builder-practice body of work — e.g. GRA's "Metabolize Session 3," or Controlled Drift's own "Route prioritization and task breakdown." It is stored as an ordinary `Project` (same shape, `Parent project` nesting as usual) but marked with the `Is workstream` checkbox. **June's hard rule: no UI that shows projects/subprojects may ever render a workstream the same visual/spatial way as a real project or subproject — in every surface, a workstream has to read as structurally distinct at the moment it touches the UI, not folded in as if it were one more subproject.** This is an ongoing convention every rendering surface must honor, not a one-time layout tweak — including surfaces built after this was decided.

- **Marking:** `Is workstream = true` is set on the *actual workstream-grain projects* (e.g. the items directly under "Build Controlled Drift" and under "Grounded Recollection (GRA)"), not on the container project that holds them (Build Controlled Drift and GRA are themselves real projects, not workstreams).
- **Inheritance:** a descendant project with `Is workstream` unset inherits `true` from its nearest ancestor that has it set — same walk-up-the-`Parent project`-chain mechanism as `Side` inheritance (`scripts/daily_plan.py`). This means a newly created sub-workstream (e.g. a future "Metabolize Session 7" nested under "Metabolize the archive") is automatically covered without hand-tagging every new leaf.
- **Known surfaces that must honor this** (update when built/found, don't let this list go stale): `scripts/orient_map.py` (the deterministic map), `scripts/review_surface.py` + `scripts/surface_template.html` (the HTML review surface, → `docs/controlled_drift_tree.html`), and `scripts/daily_plan.py` if it ever surfaces project/subproject names directly (currently it mostly surfaces tasks).
- **Status as of 2026-07-13:** the data is tagged and this convention is written down; the rendering code in the surfaces above has **not yet been updated** to act on `Is workstream`. That's the remaining build step — scoped separately given its size (multiple files) and the repo's own bar that a landed build gets cross-family review before its thread closes.
