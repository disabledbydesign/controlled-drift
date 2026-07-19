import type { PlanTaskItem } from '../../fixtures/index.ts';
import { nearestProject, node, planItemDone, toggleDone } from '../../model/index.ts';
import { RoundCheck } from '../atoms/index.ts';
import { RowActions } from './RowActions.tsx';
import { movingRowStyle, planDrag } from './placement.ts';
import { moveOptions } from './moveTargets.ts';
import type { TodayCtx } from './types.ts';
import { toggleKey } from './util.ts';

export interface TaskRowProps {
  ctx: TodayCtx;
  item: PlanTaskItem;
  /** v4's `key` — also the membership key into `heldOpen`. */
  entryKey: string;
  /** v4's `showProj` — the Priority list has its own project prefix, the bands use this one. */
  showProj: boolean;
}

/**
 * v4 `taskRow(it,key,showProj)` (~1074) — a real, checkoffable task inside a clock band.
 *
 * Renders nothing when the plan references an id that is not in the graph (v4: `if(!n)return null`).
 *
 * The whole title is a check target, not just the box — v4 puts `toggleDone` on the text span
 * as well. The project prefix inside it stops propagation and opens the project instead.
 *
 * ── spec §14 deltas applied ─────────────────────────────────────────────────
 * 1. **Held-back items expand inline.** The `· N more` affordance toggles a list of
 *    `held_back_names` under the row, and is hidden when the list is empty. ⚠ This is v4's
 *    existing behaviour, unchanged — v4 already had both the affordance and the inline
 *    expansion. The delta describes it; it did not require a change here.
 * 2. **No per-item "why" line.** No change was needed: v4's `taskRow` never rendered
 *    `it.why`. The fixture still carries the field; nothing here reads it.
 *
 * ⚠ `it.description` is also carried by the fixture and rendered by neither v4 nor this port.
 * Left unrendered to match v4 rather than invented; flagged, not fixed.
 */
