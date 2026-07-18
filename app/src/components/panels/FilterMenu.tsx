import type { ReactNode } from 'react';
import { Switch } from '../atoms/index.ts';
import { PANEL } from './types.ts';
import type { PanelCtx } from './types.ts';

/**
 * v4 `filterMenu()` (~359) — the filter block that drops under `mapControls`.
 *
 * Two controls, and they are different KINDS of control on purpose: "Hide inactive" is a
 * boolean with a switch, Side is a single-choice row of pills with an explicit "All". Both
 * are shared by all three structure tabs (v4 renders this from `structurePanel`, not from any
 * one body), which is why the Routines cadence chips and the Strategies When/Status block
 * live in their own bodies instead of here.
 *
 * The help line under "Hide inactive" is v4's copy verbatim — it lists what "inactive" means
 * per level, because `isInactive` is level-aware and nothing else says so.
 *
 * ⚠ ONE ADDITION to v4's style object: `flex:'0 0 auto'`. This is a direct child of
 * `structurePanel`'s flex column, and without it the default `flex-shrink:1` lets the block
 * compress when the list below is long. v4 has the same omission; it is a fix, not a
 * transcription, and is called out here rather than folded in silently.
 */
export function FilterMenu({ ctx }: { ctx: PanelCtx }) {
  const { T, schema, ui, up } = ctx;
  const C = T.c;

  const sw = (label: string, on: boolean, onClick: () => void, help: string): ReactNode => (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '12px',
        background: 'none',
        border: 'none',
        padding: '7px 2px',
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      <span style={{ textAlign: 'left' }}>
        <span style={{ fontSize: '12.5px', fontWeight: 600, color: C.text, display: 'block' }}>
          {label}
        </span>
        {help ? <span style={{ fontSize: '10.5px', color: C.dimmer }}>{help}</span> : null}
      </span>
      <Switch T={T} on={on} col={C.blue} />
    </button>
  );

  const sideOpt = (v: string, label: string): ReactNode => {
    const on = (ui.sideFilter || 'all') === v;
    return (
      <button
        key={v}
        onClick={() => up({ sideFilter: v })}
        style={{
          background: on ? C.side + '26' : C.panel,
          border: '1px solid ' + (on ? C.side : C.border),
          borderRadius: T.r.field,
          color: on ? C.text : C.dim,
          fontSize: '12px',
          fontFamily: 'inherit',
          padding: '6px 12px',
          cursor: 'pointer',
        }}
      >
        {label}
      </button>
    );
  };

  // v4: [['all','All']].concat(this.OPTS.side.map(s => [s, s==='Fun / hobby' ? 'Hobby' : s]))
  // The same abbreviation `chipsFor` applies to the Side chip, capitalised here because this
  // is a standalone option label rather than mid-chip text.
  const sideOpts: Array<[string, string]> = [
    ['all', 'All'],
    ...(schema.OPTS.side ?? []).map(
      (s): [string, string] => [s, s === 'Fun / hobby' ? 'Hobby' : s],
    ),
  ];

  return (
    <div
      style={{
        padding: '6px 14px 12px',
        borderBottom: '1px solid ' + C.roseBorder,
        background: C.roseBg,
        animation: 'panelin ' + PANEL,
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '10px 20px',
        flex: '0 0 auto',
      }}
    >
      {sw(
        'Hide inactive',
        ui.hideInactive,
        () => up({ hideInactive: !ui.hideInactive }),
        'Done tasks, parked/achieved goals, retired strategies…',
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px' }}>
        <div
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.1em',
            textTransform: 'uppercase',
            color: C.dimmer,
            margin: 0,
          }}
        >
          Side
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {sideOpts.map((o) => sideOpt(o[0], o[1]))}
        </div>
      </div>
    </div>
  );
}
