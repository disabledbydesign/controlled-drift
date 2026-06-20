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

WORK STREAMS — <project>:

  ● active   <stream name>
             What it is:  <one short line>
             The arc:
                ✓ <done step>
                ✓ <done step>
                → <the step we're on>        (this is the "next" — no separate field)
                ☐ <future step>
                ☐ <future step>

  ○ later    <stream name>
             What it is:  <one short line>

  ○ later    <stream name>
             What it is:  <one short line>

  ✓ <N> finished — <names while few; collapses to a count when many>
```

## The arc (replaces the flat task list)

The arc is the stream's **ordered steps**, shown as a progression so June can see forward motion vs. drift. Uniform marker on every step:

- `✓` done
- `→` where we are now (also serves as "next" — no separate next-step line)
- `☐` future step (not started)

Steps **are** the stream's tasks, ordered. "Where we are" = the first not-done step (no separate current-marker stored). Start here; if "step" needs to be broader than a task later, revisit then — don't over-build now.

The arc shows on the map **only for the active stream** (what June is in). For other streams it shows when the stream is opened.

## Finished — granularity that scales

On a long project, an enumerated Finished list grows longer than the live map and defeats "see the whole picture." So:

- While **few**, show finished stream names.
- As they **accumulate**, collapse to a count (`✓ 6 finished`), expandable on request.
- Destination: finished streams belong in the **project wins mirror** (see `map_and_arc.md`) — celebrated, held, off the live map. Until that's built, the collapsing count is the interim.

## The meta-arc (streams have their own larger arc)

Just as a stream has an arc (its steps), the **project has an arc** — its streams in a meaningful order (foundational → later), not arbitrary. The map orders streams to show that trajectory, so June sees where the whole project is, not just where each stream is. Mechanism: an explicit per-stream order reflecting the project arc (set with June, not guessed). *(Ordering mechanism is the one open implementation detail; the principle is settled.)*

## Determinism contract

The renderer reads fields and formats them — it never composes or paraphrases content. Content is written once (following `work_stream_register.md`) and shown verbatim. Wrap at a fixed conservative width so the TUI never re-breaks lines. Show the map inside a code block.
