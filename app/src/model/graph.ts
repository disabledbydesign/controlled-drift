/**
 * Graph + indexing. Ported from design/mockups/review-reorganize-mobile-v4.html
 * `index()` ~277, `node()` ~278, `pathTo()` ~279, `removeNode()` ~280.
 *
 * v4 stores ancestry ON the nodes (`n.parent`) and identity in a mutable
 * `this.byId` object. Here both live in a derived `GraphIndex`, so nodes stay
 * acyclic and structurally shareable. See `types.ts` for why.
 */

import type { Graph, GraphIndex, ModelNode } from './types.ts';

// ── indexing ────────────────────────────────────────────────────────────────

/**
 * v4:
 *   index(nodes,parent){ for(const n of nodes){ n.parent=parent;
 *     this.byId[n.id]=n; this.index(n.children,n); } }
 * plus the constructor line 76, which indexes strategies separately with a null
 * parent — strategies are NOT walked by `index()` itself. Reproduced.
 */
export function index(graph: Graph): GraphIndex {
  const byId = new Map<string, ModelNode>();
  const parentOf = new Map<string, ModelNode | null>();

  const walk = (nodes: ModelNode[], parent: ModelNode | null): void => {
    for (const n of nodes) {
      parentOf.set(n.id, parent);
      byId.set(n.id, n);
      walk(n.children, n);
    }
  };

  walk(graph.roots, null);
  for (const s of graph.strategies) {
    parentOf.set(s.id, null);
    byId.set(s.id, s);
  }

  return { byId, parentOf };
}

/** v4: `node(id){ return this.byId[id]; }` — undefined when unknown. */
export function node(idx: GraphIndex, id: string): ModelNode | undefined {
  return idx.byId.get(id);
}

/** v4: `parent` back-pointer read. Null at a root, undefined if id is unknown. */
export function parentOf(idx: GraphIndex, id: string): ModelNode | null | undefined {
  return idx.parentOf.get(id);
}

/**
 * v4:
 *   pathTo(id){ const out=[]; let n=this.node(id);
 *     while(n){ out.unshift(n); n=n.parent; } return out; }
 *
 * Root-first, INCLUDING the node itself. Empty array for an unknown id.
 */
export function pathTo(idx: GraphIndex, id: string): ModelNode[] {
  const out: ModelNode[] = [];
  let cur = node(idx, id);
  while (cur) {
    out.unshift(cur);
    const p = idx.parentOf.get(cur.id);
    cur = p ?? undefined;
  }
  return out;
}

// ── structural helpers (the immutable equivalent of v4's splice/push) ────────

/**
 * Remove `id` from a forest, returning the rebuilt forest and the removed node.
 *
 * Only the ancestors of the removed node are rebuilt; every other subtree keeps
 * its identity, which is what makes React re-render cheap.
 */
function removeFromForest(
  nodes: ModelNode[],
  id: string,
): { nodes: ModelNode[]; removed: ModelNode | null } {
  const i = nodes.findIndex((n) => n.id === id);
  if (i >= 0) {
    const removed = nodes[i] as ModelNode;
    return { nodes: [...nodes.slice(0, i), ...nodes.slice(i + 1)], removed };
  }
  for (let j = 0; j < nodes.length; j++) {
    const n = nodes[j] as ModelNode;
    const res = removeFromForest(n.children, id);
    if (res.removed) {
      const rebuilt = [...nodes];
      rebuilt[j] = { ...n, children: res.nodes };
      return { nodes: rebuilt, removed: res.removed };
    }
  }
  return { nodes, removed: null };
}

/**
 * Replace `id` in a forest by applying `fn`. `fn` returning the same reference
 * leaves the forest reference untouched.
 */
function updateInForest(
  nodes: ModelNode[],
  id: string,
  fn: (n: ModelNode) => ModelNode,
): { nodes: ModelNode[]; node: ModelNode | null } {
  for (let j = 0; j < nodes.length; j++) {
    const n = nodes[j] as ModelNode;
    if (n.id === id) {
      const next = fn(n);
      if (next === n) return { nodes, node: n };
      const rebuilt = [...nodes];
      rebuilt[j] = next;
      return { nodes: rebuilt, node: next };
    }
    const res = updateInForest(n.children, id, fn);
    if (res.node) {
      if (res.nodes === n.children) return { nodes, node: res.node };
      const rebuilt = [...nodes];
      rebuilt[j] = { ...n, children: res.nodes };
      return { nodes: rebuilt, node: res.node };
    }
  }
  return { nodes, node: null };
}

