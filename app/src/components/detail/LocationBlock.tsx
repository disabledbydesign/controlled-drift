import { Badge, typeColor } from '../atoms/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface LocationBlockProps {
  ctx: DetailCtx;
  n: ModelNode;
  /** The ancestors, root-first, EXCLUDING `n` — v4's `pathTo(id).slice(0,-1)`. */
  path: ModelNode[];
}

/**
 * v4 `locationBlock(n,path)` (~500) — where the object sits in the tree.
 *
 * ── the two branches are different KINDS of statement ────────────────────────
 * v4's own comment: "Goals and strategies have no parent by design — a goal is top-level, a
 * strategy applies globally. Show that as a stated fact, not a dead field." So the
 * non-movable branch is not a disabled control; it is a sentence, with its own heading
 * ("Position" / "Scope") and no tap target. Nothing about it can be actioned, and nothing
 * about it looks like it could be.
 *
 * The movable branch is a tap target that opens the move picker (`up({moveFor, pickerFilter})`;
 * `pickerPage` is Task 6). Its crumbs are indented 16px per level with a `↳` from the second
 * row down, and each carries a small type badge — the same containment story the Map tells,
 * restated vertically because a detail pane is narrow.
 *
 * ── the empty-path case ──────────────────────────────────────────────────────
 * An unparented movable object still renders the block, with a single crumb reading
 * "Top level · no goal yet" and NO badge (`c.level` is undefined on that synthetic crumb).
 * The block stays tappable, which is how an orphan gets filed.
 *
 * The dot in the non-movable branch is object-TYPE colour, from `typeColor` (the gallery
 * legend) — v4 read `this.TYPE[n.level]`, which is superseded. See `atoms/typeColor.ts`.
 */
export function LocationBlock({ ctx, n, path }: LocationBlockProps) {
  const { T, up } = ctx;
  const C = T.c;
  const movable = n.level !== 'GOAL' && n.level !== 'STRATEGY';

  const heading = (text: string) => (
    <div
      style={{
        fontSize: '10.5px',
        fontWeight: 700,
        letterSpacing: '.12em',
        textTransform: 'uppercase',
        color: C.dimmer,
        marginBottom: '8px',
      }}
    >
      {text}
    </div>
  );

  if (!movable) {
    const strategy = n.level === 'STRATEGY';
    const label = strategy ? 'Scope' : 'Position';
    const head = strategy ? 'Applies globally' : 'Top-level goal';
    const note = strategy
      ? 'Read into every daily plan — strategies aren’t filed under a goal or project.'
      : 'Nothing sits above a goal; projects and tasks file underneath it.';
    return (
      <div style={{ marginBottom: '16px' }}>
        {heading(label)}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '9px', padding: '2px 2px 0' }}>
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: typeColor(T, n.level),
              flex: '0 0 auto',
              marginTop: '6px',
            }}
          />
          <div style={{ minWidth: 0 }}>
            <div
              style={{ fontSize: '13.5px', fontWeight: 600, color: C.text, marginBottom: '2px' }}
            >
              {head}
            </div>
            <div style={{ fontSize: '11.5px', lineHeight: 1.45, color: C.dimmer }}>{note}</div>
          </div>
        </div>
      </div>
    );
  }

  // v4:513 — `path.length ? path.map(...) : [{t:'Top level · no goal yet'}]`
  const crumbs: Array<{ level?: string; t: string }> = path.length
    ? path.map((p) => ({ level: p.level, t: p.title }))
    : [{ t: 'Top level · no goal yet' }];

  return (
    <div style={{ marginBottom: '16px' }}>
      {heading('Belongs to')}
      <div
        onClick={() => up({ moveFor: n.id, pickerFilter: '' })}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: C.panel,
          border: '1px solid ' + C.border,
          borderRadius: T.r.ctl,
          padding: '9px 11px',
          cursor: 'pointer',
        }}
      >
        <div
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          {crumbs.map((c, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                paddingLeft: i * 16 + 'px',
              }}
            >
              {i > 0 ? (
                <span style={{ color: C.dimmer, fontSize: '13px', marginRight: '1px' }}>↳</span>
              ) : null}
              {c.level ? <Badge T={T} level={c.level} small /> : null}
              <span style={{ fontSize: '13px', color: C.text, wordBreak: 'break-word' }}>{c.t}</span>
            </div>
          ))}
        </div>
        <span
          style={{
            flex: '0 0 auto',
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            color: C.blue,
            fontSize: '12.5px',
            fontWeight: 600,
          }}
        >
          Move
          <svg width={15} height={15} viewBox="0 0 24 24" fill="none">
            <path
              d="M9 6l6 6-6 6"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </div>
    </div>
  );
}
