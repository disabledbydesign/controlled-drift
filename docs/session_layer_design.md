# The session layer — capture/weed from the overlay, and the session log beneath it

*Settled in the Add-tab design workshop, 2026-06-23 (June + Claude). This is the design residue —
read it before building. The build plan lives separately (see `docs/superpowers/plans/`).*

## What this is and why it exists

The overlay can show the plan and act on tasks (done/undo/renegotiate). It can't yet **add**
anything. The from-bed loop in `morning_build_vision.md` needs the last piece: wake, see the plan,
notice what's missing, add it, optionally replan — without opening Claude Code.

The trap we nearly fell into: building a dumb "add a task" button that writes a bare name to
Anytype. That throws away the whole point. **In Claude Code, "capture" isn't a separate LLM call —
Claude Code *is* the LLM.** It reads what June says, infers type, links to the right project, runs
the alignment check, then writes. The overlay is a plain Python server with *no* intelligence unless
we explicitly call one. So overlay capture has to call the LLM itself to get the drift-skill-equivalent
behavior. Anything less creates orphaned, unaligned items — the opposite of the telos.

## The reframe that shaped the design

Capture is not its own little feature. The weeding gate **already** handles a single item and a messy
dump identically (it reads input as a web either way). And once the session can route input to
different handlers, the same surface that captures can later carry **stuck-support** ("I'm stuck" →
think-with-me → which may *output into the plan*). Add, negotiate, and stuck are not parallel buttons —
they're entangled turns in one session. "Reorganize my day and add that task I gave you last turn" is
one sentence that crosses two of them.

So the design question moved from *"what is the Add tab"* to **"what is the session, and what can it
hold."**

## What ships now vs. the direction

- **Now (A):** a dedicated **Add tab** (Today · Map · Add) running the weeding gate via the existing
  `generate()` seam, with full Goals/Projects context. Type inference, project linking, and the
  scale-2 alignment check all come from the prompt — the UI is just a textarea + a scannable receipt.
- **Built-for (B):** a broad session conversation that routes add / negotiate / (later) stuck through
  one history. We do **not** build B now, but we build the session log in the shape B needs, so B
  becomes a UI+prompt addition later, not an infrastructure rewrite.
- **Capture history and negotiate history stay SEPARATE** (June's call) — same mechanism, two streams.

## The session log — the load-bearing piece

A generic capture log records the transaction: what, when, type, where. That serves anyone and serves
June **badly**, because it discards the channel her access needs live in. Beyond the transaction, each
turn entry holds four more things, each tied to a specific need:

1. **Raw input, verbatim.** "Call my surgeon TODAY, this is stressing me out" and "surgeon at some
   point" create the same Task but mean different things next turn. The *how* carries capacity/affect
   June doesn't always name. A result-only log kills the inference channel; both affect channels are
   first-class (spec §4), so the raw words stay.
2. **The capacity/affect read + source tag + reasoning.** What the LLM read about her state, whether
   she *stated* it or it was *inferred*, and why. So the next turn doesn't make her re-state her state
   (spoons), and so she can *see and correct* a wrong read. Guard #6 made concrete (FeelingSignal: name,
   intensity, source, raw_text).
3. **Created items + the alignment reasoning per link.** Not "Task → Material survival" but *why that
   link*. When she comes back confused about why something landed where it did, the why is there, not
   silently re-derived. Guard #6.
4. **Her corrections.** A redirect ("no, link it to Job Search") is the richest learning signal — and
   the thing that retroactively reveals a *silent* miscategorization.

**The log entry must fit the actual weed output, not a flat list.** The weeding gate emits **groups
with a through-line** (the relational insight — "these three are one thread"), then items under each.
The through-line is part of what was surfaced and is exactly what June returns to, so a weed entry holds
the group structure. **The structure carries the richness; June's receipt is a projection of it**
(store-vs-surface). Flat structure → flat surface, forever. This is why the schema decision is the
expensive one and has to be right now.

**Bounds:** time-windowed (drop entries older than ~8h on read) and truncate-oldest under a token
budget. No LLM-summarization yet — truncate is enough until there's real volume data. Lives in
`~/.controlled-drift/` (the long-running launchd server keeps it in memory across requests; the file is
the durable copy).

## Failure logging — the design driver, not hygiene

June named the real failure mode: *the system degrades → she doesn't attribute it to a fixable cause →
she forgets it could be the issue → she stops using it.* An ADHD-specific abandonment cascade, and the
telos turned against itself. "June can't hold alignment, so the system holds it" applied recursively:
**she can't be relied on to hold the record of the system's own failures, so the system holds that too**
(spec §0, applied to the session).

