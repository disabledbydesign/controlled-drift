import {
  addressedWorkItems,
  nearestProject,
  node,
  planItemDone,
  toggleDone,
} from "../../model/index.ts";
import { TaskCheck } from "../atoms/index.ts";
import { ArcStep } from "./ArcStep.tsx";
import type { TodayCtx } from "./types.ts";
import { toggleKey } from "./util.ts";

export interface PriorityListProps {
  ctx: TodayCtx;
  /**
   * True when the caller is already showing the plan's own `header` line above this list.
   * The list then drops its own "No clock times" lead so the same fact is stated once
   * instead of stacking under the woven frame and the header. Defaults to false so a
   * standalone caller still gets the lead.
   */
  reasonShown?: boolean;
}

/**
 * v4 `priorityList()` (~1024) — the second plan shape: a flat, ranked list with no clock.
 *
 * This is the fragmented-day view. It flattens every band, drops the `break` items, numbers
 * what is left, and lets the user reorder with ▲/▼.
 *
 * The ordering rule is v4's, transcribed:
 *   1. start from the stored reorder if there is one, dropping ids no longer in the plan
 *   2. otherwise take generator order
 *   3. append any plan item the stored order does not mention
 * so a regenerated plan cannot silently lose an item to a stale reorder.
 *
 * ⚠ Spec §14 leaves the ordering's source-of-truth OPEN ("what sets the order? … Decide the
 * source-of-truth and expose it as an ordered list on the plan payload"). This port keeps
 * v4's client-local reorder; nothing persists it and no reorder is logged. That is the
 * backend question, not this task's.
 *
 * ── work blocks (2026-07-18) ────────────────────────────────────────────────
 * Blocks appear here too. They USED to render their graph node's title with a project prefix
 * in front of it, and their check wrote real done-state through `toggleDone` — so the two
 * views disagreed about what checking a block means. Both are fixed here to match the
 * schedule view: June's decision is that a block is a numbered row that expands to its arc,
 * collapsed by default, because on a fragmented day the point is a short scannable list.
 *
 * ⚠ WHY THIS IS NOT `WorkBlock`. `WorkBlock.tsx` already implements this behaviour — the same
 * `blocksOpen` collapse, the same `ArcStep` addressing, the same `chunked` check — and the
 * logic below is deliberately identical to it, key for key. What could not be reused is its
 * SHELL: it is built for a band card, with a 56px clock-time gutter (a priority day has no
 * clock times, and inventing them would be fabricating data), an `EditChip`, no row number
 * and no reorder controls, and an 8px bottom margin instead of this list's hairline row.
 * Sharing one component would have meant a prop-driven shell with a branch at every one of
 * those points. If a third caller ever appears, that is the moment to extract.
 *
 * ⚠ The check writes `chunked`, NOT done — `docs/display_grain_design.md` §REVISION
 * 2026-07-14 §B: "The block *header* still carries the project-level 'did a chunk today'
 * check." Nothing here may mark the underlying project finished.
 *
 * ⚠ No project prefix on a block row. The plan phrasing is already "Work on IOP and recovery"
 * and `nearestProject` resolves to "IOP and recovery", so the plain-row path would render
 * "IOP and recovery · Work on IOP and recovery". The phrasing names the thread on its own.
 */
