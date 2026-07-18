/**
 * Field semantics. Ported from design/mockups/review-reorganize-mobile-v4.html:
 *   effective()              ~486
 *   hasSchedulableAncestor() ~485
 *   isInactive()             ~311
 *   statusColor()            ~318
 *   sideColor()              ~319
 *   chipsFor()               ~320
 *   typeOptions()            ~291
 *
 * All pure. Colours arrive as a parameter, never an import — there are two
 * themes and the model layer must not know which one is live.
 */

import type { NodeVals } from '../fixtures/index.ts';
import type { Chip, EffectiveValue, GraphIndex, ModelColors, ModelNode } from './types.ts';

/**
 * v4 reads `vals` slots straight into string positions and relies on `||`.
 * `sv` reproduces `x || ''` exactly: 0, false, '' and undefined all collapse to
 * '' (so the "set …" fallbacks fire on the same inputs), everything else
 * stringifies. Needed only because TS types `vals` as an open bag.
 */
function sv(x: NodeVals[string]): string {
  return x ? String(x) : '';
}

// ── inheritance ─────────────────────────────────────────────────────────────

/**
 * v4:
 *   effective(n,vk){ let p=n.parent;
 *     while(p){ if(Object.prototype.hasOwnProperty.call(p.vals,vk)
 *                  && p.vals[vk]!==undefined) return {val:p.vals[vk],from:p.title};
 *               p=p.parent; }
 *     return {val:'',from:null}; }
 *
 * Two things that look like details and are not:
 *
 * 1. It starts at `n.parent`, NOT at `n`. This function answers "what would I
 *    inherit", never "what is my value". The caller decides which applies —
 *    `inheritRow` (~488) does `inheriting = !hasOwnProperty(n.vals, vk)`.
 *
 * 2. The stop condition is `hasOwnProperty`, not truthiness. That is the
 *    tri-state of backend spec §4: a key PRESENT but empty is an intentional
 *    "none" and STOPS the walk, returning `{val:'', from:<that ancestor>}` —
 *    which is a different answer from "nothing inherited", `{val:'', from:null}`.
 *    v4 implements the tri-state correctly; this is a faithful port, not a fix.
 *
 * The `!==undefined` conjunct is v4's own and is kept: a key explicitly set to
 * `undefined` is skipped and the walk continues past it, unlike a key set to ''.
 */
export function effective(idx: GraphIndex, n: ModelNode, vk: string): EffectiveValue {
  let p = idx.parentOf.get(n.id) ?? null;
  while (p) {
    if (Object.prototype.hasOwnProperty.call(p.vals, vk) && p.vals[vk] !== undefined) {
      return { val: p.vals[vk] as EffectiveValue['val'], from: p.title };
    }
    p = idx.parentOf.get(p.id) ?? null;
  }
  return { val: '', from: null };
}

/**
 * v4:329 —
 *   sideOf(n){ let x=n; while(x){ if(x.vals&&x.vals.side)return x.vals.side; x=x.parent; } return null; }
 *
 * Which life-area a node belongs to, inheriting from the nearest ancestor that names one.
 * Half of `subtreeVis` (v4:330): the Side filter passes when `sideOf(n) === st.sideFilter`.
 *
 * ⚠ THIS IS NOT THE SAME INHERITANCE RULE AS `effective()` ABOVE, and the difference is v4's,
 * not an accident of the port:
 *
 *   · `sideOf` starts at **n itself** and stops on **truthiness** — an own empty `side`
 *     keeps walking up.
 *   · `effective` starts at **n.parent** and stops on **hasOwnProperty** — a present-but-empty
 *     ancestor value stops the walk and means an intentional "none" (backend spec §4 tri-state).
 *
 * They answer different questions ("what side am I in" vs. "what would I inherit if I had no
 * value"), so they are deliberately NOT harmonised. Ported exactly as v4 has it.
 *
 * Lives in the model layer rather than beside `subtreeVis` in the screens because it needs the
 * derived index to walk ancestry — v4 could read `x.parent` off the node, this port cannot
 * (see `ModelNode` in types.ts for why the back-pointer is not reproduced).
 */
