import { Fragment, useState } from 'react';
import type { ReactNode } from 'react';
import { Chip } from '../atoms/index.ts';
import {
  chipsFor,
  del,
  hasSchedulableAncestor,
  INHERIT,
  pathTo,
  setTitle,
  setVal,
} from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { Control, Level, NoteField } from '../../fixtures/index.ts';
import { Field } from './Field.tsx';
import { HeaderDone } from './HeaderDone.tsx';
import { HeaderTypeBadge } from './HeaderTypeBadge.tsx';
import { InheritRow } from './InheritRow.tsx';
import { LocationBlock } from './LocationBlock.tsx';
import { PaneCloseBtn } from './PaneCloseBtn.tsx';
import { RecurrenceCard } from './RecurrenceCard.tsx';
import { RecurringPlanRow } from './RecurringPlanRow.tsx';
import { strategyNotes } from './strategyFields.ts';
import type { DetailCtx } from './types.ts';

export interface DetailProps {
  ctx: DetailCtx;
  /** v4's `detail(id)` argument. */
  id: string;
  /** True while the close animation is running — v4's `st.detailClosing === id`. */
  closing: boolean;
  onClose: () => void;
}

/** v4 `this.NAV` (~61), duplicated in `shell/tabs.ts` for the tab animations. */
const NAV = '.26s cubic-bezier(.4,0,.2,1)';

/**
 * v4 `detail(id)` (~541) — the full-screen object editor.
 *
 * ── THE WHOLE FORM IS GENERATED FROM THE SCHEMA ──────────────────────────────
 * `CTRL[level]` gives the controls, `TEXT[level]` the free-text notes, `OPTS[rel]` the option
 * vocabularies. Nothing below hardcodes a field, an option or a level's shape. What IS
 * hardcoded is LAYOUT — which controls sit side by side, which are suppressed when a
 * neighbour makes them redundant — and that layout keys off control LABELS, not indices, so
 * a schema that reorders its tuples still lays out correctly. See `ctrlEls` below.
 *
 * ── the layout rules, restated from v4:574-583 ───────────────────────────────
 * Suppressions (a control is dropped because another control already covers it):
 *   · `Duration (min)` when `Time of day` or `Task status` is present — it is rendered
 *     BESIDE whichever of those exists instead.
 *   · `Typical block (min)` when `Deadline` or `Side` is present — rendered beside `Side`.
 *   · `Scheduled` always — rendered beside `Due date`.
 *   · `Access conditions` when the level also has an `accessNotes` note — the two are grouped
 *     together down in the notes section so the conditions and the writing about them are
 *     adjacent.
 *   · `Needs clarifying` always — rendered beside `AI Autonomous` in a bordered toggle pair.
 *   · the status control (`Project status` / `Status` / `Goal status`) — rendered beside
 *     `Engagement`, with a hairline divider after the pair.
 *   · `Strategy status` — rendered beside `Applies when`.
 * Everything not named falls through to a plain full-width field.
 *
 * ── RECURRING is the one level with a bespoke section ────────────────────────
 * v4:546-548 strips `Repeats`, `Day of week`, `Day of month`, `Time of day` and
 * `Duration (min)` from the RECURRING control list, because those five are interdependent and
 * are rendered as `RecurringPlanRow` + `RecurrenceCard` instead. v4's own comment: "Cadence,
 * day, and time all live in the recurrence card; duration rides with the in-plan toggle. Only
 * effort flags & notes flow through here."
 *
 * ── NOT PORTED, and why ──────────────────────────────────────────────────────
 * · `if(id==='__focus__') return this.focusDetail()` (v4:541). The focus-period editor SHIPPED
 *   (Task 9) but mounts as its own overlay, `components/focus/FocusOverlay`, a sibling of
 *   `DetailOverlay` in `AppShell` — it needs `periods` / `applyPeriods`, which `DetailCtx`
 *   does not carry. The guard below stays so exactly one of the two ever paints.
 * · `maybeDiscardBlank` (v4:307). v4 runs it inside `up()` whenever `detail` changes, to
 *   delete a just-created `_new` node the user closed without filling in. Its only producer is
 *   `addChild`, which has no UI yet (Task 6/8), so it is unreachable — reported rather than
 *   added, since it belongs in the shell's `up`, not here.
 * · The excitement picker (v4's `scale`/`slider` field kinds). Cut field. See `Field.tsx`.
 * · `typeSection` (v4:292). Ported as a component but not rendered — it has NO call site in
 *   v4 either — grep finds only its definition at v4:292. NOT PORTED, for the same reason
 *   renderApp()/header()/tab() were not: this repo does not port v4's dead paths, and an
 *   unwired component is the "built-but-dead" shape BUILD_DOC §3 exists to prevent. Type
 *   conversion is real and lives in the header dropdown (`HeaderTypeBadge`).
 */
