/**
 * Pure helpers over the daily PLAN.
 *
 * The plan is not part of the object `Graph` — it is a separately-generated payload that
 * *references* graph nodes by id. So it needs its own mutation seam alongside `mutations.ts`:
 * checking off a task is a graph mutation (`toggleDone`), but advancing an arc step changes
 * the plan document itself and nothing in the graph.
 *
 * Same discipline as `mutations.ts`: state in, new state out. v4 mutated the arc step in place
 * (`s.state='done'`) and called `bump()` to force a re-render; that cannot work under React's
 * reference equality, so the equivalent here rebuilds the path down to the changed step and
 * shares every untouched subtree.
 */

import type { Plan, PlanArcStep, PlanBlockItem, PlanTaskItem } from '../fixtures/index.ts';
import type { GraphIndex, ModelNode } from './types.ts';
import { pathTo } from './graph.ts';

/** A non-break plan item — the two grains that carry a real node id. */
export type PlanWorkItem = PlanBlockItem | PlanTaskItem;

/** What a plan mutation returns. Mirrors `MutationResult`, minus the graph. */
export interface PlanResult {
  plan: Plan;
  toast: string | null;
}

/**
 * v4 `workItems()` (1023) — every item across every band that is not a break, flattened.
 *
 * This is what the Priority view ranks: it drops the clock bands entirely and drops the
 * `break` grain, which has no id and nothing to check off.
 */
export function workItems(plan: Plan): PlanWorkItem[] {
  const out: PlanWorkItem[] = [];
  for (const b of plan.blocks) {
    for (const it of b.items) {
      if (it.kind !== 'break') out.push(it);
    }
  }
  return out;
}

/**
 * v4 `nearestProject(n)` (1104):
 *   let p=n.parent; while(p){ if(['PROJECT','SUBPROJECT','WORKSTREAM'].includes(p.level))return p; p=p.parent; } return null;
 *
 * Starts at the PARENT, not the node — a project row in the plan does not label itself.
 * v4 walked `parent` back-pointers; ancestry lives in the derived index here instead
 * (see `model/types.ts` on why the back-pointer was not reproduced), so this reads
 * `pathTo` root-first and scans upward from just below the node.
 */
const PROJECT_LEVELS = new Set(['PROJECT', 'SUBPROJECT', 'WORKSTREAM']);

export function nearestProject(idx: GraphIndex, id: string): ModelNode | null {
  const path = pathTo(idx, id);
  // pathTo is root-first and INCLUDES the node itself; drop the node, then walk up.
  for (let i = path.length - 2; i >= 0; i--) {
    const p = path[i];
    if (p && PROJECT_LEVELS.has(p.level)) return p;
  }
  return null;
}

/** True when a node counts as done — v4's `!!n.vals.done||n.vals.status==='Done'` (1074). */
export function isDone(n: ModelNode | undefined): boolean {
  if (!n) return false;
  return !!n.vals['done'] || n.vals['status'] === 'Done';
}

/**
 * Done-state for a row that is IN today's plan. **Prefer this over `isDone` for plan rows.**
 *
 * A RECURRING's completion is per-DAY, so it cannot live on the object — it is written to
 * `completion_log` and comes back on the plan payload as `done`. The graph node carries
 * nothing. Reading the graph alone showed June three chores she had already finished today
 * ("Do the dishes", "Clean the kitchen", "Do laundry") as still outstanding, on a day framed
 * around very little capacity. The plan knew; nothing read it.
 *
 * `item.done` is authoritative WHEN PRESENT, including when it is explicitly `false` — an
 * item she reopened today must not be resurrected by an object whose `status` still says Done.
 * Absent, the graph answers, which is right for a plain Task.
 */
export function planItemDone(item: object | undefined, n: ModelNode | undefined): boolean {
  // A BLOCK item carries no `done` — its "did a chunk today" state is separate (see WorkBlock),
  // so it falls through to the graph rather than being forced into this field.
  const d = item && 'done' in item ? (item as { done?: unknown }).done : undefined;
  if (typeof d === 'boolean') return d;
  return isDone(n);
}

/**
 * v4 `arcStep`'s `toggle` (1099), extracted as a pure function.
 *
 * v4:
 *   if(done){ s.state='ahead'; }
 *   else { s.state='done'; if(here&&arc&&arc[i+1]&&arc[i+1].state==='ahead') arc[i+1].state='here'; }
 *
 * Spec §14 calls the second half out explicitly ("Arc 'here' advance"): checking off the
 * current step promotes the next `ahead` step to `here`. Reopening a step sends it to
 * `ahead` and does NOT demote anything — that asymmetry is v4's and is preserved.
 *
 * Addressing is by (band index, item index, step index) rather than by object identity,
 * because the caller is rebuilding an immutable tree and has no stable step reference.
 */
export function toggleArcStep(
  plan: Plan,
  bandIndex: number,
  itemIndex: number,
  stepIndex: number,
): PlanResult {
  const band = plan.blocks[bandIndex];
  const item = band?.items[itemIndex];
  if (!band || !item || item.kind !== 'block' || !item.arc) return { plan, toast: null };

  const step = item.arc[stepIndex];
  if (!step) return { plan, toast: null };

  const wasDone = step.state === 'done';
  const wasHere = step.state === 'here';

  const arc: PlanArcStep[] = item.arc.map((s, i) => {
    if (i === stepIndex) return { ...s, state: wasDone ? ('ahead' as const) : ('done' as const) };
    // The advance: only when the checked step was the current one, only for the step
    // immediately after it, and only if that step is still `ahead`.
    if (!wasDone && wasHere && i === stepIndex + 1 && s.state === 'ahead') {
      return { ...s, state: 'here' as const };
    }
    return s;
  });

  const items = band.items.map((it, i) => (i === itemIndex ? { ...item, arc } : it));
  const blocks = plan.blocks.map((b, i) => (i === bandIndex ? { ...band, items } : b));

  return { plan: { ...plan, blocks }, toast: wasDone ? 'Reopened' : 'Nice — one down' };
}
