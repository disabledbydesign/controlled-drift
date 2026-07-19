import { alpha } from '@tokens';
import type { PlanBlock } from '../../fixtures/index.ts';
import { bevel } from '../atoms/index.ts';
import { PlanEntry } from './PlanEntry.tsx';
import { PlaceTarget } from './PlaceTarget.tsx';
import { placementFor, planDrag, slotsInBand } from './placement.ts';
import type { TodayCtx } from './types.ts';

export interface BandProps {
  ctx: TodayCtx;
  band: PlanBlock;
  bandIndex: number;
}

/**
 * v4 `band(b,bi)` (~1053) — one clock band of the schedule ("Morning · 9:00 – 12:00").
 *
 * A full SHAPE fork on `isHW()`, not a colour swap — both halves transcribed:
 *
 *   celestial · header is a glowing `horizon` dot + uppercase label + time; the band itself
 *               is flat padding with a hairline rule under it
 *   hardware  · header is a mono `┌ LABEL` bracket, a rule that fades out to the right
 *               (`linear-gradient(90deg, blue55, transparent)`), and a mono time; the band is
 *               a bordered, bevelled panel with a 2px blue left edge, inset from the frame
 *
 * v4's `C.blue+'55'` is transcribed as `alpha(C.blue, .333)` (0x55 = 85/255).
 *
 * ⚠ `band.framing` ("Freshest energy goes to the writing that's nearly done.") is present in
 * the fixture and rendered by NEITHER v4 nor this port — v4 builds its body as
 * `[label].concat(items)` and never reads the field. Ported as-is and flagged, per the
 * port-don't-fix rule; whether the per-band framing should surface is a design call.
 */
export function Band({ ctx, band, bandIndex }: BandProps) {
  const C = ctx.T.c;
  const hw = ctx.T.mode === 'hardware';

  /**
   * A band with NO label renders NO header — not an empty one.
   *
   * ⚠ FOUND ON REAL DATA 2026-07-18. Every band in `seedPlan` is labelled, so this never came
   * up on fixtures. June's live plan is PRIORITY-shaped, and the Schedule view still renders it
   * through one unlabelled container band (`api/adapt.planFromLive`) — which made the hardware
   * theme paint a bare `┌ ` corner glyph and a rule above the list, and the celestial theme a
   * horizon dot with nothing beside it. Both read as a broken heading rather than as no heading.
   */
  const labelled = String(band.label ?? '').trim() !== '' || String(band.time ?? '').trim() !== '';

  const label = !labelled ? null : hw ? (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '9px' }}>
      <span
        style={{
          fontFamily: ctx.T.mono,
          fontSize: '10px',
          letterSpacing: '.1em',
          color: C.blue,
          whiteSpace: 'nowrap',
        }}
      >
        {'┌ ' + String(band.label).toUpperCase()}
      </span>
      <span
        style={{
          flex: 1,
          height: '1px',
          background: `linear-gradient(90deg,${alpha(C.blue, 0.333)},transparent)`,
        }}
      />
      <span
        style={{
          fontFamily: ctx.T.mono,
          fontSize: '9.5px',
          color: C.dimmer,
          whiteSpace: 'nowrap',
        }}
      >
        {band.time}
      </span>
    </div>
  ) : (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
      <span
        style={{
          width: '7px',
          height: '7px',
          borderRadius: '50%',
          background: C.horizon,
          boxShadow: `0 0 6px ${alpha(C.horizon, 0.667)}`,
          flex: '0 0 auto',
        }}
      />
      <span
        style={{
          fontSize: '11px',
          fontWeight: 600,
          color: C.horizon,
          textTransform: 'uppercase',
          letterSpacing: '.07em',
        }}
      >
        {band.label}
      </span>
      <span style={{ fontSize: '10px', color: C.dimmer }}>{band.time}</span>
    </div>
  );

  /**
   * A2 — WHERE THINGS GO, DRAWN IN THE PLAN. While a placement is in flight the band renders its
   * rows interleaved with landing slots, one at every legal position. Transcribed in mechanism
   * from the old surface's `renderBlockPlacement` (`docs/overlay_daily.html:2797`); the slot's
   * own appearance is v4 grammar, see `PlaceTarget`.
   *
   * Slots appear ABOVE the moving row as readily as below it. That is what makes the bilateral
   * move visible without naming a direction in words.
   */
  const placing = placementFor(ctx);
  const slots = placing.movingId ? slotsInBand(placing, bandIndex) : [];
  const slotsBefore = (ii: number) =>
    slots
      .filter((d) => d.beforeIndex === ii)
      .map((d) => (
        <PlaceTarget
          key={'slot-' + d.key}
          ctx={ctx}
          dest={d}
          dropping={!!planDrag.id}
          onPick={(dd) => ctx.moveItem(placing.movingId!, dd.target)}
        />
      ));

  const body = (
    <>
      {label}
      {band.items.map((it, ii) => (
        <div key={bandIndex + '-' + ii}>
          {slotsBefore(ii)}
          <PlanEntry
            ctx={ctx}
            item={it}
            entryKey={bandIndex + '-' + ii}
            showProj
            bandIndex={bandIndex}
            itemIndex={ii}
          />
        </div>
      ))}
      {/* The slot below the last row — a real destination, and the one an "after the last thing"
          move lands in. */}
      {slotsBefore(band.items.length)}
    </>
  );

  if (hw) {
    return (
      <div
        style={{
          margin: '10px 12px',
          padding: '11px 13px 8px',
          border: '1px solid ' + C.border,
          borderLeft: '2px solid ' + C.blue,
          borderRadius: ctx.T.r.card,
          background: C.panel,
          boxShadow: bevel(ctx.T),
        }}
      >
        {body}
      </div>
    );
  }
  return <div style={{ padding: '11px 14px 10px', borderBottom: '1px solid ' + C.hair }}>{body}</div>;
}
