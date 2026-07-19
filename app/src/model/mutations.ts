/**
 * Mutations. Ported from design/mockups/review-reorganize-mobile-v4.html:
 *   setVal ~282 · toggleMulti ~283 · setTitle ~284 · del ~285 · move ~286
 *   setType ~287 · toggleDone ~297 · toggleActive ~298 · addChild ~299
 *   clearVal ~487
 *
 * ── THE MECHANISM CHANGE, STATED ONCE ───────────────────────────────────────
 * v4 mutates node objects in place and calls `bump()` to force a re-render;
 * `flash(msg)` shows a toast; `up(patch)` merges into the UI-state bag. None of
 * that survives immutable React state.
 *
 * Every function here is pure: `(graph, …) -> MutationResult`. The new graph
 * replaces `bump()`, the `toast` string replaces `flash()`, and the `ui` bag
 * carries `up()`'s patch verbatim for the component to apply. A no-op returns
 * the SAME graph reference and a null toast wherever v4 returned before
 * flashing — the early-return guards are the part most worth getting exact.
 *
 * The LOGIC is otherwise transcribed: same guards, same order, same keys
 * written, same keys left alone. Anywhere v4 looked surprising it is ported
 * anyway and flagged in a comment.
 *
 * Callers must rebuild the index (`index(result.graph)`) after every mutation.
 */

import type { NodeVals } from '../fixtures/index.ts';
import type { Graph, ModelNode, MutationResult } from './types.ts';
import { appendChild, index, isSelfOrDescendant, node, removeNode, updateNode } from './graph.ts';
import { isDone } from './plan.ts';

/** A mutation that did nothing: same graph, no toast, no UI patch. */
function noop(graph: Graph): MutationResult {
  return { graph, toast: null, ui: null, node: null };
}

// ── value writes ────────────────────────────────────────────────────────────

/**
 * v4:
 *   setVal(id,k,v){ const n=this.node(id); if(!n)return;
 *     n.vals={...n.vals,[k]:v}; this.bump(); this.flash('Saved'); }
 *
 * Note v4 already replaced the `vals` object rather than mutating it in place.
 */
export function setVal(
  graph: Graph,
  id: string,
  k: string,
  v: NodeVals[string],
): MutationResult {
  const res = updateNode(graph, id, (n) => ({ ...n, vals: { ...n.vals, [k]: v } }));
  if (!res.node) return noop(graph);
  return {
    graph: res.graph,
    toast: 'Saved',
    ui: null,
    node: res.node,
    write: { op: 'patchVals', id, vals: { [k]: v } },
  };
}

/**
 * v4:
 *   toggleMulti(id,k,opt){ const n=this.node(id);
 *     const cur=(n.vals[k]||'').split(',').map(s=>s.trim()).filter(Boolean);
 *     const i=cur.indexOf(opt); if(i<0)cur.push(opt); else cur.splice(i,1);
 *     n.vals={...n.vals,[k]:cur.join(', ')}; this.bump(); this.flash('Saved'); }
 *
 * SURPRISING (ported anyway): unlike every sibling mutation, this one has NO
 * `if(!n) return` guard — v4 throws on an unknown id. Reproducing a throw would
 * be a hostile port, so an unknown id no-ops here, consistent with the others.
 * That is the single behavioural difference and it only affects a code path
 * that was a crash.
 *
 * Storage format is a COMMA-JOINED STRING, joined with ', ' and split on ','.
 * That is the fixture's format and api_contract_v2 §2.2 keeps it at the seam.
 * The `String(...)` coercion below is the one concession to TypeScript: the
 * fixtures type multi fields as `string | string[]` because Anytype genuinely
 * returns arrays (contract appendix, "Fixture extraction notes" item 1). For a
 * string it is identical to v4; for an array it does the sane thing
 * (`['a','b'].toString() === 'a,b'`) where v4 would have thrown.
 */
