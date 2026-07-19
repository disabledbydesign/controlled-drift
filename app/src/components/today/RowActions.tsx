/**
 * The per-row ACTION PANEL — "not today", duration, move.
 *
 * ── WHY THESE EXIST AGAIN ────────────────────────────────────────────────────
 * All three were on every row of the overlay June used daily, and all three backends have been
 * live since before the v4 rebuild. The rebuilt row simply never called them. This is restoring
 * function she had, not adding features.
 *
 * ── HOW THEY ARE REVEALED, AND WHERE THAT DECISION COMES FROM ────────────────
 * Behind one per-row chip, not always visible. Stating the provenance plainly, because this is
 * the kind of thing that gets presented as a transcription when it is a derivation:
 *
 *   • The v4 mockup has NO rendered precedent for this. It declares `editOpen: new Set()` in its
 *     Today state and never reads it — grepped, one occurrence, the declaration. So the mockup
 *     anticipated a per-row reveal here and left it unbuilt. The state NAME is v4's; the
 *     rendering is not.
 *   • The treatment is derived from the OLD OVERLAY, which put exactly these three controls
 *     behind one per-row reveal, for a reason recorded at the point of the change: June found the
 *     separate always-visible chips "messy" (`docs/overlay_daily.html`, `editChipHtml` ~2113).
 *     Today is a phone surface with seven-plus rows; three always-visible controls per row is the
 *     arrangement she already rejected once.
 *   • The existing `EditChip` could not be reused as the entry point, because on this surface it
 *     is already taken — it opens the object editor. So the panel needs its own affordance.
 *
 * ⚠ THE ONE THING THAT IS MINE AND SHOULD BE HERS: the chip's WORD. The old overlay's said
 * "edit", which is unavailable here. "when" is the most literal cover I could find for the three
 * (move it, how long it takes, not today) — but naming is June's call, and this is a one-word
 * change if she wants a different one.
 *
 * ── TOUCH TARGETS ────────────────────────────────────────────────────────────
 * Following commit 3474eef: hit area enlarged with padding plus a matching negative margin, so
 * the target grows and the tuned visual does not move. Her visual design is untouched.
 *
 * ── NO METAPHORS ─────────────────────────────────────────────────────────────
 * Every June-facing string here is literal. This is a hard accessibility rule, not a style
 * preference: metaphors block her parsing.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import type { PlanItem } from '../../fixtures/index.ts';
import { node } from '../../model/index.ts';
import { moveDestinations } from './moveTargets.ts';
import type { TodayCtx } from './types.ts';

export interface RowActionsProps {
  ctx: TodayCtx;
  /** The row's id — a task id, or for a block the PROJECT id the server dispatches on. */
  id: string;
  kind: 'task' | 'block';
  /** Minutes already set: a task's own duration, or a block's chunk length. 0 means unset. */
  durationMin: number;
}

export function RowActions({ ctx, id, kind, durationMin }: RowActionsProps) {
  const C = ctx.T.c;
  const isBlock = kind === 'block';
  const open = !!ctx.ui.editOpen[id];
  const picking = ctx.ui.movePick === id;
  const [editingMinutes, setEditingMinutes] = useState(false);
  const [draft, setDraft] = useState('');

  const chip = (label: string, onClick: () => void, ariaLabel?: string) => (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      {...(ariaLabel ? { 'aria-label': ariaLabel } : null)}
      style={{
        // Hit area first, visual second — the padding/negative-margin pair of commit 3474eef.
        padding: '6px 10px',
        margin: '-6px -4px',
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontFamily: 'inherit',
        fontSize: '11.5px',
        color: C.dim,
        textDecoration: 'underline',
        textDecorationColor: C.roseBorder,
        textUnderlineOffset: '2px',
      }}
    >
      {label}
    </button>
  );

  // The reveal. Closed is the resting state: three controls on every row of a phone list is the
  // arrangement June already called messy once.
  if (!open) {
    return chip('when', () => ctx.up({ editOpen: { ...ctx.ui.editOpen, [id]: true } }), 'change when');
  }

  /**
   * ONE endpoint, TWO meanings — dispatched server-side on whether the row is a block. A block
   * sets how long she works on that project in a sitting; a task sets how long that one thing
   * takes. The old overlay named them separately and so does this. Collapsing them into one word
   * would flatten a distinction she uses.
   */
  const durationLabel = durationMin
    ? durationMin + ' min'
    : isBlock
      ? 'set chunk length'
      : 'set duration';

  const closePanel = () => {
    const next = { ...ctx.ui.editOpen };
    delete next[id];
    ctx.up({ editOpen: next, ...(picking ? { movePick: null } : null) });
  };

  const submitMinutes = (e: FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const n = Number(draft.trim());
    // The server 400s a non-positive value. Refusing to send it keeps a failure she cannot act on
    // out of her way — and says so, rather than letting the tap do nothing.
    if (!Number.isFinite(n) || n <= 0) {
      ctx.flash('That needs to be a number of minutes above zero.');
      return;
    }
    ctx.setDuration(id, Math.round(n));
    setEditingMinutes(false);
    setDraft('');
  };

  const titleOf = (it: PlanItem): string => {
    if ('id' in it && it.id) {
      const n = node(ctx.idx, it.id);
      if (n?.title) return n.title;
    }
    return 'task' in it && it.task ? it.task : 'this row';
  };

  const destinations = picking ? moveDestinations(ctx.plan, id, titleOf) : [];

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '10px',
        padding: '7px 0 2px',
      }}
    >
      {/* A block is not one movable row — the old overlay withheld move on blocks for the same
          reason, and `plan_store.move_item` addresses task rows. */}
      {isBlock
        ? null
        : picking
          ? chip('cancel', () => ctx.up({ movePick: null }))
          : chip('move', () => ctx.up({ movePick: id }))}

      {editingMinutes ? (
        <form onSubmit={submitMinutes} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <input
            aria-label="minutes"
            autoFocus
            inputMode="numeric"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '58px',
              background: C.panel,
              border: '1px solid ' + C.border,
              borderRadius: ctx.T.r.field,
              color: C.text,
              fontSize: '12px',
              padding: '5px 7px',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '6px 10px',
              margin: '-6px -4px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '11.5px',
              color: C.dim,
              textDecoration: 'underline',
              textDecorationColor: C.roseBorder,
              textUnderlineOffset: '2px',
            }}
          >
            save
          </button>
        </form>
      ) : (
        chip(durationLabel, () => {
          setDraft(durationMin ? String(durationMin) : '');
          setEditingMinutes(true);
        })
      )}

      {chip('not today', () => ctx.notToday(id, kind))}
      {chip('close', closePanel)}

      {picking ? (
        <div style={{ flexBasis: '100%', paddingTop: '4px' }}>
          {destinations.length === 0 ? (
            <div style={{ fontSize: '11.5px', color: C.dimmer, padding: '4px 0' }}>
              There is nowhere else to put this today.
            </div>
          ) : (
            destinations.map((d) => (
              <button
                type="button"
                key={d.key}
                onClick={(e) => {
                  e.stopPropagation();
                  ctx.moveItem(id, d.target);
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  // 11px vertical on a 12px line gives a ~38px row; the Map picker's own
                  // destination rows sit at the same rhythm.
                  padding: '11px 10px',
                  marginBottom: '2px',
                  background: C.panel,
                  border: '1px solid ' + C.border,
                  borderRadius: ctx.T.r.field,
                  color: C.text,
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                {d.label}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
