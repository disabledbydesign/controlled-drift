import type { CSSProperties, DragEvent } from 'react';
import { Badge, Chip } from '../atoms/index.ts';
import { chipsFor, isSelfOrDescendant, move } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import { ChipStrip } from '../panels/ChipStrip.tsx';
import { Lead } from './Lead.tsx';
import { D } from './types.ts';
import type { RowCtx } from './types.ts';

/**
 * The id currently being dragged.
 *
 * v4 keeps this on the component instance (`this._dragMoveId`) precisely because it must NOT
 * trigger a re-render — it changes on `dragstart` and is read inside `dragover`, which fires
 * many times a second. A module-level holder reproduces that: v4 has exactly one component
 * instance, so one shared slot is the same scope, not a widening of it.
 *
 * Only `dragOverId` — the thing that must repaint — goes through UI state, as in v4.
 */
const drag: { id: string | null } = { id: null };

export interface RowOptions {
  /** Indentation level. v4: `paddingLeft = 8 + depth*16`. */
  depth?: number;
  expandable?: boolean;
  /** Chevron rotation. Meaningful only with `expandable`. */
  open?: boolean;
  onExpand?: (() => void) | undefined;
  onTap?: (() => void) | undefined;
  /** Suppress the type badge (Routines and Strategies already group by type). */
  hideBadge?: boolean;
  /** Chips render UNDER the title instead of right-aligned beside it. */
  chipsBelow?: boolean;
  /** Force the active/selected highlight (the desktop path selects without opening detail). */
  sel?: boolean;
  /** Suppress the trailing edit (pencil) button. */
  noMenu?: boolean;
  /** Enable drag-to-reparent on this row. */
  dnd?: boolean;
  /** Badge sits ABOVE the title rather than inline before it. */
  badgeAbove?: boolean;
  /**
   * ⚠ v4 DESTRUCTURES `flat` and `directEdit` in row()'s signature and then NEVER READS
   * EITHER in the body — verified by reading lines 436-462 whole. Two call sites pass
   * `flat:true` (672, 692) believing it does something. They are dead parameters in v4.
   * Ported as accepted-and-ignored so those call sites port across unchanged rather than
   * becoming type errors; flagged rather than silently dropped or silently implemented.
   */
  flat?: boolean;
  /** @see flat — dead in v4. */
  directEdit?: boolean;
}

export interface RowProps extends RowOptions {
  ctx: RowCtx;
  n: ModelNode;
}

/**
 * v4 `row(n, opts)` (~436) — the workhorse row.
 *
 * ONE component, FOUR screens: the Map tree, Routines, Strategies and the move/re-parent
 * picker all render through it. That is why the options bag is wide — each screen turns a
 * different subset on — and why a subtle error here propagates everywhere.
 *
 * ── what the row is made of, left to right ───────────────────────────────────
 *   `Lead`          chevron / checkbox / recurring switch / spacer
 *   the tap target  badge + title (+ chips underneath, when `chipsBelow`)
 *   chips           right-aligned column, ONLY when NOT `chipsBelow`
 *   edit button     pencil → opens the detail editor, unless `noMenu`
 *
 * ── DEPTH IS INDENTATION, NEVER HUE ──────────────────────────────────────────
 * `paddingLeft = 8 + depth*16` is the ONLY thing depth changes. It does not tint the row, the
 * title or the background. Gallery 4a L60 / 4c L110 show the same rule from the other side:
 * nested children carry status-glyph colour (green done, rose current, dim pending) and
 * nothing else. Object-TYPE colour appears only in the `Badge` (and `Rail`, elsewhere), and
 * comes from the gallery legend via `typeColor` — never v4's `TYPE` map, which coloured TASK
 * green and collided with the completion green used here for `done`.
 *
 * ── the title colour cascade (v4's, exactly) ─────────────────────────────────
 *   done or paused → `dimmer`   ·  brand-new node (`_new`) → `green`  ·  otherwise → `text`
 * with `line-through` on done only. GOAL is the only level with weight 700; everything else
 * is 500.
 *
 * ── what "active" means ──────────────────────────────────────────────────────
 * A row is highlighted when it is selected, has the detail editor open, has its menu open, OR
 * has a chip strip open on it. One rose left-edge inset plus a rose gradient wash. `dragOver`
 * outranks it: a row being dragged onto shows the blue dashed outline INSTEAD, and v4
 * suppresses the rose inset in that case (`active && !dragOver`) so the two never stack.
 *
 * ── the two strips underneath (Task 6) ───────────────────────────────────────
 * v4:460 renders `chipStrip(n,depth,chipsBelow)` beneath the line when this row has a chip
 * being edited. That is now mounted.
 *
 * ⚠ `menuStrip` (v4:477) is NOT ported. It is DEAD IN v4 — `menuStrip` appears exactly once
 * (its own definition) and all 18 `menuFor:` assignments in v4 are `null`, so the strip is
 * unreachable there. A first pass ported it and mounted it here on inferred placement; removed
 * for the same reason `typeSection` and `renderApp`/`header`/`tab` were, and because inferred
 * placement of unreachable code is worse than its absence. Its Move action is reachable anyway,
 * through the detail editor's location block. `ui.menuFor` and `row()`'s `active` test still
 * read it, faithfully, in the same
 * `ui.menuFor === n.id` — see its own header for why that placement is INFERRED rather than
 * transcribed, and why nothing in v4 or here currently sets `menuFor` to a non-null value.
 */
