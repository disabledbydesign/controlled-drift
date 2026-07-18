import { setVal, sideColor, statusColor } from '../../model/index.ts';
import type { DerivedSchema, ModelNode } from '../../model/index.ts';
import { FLABEL, PANEL } from './types.ts';
import type { PanelCtx } from './types.ts';

/**
 * v4 `chipOpts(n,field)` (~328), verbatim.
 *
 * Which option list a chip offers. `status` is the one that forks four ways, because four
 * levels each have their own status vocabulary — a Goal is Active/Parked/Achieved, a Task is
 * not. An unrecognised field returns `[]`, which renders a header and no options.
 */
export function chipOpts(schema: DerivedSchema, n: ModelNode, field: string): string[] {
  const O = schema.OPTS;
  if (field === 'engagement') return (n.level === 'GOAL' ? O.goalEng : O.proj) ?? [];
  if (field === 'status') {
    return (
      (n.level === 'GOAL'
        ? O.goalStatus
        : n.level === 'TASK'
          ? O.taskStatus
          : n.level === 'STRATEGY'
            ? O.strategyStatus
            : O.projStatus) ?? []
    );
  }
  if (field === 'side') return O.side ?? [];
  if (field === 'horizon') return O.horizon ?? [];
  if (field === 'when') return O.strategyState ?? [];
  if (field === 'unit') return O.unit ?? [];
  return [];
}

export interface ChipStripProps {
  ctx: PanelCtx;
  n: ModelNode;
  /** The row's indentation depth — positions the strip under the chip that opened it. */
  depth: number;
  /** Whether that row renders its chips below the title rather than right-aligned. */
  chipsBelow: boolean;
}

/**
 * v4 `chipStrip(n,depth,chipsBelow)` (~464) — the option list that drops out of a tapped chip.
 *
 * Set a field without opening the editor. Tap a chip on any row, pick a value, done; the strip
 * closes itself (`up({chipEdit:null})` fires in the same handler as `setVal`).
 *
 * ── the one piece of geometry that carries meaning ───────────────────────────
 * The strip anchors under the chip it came from, and chips sit in two different places
 * depending on the row: LEFT-aligned at the row's indentation when `chipsBelow` (Task and
 * Recurring rows), RIGHT-aligned otherwise. So the anchor swaps sides —
 * `left: 8+depth*16` vs `right: 8` — using the same `8 + depth*16` expression `Row` uses for
 * its padding. Get this wrong and the strip detaches from its chip on half the rows.
 *
 * ── colour is per-field, not per-value ──────────────────────────────────────
 * `unit` is teal for as-needed and orange otherwise, `side` is the one uniform life-area hue
 * (`sideColor` ignores its argument, deliberately — see the model layer), `horizon` is its own
 * hue, and everything else reads as a status. The selected option is tinted and check-marked.
 *
 * `data-mkeep` on the wrapper is v4's own attribute, carried across. Task 1 already ported it
 * onto the `Chip` atom and documented it there as "a click inside this element must not close
 * the open menu" — same marker, same purpose, one level out.
 */
export function ChipStrip({ ctx, n, depth, chipsBelow }: ChipStripProps) {
  const { T, graph, schema, ui, up, apply } = ctx;
  const C = T.c;
  if (!ui.chipEdit) return null;

  const field = ui.chipEdit.field;
  const opts = chipOpts(schema, n, field);
  const cur = n.vals[field];

  /** v4:465 — only `unit` relabels; every other field shows its raw option value. */
  const unitLabel: Record<string, string> = {
    day: 'Every day',
    week: 'Every week',
    month: 'Every month',
    as_needed: 'As needed',
  };

  return (
    <div
      data-mkeep="1"
      style={{
        position: 'absolute',
        top: '100%',
        marginTop: '2px',
        left: chipsBelow ? 8 + depth * 16 + 'px' : undefined,
        right: chipsBelow ? undefined : '8px',
        zIndex: 49,
        background: C.roseBg,
        border: '1px solid ' + C.border,
        borderRadius: T.r.ctl,
        padding: '6px',
        minWidth: '176px',
        boxShadow: '0 14px 34px rgba(0,0,0,.55)',
        animation: 'panelin ' + PANEL,
      }}
    >
      <div
        style={{
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '.08em',
          textTransform: 'uppercase',
          color: C.dimmer,
          padding: '4px 8px 6px',
        }}
      >
        {FLABEL[field] || field}
      </div>
      {opts.map((o) => {
        const on = cur === o;
        const col =
          field === 'unit'
            ? o === 'as_needed'
              ? C.teal
              : C.orange
            : field === 'side'
              ? sideColor(o, C)
              : field === 'horizon'
                ? C.horizon
                : statusColor(o, C);
        const label = field === 'unit' ? unitLabel[o] || o : o;
        return (
          <button
            key={o}
            onClick={(e) => {
              // Not v4's: v4's chips are not nested inside a tap target on every row, but here
              // the strip is a child of `Row`'s wrapper and a bubbling click re-opens the row.
              e.stopPropagation();
              apply(setVal(graph, n.id, field, o));
              up({ chipEdit: null });
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              width: '100%',
              textAlign: 'left',
              background: on ? col + '1c' : 'none',
              border: 'none',
              color: on ? col : C.text,
              fontSize: '13px',
              fontWeight: on ? 700 : 500,
              padding: '8px 9px',
              borderRadius: T.r.ctl,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: col,
                flex: '0 0 auto',
              }}
            />
            <span style={{ flex: 1 }}>{label}</span>
            {on ? <span style={{ color: col, fontSize: '13px' }}>✓</span> : null}
          </button>
        );
      })}
    </div>
  );
}
