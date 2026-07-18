import type { PlanBreakItem } from '../../fixtures/index.ts';
import type { TodayCtx } from './types.ts';

export interface InterstitialProps {
  ctx: TodayCtx;
  item: PlanBreakItem;
}

/**
 * v4 `interstitial(it,key)` (~1068) — a break in the plan (lunch, a real stop).
 *
 * Not checkoffable and carries no id: the empty 15px span in front stands where the checkbox
 * would be, so the time column still lines up with the task rows above and below it.
 * The time itself is at `opacity:.5` — dimmer than any other time in the plan, because a
 * break is not something to be on time for.
 */
export function Interstitial({ ctx, item }: InterstitialProps) {
  const C = ctx.T.c;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '7px',
        padding: '3px 0',
        marginTop: '6px',
      }}
    >
      <span style={{ width: '15px', flex: '0 0 auto' }} />
      <span
        style={{
          width: '56px',
          flex: '0 0 auto',
          fontSize: '10px',
          color: C.dimmer,
          opacity: 0.5,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {item.time}
      </span>
      <span style={{ fontSize: '13px', fontWeight: 600, color: C.dim }}>{item.task}</span>
    </div>
  );
}
