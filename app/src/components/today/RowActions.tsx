/**
 * The per-row ACTION PANEL — "not today", duration, move.
 *
 * ── WHY THESE EXIST AGAIN ────────────────────────────────────────────────────
 * All three were on every row of the overlay June used daily, and all three backends have been
 * live since before the v4 rebuild. The rebuilt row simply never called them. This is restoring
 * function she had, not adding features.
 *
 * ── WHAT SHE RULED AFTER USING THE FIRST ATTEMPT, AND WHERE EACH ANSWER COMES FROM ──
 *
 * A4 · THE WORD IS `edit`, the title is `edit timing`. Transcribed from the old surface
 *      (`docs/overlay_daily.html:2128`). "when" was the rebuild's invention and she rejected it.
 *      ⚠ THIS COLLIDES, AND THE COLLISION IS REPORTED RATHER THAN SILENTLY RESOLVED: the v4
 *      mockup's `EditChip` already renders the visible word "edit" on the same row line, and it
 *      opens the object editor. The old surface had no such chip, so the word was free there and
 *      is not free here. Both are labelled `edit` until June rules on it; they are separated for
 *      assistive tech by `aria-label` ("edit timing" vs "open editor") and by `title`.
 *
 * A1 · THE TRIGGER IS INLINE IN THE ROW, and opening the panel does not move anything.
 *      The inline trigger is TRANSCRIBED — the old surface called `editChipHtml` inside
 *      `.item-top` (`:2236`, `:2298`, `:2518`). The NON-REFLOWING panel is DERIVED, and needs
 *      saying plainly: the old surface's panel sat on its own line under the row and DID push
 *      the rows below it down. June asked for a dropdown that expands "without knocking the
 *      other elements around", so the panel is a floating pane anchored under the trigger,
 *      built from this codebase's own menu/popover tokens (`T.pane`, `T.paneBlur`,
 *      `C.paneShadow`) as used by `PickerPage` and `DeskShell`. No new token was introduced.
 *
 * A2 · MOVE IS A PLACEMENT MODE, NOT A LIST OF LABELS. Tapping `move` collapses this panel and
 *      fills the plan with landing slots; this component's only remaining job while placing is
 *      the `cancel`. Transcribed from the old surface's `_placing` (`:2119-2129`), including the
 *      rule that every OTHER row's affordance disappears while a placement is in flight. The
 *      slots themselves live in `PlaceTarget.tsx`.
 *
 * A4/C · THE DURATION IS LABELLED, not a bare verb: `duration: 45 min`, or `chunk length:` on a
 *      block. Transcribed from `editPanelHtml` (`:2140-2151`). When nothing is set it says so
 *      literally — `not set` — and never shows a fabricated default as though it were a decision.
 *      ⚠ The value does not currently arrive for TASK rows; it is dropped server-side at row
 *      assembly. That is another task's fix. This reads whatever arrives and is honest meanwhile.
 *
 * ── GUARDS ───────────────────────────────────────────────────────────────────
 * B2 · No id, no panel. A generated row (a rest suggestion, the walk) has nothing to persist to,
 *      and `server.py`'s own comment on `/api/duration` states this as the invariant. The old
 *      surface withheld it the same way (`:2135`). `rowWriteGuard` catching it at write time is
 *      too late: by then she has already tapped something that could only fail.
 * B1 · No move on an appointment. `adapt.ts` renders appointments as ordinary task rows, but the
 *      server never indexed them, so any destination offered can only 404.
 * B5 · Three different truths, three different sentences. See `MoveRefusal`.
 *
 * ── TOUCH TARGETS ────────────────────────────────────────────────────────────
 * Following commit 3474eef: hit area enlarged with padding plus a matching negative margin, so
 * the target grows and the tuned visual does not move. Her visual design is untouched.
 *
 * ── THEMES ───────────────────────────────────────────────────────────────────
 * No `isHW()` fork on the controls themselves, deliberately and unchanged: this row's vocabulary
 * is underlined text buttons, and its neighbour `EditChip` does not fork either. The two things
 * that ARE new surfaces — the floating pane and `PlaceTarget` — take the fork the codebase
 * already applies to panes and chips respectively, so shape (not only colour) differs per theme.
 *
 * ── NO METAPHORS ─────────────────────────────────────────────────────────────
 * Every June-facing string here is literal. This is a hard accessibility rule, not a style
 * preference: metaphors block her parsing.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import type { PlanItem } from '../../fixtures/index.ts';
import { node } from '../../model/index.ts';
import { moveOptions } from './moveTargets.ts';
import type { MoveRefusal } from './moveTargets.ts';
import type { TodayCtx } from './types.ts';

export interface RowActionsProps {
  ctx: TodayCtx;
  /** The row's id — a task id, or for a block the PROJECT id the server dispatches on. */
  id: string;
  kind: 'task' | 'block';
  /** Minutes already set: a task's own duration, or a block's chunk length. 0 means unset. */
  durationMin: number;
}

/**
 * One sentence per truth (B5). The old single sentence — "There is nowhere else to put this
 * today." — was said for all three, and for two of them it was not true.
 */
