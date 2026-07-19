import type { PlanBlockItem } from "../../fixtures/index.ts";
import { TaskCheck } from "../atoms/index.ts";
import { ArcStep } from "./ArcStep.tsx";
import { RowActions } from "./RowActions.tsx";
import type { TodayCtx } from "./types.ts";
import { toggleKey } from "./util.ts";

export interface WorkBlockProps {
  ctx: TodayCtx;
  item: PlanBlockItem;
  /** v4's `key` — also the membership key into `chunked` / `blocksOpen`. */
  entryKey: string;
  bandIndex: number;
  itemIndex: number;
}

/**
 * v4 `workBlock(it,key)` (~1089) — an ongoing-work block ("Work on the reviewer response").
 *
 * The other grain of the plan: not a task to finish today, a thread to spend time on. It
 * renders gold rather than rose, carries a chunk length instead of a duration, and can expand
 * into an arc of steps (`ArcStep`), where the step marked `here` is the real, checkoffable
 * task id.
 *
 * Tapping the header row expands the arc — but only when there IS one (`expandable`).
 *
 * ── spec §14 deltas applied ─────────────────────────────────────────────────
 * 1. **The check reads as COMPLETION, not a chunk-note.** v4 already struck the title through
 *    on check (`textDecoration:chunked?'line-through':'none'`, plus `opacity:.55`), so the
 *    VISUAL is v4's, unchanged. What changed is the language around it: v4's
 *    `aria-label`/`title` of "did a chunk today" and its `flash('Did a chunk today')` are the
 *    chunk-note narration the spec removes, so they now read as completion. The
 *    returns-tomorrow semantics stay in the backend; this surface does not narrate them.
 *    ⚠ The state key is still `chunked` — the backend concept is unchanged and renaming it
 *    would claim a data change that was not made.
 * 2. **No per-item "why" line.** No change was needed: v4's `workBlock` never rendered
 *    `it.why`. The fixture still carries the field; nothing here reads it.
 * 3. The spec also directs removing a "did a chunk today — comes back tomorrow" caption.
 *    ⚠ **No such caption exists in v4** — grepped for "comes back" / "tomorrow" across the
 *    whole mockup, zero hits. Nothing to remove; recorded so the absence is not read as a
 *    missed delta.
 */
export function WorkBlock({
  ctx,
  item,
  entryKey,
  bandIndex,
  itemIndex,
}: WorkBlockProps) {
  const C = ctx.T.c;
  const arc = item.arc || [];
  const expandable = arc.length >= 1;
  // ⚠ Keyed by the BLOCK ID, not `entryKey`. `entryKey` is `bandIndex-itemIndex` — a slot
  // position — and a regenerated plan reassigns those slots, so a persisted check would
  // reattach to whatever item now occupies the slot. The id also gives a block ONE state
  // across the Schedule/Priority toggle instead of one per view.
  // Absent means the SERVER's record decides (`didChunkToday` off the plan). An explicit
  // entry is her own tap, which must outrank the plan row until the server's answer
  // replaces it — including an explicit `false`, which is an un-check.
  const chunked = ctx.ui.chunked[item.id] ?? item.didChunkToday ?? false;
  const open = !!ctx.ui.blocksOpen[item.id];

  return (
    <div style={{ marginBottom: "8px" }}>
      <div
        onClick={
          expandable
            ? () =>
                ctx.up({ blocksOpen: toggleKey(ctx.ui.blocksOpen, item.id) })
            : undefined
        }
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "7px",
          cursor: expandable ? "pointer" : "default",
        }}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            // The shell owns the write AND the message: it raises success only once the
            // server confirms, and reports the failure itself. Previously this wrote local
            // state and flashed "Done" immediately — which reverted on reload.
            ctx.chunk(item.id, !chunked);
          }}
          aria-label="mark done"
          aria-pressed={chunked}
          style={{
            flex: "0 0 auto",
            border: "none",
            background: "none",
            cursor: "pointer",
            // Tap-target expansion (2026-07-18, TRIAL) — see `RoundCheck`, same row shape and
            // the same ~26px pitch cap. Glyph stays 15; only the hit area grows.
            padding: "5px 10px",
            margin: "-5px -10px",
            position: "relative",
            top: "2px",
            display: "flex",
          }}
        >
          <TaskCheck T={ctx.T} done={chunked} col={C.gold} size={15} />
        </button>
        <span
          style={{
            width: "56px",
            flex: "0 0 auto",
            fontSize: "10px",
            color: C.dimmer,
            lineHeight: 1.3,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {item.time}
        </span>
        <span
          style={{
            flex: 1,
            minWidth: 0,
            fontSize: "13px",
            fontWeight: 600,
            color: C.gold,
            lineHeight: 1.35,
            textDecoration: chunked ? "line-through" : "none",
            opacity: chunked ? 0.55 : 1,
          }}
        >
          {item.task}
        </span>
        {/* Inline in the row (A1). `kind="block"` is load-bearing twice over: the removal drops
            every row of the project, and the length control says "chunk length" rather than
            "duration" — how long she works on this in a sitting, not how long one thing takes.

            A5 — the row's own `EditChip` is gone from here for the reason given in `TaskRow`:
            it put the word `edit` on this line twice. The way into the block's object editor is
            now the fourth item inside the panel, dispatching on this same project id. */}
        <RowActions ctx={ctx} id={item.id} kind="block" durationMin={item.chunkMin} />
      </div>
      {open ? (
        <div
          style={{
            paddingLeft: "62px",
            paddingTop: "5px",
            paddingRight: "8px",
          }}
        >
          {arc.map((s, i) => (
            <ArcStep
              key={entryKey + "-a" + i}
              ctx={ctx}
              step={s}
              bandIndex={bandIndex}
              itemIndex={itemIndex}
              stepIndex={i}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