export function Detail({ ctx, id, closing, onClose }: DetailProps) {
  const { T, graph, idx, schema, ui, up, apply, flash, wide } = ctx;
  const C = T.c;

  // v4:476 `askDelete` — a two-tap confirm that disarms itself after a timeout. Local rather
  // than in the shared UI bag: nothing outside this pane reads it, and it must not survive
  // the pane closing (an armed delete carried onto the next object would be dangerous).
  const [confirmDelete, setConfirmDelete] = useState(false);

  // The focus period has its own overlay (see the header note). Returning null keeps this
  // pane from painting a wrong editor underneath it.
  if (id === '__focus__') return null;

  const n: ModelNode | undefined = idx.byId.get(id);
  if (!n) return null;

  const path = pathTo(idx, id).slice(0, -1);
  const level = n.level as Level;
  const ctrls: readonly Control[] = schema.CTRL[level] || [];
  const rawTexts: readonly NoteField[] = schema.TEXT[level] || [];
  const done = n.level === 'TASK' && (!!n.vals.done || n.vals.status === 'Done');
  const paused = n.level === 'RECURRING' && !!n.vals.paused;

  let ctrls2: readonly Control[] = ctrls;
  if (n.level === 'RECURRING') {
    // v4:546-548 — see the RECURRING note in the header comment.
    ctrls2 = ctrls.filter(
      (s) =>
        !['Repeats', 'Day of week', 'Day of month', 'Time of day', 'Duration (min)'].includes(s[1]),
    );
  }
  // The Strategy override (see `strategyFields.ts`) is the ONE place the form is not a
  // straight read of the schema, and it is a data-model correction, not a design change.
  const texts2: readonly NoteField[] = n.level === 'STRATEGY' ? strategyNotes(rawTexts) : rawTexts;

  const field = (spec: Control, key?: string) => (
    <Field key={key ?? spec[1]} ctx={ctx} n={n} spec={spec} />
  );

  const ctrlLabel =
    n.level === 'RECURRING'
      ? 'Schedule'
      : n.level === 'STRATEGY'
        ? 'Trigger & status'
        : 'Plan controls';

  const accessSpec = ctrls2.find((x) => x[1] === 'Access conditions');
  const hasAccessNotes = texts2.some((t) => t[1] === 'accessNotes');
  const hasStatus = ctrls2.some((s) => s[1] === 'Task status');
  const statusSpec = ctrls2.find((x) =>
    ['Project status', 'Status', 'Goal status'].includes(x[1]),
  );
  const hasDeadline = ctrls2.some((s) => s[1] === 'Deadline');
  const hasTime = ctrls2.some((s) => s[1] === 'Time of day');

  const pairRow = (key: string, a: Control | undefined, b: Control | undefined) => (
    <div key={key} style={{ display: 'flex', gap: '12px' }}>
      {a ? <div style={{ flex: 1, minWidth: 0 }}>{field(a)}</div> : null}
      {b ? <div style={{ flex: 1, minWidth: 0 }}>{field(b)}</div> : null}
    </div>
  );

  const classDivider = (
    <div key="clsdiv" style={{ height: '1px', background: C.hair, margin: '2px 0 12px' }} />
  );

  // v4:583, transcribed. The order of the tests matters: the first match wins and returns.
  const ctrlEls: ReactNode[] = [];
  ctrls2.forEach((s) => {
    if (s[1] === 'Duration (min)' && (hasTime || hasStatus)) return;
    if (s[1] === 'Typical block (min)' && (hasDeadline || ctrls2.some((x) => x[1] === 'Side')))
      return;
    if (s[1] === 'Scheduled') return;
    if (s[1] === 'Access conditions' && hasAccessNotes) return;
    if (s[1] === 'Needs clarifying') return;
    if (statusSpec && s === statusSpec) return;
    if (s[1] === 'Strategy status') return;
    if (s[1] === 'AI Autonomous') {
      const nc = ctrls2.find((x) => x[1] === 'Needs clarifying');
      ctrlEls.push(
        <div
          key="togglepair"
          style={{
            display: 'flex',
            gap: '16px',
            background: C.panel,
            border: '1px solid ' + C.border,
            borderRadius: T.r.ctl,
            padding: '12px 14px',
            margin: '4px 0 14px',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>{field(s)}</div>
          {nc ? <div style={{ flex: 1, minWidth: 0 }}>{field(nc)}</div> : null}
        </div>,
      );
      return;
    }
    if (s[1] === 'Time of day') {
      const dur = ctrls2.find((x) => x[1] === 'Duration (min)');
      ctrlEls.push(pairRow('todpair', s, dur));
      return;
    }
    if (s[1] === 'Due date') {
      const sched = ctrls2.find((x) => x[1] === 'Scheduled');
      ctrlEls.push(pairRow('duesched', s, sched));
      return;
    }
    if (s[1] === 'Task status') {
      const dur = ctrls2.find((x) => x[1] === 'Duration (min)');
      // v4 uses `flex:'0 0 auto'` for the duration half HERE and `flex:1` in `pairRow` —
      // status wants the room, duration is a small number box. Not a pairRow call in v4.
      ctrlEls.push(
        <div key="statusdur" style={{ display: 'flex', gap: '12px' }}>
          <div style={{ flex: 1, minWidth: 0 }}>{field(s)}</div>
          {dur ? <div style={{ flex: '0 0 auto' }}>{field(dur)}</div> : null}
        </div>,
      );
      return;
    }
    if (s[1] === 'Engagement') {
      ctrlEls.push(pairRow('engstat', statusSpec, s));
      if (statusSpec) ctrlEls.push(classDivider);
      return;
    }
    if (s[1] === 'Applies when') {
      const stat = ctrls2.find((x) => x[1] === 'Strategy status');
      ctrlEls.push(pairRow('whenstat', s, stat));
      return;
    }
    if (s[1] === 'Deadline') {
      ctrlEls.push(field(s));
      return;
    }
    if (s[1] === 'Side') {
      const blk = ctrls2.find((x) => x[1] === 'Typical block (min)');
      ctrlEls.push(blk ? pairRow('sideblk', s, blk) : field(s));
      return;
    }
    ctrlEls.push(field(s));
  });

  const headerChips = chipsFor(n, C);

  const backLabel =
    ui.returnFrom === 'today' ? 'Today' : ui.returnFrom === 'add' ? 'Add' : 'Back';

  const crumbTappable = path.length > 0 && n.level !== 'STRATEGY';

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: T.pane,
        backdropFilter: T.paneBlur,
        WebkitBackdropFilter: T.paneBlur,
        display: 'flex',
        flexDirection: 'column',
        animation: (closing ? 'slideout' : 'slidein') + ' ' + NAV + (closing ? ' forwards' : ''),
        zIndex: 30,
      }}
    >
      <div style={{ padding: '12px 16px 11px', borderBottom: '1px solid ' + C.hair, flex: '0 0 auto' }}>
        {wide ? (
          <PaneCloseBtn T={T} onClose={onClose} />
        ) : (
          <button
            onClick={onClose}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'none',
              border: 'none',
              color: C.blue,
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              padding: 0,
              marginBottom: '9px',
              fontFamily: 'inherit',
            }}
          >
            <svg width={18} height={18} viewBox="0 0 24 24" fill="none">
              <path
                d="M15 6l-6 6 6 6"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {backLabel}
          </button>
        )}

        {/* The breadcrumb doubles as a second way into the move picker — but only when there
            IS a path and the object is not a Strategy (a Strategy has no parent to change).
            v4 gates the click handler, the cursor and the "· move ›" affix on the same test. */}
        <div
          onClick={crumbTappable ? () => up({ moveFor: n.id, pickerFilter: '' }) : undefined}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            flexWrap: 'wrap',
            fontSize: '11px',
            color: C.dimmer,
            marginBottom: '8px',
            cursor: crumbTappable ? 'pointer' : 'default',
          }}
        >
          {path.length ? (
            path.map((p, i) => (
              <span key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {i > 0 ? <span>›</span> : null}
                <span style={{ color: C.dim }}>{p.title}</span>
              </span>
            ))
          ) : (
            <span>{n.level === 'STRATEGY' ? 'Strategy' : 'Top level'}</span>
          )}
          {crumbTappable ? (
            <span style={{ color: C.blue, fontWeight: 600, whiteSpace: 'nowrap' }}>· move ›</span>
          ) : null}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
          <HeaderDone ctx={ctx} n={n} />
          <HeaderTypeBadge ctx={ctx} n={n} />
          <textarea
            value={n.title}
            placeholder="Title…"
            rows={1}
            aria-label="Title"
            onChange={(e) => apply(setTitle(graph, id, e.target.value))}
            onBlur={() => flash('Saved')}
            style={{
              flex: 1,
              minWidth: 0,
              background: 'none',
              border: 'none',
              textDecoration: done ? 'line-through' : 'none',
              fontSize: '19px',
              fontWeight: 700,
              lineHeight: 1.3,
              padding: '2px 0',
              outline: 'none',
              fontFamily: 'inherit',
              resize: 'none',
              overflow: 'hidden',
              // v4 sets `color` TWICE in this style object (once from `done`, then from
              // `done||paused`). The second wins in JS object literals, so only the second is
              // reproduced — the first is dead in v4 too.
              color: done || paused ? C.dimmer : C.text,
            }}
          />
        </div>
        {headerChips.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
            {headerChips.map((c, i) => (
              <span key={i}>
                <Chip T={T} c={c} />
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 90px' }}>
        <LocationBlock ctx={ctx} n={n} path={path} />
        <div
          style={{
            fontSize: '10.5px',
            fontWeight: 700,
            letterSpacing: '.12em',
            textTransform: 'uppercase',
            color: C.dimmer,
            marginBottom: '12px',
          }}
        >
          {ctrlLabel}
        </div>
        {n.level === 'RECURRING' ? <RecurringPlanRow ctx={ctx} n={n} /> : null}
        {n.level === 'RECURRING' ? <RecurrenceCard ctx={ctx} n={n} /> : null}
        {ctrlEls}

        {texts2.length ? (
          <div
            style={{
              fontSize: '10.5px',
              fontWeight: 700,
              letterSpacing: '.12em',
              textTransform: 'uppercase',
              color: C.dimmer,
              margin: '6px 0 12px',
            }}
          >
            Notes &amp; context
          </div>
        ) : null}

        {texts2.map(([label, vk]) => {
          const raw = n.vals[vk];
          const v = raw ? String(raw) : '';
          const ta = (
            <textarea
              value={v}
              placeholder="—"
              aria-label={label}
              onChange={(e) => apply(setVal(graph, id, vk, e.target.value))}
              onBlur={() => {
                if (v) flash('Saved');
              }}
              // v4: three keys get 3 rows, everything else 2. `directive` is in that list and
              // stays in it — it is the Strategy instruction field, relabelled but not moved.
              rows={vk === 'context' || vk === 'description' || vk === 'directive' ? 3 : 2}
              style={{
                width: '100%',
                background: C.panel,
                border: '1px solid ' + C.border,
                borderRadius: T.r.field,
                color: C.text,
                fontSize: '13.5px',
                lineHeight: 1.5,
                padding: '9px 11px',
                outline: 'none',
                resize: 'vertical',
                fontFamily: 'inherit',
              }}
            />
          );
          const textField =
            INHERIT.has(vk) && hasSchedulableAncestor(idx, n) ? (
              <InheritRow key={vk} ctx={ctx} n={n} vk={vk} label={label} hint={null} editor={ta} />
            ) : (
              <div key={vk} style={{ marginBottom: '13px' }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: 600,
                    letterSpacing: '.04em',
                    textTransform: 'uppercase',
                    color: C.dim,
                    marginBottom: '6px',
                  }}
                >
                  {label}
                </label>
                {ta}
              </div>
            );
          // The access-conditions control was suppressed above precisely so it could be
          // rendered HERE, immediately before the notes about it.
          if (vk === 'accessNotes' && accessSpec) {
            return (
              <Fragment key="accessgrp">
                {field(accessSpec, 'accessctl')}
                {textField}
              </Fragment>
            );
          }
          return textField;
        })}

        <div style={{ display: 'flex', gap: '10px', marginTop: '18px' }}>
          <button
            onClick={() => {
              // v4:476 `askDelete(id)` — first tap arms, second deletes. v4 also disarms on a
              // timeout; here the pane unmounts on delete and the state dies with it, so the
              // only thing the timer added was disarming after inaction. Kept simple: the
              // armed state is local and gone as soon as the pane closes.
              if (confirmDelete) {
                apply(del(graph, id));
                setConfirmDelete(false);
              } else {
                setConfirmDelete(true);
              }
            }}
            style={{
              flex: 1,
              background: confirmDelete ? C.red : C.panel,
              border: '1px solid ' + (confirmDelete ? C.red : C.border),
              borderRadius: T.r.ctl,
              color: confirmDelete ? '#0b0b0d' : C.red,
              fontSize: '13px',
              fontWeight: 600,
              padding: '11px',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {confirmDelete ? 'Tap again to delete' : 'Delete'}
          </button>
        </div>
        <div
          style={{
            marginTop: '16px',
            fontSize: '11px',
            color: C.dimmer,
            textAlign: 'center',
            lineHeight: 1.5,
          }}
        >
          Edits apply to Anytype live · logged for the learning loop
          <br />
          <span style={{ opacity: 0.7 }}>{'#' + id}</span>
        </div>
      </div>
    </div>
  );
}