Three routes, in increasing subtlety:

- **Hard failures** — context-window exceeded, create failed, parse failed → logged loudly with full
  context, never silent. (Context-window-exceeded is explicit: log prompt size + which entries were
  dropped.)
- **Silent failures** (nothing errors — the dangerous kind) — a correction at 11:05 referencing a
  capture at 10:23 is a *detectable* "that capture was wrong" signal. The failure lives in the
  **relation between two log entries**, and the timestamped log with raw inputs is what lets a loop find
  it (the openings/takings-up move — the finding is in the relation, not either record alone).
- **The abandonment guard** — errors rising, corrections spiking, **affective drift in June's own
  prompts** (frustration/desperation creeping in), or **usage cadence dropping / app abandoned** are
  degradation patterns a maintenance pass or the morning push can surface ("capture's been erroring this
  week — worth a look") so June never has to be the one who notices and diagnoses. *(Both new signals —
  prompt-affect drift and disengagement — flagged in Anytype under "Learning loops design".)*

## Undo

Banner-triggered, cheap, no LLM round-trip: call `gsdo_objects` with the item id, write an undo entry to
the log. The LLM sees the undo in the log next turn without processing it. (In B, "actually undo that"
as a message reaches the same log entry.) Either way **the undo lives in the log** — it's part of the
session record.

## Deliberately NOT in scope (so the build stays bounded)

- **Stuck-support's response shape** — genuinely undesigned (spec §10); first case data is in Anytype,
  not ready to build. Flagged: don't freeze the log schema in a shape that can't hold its output.
- **B fully absorbing the Today/negotiate flow** — a direction, not a commitment.
- **LLM-summarizing the log** — truncate-oldest until real volume data says otherwise.
- **Smart context trimming / granularity-by-stream for scale** — current data is minimal and not
  representative; tune when the system is actually large, not now. (Real concern, wrong time.)
- **Agentic verification/looping or forking transcripts per tool** — June flagged as likely overkill;
  the structured log + per-prompt assembly achieves the same end more simply.

## Edge cases / stress tests to carry into the build

- Track prompt size every assembly; log when it crosses a threshold; log context-window-exceeded
  explicitly (never silent).
- Stress-test with realistic task volume — the live space is minimal test data, not representative.
- Keep capture vs. negotiate history strictly separate.
- Session entries from a prior day must not bleed into today (the time window handles this).

## Shared-vs-divergent logic (the no-drift audit — June's standing concern)

The weeding *intelligence* is single-source and won't drift: `prompts/weeding_gate.md` is run by
BOTH the Claude Code drift skill and `capture_generate.py`, and both write through
`gsdo_objects.create`. Two things surfaced during the build:

- **Over-eager dedup (fixed in the shared prompt, 2026-06-23).** The gate was treating same-topic/
  same-project items as duplicates (it skipped "email the editor about the paper" as a dup of an
  existing Haraway email). Tightened in `weeding_gate.md`: a match means the *same action/
  deliverable*, not the same topic/project/person; when unsure, **create-with-a-note, never silently
  drop**. Because it's in the shared prompt, both paths get the fix. The overlay's JSON contract was
  also slimmed to *mechanics only* so it no longer restates (and could drift from) the gate's dedup
  judgment.
- **⚠️ Link-kind guard is OVERLAY-ONLY (divergence to watch — flagged in Anytype under "v1 — capture
  and write quality").** `capture_generate.py` drops a wrong-kind link (a Task pointed at a Goal),
  but that guard lives in the overlay because the P#/G# tokens are an overlay mechanism. The Claude
  Code path links directly and has no equivalent. The fix is to move the underlying rule into the
  shared write layer (`gsdo_objects.create` or a shared validator that checks the target's type
  against the link property), so both inherit it. Until then: marked in code (the `_LINK_TOKEN_PREFIX`
  comment) and tracked in Anytype.

## What the build will likely touch (for the plan)

- `scripts/session_store.py` (new) — the structured action log (entry shape above; time-bound;
  truncate-oldest; failure entries).
- `scripts/capture_generate.py` (new) — weeding gate via `generate()`; reuses `build_context()`;
  reads recent session entries; parses grouped output; creates via `gsdo_objects.create`; writes the log.
- `scripts/server.py` — `POST /api/capture` (async, 202 + poll, mirrors `/api/negotiate`); wire
  negotiate to read its own session history.
- `scripts/plan_generate.py` — `negotiate()` reads negotiate-history; prompt-size + context-window
  logging.
- `docs/overlay_daily.html` — Add tab, session receipt, undo affordance.
- `tests/` — `test_session_store.py`, `test_capture_generate.py`, capture route in `test_server.py`.