/** Append `child` to `parentId`'s children. No-op if the parent is not found. */
function appendChildInForest(
  nodes: ModelNode[],
  parentId: string,
  child: ModelNode,
): { nodes: ModelNode[]; ok: boolean } {
  const res = updateInForest(nodes, parentId, (p) => ({
    ...p,
    children: [...p.children, child],
  }));
  return { nodes: res.nodes, ok: res.node !== null };
}

// ── graph-level operations ──────────────────────────────────────────────────

/**
 * v4:
 *   removeNode(id){ const n=this.node(id); if(!n)return;
 *     const arr = n.parent ? n.parent.children
 *               : (n.level==='STRATEGY' ? this.strategies : this.data);
 *     const i=arr.indexOf(n); if(i>=0)arr.splice(i,1); }
 *
 * Removing a node removes its whole subtree with it — the children hang off the
 * spliced-out object. Preserved: children are not re-parented or orphaned.
 *
 * Returns the SAME graph reference when `id` is unknown, matching v4's no-op.
 */
export function removeNode(graph: Graph, id: string): { graph: Graph; removed: ModelNode | null } {
  const fromRoots = removeFromForest(graph.roots, id);
  if (fromRoots.removed) {
    return { graph: { ...graph, roots: fromRoots.nodes }, removed: fromRoots.removed };
  }
  const fromStrategies = removeFromForest(graph.strategies, id);
  if (fromStrategies.removed) {
    return {
      graph: { ...graph, strategies: fromStrategies.nodes },
      removed: fromStrategies.removed,
    };
  }
  return { graph, removed: null };
}

/**
 * Apply `fn` to the node with `id`, in whichever forest it lives.
 * Same graph reference back when `id` is unknown or `fn` returns its argument.
 */
export function updateNode(
  graph: Graph,
  id: string,
  fn: (n: ModelNode) => ModelNode,
): { graph: Graph; node: ModelNode | null } {
  const inRoots = updateInForest(graph.roots, id, fn);
  if (inRoots.node) {
    if (inRoots.nodes === graph.roots) return { graph, node: inRoots.node };
    return { graph: { ...graph, roots: inRoots.nodes }, node: inRoots.node };
  }
  const inStrategies = updateInForest(graph.strategies, id, fn);
  if (inStrategies.node) {
    if (inStrategies.nodes === graph.strategies) return { graph, node: inStrategies.node };
    return { graph: { ...graph, strategies: inStrategies.nodes }, node: inStrategies.node };
  }
  return { graph, node: null };
}

/** Append a node under `parentId` (both forests searched), or at a forest root. */
export function appendChild(
  graph: Graph,
  parentId: string | null,
  child: ModelNode,
): { graph: Graph; ok: boolean } {
  if (parentId === null) {
    // v4: `(lvl==='STRATEGY' ? this.strategies : this.data).push(n)`
    if (child.level === 'STRATEGY') {
      return { graph: { ...graph, strategies: [...graph.strategies, child] }, ok: true };
    }
    return { graph: { ...graph, roots: [...graph.roots, child] }, ok: true };
  }
  const inRoots = appendChildInForest(graph.roots, parentId, child);
  if (inRoots.ok) return { graph: { ...graph, roots: inRoots.nodes }, ok: true };
  const inStrategies = appendChildInForest(graph.strategies, parentId, child);
  if (inStrategies.ok) {
    return { graph: { ...graph, strategies: inStrategies.nodes }, ok: true };
  }
  return { graph, ok: false };
}

/** True when `candidateId` is `rootId` itself or anywhere beneath it. */
export function isSelfOrDescendant(idx: GraphIndex, rootId: string, candidateId: string): boolean {
  let cur: ModelNode | null | undefined = node(idx, candidateId);
  while (cur) {
    if (cur.id === rootId) return true;
    cur = idx.parentOf.get(cur.id);
  }
  return false;
}