export function TaskRow({ ctx, item, entryKey, showProj }: TaskRowProps) {
  const C = ctx.T.c;
  const n = node(ctx.idx, item.id);
  if (!n) return null;

  // ⚠ NOT `isDone(n)`. A recurring's done-for-today reaches the client only on the plan
  // payload — the graph node has nothing. See `planItemDone`.
  const done = planItemDone(item, n);
  const proj = nearestProject(ctx.idx, item.id);
  const held = item.heldBack || [];
  const heldOpen = !!ctx.ui.heldOpen[entryKey];

  /**
   * A3 — CLICK-AND-DRAG, ON THE DESKTOP ONLY.
   *
   * June asked for drag on the desktop and rejected it on her phone, where it does not work, so
   * `ctx.wide` (the 900px breakpoint, one read, drilled from `useSurface`) chooses. The drag does
   * not open a second way of computing a move: it enters the SAME placement mode a tap does, so
   * the slots, the arithmetic and the legality rules are one set.
   *
   * ⚠ AN ILLEGAL DRAG REFUSES IN WORDS. `dragstart` asks `moveOptions` first, and on a refusal it
   * calls `preventDefault()` and says why — a row that lifts, travels and snaps back with nothing
   * said is the failure `desk.test.tsx` documents for the Map drag, arriving here by another
   * route. An appointment therefore never begins a drag at all.
   */
  const moving = ctx.ui.movePick === item.id;
  const dragProps = !ctx.wide
    ? {}
    : {
        draggable: true,
        onDragStart: (e: import('react').DragEvent<HTMLDivElement>) => {
          e.stopPropagation();
          const opts = moveOptions(ctx.plan, item.id, (it) =>
            'task' in it && it.task ? it.task : 'this row',
          );
          if (opts.refusal) {
            // Never a silent snap-back.
            e.preventDefault();
            ctx.flash(
              opts.refusal === 'appointment'
                ? 'This is an appointment at a fixed time, so it does not move.'
                : opts.refusal === 'not-found'
                  ? 'I could not find this row in today’s plan, so it cannot be moved.'
                  : 'There is nowhere else to put this today.',
            );
            return;
          }
          planDrag.id = item.id;
          try {
            e.dataTransfer.setData('text/plain', item.id);
          } catch {
            // Some browsers throw on setData outside a real drag; `Row.tsx` swallows it too.
          }
          e.dataTransfer.effectAllowed = 'move';
          ctx.up({ movePick: item.id });
        },
        onDragEnd: () => {
          planDrag.id = null;
          // The slots come down with the drag. A drop has already cleared `movePick` itself.
          if (ctx.ui.movePick === item.id) ctx.up({ movePick: null });
        },
      };

  return (
    <div
      // Markers, not styling: `data-moving-row` is how a test can see WHERE the moving row sits
      // relative to the landing slots (the bilateral check), and `data-row-line` is how it can
      // see that the trigger shares the row's own line rather than having taken a new one.
      data-moving-row={moving ? '1' : undefined}
      style={{ marginBottom: '9px', ...(movingRowStyle(ctx, moving) ?? {}) }}
      {...dragProps}
    >
      <div data-row-line="1" style={{ display: 'flex', alignItems: 'baseline', gap: '7px' }}>
        <RoundCheck T={ctx.T} done={done} onClick={() => ctx.apply(toggleDone(ctx.graph, item.id, done))} />
        <span
          style={{
            width: '56px',
            flex: '0 0 auto',
            fontSize: '10px',
            color: C.dimmer,
            lineHeight: 1.3,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {item.time}
        </span>
        <span
          onClick={() => ctx.apply(toggleDone(ctx.graph, item.id, done))}
          style={{
            flex: 1,
            minWidth: 0,
            fontSize: '13px',
            color: done ? C.dimmer : C.text,
            lineHeight: 1.35,
            cursor: 'pointer',
            textDecoration: done ? 'line-through' : 'none',
          }}
        >
          {showProj && proj ? (
            <>
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  ctx.openDetail(proj.id);
                }}
                style={{
                  color: C.dim,
                  textDecoration: 'underline',
                  textDecorationColor: C.roseBorder,
                  textUnderlineOffset: '2px',
                }}
              >
                {proj.title}
              </span>
              <span style={{ color: C.dimmer }}>{' · '}</span>
            </>
          ) : null}
          <span>{n.title}</span>
          {held.length ? (
            <span
              onClick={(e) => {
                e.stopPropagation();
                ctx.up({ heldOpen: toggleKey(ctx.ui.heldOpen, entryKey) });
              }}
              style={{
                color: C.dim,
                fontSize: '12px',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                textDecoration: 'underline',
                textDecorationColor: C.roseBorder,
                textUnderlineOffset: '2px',
              }}
            >
              {' · ' + held.length + ' more'}
            </span>
          ) : null}
        </span>
        {/* A1 — INLINE IN THE ROW, as the old surface had it (`editChipHtml` inside `.item-top`,
            `docs/overlay_daily.html:2236`). It no longer occupies a line of its own: that line was
            added to EVERY row of a phone list, and the panel it opened pushed the rows below it
            down. The panel is now a floating pane anchored to this trigger.

            A5 — THE ROW'S `EditChip` IS GONE FROM HERE. It rendered the word `edit` on this same
            line, beside a trigger June ruled must also say `edit`. The route into the object
            editor is not lost: it is the fourth item inside the panel (`RowActions`), which
            costs one tap and is what she chose over two controls sharing a word. */}
        <RowActions ctx={ctx} id={item.id} kind="task" durationMin={item.durationMin} />
      </div>
      {held.length && heldOpen ? (
        <div style={{ paddingLeft: '78px', marginTop: '3px' }}>
          <div style={{ fontSize: '10.5px', color: C.dimmer, marginBottom: '2px' }}>
            held under this thread, not today:
          </div>
          {held.map((nm, ix) => (
            <div key={ix} style={{ fontSize: '12px', color: C.dim, lineHeight: 1.4 }}>
              {nm}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