export function sideOf(idx: GraphIndex, n: ModelNode): string | null {
  let x: ModelNode | null = n;
  while (x) {
    if (x.vals && x.vals.side) return String(x.vals.side);
    x = idx.parentOf.get(x.id) ?? null;
  }
  return null;
}

/** True when this node has its own value for `vk` — v4's `inheritRow` test. */
export function isOwnValue(n: ModelNode, vk: string): boolean {
  return Object.prototype.hasOwnProperty.call(n.vals, vk);
}

/**
 * v4:74 — `this.INHERIT = new Set(['access','blockMin','affective'])`
 *
 * WHICH FIELDS INHERIT AT ALL. This is the model-layer half of the inheritance gate, and it
 * pairs with `hasSchedulableAncestor` below. v4:572 uses them together:
 *
 *   if (this.INHERIT.has(vk) && this.hasSchedulableAncestor(n))
 *     return this.inheritRow(n, vk, label, hint, () => ctl);
 *
 * ⚠ Do NOT apply `effective()` to a field outside this set. Doing so renders an inheritance
 * display for a field that does not inherit — wrong, with no visual signal that it is wrong.
 * Added 2026-07-18 (review gate): it was missed on the first pass while its conjunct partner
 * was ported, leaving half the gate in this layer and half nowhere.
 */
export const INHERIT: ReadonlySet<string> = new Set(['access', 'blockMin', 'affective']);

/**
 * v4:
 *   hasSchedulableAncestor(n){ let p=n.parent;
 *     while(p){ if(['PROJECT','SUBPROJECT','WORKSTREAM'].includes(p.level))return true;
 *               p=p.parent; } return false; }
 */
export function hasSchedulableAncestor(idx: GraphIndex, n: ModelNode): boolean {
  let p = idx.parentOf.get(n.id) ?? null;
  while (p) {
    if (p.level === 'PROJECT' || p.level === 'SUBPROJECT' || p.level === 'WORKSTREAM') return true;
    p = idx.parentOf.get(p.id) ?? null;
  }
  return false;
}

// ── activity ────────────────────────────────────────────────────────────────

/**
 * v4 ~311. Level-aware "is this thing done/off". Drives `hideInactive`.
 * The default branch covers PROJECT / SUBPROJECT / WORKSTREAM and anything else.
 */
export function isInactive(n: ModelNode): boolean {
  const v: NodeVals = n.vals || {};
  const status = v.status as unknown;
  switch (n.level) {
    case 'GOAL':
      return status === 'Parked' || status === 'Achieved';
    case 'TASK':
      return !!v.done || status === 'Done' || status === 'Parked';
    case 'RECURRING':
      return !!v.paused;
    case 'STRATEGY':
      return status === 'Retired';
    default:
      return v.engagement === 'Done' || status === 'Parked' || status === 'Inactive';
  }
}

// ── colours ─────────────────────────────────────────────────────────────────

/**
 * v4 ~318. One flat map across engagement values, statuses and goal statuses —
 * they share a namespace deliberately (Active/Ready both read as "going").
 * Unknown or unset falls to `dimmer`.
 */
export function statusColor(v: string | undefined, C: ModelColors): string {
  const map: Record<string, string> = {
    Steady: C.green,
    Open: C.blue,
    Sprint: C.amber,
    Hyperfixation: C.orange,
    Backburner: C.dimmer,
    Active: C.green,
    Ready: C.green,
    Parked: C.dimmer,
    Inactive: C.dimmer,
    Achieved: C.dimmer,
    Retired: C.dimmer,
    'Needs Clarifying': C.amber,
    Blocked: C.red,
    'In Design': C.purple,
    Done: C.dimmer,
  };
  return (v !== undefined ? map[v] : undefined) || C.dimmer;
}

/**
 * v4 ~319: `sideColor(v){ return this.C.side; }` with the comment
 *   "one uniform 'life-area' hue — never reuses a status color".
 *
 * SURPRISING, AND DELIBERATE: the argument is ignored. Every Side value gets
 * the same hue, precisely so Side can never be misread as a status. Ported
 * as-is, argument kept, because the call sites pass one and the semantics are
 * "the life-area colour of this value" even though today it is constant.
 */
export function sideColor(_v: string | undefined, C: ModelColors): string {
  return C.side;
}

// ── chips ───────────────────────────────────────────────────────────────────

