import { TaskCheck } from '../atoms/index.ts';
import { toggleDone } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface HeaderDoneProps {
  ctx: DetailCtx;
  n: ModelNode;
}

/**
 * v4 `headerDone(n)` (~521) — the check-off control in the detail header.
 *
 * TASK ONLY. Every other level returns null, which is why the header's flex row can hold a
 * `null` in that slot without collapsing. `done` is the same two-part read as everywhere else
 * in this app: the `done` flag OR `status === 'Done'`, because a task can arrive from the
 * backend with the status set and the flag unwritten.
 *
 * The 23px size is v4's, and it is NOT `TaskCheck`'s default (19) — the detail header wants a
 * bigger target than a list row. `TaskCheck` forks its border weight at >=17, so 23 lands in
 * the same 2px-border branch as the row checkbox and only the box grows.
 */
export function HeaderDone({ ctx, n }: HeaderDoneProps) {
  if (n.level !== 'TASK') return null;
  const { T, graph, apply } = ctx;
  const C = T.c;
  const done = !!n.vals.done || n.vals.status === 'Done';

  return (
    <button
      onClick={() => apply(toggleDone(graph, n.id))}
      aria-label={done ? 'reopen' : 'mark done'}
      title={done ? 'Done — tap to reopen' : 'Mark done'}
      style={{
        flex: '0 0 auto',
        width: '26px',
        height: '26px',
        border: 'none',
        background: 'none',
        cursor: 'pointer',
        padding: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <TaskCheck T={T} done={done} col={C.green} size={23} />
    </button>
  );
}
