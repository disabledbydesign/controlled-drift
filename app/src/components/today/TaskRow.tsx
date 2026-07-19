import type { PlanTaskItem } from '../../fixtures/index.ts';
import { nearestProject, node, planItemDone, toggleDone } from '../../model/index.ts';
import { EditChip, RoundCheck } from '../atoms/index.ts';
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

  return (
    <div style={{ marginBottom: '9px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '7px' }}>
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
        <EditChip T={ctx.T} onClick={() => ctx.openDetail(item.id)} />
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