const REFUSAL_WORDS: Record<MoveRefusal, string> = {
  'not-found': 'I could not find this row in today’s plan, so it cannot be moved.',
  appointment: 'This is an appointment at a fixed time, so it does not move.',
  nowhere: 'There is nowhere else to put this today.',
};

export function RowActions({ ctx, id, kind, durationMin }: RowActionsProps) {
  const C = ctx.T.c;
  const isBlock = kind === 'block';
  const [editingMinutes, setEditingMinutes] = useState(false);
  const [draft, setDraft] = useState('');

  // B2 — before anything else. A row with no backing object has nowhere to persist to, so it
  // gets no control at all rather than one that can only fail.
  if (!id) return null;

  const open = !!ctx.ui.editOpen[id];
  const placing = ctx.ui.movePick;

  const chipStyle = {
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
  } as const;

  const chip = (label: string, onClick: () => void, aria?: string, title?: string) => (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      {...(aria ? { 'aria-label': aria } : null)}
      {...(title ? { title } : null)}
      style={chipStyle}
    >
      {label}
    </button>
  );

  /**
   * PLACEMENT MODE COLLAPSES EVERYTHING ELSE — one thing at a time. Transcribed from the old
   * surface: while `_placing`, the moving row shows a `cancel` and every other row shows nothing
   * at all, so the only affordances on screen are the landing slots.
   */
  if (placing) {
    if (placing !== id) return null;
    return chip('cancel', () => ctx.up({ movePick: null }), 'cancel this move');
  }

  const titleOf = (it: PlanItem): string => {
    if ('id' in it && it.id) {
      const n = node(ctx.idx, it.id);
      if (n?.title) return n.title;
    }
    return 'task' in it && it.task ? it.task : 'this row';
  };

  // A block is not one movable row — the old overlay withheld move on blocks for the same
  // reason, and `plan_store.move_item` addresses task rows.
  const opts = isBlock ? null : moveOptions(ctx.plan, id, titleOf);
  // B1: an appointment cannot move at all, so the control is withheld rather than offered and
  // 404ed. Every other refusal keeps the control and answers in words when she taps it, because
  // "nowhere to put this today" is a fact about today that is worth being told.
  const showMove = !!opts && opts.refusal !== 'appointment';

  const startPlacing = () => {
    if (!opts) return;
    if (opts.refusal) {
      ctx.flash(REFUSAL_WORDS[opts.refusal]);
      return;
    }
    // The panel gives way to the slots — it is not a menu she picks from any more.
    const next = { ...ctx.ui.editOpen };
    delete next[id];
    ctx.up({ editOpen: next, movePick: id });
  };

  // The reveal. Closed is the resting state: three controls on every row of a phone list is the
  // arrangement June already called messy once.
  const trigger = chip(
    'edit',
    () => ctx.up({ editOpen: { ...ctx.ui.editOpen, [id]: true } }),
    'edit timing',
    'edit timing',
  );

  if (!open) return trigger;

  /**
   * ONE endpoint, TWO meanings — dispatched server-side on whether the row is a block. A block
   * sets how long she works on that project in a sitting; a task sets how long that one thing
   * takes. The old overlay named them separately and so does this. Collapsing them into one word
   * would flatten a distinction she uses.
   *
   * The LABEL is separate from the VALUE, as it was on the old surface: `duration: 45 min`, not
   * a verb standing in for a reading. `not set` is the honest empty state — never a default
   * number, which would read as a decision that was never made.
   */
  const durationName = isBlock ? 'chunk length:' : 'duration:';
  const durationValue = durationMin ? durationMin + ' min' : 'not set';

  const closePanel = () => {
    const next = { ...ctx.ui.editOpen };
    delete next[id];
    ctx.up({ editOpen: next });
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

  return (
    <span style={{ position: 'relative', display: 'inline-flex', flex: '0 0 auto' }}>
      {trigger}
      {/**
       * A1 — THE FLOATING PANE. `position:absolute` is the whole point: the panel is taken out
       * of the row's flow, so it can neither add a line of height to every row nor push the rows
       * below it down when it opens. Anchored to the trigger's right edge so it opens inward on
       * a 392px phone instead of off the screen.
       */}
      <div
        role="group"
        aria-label="edit timing"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          zIndex: 30,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '10px',
          padding: '9px 11px',
          minWidth: '206px',
          textAlign: 'left',
          background: ctx.T.pane,
          backdropFilter: ctx.T.paneBlur,
          WebkitBackdropFilter: ctx.T.paneBlur,
          border: '1px solid ' + C.border,
          borderRadius: ctx.T.r.card,
          boxShadow: ctx.T.effects.paneShadow,
        }}
      >
        {showMove ? chip('move', startPlacing, 'move this row') : null}

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
            <button type="submit" style={chipStyle}>
              save
            </button>
          </form>
        ) : (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '5px' }}>
            <span style={{ fontSize: '11.5px', color: C.dimmer }}>{durationName}</span>
            {chip(
              durationValue,
              () => {
                setDraft(durationMin ? String(durationMin) : '');
                setEditingMinutes(true);
              },
              isBlock ? 'set how long a chunk is' : 'set how long this takes',
            )}
          </span>
        )}

        {chip('not today', () => ctx.notToday(id, kind))}
        {chip('close', closePanel)}
      </div>
    </span>
  );
}