export function Row({
  ctx,
  n,
  depth = 0,
  expandable = false,
  open = false,
  onExpand,
  onTap,
  hideBadge = false,
  chipsBelow = false,
  sel = false,
  noMenu = false,
  dnd = false,
  badgeAbove = false,
}: RowProps) {
  const { T, ui, up } = ctx;
  const C = T.c;

  const chips = chipsFor(n, C);
  const done = n.level === 'TASK' && (!!n.vals.done || n.vals.status === 'Done');
  const paused = n.level === 'RECURRING' && !!n.vals.paused;
  const active =
    sel || ui.detail === n.id || ui.menuFor === n.id || (!!ui.chipEdit && ui.chipEdit.id === n.id);

  // v4: a chip with no `field` is not editable — tapping it opens the detail editor instead.
  // Otherwise the chip strip TOGGLES: tapping the already-open field closes it.
  const onChip = (field: string | undefined) => {
    if (!field) {
      up({ detail: n.id });
      return;
    }
    const ce = ui.chipEdit;
    const same = !!ce && ce.id === n.id && ce.field === field;
    up({ chipEdit: same ? null : { id: n.id, field }, menuFor: null });
  };

  // ── drag to re-parent ──────────────────────────────────────────────────────
  // A GOAL is a root and a STRATEGY lives outside the hierarchy, so neither can be moved;
  // only container levels can receive a drop.
  //
  // ⚠ CORRECTED 2026-07-18 (review gate). This previously asserted "no call site in v4 passes
  // `dnd:true`, so this whole branch is unreachable there" — WRONG. v4:747, `deskApp`'s Map
  // panel row, passes `dnd:true` (with sel/noMenu/badgeAbove). Drag-to-reparent is a LIVE path
  // in v4's DESKTOP Map, so this lands in Task 10, not Task 6.
  //
  // Carry forward to Task 11: an invalid drop no-ops SILENTLY — the guard fires here and again
  // inside move() (mutations.ts:191), neither with feedback. That is v4's own shape, but it is
  // exactly the reachable-but-silent case the toast should cover.
  const movable = dnd && n.level !== 'GOAL' && n.level !== 'STRATEGY';
  const dropTarget =
    dnd && ['GOAL', 'PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(n.level);
  const dragOver = dnd && ui.dragOverId === n.id;

  const dragProps: {
    draggable?: boolean;
    onDragStart?: (e: DragEvent<HTMLDivElement>) => void;
    onDragEnd?: () => void;
    onDragOver?: (e: DragEvent<HTMLDivElement>) => void;
    onDragLeave?: () => void;
    onDrop?: (e: DragEvent<HTMLDivElement>) => void;
  } = {};

  if (movable) {
    dragProps.draggable = true;
    dragProps.onDragStart = (e) => {
      e.stopPropagation();
      drag.id = n.id;
      try {
        e.dataTransfer.setData('text/plain', n.id);
      } catch {
        // v4 swallows this: some browsers throw on setData outside a real drag.
      }
      e.dataTransfer.effectAllowed = 'move';
    };
    dragProps.onDragEnd = () => {
      drag.id = null;
      up({ dragOverId: null });
    };
  }

  if (dropTarget) {
    dragProps.onDragOver = (e) => {
      if (!drag.id || drag.id === n.id) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (ui.dragOverId !== n.id) up({ dragOverId: n.id });
    };
    dragProps.onDragLeave = () => {
      if (ui.dragOverId === n.id) up({ dragOverId: null });
    };
    dragProps.onDrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const id = drag.id;
      up({ dragOverId: null });
      drag.id = null;
      if (!id || id === n.id) return;
      // v4 walks `t.parent` up from the drop target looking for the dragged id — i.e. refuses
      // to drop a node inside its own subtree, which would detach that subtree from the graph.
      // `isSelfOrDescendant(idx, id, n.id)` is that same question asked of the derived index.
      if (!isSelfOrDescendant(ctx.idx, id, n.id)) ctx.apply(move(ctx.graph, id, n.id));
    };
  }

  const titleStyle: CSSProperties = {
    fontSize: D.title,
    fontWeight: n.level === 'GOAL' ? 700 : 500,
    color: done || paused ? C.dimmer : n._new ? C.green : C.text,
    textDecoration: done ? 'line-through' : 'none',
    lineHeight: 1.4,
    wordBreak: 'break-word',
    textWrap: 'pretty',
  };

  const title = <span style={titleStyle}>{n.title || '(untitled)'}</span>;

  const chipRow = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {chips.map((c, i) => (
        <span key={i}>
          <Chip
            T={T}
            c={c}
            onClick={(e) => {
              // v4:452/455 — `e.stopPropagation()` BEFORE onChip. Without it the chipsBelow
              // strip, which is a child of the row's tap target, fires onTap as well.
              e.stopPropagation();
              onChip(c.field);
            }}
          />
        </span>
      ))}
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
      <div
        {...dragProps}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '5px',
          // THE indentation rule. Nothing else reads `depth`.
          paddingLeft: 8 + depth * 16 + 'px',
          background: dragOver
            ? C.blue + '2a'
            : active
              ? 'linear-gradient(90deg,' + C.rose + '26,' + C.rose + '0a 78%)'
              : 'transparent',
          boxShadow: active && !dragOver ? 'inset 2px 0 0 ' + C.rose : 'none',
          outline: dragOver ? '2px dashed ' + C.blue : 'none',
          outlineOffset: '-2px',
          borderBottom: '1px solid ' + C.hair,
          cursor: movable ? 'grab' : undefined,
        }}
      >
        <Lead ctx={ctx} n={n} expandable={expandable} open={open} onExpand={onExpand} />

        {chipsBelow ? (
          <div
            onClick={onTap}
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              cursor: 'pointer',
              padding: D.padV + ' 2px ' + D.padV + ' 0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '7px' }}>
              {hideBadge ? null : (
                <span style={{ marginTop: '2px' }}>
                  <Badge T={T} level={n.level} small />
                </span>
              )}
              {title}
            </div>
            {chips.length ? chipRow : null}
          </div>
        ) : (
          <div
            onClick={onTap}
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: badgeAbove ? 'column' : 'row',
              alignItems: 'flex-start',
              gap: badgeAbove ? '3px' : '7px',
              cursor: 'pointer',
              padding: D.padV + ' 2px ' + D.padV + ' 0',
            }}
          >
            {hideBadge ? null : (
              <span style={{ marginTop: badgeAbove ? '0' : '2px' }}>
                <Badge T={T} level={n.level} small />
              </span>
            )}
            {title}
          </div>
        )}

        {!chipsBelow && chips.length ? (
          <div
            style={{
              flex: '0 1 auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
              gap: '4px',
              padding: '9px 10px 9px 0',
            }}
          >
            {chips.map((c, i) => (
              <span key={i}>
                <Chip
                  T={T}
                  c={c}
                  onClick={(e) => {
                    // v4:455 — see the note on the inline chip row above.
                    e.stopPropagation();
                    onChip(c.field);
                  }}
                />
              </span>
            ))}
          </div>
        ) : null}

        {noMenu ? null : (
          <button
            onClick={(e) => {
              e.stopPropagation();
              up({ detail: n.id, menuFor: null, chipEdit: null });
            }}
            aria-label="edit"
            style={{
              width: '30px',
              minHeight: D.leadH,
              flex: '0 0 auto',
              border: 'none',
              background: 'none',
              color: active ? C.text : C.dim,
              cursor: 'pointer',
              padding: 0,
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'center',
              paddingTop: '12px',
            }}
          >
            <svg width={16} height={16} viewBox="0 0 24 24" fill="none">
              <path d="M12 20h9" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
              <path
                d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </div>
      {/* v4:460 — `dropdown = (st.chipEdit && st.chipEdit.id===n.id) ? chipStrip(...) : null`.
          The wrapper above is `position:relative`, which is what the strip's `top:100%`
          anchors to. */}
      {ui.chipEdit && ui.chipEdit.id === n.id ? (
        <ChipStrip ctx={ctx} n={n} depth={depth} chipsBelow={chipsBelow} />
      ) : null}
    </div>
  );
}
