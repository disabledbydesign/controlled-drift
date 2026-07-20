import { useEffect, useRef } from "react";
import {
  addressedWorkItems,
  nearestProject,
  node,
  planItemDone,
  toggleDone,
} from "../../model/index.ts";
import { readPriorityOrder, savePriorityOrder } from "../../api/planRow.ts";
import type { PlanItem } from "../../fixtures/index.ts";
import { TaskCheck } from "../atoms/index.ts";
import { ArcStep } from "./ArcStep.tsx";
import { RowActions } from "./RowActions.tsx";
import { PlaceTarget } from "./PlaceTarget.tsx";
import { neighbourSlot, placementFor, planDrag } from "./placement.ts";
import type { NudgeRefusal } from "./placement.ts";
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
 * ⚠ RESOLVED 2026-07-19 — this note used to read "nothing persists it". Spec §14 left the
 * ordering's source-of-truth open ("Decide the source-of-truth and expose it as an ordered list
 * on the plan payload") and June has now decided it: "Yes, should persist." Her reorder is
 * written to `POST /api/plan/priority-order` and rides back on the plan payload as
 * `priority_order`, which is exactly the shape §14 asked for. See `move` below.
 *
 * The three-step ordering rule above is what makes a stale order safe: ids no longer in the
 * plan are dropped and unmentioned items are appended, so a persisted order can never hide a
 * row. A REGENERATION drops the saved order outright — see `plan_store.set_priority_order`
 * for that decision and the alternative left open for June.
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
/**
 * A task row's own duration, or 0 when it is unset or the row is not a task. Only `PlanTaskItem`
 * carries `durationMin`; reading it off a block would report a chunk length as a duration, which
 * is the one distinction the length control exists to keep straight.
 */
function durationOf(item: PlanItem | undefined): number {
  return item && item.kind === 'task' ? item.durationMin : 0;
}

