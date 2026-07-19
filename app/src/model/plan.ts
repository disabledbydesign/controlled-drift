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

/**
 * The plan's age, in plain relative words — so a plan left over from yesterday (a failed
 * morning generation) never reads as today's.
 *
 * ⚠ RESTORED, not invented. This is a transcription of `renderPlanAge()` in
 * `docs/overlay_daily.html` (~2409) — the surface June used for months and tuned to herself.
 * The branch structure, the part-of-day thresholds, the calendar-day arithmetic and the exact
 * sentences are hers. What changed in the port: it returns a string instead of writing to a DOM
 * node, and `now` is a parameter so the behaviour is testable without faking the clock.
 *
 * WHY IT CAME BACK. `adapt.ts` blanked this field with the note "Spec §14 removed the plan-age
 * line" — so she saw a date she read as today's, with no cue the plan was stale. The spec line
 * is not authority over the function: the whole system exists so her commitments live outside
 * her head, and a plan that presents yesterday as today is the system lying about exactly that.
 *
 * ⚠ Called at RENDER time, not at adapt time, and that is load-bearing. If the age were baked
 * in when the payload was fetched, a surface left open across midnight would keep insisting the
 * plan was built "this morning". `Plan.generated` therefore carries the raw ISO timestamp, and
 * this function is what turns it into words.
 *
 * Returns '' when there is nothing true to say — no timestamp, or one that will not parse.
 * The caller renders nothing at all rather than a placeholder; that is the same defect class
 * this function exists to remove.
 *
 * Dim by design at the call site: an honest fact, not an alert.
 */
export function planAgeText(iso: string | undefined | null, now: Date = new Date()): string {
  const built = iso ? new Date(iso) : null;
  if (!built || Number.isNaN(built.getTime())) return '';

  // Calendar days apart, NOT elapsed hours. What she needs to know is "is this today's plan" —
  // a plan built at 11pm is yesterday's at 1am even though it is two hours old.
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dayDiff = Math.round(
    (startOfDay(now).getTime() - startOfDay(built).getTime()) / 86400000,
  );

  // The part of day is read off the BUILD hour, never the current one.
  const h = built.getHours();
  const partOfDay = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening';
  const time = built.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  let text: string;
  let stale: boolean;
  if (dayDiff <= 0) {
    text = `built this ${partOfDay} at ${time}`;
    stale = false;
  } else if (dayDiff === 1) {
    // The morning-generation-failed case — the reason the line exists at all.
    text = `built yesterday ${partOfDay} at ${time}`;
    stale = true;
  } else {
    // Older still — an unambiguous date, not a weekday name that collides with this week's.
    const dateStr = built.toLocaleDateString([], { month: 'short', day: 'numeric' });
    text = `built ${dateStr} at ${time}`;
    stale = true;
  }
  // Names the control that fixes it, by its own on-screen label ('↻ Fresh plan').
  if (stale) text += ' — tap Fresh plan for today’s';
  return text;
}

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
 * A work item together with the address at which it actually sits in the plan.
 *
 * `item` is typed `PlanWorkItem`, not `PlanItem`: breaks are filtered out below, so a consumer
 * would otherwise have to narrow away a case that cannot occur.
 */
export interface AddressedItem {
  item: PlanWorkItem;
  bandIndex: number;
  itemIndex: number;
}

/**
 * `workItems`, but each item keeps the address `toggleArcStep` needs.
 *
 * `toggleArcStep(plan, bandIndex, itemIndex, stepIndex)` resolves a step as
 * `plan.blocks[bandIndex].items[itemIndex].arc[stepIndex]`, and answers a miss with a SILENT
 * no-op — `{plan, toast: null}`, no error, no toast, no visual change. So a wrong address does
 * not crash and does not warn; it produces a checkbox that is tapped and does nothing, forever.
 *
 * Two independent things make a naively-derived index wrong, which is why the address has to
 * travel with the item rather than being recomputed at the call site:
 *
 * 1. The list a consumer renders can be reordered by the user (`priOrder`), so a row's position
 *    on screen is not its position in the plan.
 * 2. `adapt.ts` PREPENDS appointments into `blocks[0].items`, so an item's index in the wire
 *    payload is not its index in `plan.blocks[0].items` either.
 *
 * ⚠ `itemIndex` is the index WITHIN its band — never a running counter across the whole plan.
 * On any plan with more than one band a running counter addresses the wrong item, or none.
 */
export function addressedWorkItems(plan: Plan): AddressedItem[] {
  const out: AddressedItem[] = [];
  plan.blocks.forEach((b, bandIndex) => {
    b.items.forEach((item, itemIndex) => {
      if (item.kind !== 'break') out.push({ item, bandIndex, itemIndex });
    });
  });
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
 * One arc step, named two ways at once: WHERE it sits and WHAT it is.
 *
 * The address (`bandIndex`/`itemIndex`/`stepIndex`) is what `toggleArcStep` needs to redraw the
 * plan. The `id` is the step's real Anytype task id, and it is what the SERVER needs — the two
 * are not interchangeable, and a slot address is only valid for the plan generation it was read
 * from. Carrying both together is what keeps a write keyed by id while the redraw stays keyed
 * by position. See `completeArcStep` in `shell/useAppState.ts`.
 */
export interface ArcStepRef {
  /** The step's own Anytype task id. Empty when the plan row carries none. */
  id: string;
  bandIndex: number;
  itemIndex: number;
  stepIndex: number;
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
