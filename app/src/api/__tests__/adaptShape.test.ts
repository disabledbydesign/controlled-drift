/**
 * The plan's SHAPE and the REASON for that shape, as they cross the wire.
 *
 * Both assertions here exist because the app must not compose the reason itself.
 * `scripts/focus_period.py::resolve_output_shape` reaches `priority` by more than one path — an
 * explicit `Output format` of "Priority list" OR `Auto` plus today falling inside the
 * availability window — so any sentence the client writes locally would, on some days, state a
 * cause that is not the cause. The server already sends the true per-day line in `header`.
 */

import { describe, expect, it } from 'vitest';
import { planFromLive } from '../adapt.ts';
import type { LivePlan } from '../adapt.ts';

const LIVE_PRIORITY = {
  shape: 'priority',
  header: "Today's fragmented—start at the top when you get a window.",
  woven_frame: 'w',
  items: [{ project: 'household', task: 'Do the dishes', id: 'bafy-dishes' }],
} as unknown as LivePlan;

describe('planFromLive — shape and reason', () => {
  it('carries the server-generated header, which is the only honest reason for the shape', () => {
    expect(planFromLive(LIVE_PRIORITY).header).toBe(
      "Today's fragmented—start at the top when you get a window.",
    );
  });

  it('keeps priority items inside the container band, where arc addressing works', () => {
    const p = planFromLive(LIVE_PRIORITY);
    expect(p.shape).toBe('priority');
    expect(p.blocks.length).toBe(1); // the container band — NOT a label she reads
    expect(p.blocks[0]!.items.length).toBe(1);
  });

  it('answers a missing header with an empty string, never the word "undefined"', () => {
    // A plan whose generator produced no header line must render nothing, not a literal
    // "undefined" on her main surface — the fabricated-content class this surface is being
    // cleaned of.
    expect(planFromLive({ shape: 'priority', items: [] }).header).toBe('');
  });
});
