// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * The NOTICE signal — "you have not filled this in yet".
 *
 * ── why a third kind, rather than reusing failure ────────────────────────────
 * `/api/focus/commit` and `/api/focus/update` refuse a period with no start or end date. That
 * refusal is not breakage: nothing fell over, and the period was not lost — she simply has not
 * put a date in yet. Sending it down the failure channel would address her in the register of
 * something having gone wrong (red, alarm, `role="alert"`) and would log it as a defect, which
 * makes the error log useless for finding real ones.
 *
 * Sending it down the SUCCESS channel is worse: success presents `inline` and near-silently,
 * because a successful write is already visible at the control. A refusal is not visible
 * anywhere — if she does not read it, she believes the period saved. So a notice must reach the
 * BAR, while being neither one.
 *
 * ── the second notice, added 2026-07-20 ──────────────────────────────────────
 * A REFUSAL is also a notice — "that needs to be a number of minutes above zero", "this is an
 * appointment at a fixed time, so it does not move". It reaches the bar for the same reason the
 * period notice does: it has to be read. It does NOT persist, and the difference is not a matter
 * of degree. June's ruling: *"if a change can't be made, the UI content needs to show what's
 * really in the data — that's essential."* The control a refusal comes from reverts to the
 * STORED value, so the screen is truthful whether or not the sentence is still up; the sentence
 * explains a truthful screen rather than standing in for one, and may fade.
 *
 * The period notice has no such control behind it — nothing on screen changed — so it holds.
 * `Signal.hold` is what says which of the two a signal is.
 */

import { describe, expect, it } from 'vitest';
import { present } from '../signals.ts';
import type { Signal } from '../signals.ts';

function sig(kind: Signal['kind'], msg = 'Add the end date, then save.'): Signal {
  return { kind, msg, seq: 1, nodeId: null };
}

/** The period notice: nothing on screen carries it, so it holds. */
function held(msg = 'Add the end date, then save.'): Signal {
  return { kind: 'notice', msg, seq: 1, nodeId: null, hold: true };
}

describe('present — a notice is its own case', () => {
  /**
   * The load-bearing assertion, stated positively: she must SEE it and it must not vanish
   * before she reads it.
   */
  it('shows a notice in the bar and keeps it there until she dismisses it', () => {
    expect(present(held())).toEqual({ mode: 'bar', persist: true, ms: 0 });
  });

  /**
   * The one that stops the collapse this whole task exists to prevent. If a notice ever
   * presented as success it would settle a row inline and disappear in 900ms, and she would
   * be left believing a period saved that the server refused.
   */
  it('does not present a notice the way it presents a success', () => {
    expect(present(held()).mode).not.toBe(present(sig('success')).mode);
    expect(present(held()).persist).toBe(true);
  });

  /**
   * THE FIX OF 2026-07-20, stated positively: a refusal is TEXT SHE CAN SEE, in the bar, for
   * long enough to read a sentence.
   *
   * The bug it closes is that a refusal used to travel as a success with no node — `present()`
   * answered `inline`, `useSurface` drops an inline success that has no node to settle on, and
   * the sentence therefore rendered NOWHERE. A refused save and a real one looked identical.
   */
  it('shows a refusal in the bar, where she can read it', () => {
    const p = present(sig('notice', 'That needs to be a number of minutes above zero.'));
    expect(p.mode).toBe('bar');
  });

  /**
   * And it goes away by itself, because the control has already told the truth. Asserted as a
   * real readable duration, not merely as "not the success timing": 900ms is far too short for
   * a sentence, so the number is the requirement, not the inequality.
   */
  it('lets a refusal fade on its own, after long enough to read it', () => {
    const p = present(sig('notice', 'There is nowhere else to put this today.'));
    expect(p.persist).toBe(false);
    expect(p.ms).toBeGreaterThanOrEqual(4000);
    expect(p.ms).toBeLessThanOrEqual(6000);
  });

  it('still presents a real failure in the persistent bar', () => {
    expect(present(sig('failure'))).toEqual({ mode: 'bar', persist: true, ms: 0 });
  });

  it('still presents a success inline and briefly', () => {
    expect(present(sig('success'))).toEqual({ mode: 'inline', persist: false, ms: 900 });
  });
});