export function PriorityList({ ctx, reasonShown = false }: PriorityListProps) {
  const C = ctx.T.c;
  // Each item arrives with the band/item address `toggleArcStep` and the `blocksOpen` /
  // `chunked` keys need. A row's position on screen is NOT its position in the plan — the
  // reorder below moves rows freely — so the address has to travel with the item rather than
  // be recomputed from the loop index. `addressedWorkItems` drops breaks, exactly as
  // `workItems` did, and returns them in the same order.
  const addressed = addressedWorkItems(ctx.plan);
  const items = addressed.map((a) => a.item);
  // The plan item is the authority for done-ness on a plan row (a recurring's done-for-today
  // never reaches the graph). This component previously dropped the items and re-derived every
  // row from the graph alone, which is why finished chores rendered as outstanding.
  const itemById = new Map(items.map((it) => [it.id, it]));
  const addressById = new Map(addressed.map((a) => [a.item.id, a]));
  const present = new Set(items.map((it) => it.id));

  const stored = ctx.ui.priOrder;
  const order = stored
    ? stored.filter((id) => present.has(id))
    : items.map((it) => it.id);
  for (const it of items) {
    if (order.indexOf(it.id) < 0) order.push(it.id);
  }

  const move = (i: number, d: number) => {
    const a = order.slice();
    const j = i + d;
    if (j < 0 || j >= a.length) return;
    const t = a[i]!;
    a[i] = a[j]!;
    a[j] = t;
    ctx.up({ priOrder: a });
  };

  /**
   * The numbered gutter, shared by both row kinds so a block row sits in the same list rhythm
   * as a task row. Styles stay inline — this is a render helper, not a style abstraction.
   */
  const numberGutter = (i: number) => (
    <span
      style={{
        fontSize: "11px",
        color: C.dimmer,
        width: "16px",
        flex: "0 0 auto",
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {i + 1 + "."}
    </span>
  );

  /**
   * The ▲/▼ pair. `stopPropagation` matters on a BLOCK row, whose whole header is the
   * expand/collapse target — without it, reordering a block would also toggle it open.
   */
  const reorder = (i: number) => (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        flex: "0 0 auto",
      }}
    >
      <button
        onClick={(e) => {
          e.stopPropagation();
          move(i, -1);
        }}
        aria-label="move up"
        style={{
          background: "none",
          border: "1px solid " + C.border,
          borderRadius: "5px",
          color: i === 0 ? C.dimmer : C.dim,
          fontSize: "9px",
          cursor: i === 0 ? "default" : "pointer",
          padding: "2px 6px",
          fontFamily: "inherit",
        }}
      >
        ▲
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          move(i, 1);
        }}
        aria-label="move down"
        style={{
          background: "none",
          border: "1px solid " + C.border,
          borderRadius: "5px",
          color: i === order.length - 1 ? C.dimmer : C.dim,
          fontSize: "9px",
          cursor: i === order.length - 1 ? "default" : "pointer",
          padding: "2px 6px",
          fontFamily: "inherit",
        }}
      >
        ▼
      </button>
    </div>
  );

  return (
    <div>
      {reasonShown ? null : (
        <div
          style={{
            fontSize: "11px",
            color: C.dimmer,
            padding: "6px 14px 8px",
            lineHeight: 1.45,
          }}
        >
          No clock times — a ranked to-do list to pull from.
        </div>
      )}
      {order.map((id, i) => {
        const addr = addressById.get(id);
        const item = addr?.item;
        if (addr && item && item.kind === "block") {
          // The SAME keys the schedule view uses (`Band.tsx:112`). Keying by row id instead
          // would give one block two independent expand-and-chunk states that silently
          // diverge the moment she flips the Schedule/Priority toggle.
          const entryKey = addr.bandIndex + "-" + addr.itemIndex;
          const arc = item.arc || [];
          // A block with no arc is a bare did-a-chunk row with nothing to open —
          // `display_grain_design.md` decision 4 (a container project with no discrete tasks).
          const expandable = arc.length >= 1;
          // Keyed by BLOCK ID, matching the schedule view — see `WorkBlock`. A slot-position
          // key would reattach to the wrong item after a regenerate, and would give one block
          // two independent states across the Schedule/Priority toggle.
          // Absent means the SERVER's record decides (`didChunkToday` off the plan). An explicit
          // entry is her own tap, which must outrank the plan row until the server's answer
          // replaces it — including an explicit `false`, which is an un-check.
          const chunked = ctx.ui.chunked[item.id] ?? item.didChunkToday ?? false;
          const open = !!ctx.ui.blocksOpen[item.id];
          return (
            <div key={id} style={{ borderBottom: "1px solid " + C.hair }}>
              <div
                onClick={
                  expandable
                    ? () =>
                        ctx.up({
                          blocksOpen: toggleKey(ctx.ui.blocksOpen, item.id),
                        })
                    : undefined
                }
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "9px",
                  padding: "9px 14px",
                  cursor: expandable ? "pointer" : "default",
                }}
              >
                {numberGutter(i)}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Identical to the schedule view's handler: the shell owns the write and
                    // the message, and only confirms once the server has answered.
                    ctx.chunk(item.id, !chunked);
                  }}
                  aria-label="mark done"
                  aria-pressed={chunked}
                  style={{
                    flex: "0 0 auto",
                    border: "none",
                    background: "none",
                    cursor: "pointer",
                    padding: 0,
                    display: "flex",
                  }}
                >
                  {/* Gold, as in `WorkBlock` — this check means a chunk of ongoing work, not a
                      task finished, and the rose check on every other row means the latter. */}
                  <TaskCheck T={ctx.T} done={chunked} col={C.gold} size={15} />
                </button>
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
                {reorder(i)}
              </div>
              {open && expandable ? (
                <div
                  style={{
                    paddingLeft: "39px",
                    paddingRight: "14px",
                    paddingBottom: "8px",
                  }}
                >
                  {arc.map((s, si) => (
                    <ArcStep
                      key={entryKey + "-a" + si}
                      ctx={ctx}
                      step={s}
                      bandIndex={addr.bandIndex}
                      itemIndex={addr.itemIndex}
                      stepIndex={si}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          );
        }
        const n = node(ctx.idx, id);
        if (!n) return null;
        const done = planItemDone(itemById.get(id), n);
        const proj = nearestProject(ctx.idx, id);
        return (
          <div
            key={id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "9px",
              padding: "9px 14px",
              borderBottom: "1px solid " + C.hair,
            }}
          >
            {numberGutter(i)}
            <button
              onClick={() => ctx.apply(toggleDone(ctx.graph, id, done))}
              aria-label="mark done"
              aria-pressed={done}
              style={{
                flex: "0 0 auto",
                border: "none",
                background: "none",
                cursor: "pointer",
                padding: 0,
                display: "flex",
              }}
            >
              <TaskCheck T={ctx.T} done={done} col={C.rose} size={15} />
            </button>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: "13px",
                color: done ? C.dimmer : C.text,
                lineHeight: 1.35,
                textDecoration: done ? "line-through" : "none",
              }}
            >
              {proj ? (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    ctx.openDetail(proj.id);
                  }}
                  style={{
                    color: C.dim,
                    textDecoration: "underline",
                    textDecorationColor: C.roseBorder,
                    textUnderlineOffset: "2px",
                  }}
                >
                  {proj.title + " · "}
                </span>
              ) : null}
              {n.title}
            </span>
            {reorder(i)}
          </div>
        );
      })}
    </div>
  );
}