export function toggleMulti(graph: Graph, id: string, k: string, opt: string): MutationResult {
  const res = updateNode(graph, id, (n) => {
    const raw = n.vals[k];
    const cur = String(raw || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const i = cur.indexOf(opt);
    if (i < 0) cur.push(opt);
    else cur.splice(i, 1);
    return { ...n, vals: { ...n.vals, [k]: cur.join(', ') } };
  });
  if (!res.node) return noop(graph);
  // The persisted value is the JOINED string the model just computed, not the option tapped —
  // a multi-select write replaces the whole set.
  return {
    graph: res.graph,
    toast: 'Saved',
    ui: null,
    node: res.node,
    write: { op: 'patchVals', id, vals: { [k]: res.node.vals[k] } },
  };
}

/**
 * v4:
 *   setTitle(id,t){ const n=this.node(id); if(n)n.title=t; this.bump(); }
 *
 * SURPRISING (ported): no toast. Every other write flashes 'Saved'; the title
 * does not — it fires per keystroke, so a toast would strobe. api_contract_v2
 * §4 notes this endpoint needs client-side debouncing for the same reason.
 */
export function setTitle(graph: Graph, id: string, t: string): MutationResult {
  const res = updateNode(graph, id, (n) => ({ ...n, title: t }));
  if (!res.node) return noop(graph);
  return {
    graph: res.graph,
    toast: null,
    ui: null,
    node: res.node,
    write: { op: 'patchTitle', id, title: t },
  };
}

/**
 * v4:
 *   clearVal(id,k){ const n=this.node(id); if(!n)return;
 *     const v={...n.vals}; delete v[k]; n.vals=v;
 *     this.bump(); this.flash('Inheriting'); }
 *
 * DELETES the key rather than setting it empty. That distinction is the whole
 * tri-state of backend spec §4 — absent means inherit, present-and-empty means
 * an intentional "none". Setting '' here would silently break inheritance.
 */
export function clearVal(graph: Graph, id: string, k: string): MutationResult {
  const res = updateNode(graph, id, (n) => {
    const v = { ...n.vals };
    delete v[k];
    return { ...n, vals: v };
  });
  if (!res.node) return noop(graph);
  // WIRED 2026-07-18. `POST /api/object/{id}/clear-field` (contract §1 NEW) is now built —
  // `api_write.clear_field`. It REMOVES the property rather than setting it empty, which is the
  // whole tri-state of spec §4: a property removed inherits again, a property set to '' is an
  // intentional "none". This previously reported `unsupported` because whether Anytype could
  // remove a property value was unverified; it has since been verified live, and the answer is
  // format-dependent — the server refuses (400, a sentence) for a format with no removal path,
  // so an unclearable field still fails honestly rather than silently.
  return {
    graph: res.graph,
    toast: 'Inheriting',
    ui: null,
    node: res.node,
    write: { op: 'clearField', id, field: k },
  };
}

// ── structural ──────────────────────────────────────────────────────────────

/**
 * v4:
 *   del(id){ this.removeNode(id);
 *     this.up({detail:null,moveFor:null,menuFor:null,chipEdit:null});
 *     this.flash('Deleted · synced'); this.bump(); }
 *
 * SURPRISING (ported): it flashes and clears the detail pane unconditionally,
 * even when `removeNode` found nothing. The UI patch is what closes the pane of
 * the thing just deleted, so it must fire regardless.
 *
 * Deleting removes the whole subtree — children go with the parent, they are
 * not re-parented. That is v4's array splice, preserved.
 */
export function del(graph: Graph, id: string): MutationResult {
  const res = removeNode(graph, id);
  return {
    graph: res.graph,
    toast: 'Deleted · synced',
    ui: { detail: null, moveFor: null, menuFor: null, chipEdit: null },
    node: res.removed,
    // Archive, not hard delete — recoverable in Anytype's bin (`api_write.delete_object`).
    ...(res.removed ? { write: { op: 'archive' as const, id } } : null),
  };
}

/**
 * v4:
 *   move(id,toId){ const n=this.node(id),to=this.node(toId); if(!n||!to)return;
 *     this.removeNode(id); n.parent=to; to.children.push(n);
 *     this.up({moveFor:null,menuFor:null,pickerFilter:''});
 *     this.flash('Moved · synced'); this.bump(); }
 *
 * The moved node keeps its subtree, its level and every value — only its parent
 * changes. It is appended LAST among the target's children.
 *
 * ⚠ DELIBERATE DIVERGENCE, the only one in this file. v4 has NO guard against
 * moving a node into its own descendant. In v4 that produced a subtree detached
 * from the root but still cyclically linked — the node vanishes from the tree
 * while `pathTo` loops forever. It is a latent bug, not a feature; there is no
 * UI affordance that intends it: v4 guards it at the CALL SITE instead, in
 * `pickerPage` (v4:605), which builds an `exclude` set by walking the moved
 * node's subtree and skips those ids when building the destination list. So the
 * cycle is unreachable from v4's UI, and this guard is defence-in-depth.
 *
 * ⚠ TASK 6 REQUIREMENT: if the `pickerPage` port drops that `exclude` set, this
 * guard becomes REACHABLE — and it is a silent dead end, since it returns no
 * toast and no `ui` patch, so `moveFor` never clears and the picker just sits
 * there with no feedback. Keep the exclusion.
 *
 * (Corrected 2026-07-18 (review gate): this comment previously cited a function
 * `filterMoveTree`, which does not exist anywhere in v4 — a fabricated symbol in
 * a load-bearing comment. It also claimed the cycle "cannot be reproduced
 * immutably", which is false; it can, by appending into the detached subtree.
 * The conclusion was right, the reasoning was not.)
 *
 * The index is derived from `graph` internally rather than taken as a parameter:
 * this was the ONE mutation accepting both, so a caller passing a stale index
 * would have evaluated the cycle guard against stale ancestry while splicing the
 * fresh graph — wrong, and silent. Deriving it removes that class entirely and
 * makes the mutation API uniform.
 */
export function move(graph: Graph, id: string, toId: string): MutationResult {
  const idx = index(graph);
  const n = node(idx, id);
  const to = node(idx, toId);
  if (!n || !to) return noop(graph);
  if (isSelfOrDescendant(idx, id, toId)) return noop(graph); // see ⚠ above

  const removed = removeNode(graph, id);
  if (!removed.removed) return noop(graph);
  const inserted = appendChild(removed.graph, toId, removed.removed);
  if (!inserted.ok) return noop(graph);

  return {
    graph: inserted.graph,
    toast: 'Moved · synced',
    ui: { moveFor: null, menuFor: null, pickerFilter: '' },
    node: removed.removed,
    write: { op: 'move', id, parentId: toId },
  };
}

/**
 * v4:
 *   setType(id,target){ const n=this.node(id); if(!n)return;
 *     if((target==='Task'||target==='Recurring')&&n.children.length){
 *       this.flash('Can’t convert — has sub-items, move them first'); return; }
 *     if(target==='Task'){n.type='Task';n.level='TASK';}
 *     else if(target==='Recurring'){n.type='Recurring';n.level='RECURRING';}
 *     else if(target==='Subproject'){n.type='Project';n.level='SUBPROJECT';}
 *     else if(target==='Workstream'){n.type='Project';n.level='WORKSTREAM';}
 *     else if(target==='Project'){n.type='Project';n.level='PROJECT';}
 *     this.bump(); this.flash('Type → '+target+' · fields kept'); }
 *
 * Two things preserved exactly:
 *   - The leaf guard flashes and changes NOTHING. Backend spec §5 wants the
 *     same guard server-side; a client check is an affordance, not a constraint.
 *   - `vals` is untouched by every branch. "fields kept" is literal — a Task
 *     converted to a Project keeps its `due`, `duration`, everything. Nothing
 *     is pruned to fit the new level's control set.
 *
 * SURPRISING (ported): an unrecognised `target` falls through every branch,
 * changes nothing, and STILL flashes 'Type → X · fields kept'. A lie, but the
 * type buttons only ever pass the five known values, so it is unreachable from
 * the UI. Left as-is rather than adding a sixth condition.
 *
 * The apostrophe in the toast is v4's typographic ’ (U+2019), not '. Kept —
 * the toast strings are user-visible text she tuned.
 */
export function setType(graph: Graph, id: string, target: string): MutationResult {
  const n = nodeInGraph(graph, id);
  if (!n) return noop(graph);
  if ((target === 'Task' || target === 'Recurring') && n.children.length) {
    return {
      graph,
      toast: 'Can’t convert — has sub-items, move them first',
      ui: null,
      node: null,
    };
  }

  const res = updateNode(graph, id, (cur) => {
    if (target === 'Task') return { ...cur, type: 'Task' as const, level: 'TASK' as const };
    if (target === 'Recurring')
      return { ...cur, type: 'Recurring' as const, level: 'RECURRING' as const };
    if (target === 'Subproject')
      return { ...cur, type: 'Project' as const, level: 'SUBPROJECT' as const };
    if (target === 'Workstream')
      return { ...cur, type: 'Project' as const, level: 'WORKSTREAM' as const };
    if (target === 'Project')
      return { ...cur, type: 'Project' as const, level: 'PROJECT' as const };
    return cur; // unrecognised target — see SURPRISING note above
  });

  return {
    graph: res.graph,
    toast: 'Type → ' + target + ' · fields kept',
    ui: null,
    node: res.node,
    // ⚠ NO ENDPOINT. `POST /api/object/{id}/type` is contract §1 NEW and gated on §6 Q2 (does
    // Anytype support an in-place type change, or is it create-copy-relink-delete?).
    // `api_write.py`'s own docstring records the conversion seam as deliberately not built.
    write: { op: 'unsupported', id, what: 'change the type' },
  };
}

// ── toggles ─────────────────────────────────────────────────────────────────

/**
 * v4:
 *   toggleDone(n){ const nv=!n.vals.done; const patch={done:nv};
 *     if(n.level==='TASK')patch.status=nv?'Done'
 *       :(n.vals.status==='Done'?'Ready':(n.vals.status||'Ready'));
 *     n.vals={...n.vals,...patch};
 *     this.flash(nv?'Done · synced':'Reopened'); this.bump(); }
 *
 * The reopen branch is careful and worth not flattening: un-done-ing a task
 * whose status is 'Done' returns it to 'Ready', but a task that was 'Blocked'
 * or 'In Design' when checked off gets its OWN status back, not 'Ready'.
 * Only a task with no status at all defaults to 'Ready'.
 *
 * Non-TASK levels get `done` flipped and NO status write. v4 takes a node, not
 * an id; taking an id here keeps the mutation API uniform.
 */
/**
 * @param currentDone What the SCREEN currently shows. Pass it for any row that came from the
 *   plan — a RECURRING's done-for-today lives in `completion_log`, reaches the client only on
 *   the plan payload, and is invisible to the graph. Omitted, the node answers.
 */
export function toggleDone(graph: Graph, id: string, currentDone?: boolean): MutationResult {
  const n = nodeInGraph(graph, id);
  if (!n) return noop(graph);
  // ⚠ Was `!n.vals.done`, which read a DIFFERENT rule than the one the screen renders by.
  // `isDone` also accepts `status === 'Done'`, so June's "Go to the grocery store" — `done:false`
  // with `status:'Done'` — rendered as checked while this computed `!false` and asked the server
  // to complete it a second time. The box was checked and could not be unchecked.
  // Read and write must share one predicate; `isDone` is it.
  const nv = !(typeof currentDone === 'boolean' ? currentDone : isDone(n));

  const res = updateNode(graph, id, (cur) => {
    const patch: NodeVals = { done: nv };
    if (cur.level === 'TASK') {
      patch['status'] = nv
        ? 'Done'
        : cur.vals.status === 'Done'
          ? 'Ready'
          : (cur.vals.status as string) || 'Ready';
    }
    return { ...cur, vals: { ...cur.vals, ...patch } };
  });

  return {
    graph: res.graph,
    toast: nv ? 'Done · synced' : 'Reopened',
    ui: null,
    node: res.node,
    write: { op: 'complete', id, done: nv },
  };
}

/**
 * v4:
 *   toggleActive(n){ n.vals={...n.vals,paused:!n.vals.paused};
 *     this.flash(n.vals.paused?'Paused — out of plan':'Active — in plan');
 *     this.bump(); }
 *
 * The UI stores `paused`; the backend endpoint takes `active` — the INVERSE.
 * api_contract_v2 Q3 flags this and recommends the frontend invert at the seam.
 * The model keeps `paused` because that is what the fixtures carry.
 */
export function toggleActive(graph: Graph, id: string): MutationResult {
  const n = nodeInGraph(graph, id);
  if (!n) return noop(graph);
  const nv = !n.vals.paused;
  const res = updateNode(graph, id, (cur) => ({
    ...cur,
    vals: { ...cur.vals, paused: nv },
  }));
  return {
    graph: res.graph,
    toast: nv ? 'Paused — out of plan' : 'Active — in plan',
    ui: null,
    node: res.node,
    // The seam where the polarity flips — contract §6 Q3. The UI stores `paused`; the endpoint
    // takes `active`. Inverted HERE, once, rather than at the call sites.
    write: { op: 'recurringActive', id, active: !nv },
  };
}

// ── creation ────────────────────────────────────────────────────────────────

/** v4: `const id='new'+Math.random().toString(36).slice(2,7);` */
export function defaultNewId(): string {
  return 'new' + Math.random().toString(36).slice(2, 7);
}

/**
 * v4:
 *   addChild(parentId,type){ const p=parentId?this.node(parentId):null;
 *     const lvl = type==='Goal'?'GOAL' : type==='Strategy'?'STRATEGY'
 *               : type==='Task'?'TASK' : type==='Recurring'?'RECURRING'
 *               : (!p||p.level==='GOAL' ? 'PROJECT'
 *                  : (p.level==='WORKSTREAM' ? 'WORKSTREAM' : 'SUBPROJECT'));
 *     const id='new'+Math.random().toString(36).slice(2,7);
 *     const n={id,level:lvl,type,title:'',vals:{},children:[],parent:p||null,_new:true};
 *     (lvl==='STRATEGY'?this.strategies:(p?p.children:this.data)).push(n);
 *     this.byId[id]=n;
 *     this.up({detail:id,addOpen:false,addParentFor:null,pickerFilter:''});
 *     this.flash('Created · editing'); this.bump(); }
 *
 * The level rule, spelled out: the requested TYPE decides the level outright
 * for Goal / Strategy / Task / Recurring. Only 'Project' consults the parent —
 * under a Goal or at the root it is a PROJECT, under a WORKSTREAM it is another
 * WORKSTREAM, under anything else a SUBPROJECT.
 *
 * SURPRISING (ported): a Strategy created with a `parentId` is placed in the
 * flat strategies list, not under that parent — the `lvl==='STRATEGY'` test
 * wins over `p`. Strategy is global and non-hierarchical, so this is right,
 * but it means `parentId` is silently ignored for that one type.
 *
 * `_new:true` marks a node that `maybeDiscardBlank` (~307) removes again if the
 * pane closes with no title and no values. That cleanup is UI-driven and lives
 * with the component, not here.
 *
 * The id generator is injectable ONLY so tests are deterministic; production
 * callers pass nothing and get v4's `Math.random` id.
 */
export function addChild(
  graph: Graph,
  parentId: string | null,
  type: ModelNode['type'],
  newId: () => string = defaultNewId,
): MutationResult {
  const p = parentId ? nodeInGraph(graph, parentId) : null;

  const lvl: ModelNode['level'] =
    type === 'Goal'
      ? 'GOAL'
      : type === 'Strategy'
        ? 'STRATEGY'
        : type === 'Task'
          ? 'TASK'
          : type === 'Recurring'
            ? 'RECURRING'
            : !p || p.level === 'GOAL'
              ? 'PROJECT'
              : p.level === 'WORKSTREAM'
                ? 'WORKSTREAM'
                : 'SUBPROJECT';

  const id = newId();
  const n: ModelNode = { id, level: lvl, type, title: '', vals: {}, children: [], _new: true };

  // v4: `(lvl==='STRATEGY' ? this.strategies : (p ? p.children : this.data)).push(n)`
  const target = lvl === 'STRATEGY' ? null : p ? p.id : null;
  const inserted = appendChild(graph, target, n);

  return {
    graph: inserted.graph,
    toast: 'Created · editing',
    ui: { detail: id, addOpen: false, addParentFor: null, pickerFilter: '' },
    node: n,
    // ⚠ `api_write.create_child` REFUSES an empty title (400) — an empty name matches every
    // other empty-named object under `gsdo_objects.create`'s dedup-by-name, which is the
    // BUILD_DOC §6 hazard at its worst. v4 creates with `title:''` and fills it in afterwards,
    // so the placeholder below is what makes that flow legal. `api_write.py` flags this exact
    // mismatch in its own docstring rather than papering over it.
    write: {
      op: 'create',
      tempId: id,
      level: lvl,
      title: 'Untitled ' + type.toLowerCase(),
      parentId: lvl === 'STRATEGY' ? null : (p?.id ?? null),
    },
  };
}

/** v4 capture(): `const id='cap'+Math.random().toString(36).slice(2,6);` */
export function defaultCaptureId(): string {
  return 'cap' + Math.random().toString(36).slice(2, 6);
}

/**
 * v4 `capture()` (1136):
 *   capture(){ const t=(this.st.addText||'').trim(); if(!t)return; const p=this.node('vyzxdu');
 *     const id='cap'+Math.random().toString(36).slice(2,6);
 *     const n={id,level:'TASK',type:'Task',title:t,vals:{status:'Ready'},children:[],parent:p,_new:true};
 *     p.children.push(n); this.byId[id]=n;
 *     this.receipt=[{id,text:t,project:p.title},...this.receipt];
 *     this.up({addText:''}); this.flash('Sorted into '+p.title); this.bump(); }
 *
 * ⚠ FLAGGED, PORTED AS-IS: the destination project id `'vyzxdu'` ("Build Controlled Drift")
 * is HARDCODED in v4. The Add tab's own copy says "It sorts what you write into the right
 * places" — in the mockup nothing sorts, every captured line lands in the same project. The
 * real sorter is the backend's capture path (out of scope for Track A, which makes no network
 * calls), so the constant is transcribed rather than invented around. `projectId` is a
 * parameter so the seam has somewhere to attach without a rewrite.
 *
 * ⚠ ALSO FLAGGED: v4 does not parse the text at all. `capture()` splits nothing, extracts no
 * dates, reads no tags — the whole trimmed string becomes one task title, and `vals` gets
 * exactly `{status:'Ready'}`. The placeholder ("call the surgeon's office, AND I keep meaning
 * to meditate daily…") shows two items in one line, so the mockup's copy promises a split the
 * mockup does not perform. Not fixed here.
 *
 * Deviation from v4, and the only one: an unknown/missing destination project no-ops instead
 * of throwing on `p.children` of `undefined`. Same call made for `toggleMulti` above.
 */
export const CAPTURE_PROJECT_ID = 'vyzxdu';

export function capture(
  graph: Graph,
  text: string,
  projectId: string = CAPTURE_PROJECT_ID,
  newId: () => string = defaultCaptureId,
): MutationResult {
  const t = text.trim();
  if (!t) return noop(graph);

  const p = nodeInGraph(graph, projectId);
  if (!p) return noop(graph);

  const id = newId();
  const n: ModelNode = {
    id,
    level: 'TASK',
    type: 'Task',
    title: t,
    vals: { status: 'Ready' },
    children: [],
    _new: true,
  };

  const inserted = appendChild(graph, p.id, n);
  return {
    graph: inserted.graph,
    toast: 'Sorted into ' + p.title,
    // v4's `up({addText:''})`. The receipt is NOT here: v4 keeps it on the instance
    // (`this.receipt`), and the caller composes it from `node` + the destination title.
    ui: { addText: '' },
    node: n,
    // Creates a plain Task under the destination project. NOTE this is v4's local `capture()`,
    // which does no weeding — the real sorter is `POST /api/capture`, an async LLM path that
    // creates objects of its own. Wiring THAT is a separate decision (it writes several objects
    // per call and has its own polling contract, §2.6), so this persists what v4 actually does.
    write: { op: 'create', tempId: id, level: 'TASK', title: t, parentId: p.id },
  };
}

// ── internal ────────────────────────────────────────────────────────────────

/**
 * Find a node without requiring the caller to hold an index. O(n) over a tree
 * of a few dozen nodes; the alternative is threading a possibly-stale index
 * through every mutation, which is the bug this layer exists to avoid.
 */
function nodeInGraph(graph: Graph, id: string): ModelNode | null {
  const find = (nodes: ModelNode[]): ModelNode | null => {
    for (const n of nodes) {
      if (n.id === id) return n;
      const hit = find(n.children);
      if (hit) return hit;
    }
    return null;
  };
  // Orphan buckets are searched too — a node in one is an ordinary node that happens to have no
  // parent, and every mutation must be able to reach it. See `OrphanBucket` in types.ts.
  const inBuckets = (graph.orphans ?? []).reduce<ModelNode | null>(
    (hit, b) => hit ?? find(b.nodes),
    null,
  );
  return find(graph.roots) ?? find(graph.strategies) ?? inBuckets;
}