/**
 * v4 ~320. The collapsed row's chip set, per level.
 *
 * Per the resolved §7 note in docs/api_contract_v2.md, this chip row is what
 * absorbs the old surface's "primary inline field".
 *
 * Note the asymmetry, which is v4's: only the GOAL / PROJECT / SUBPROJECT /
 * TASK chips carry `unset`. The RECURRING and STRATEGY chips never do — they
 * always have a displayable default ('every week', 'Active', 'when: Always'),
 * so there is no unset state to render.
 */
export function chipsFor(n: ModelNode, C: ModelColors): Chip[] {
  const v: NodeVals = n.vals || {};

  const eng = (): Chip => {
    const e = sv(v.engagement);
    return {
      text: e || 'set engagement',
      color: e ? statusColor(e, C) : C.dimmer,
      field: 'engagement',
      unset: !e,
    };
  };
  // v4 declares `stat(opts)` and never passes or reads `opts`. Dropped.
  const stat = (): Chip => {
    const s = sv(v.status);
    return {
      text: s || 'set status',
      color: s ? statusColor(s, C) : C.dimmer,
      field: 'status',
      unset: !s,
    };
  };

  if (n.level === 'GOAL') {
    const hz = sv(v.horizon);
    return [
      stat(),
      {
        text: hz || 'set horizon',
        color: hz ? C.horizon : C.dimmer,
        field: 'horizon',
        unset: !hz,
      },
    ];
  }

  if (n.level === 'RECURRING') {
    if (v.unit === 'as_needed') return [{ text: 'as needed', color: C.teal, field: 'unit' }];
    // v4: `const c=v.count||1, u=v.unit||'week'`
    const c = Number(v.count) || 1;
    const u = sv(v.unit) || 'week';
    return [
      {
        text: 'every ' + (c > 1 ? c + ' ' : '') + u + (c > 1 ? 's' : ''),
        color: C.orange,
        field: 'unit',
      },
    ];
  }

  if (n.level === 'TASK') return [stat()];

  if (n.level === 'STRATEGY') {
    return [
      {
        text: sv(v.status) || 'Active',
        color: isInactive(n) ? C.dimmer : C.strategy,
        field: 'status',
      },
      { text: 'when: ' + (sv(v.when) || 'Always'), color: C.dimmer, field: 'when' },
    ];
  }

  // PROJECT / SUBPROJECT / WORKSTREAM
  const o: Chip[] = [eng()];
  if (n.level === 'PROJECT' || n.level === 'SUBPROJECT') {
    const side = sv(v.side);
    o.push({
      // 'Fun / hobby' is abbreviated to 'hobby' for chip width; other values verbatim.
      text: side ? (side === 'Fun / hobby' ? 'hobby' : side) : 'set side',
      color: side ? sideColor(side, C) : C.dimmer,
      field: 'side',
      unset: !side,
    });
  }
  return o;
}

// ── type conversion options ─────────────────────────────────────────────────

/**
 * v4 ~291:
 *   typeOptions(n){ if(!['TASK','RECURRING','SUBPROJECT','WORKSTREAM','PROJECT']
 *       .includes(n.level))return null;
 *     return this.hasSchedulableAncestor(n)
 *       ? ['Task','Recurring','Subproject','Workstream']
 *       : ['Project','Workstream']; }
 *
 * null = this level cannot be converted at all (GOAL, STRATEGY).
 * Note `Project` is offered ONLY in the no-schedulable-ancestor branch, and
 * `Subproject` only in the other — the two lists are not supersets.
 */
export function typeOptions(idx: GraphIndex, n: ModelNode): string[] | null {
  if (!['TASK', 'RECURRING', 'SUBPROJECT', 'WORKSTREAM', 'PROJECT'].includes(n.level)) return null;
  return hasSchedulableAncestor(idx, n)
    ? ['Task', 'Recurring', 'Subproject', 'Workstream']
    : ['Project', 'Workstream'];
}

/** v4's `typeSection` current-label map (~292), lifted so callers share it. */
export const TYPE_LABEL_FOR_LEVEL: Record<string, string> = {
  TASK: 'Task',
  RECURRING: 'Recurring',
  SUBPROJECT: 'Subproject',
  WORKSTREAM: 'Workstream',
  PROJECT: 'Project',
};
