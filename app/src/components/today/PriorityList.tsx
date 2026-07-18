import { isDone, nearestProject, node, toggleDone, workItems } from '../../model/index.ts';
import { TaskCheck } from '../atoms/index.ts';
import type { TodayCtx } from './types.ts';

export interface PriorityListProps {
  ctx: TodayCtx;
}

/**
 * v4 `priorityList()` (~1024) — the second plan shape: a flat, ranked list with no clock.
 *
 * This is the fragmented-day view. It flattens every band, drops the `break` items
 * (`workItems`), numbers what is left, and lets the user reorder with ▲/▼.
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
 * ⚠ Blocks appear here too, and they render their NODE's title (`n.title`), not the plan's
 * "Work on X" phrasing (`it.task`) that the schedule view uses. v4's behaviour; flagged, not
 * fixed. The check also writes real done-state through `toggleDone`, where the schedule
 * view's block check writes the separate `chunked` UI state — the two views disagree about
 * what checking a block means. v4's, flagged, not fixed.
 */
export function PriorityList({ ctx }: PriorityListProps) {
  const C = ctx.T.c;
  const items = workItems(ctx.plan);
  const present = new Set(items.map((it) => it.id));

  const stored = ctx.ui.priOrder;
  const order = stored ? stored.filter((id) => present.has(id)) : items.map((it) => it.id);
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

  return (
    <div>
      <div style={{ fontSize: '11px', color: C.dimmer, padding: '6px 14px 8px', lineHeight: 1.45 }}>
        No clock times — a ranked to-do list to pull from.
      </div>
      {order.map((id, i) => {
        const n = node(ctx.idx, id);
        if (!n) return null;
        const done = isDone(n);
        const proj = nearestProject(ctx.idx, id);
        return (
          <div
            key={id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '9px',
              padding: '9px 14px',
              borderBottom: '1px solid ' + C.hair,
            }}
          >
            <span
              style={{
                fontSize: '11px',
                color: C.dimmer,
                width: '16px',
                flex: '0 0 auto',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {i + 1 + '.'}
            </span>
            <button
              onClick={() => ctx.apply(toggleDone(ctx.graph, id))}
              aria-label="mark done"
              style={{
                flex: '0 0 auto',
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                padding: 0,
                display: 'flex',
              }}
            >
              <TaskCheck T={ctx.T} done={done} col={C.rose} size={15} />
            </button>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: '13px',
                color: done ? C.dimmer : C.text,
                lineHeight: 1.35,
                textDecoration: done ? 'line-through' : 'none',
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
                    textDecoration: 'underline',
                    textDecorationColor: C.roseBorder,
                    textUnderlineOffset: '2px',
                  }}
                >
                  {proj.title + ' · '}
                </span>
              ) : null}
              {n.title}
            </span>
            <div
              style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: '0 0 auto' }}
            >
              <button
                onClick={() => move(i, -1)}
                aria-label="move up"
                style={{
                  background: 'none',
                  border: '1px solid ' + C.border,
                  borderRadius: '5px',
                  color: i === 0 ? C.dimmer : C.dim,
                  fontSize: '9px',
                  cursor: i === 0 ? 'default' : 'pointer',
                  padding: '2px 6px',
                  fontFamily: 'inherit',
                }}
              >
                ▲
              </button>
              <button
                onClick={() => move(i, 1)}
                aria-label="move down"
                style={{
                  background: 'none',
                  border: '1px solid ' + C.border,
                  borderRadius: '5px',
                  color: i === order.length - 1 ? C.dimmer : C.dim,
                  fontSize: '9px',
                  cursor: i === order.length - 1 ? 'default' : 'pointer',
                  padding: '2px 6px',
                  fontFamily: 'inherit',
                }}
              >
                ▼
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