export function PriorityList({ ctx, reasonShown = false }: PriorityListProps) {
  const C = ctx.T.c;
  // Each item arrives with the band/item address `toggleArcStep` and the `blocksOpen` /
  // `chunked` keys need. A row's position on screen is NOT its position in the plan — the
  // reorder below moves rows freely — so the address has to travel with the item rather than
  // be recomputed from the loop index. `addressedWorkItems` drops breaks, exactly as
  // `workItems` did, and returns them in the same order.
  /*
   * ⚠ AN ID-LESS ROW IS NOT ADDRESSABLE AND MUST NOT REACH THE WIRE (live-verified 2026-07-20).
   *
   * `addressedWorkItems` drops `kind:'break'` rows, and that used to be the whole filter. It is
   * not enough: a fixed anchor the generator writes without an id (Lunch, "Rest or light
   * activity") arrives as `kind:'task'` with `id: ''`. Such a row renders NOTHING — `node()`
   * below cannot resolve `''` and the row returns null — but it still entered `order`, so the
   * reorder payload went out as
   *     {"order":["bafyrei…","bafyrei…","","bafyrei…", …]}
   * and the server answered 400 for the whole request. Her reordering then reverted on reload
   * with no message: the exact silent failure this screen exists to remove.
   *
   * A duplicate id is rejected the same way and for the same reason — it makes a ranking that
   * names one row twice, and two React children with one key.
   *
   * Filtering HERE rather than at the send site is deliberate: `order`, the rendered rows and
   * the ▲▼ indices all have to describe one list, or a move computed in one space lands in
   * another.
   */
  const addressed = addressedWorkItems(ctx.plan).filter((a) => Boolean(a.item.id));
  const items = addressed.map((a) => a.item);
  // The plan item is the authority for done-ness on a plan row (a recurring's done-for-today
  // never reaches the graph). This component previously dropped the items and re-derived every
  // row from the graph alone, which is why finished chores rendered as outstanding.
  const itemById = new Map(items.map((it) => [it.id, it]));
  const addressById = new Map(addressed.map((a) => [a.item.id, a]));
  const present = new Set(items.map((it) => it.id));

  // The three-step rule, unchanged in intent: start from her stored ranking, drop ids the plan
  // no longer has, then append anything the ranking does not mention — so a stale order can
  // never hide a row. `seen` adds only the de-duplication above; an id already placed is not
  // placed again, in either step.
  /*
   * ⚠ ON A CLOCK-SHAPE DAY THIS VIEW SHOWS THE PLAN'S OWN ORDER, AND ONLY THAT.
   *
   * June, 2026-07-20, on what the Priority toggle should show on a timed day: "the same list as
   * the clock times, but as a list rather than a schedule with clock times." Same rows, same
   * order. She did not design a separate ranking for a timed day, so there is none: `ui.priOrder`
   * is a FRAGMENTED-day ranking, and applying it here would show her a list whose order the clock
   * view contradicts — two answers to "what is my day", from one plan.
   *
   * It is reachable state, not a hypothetical: a ranking hydrated on a fragmented day survives in
   * `ui` across a regenerate that hands back a clock-shape plan.
   */
  const timedDay = ctx.plan.shape !== 'priority';
  const stored = timedDay ? null : ctx.ui.priOrder;
  const seen = new Set<string>();
  const order: string[] = [];
  // ONE gate, not two: `present` is built from the id-filtered `addressed` above, so an id-less
  // row is already absent from it and needs no second `!id` test here. A duplicated guard reads
  // as belt-and-braces and behaves as dead code — either half can be removed with every test
  // still green, which is how a rule quietly stops being enforced.
  const place = (id: string) => {
    if (seen.has(id) || !present.has(id)) return;
    seen.add(id);
    order.push(id);
  };
  for (const id of stored ?? []) place(id);
  for (const it of items) place(it.id);

  /**
   * A2 on the FRAGMENTED day — the same landing slots the schedule view draws, anchored by the
   * ROW they follow rather than by a plan index.
   *
   * ⚠ This is why `MoveDestination` carries `afterId` as well as `beforeIndex`. This list is not
   * the plan's band verbatim: it drops breaks, and it honours June's own local reorder
   * (`ui.priOrder`), so a numeric plan index does not address a row on this screen. Anchoring to
   * the named row puts the slot under the row she is actually looking at.
   *
   * ⚠ FLAGGED, NOT SILENTLY HANDLED, AND NOW MORE REACHABLE: when she has reordered this list,
   * the position sent to the server is computed against the PLAN's order (`moveTargets.locate`
   * works in the server's index space) while the slot she taps is anchored by `afterId` in her
   * DISPLAYED order. So a move made against a reordered view can land somewhere other than
   * where the slot appeared.
   *
   * That divergence predates this file's persistence change, but persistence widens it: the
   * reorder used to die on reload, so a fresh session always displayed the plan's own order and
   * the two spaces agreed. Now her order is there every session.
   *
   * ⚠ PARTIALLY MITIGATED, NOT FIXED. `plan_store.move_priority_item` clears the saved ranking,
   * so after a move the list falls back to the plan's real order and she SEES where the item
   * actually went instead of a stale ranking hiding it. The move can still land in the wrong
   * spot. The clean fix is available now and is NOT done here: this screen could send the
   * resulting full id order to `POST /api/plan/priority-order` instead of a position, which has
   * no index space to disagree with. Reported for a separate task.
   */
  /*
   * ⚠ THE VISIBLE NUMBER COUNTS RENDERED ROWS, NOT ENTRIES IN `order`.
   *
   * The gutter used to print the `order` index, so any row that did not render still consumed
   * its number and the list read "1, 2, 4, 5, 6" — she is asked to work a ranked list whose
   * numbering says a row is missing. A row can still fail to render for a reason this component
   * does not control: `node(ctx.idx, id)` resolves against the graph, and a plan can name a task
   * the loaded graph does not have.
   *
   * Such a row keeps its place in `order` — dropping it would silently discard its ranking on
   * the next save — so the two indices are tracked separately: `order` position drives ▲▼ (the
   * space `move` works in), and this map drives what she reads.
   */
  const renderIndex = new Map<string, number>();
  for (const id of order) {
    const a = addressById.get(id);
    if (a?.item.kind === 'block' || node(ctx.idx, id)) renderIndex.set(id, renderIndex.size);
  }

  const placing = placementFor(ctx);
  const slotFor = (afterId: string | null) =>
    placing.movingId
      ? placing.slots
          .filter((d) => d.afterId === afterId)
          .map((d) => (
            <PlaceTarget
              key={"slot-" + d.key}
              ctx={ctx}
              dest={d}
              dropping={!!planDrag.id}
              onPick={(dd) => ctx.moveItem(placing.movingId!, dd.target)}
            />
          ))
      : null;

  /**
   * ── HER ORDERING NOW SURVIVES A RELOAD (2026-07-19) ─────────────────────────
   * June's decision: "Yes, should persist." This closes `docs/api_contract_v2.md` §6 Q1 and the
   * open question this file's header used to record ("nothing persists it").
   *
   * ⚠ WHY THE READ AND THE WRITE ARE HERE AND NOT IN THE SHELL. Every other server write on this
   * screen arrives as a `TodayCtx` callback that `useAppState` implements — `chunk`, `notToday`,
   * `setDuration`, `moveItem` — and that is where this one belongs too. It is not there because
   * `shell/useAppState.ts`, `today/types.ts` and `api/adapt.ts` were all held by a concurrent
   * build when this landed, and staging a shared file would have committed someone else's
   * unfinished work. The seam is deliberately shaped so lifting it later is a move, not a
   * rewrite: both calls are single expressions against `api/planRow.ts` and neither reads
   * anything a shell callback could not be handed.
   *
   * The hydrating read costs one extra `GET /api/plan` on first render of a fragmented day. If
   * this is lifted into the shell, that read disappears entirely — the shell already has the
   * plan payload the order rides on.
   */
  const hydrated = useRef(false);
  const storedOrder = ctx.ui.priOrder;
  const upFn = ctx.up;
  useEffect(() => {
    // Only when she has no ordering on screen yet. An order already in `ui` is either hers from
    // this session or an earlier hydration, and re-reading would overwrite a fresh reorder with
    // whatever the server last heard.
    // Nothing to hydrate on a timed day: the stored ranking is a fragmented-day one and this
    // view does not apply it (see `timedDay` above), so reading it would spend a request on a
    // value nothing renders.
    if (timedDay || storedOrder || hydrated.current) return;
    hydrated.current = true;
    void (async () => {
      const saved = await readPriorityOrder();
      // ⚠ `null` covers BOTH "nothing saved" and "the read failed", and both must leave the
      // generator's order standing in silence. Neither is something she did wrong, and neither
      // is worth a message about a ranking she may never have made.
      if (saved && saved.length) upFn({ priOrder: saved });
    })();
  }, [timedDay, storedOrder, upFn]);

  /**
   * Why a nudge on a timed day did not happen, in her words. Literal throughout: each one names
   * the row's real obstacle and then says the thing she needs to know, which is that her ordering
   * is unchanged. A refusal that only explains itself still leaves her guessing whether the list
   * moved.
   */
  const nudgeRefusalText = (why: NudgeRefusal): string => {
    if (why === 'appointment') {
      return 'That row has a fixed time, so it stays where it is — your ordering did not change.';
    }
    if (why === 'not-found') {
      return 'I could not find that row in today’s plan, so nothing moved — your ordering did not change.';
    }
    // 'nowhere' and 'no-slot' are one sentence to her: both mean the plan has no other position
    // for this row in the direction she pushed it.
    return 'There is no other place in today’s plan for that row, so nothing moved — your ordering did not change.';
  };

  /**
   * ── THE ▲/▼ CONTROLS ROUTE BY THE PLAN'S SHAPE ───────────────────────────────
   *
   * A fragmented day has a flat ranking and `POST /api/plan/priority-order` stores it. A
   * CLOCK-SHAPE day does not: `plan_store.set_priority_order` raises `LookupError` for one,
   * because a clock-shape day orders its rows under `blocks[]`. Until 2026-07-20 both shapes sent
   * the same request, so on a timed day these arrows moved the row on screen, took a 400, said
   * NOTHING, and the ordering reverted on the next load — live-verified against her real plan.
   *
   * A timed day therefore goes to `POST /api/task/move`, which already relocates one row in the
   * cached plan in either direction and re-flows the clock times. That is what moving a row up or
   * down on a timed day means, and it is the endpoint that means it.
   */
  const move = (i: number, d: number) => {
    const a = order.slice();
    const j = i + d;
    if (j < 0 || j >= a.length) return;
    if (timedDay) {
      const id = a[i]!;
      // Where the row should end up: immediately below the neighbour it passes going DOWN, and
      // immediately below that neighbour's own predecessor going UP — which for the top of the
      // list is the band's first slot, named by `null`.
      const anchorId = d > 0 ? a[j]! : j > 0 ? a[j - 1]! : null;
      const anchorBand = addressById.get(a[j]!)?.bandIndex ?? 0;
      const nudge = neighbourSlot(ctx, id, anchorId, anchorBand);
      if (nudge.refusal) {
        // Said as a FAILURE and recorded, not flashed as a success. Nothing moved on screen
        // either, so there is nothing to put back — she sees one message and one unchanged list.
        ctx.fail(nudgeRefusalText(nudge.refusal), id);
        return;
      }
      // `moveRow` in the shell owns the request, the rewritten plan it answers with, and the
      // report either way — including "That did not move — it is where it was." on a refusal from
      // the server. Reporting it a second time here would tell her twice.
      ctx.moveItem(id, nudge.target);
      return;
    }
    const t = a[i]!;
    a[i] = a[j]!;
    a[j] = t;
    // The screen moves first and the write follows. Gating the reorder on the round-trip would
    // make an arrow tap feel dead; the ordering is hers either way, and a failure says so below.
    ctx.up({ priOrder: a });
    void (async () => {
      const res = await savePriorityOrder(a);
      // No silent failures: an unsaved ordering that looks saved is the exact thing this whole
      // change removes. The row stays where she put it for this session — undoing her move on
      // top of the bad news would be a second surprise — and the sentence is the server's own.
      if (res.kind === 'failed') {
        // ⚠ `fail`, NOT `flash` (2026-07-20). `flash` routes through `apply` and raises a
        // SUCCESS-kind signal, so this sentence was arriving in the same bar that says a write
        // landed — and reached no log, so a message she swiped away left no trace. `fail` raises
        // the failure signal and records it through `POST /api/log/correction`.
        ctx.fail(
          'That new order did not save, so it will not be here next time. ' + res.error,
          a[i] ?? null,
        );
      }
    })();
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
      {/* The slot at the top of the list — "first in the list", the earlier direction made
          visible. */}
      {slotFor(null)}
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
            <div key={id}>
            <div style={{ borderBottom: "1px solid " + C.hair }}>
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
                {numberGutter(renderIndex.get(id)!)}
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
                {/* Inline in the row (A1). A block: the removal drops every row of the project,
                    and the length is a chunk length, not a duration. */}
                <RowActions ctx={ctx} id={item.id} kind="block" durationMin={item.chunkMin} />
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
            {slotFor(id)}
            </div>
          );
        }
        const n = node(ctx.idx, id);
        if (!n) return null;
        const done = planItemDone(itemById.get(id), n);
        const proj = nearestProject(ctx.idx, id);
        return (
          // The hairline moves to an OUTER wrapper so the action panel opens INSIDE the row's
          // rule rather than below it. The flex line itself is unchanged.
          <div key={id} data-moving-row={ctx.ui.movePick === id ? "1" : undefined}>
          <div style={{ borderBottom: "1px solid " + C.hair }}>
          <div
            data-row-line="1"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "9px",
              padding: "9px 14px",
            }}
          >
            {numberGutter(renderIndex.get(id)!)}
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
            {/* Inline in the row (A1) — see `TaskRow`. */}
            <RowActions
              ctx={ctx}
              id={id}
              kind="task"
              durationMin={durationOf(itemById.get(id))}
            />
            {reorder(i)}
          </div>
          </div>
          {slotFor(id)}
          </div>
        );
      })}
    </div>
  );
}
