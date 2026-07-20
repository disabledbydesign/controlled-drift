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
 * BAR and must PERSIST, exactly like a failure, while being neither one.
 */

import { describe, expect, it } from 'vitest';
import { present } from '../signals.ts';
import type { Signal } from '../signals.ts';

function sig(kind: Signal['kind'], msg = 'Add the end date, then save.'): Signal {
  return { kind, msg, seq: 1, nodeId: null };
}

describe('present — a notice is its own case', () => {
  /**
   * The load-bearing assertion, stated positively: she must SEE it and it must not vanish
   * before she reads it.
   */
  it('shows a notice in the bar and keeps it there until she dismisses it', () => {
    expect(present(sig('notice'))).toEqual({ mode: 'bar', persist: true, ms: 0 });
  });

  /**
   * The one that stops the collapse this whole task exists to prevent. If a notice ever
   * presented as success it would settle a row inline and disappear in 900ms, and she would
   * be left believing a period saved that the server refused.
   */
  it('does not present a notice the way it presents a success', () => {
    expect(present(sig('notice')).mode).not.toBe(present(sig('success')).mode);
    expect(present(sig('notice')).persist).toBe(true);
  });

  it('still presents a real failure in the persistent bar', () => {
    expect(present(sig('failure'))).toEqual({ mode: 'bar', persist: true, ms: 0 });
  });

  it('still presents a success inline and briefly', () => {
    expect(present(sig('success'))).toEqual({ mode: 'inline', persist: false, ms: 900 });
  });
});