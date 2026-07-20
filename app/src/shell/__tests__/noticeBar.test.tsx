/**
 * How a NOTICE renders, as distinct from a failure.
 *
 * `SignalBar` chose between its two bars on `persist` alone. A notice persists — so without this
 * split it renders as the failure bar: red, `role="alert"`, a `!` glyph. That would tell June
 * something had broken when what actually happened is that she has not typed an end date yet.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { SignalBar } from '../SignalBar.tsx';
import { themes } from '@tokens';
import type { Signal } from '../signals.ts';

// `vite.config` sets `globals:false`, so cleanup is explicit or renders accumulate.
afterEach(cleanup);

const T = themes.celestial;

function bar(sig: Signal) {
  return render(<SignalBar T={T} sig={sig} onDismiss={vi.fn()} />);
}

const notice: Signal = {
  kind: 'notice',
  msg: 'Add the end date, then save.',
  seq: 1,
  nodeId: null,
  hold: true,
};
/** A REFUSAL — the same kind, but with a control behind it that has already told the truth. */
const refusal: Signal = {
  kind: 'notice',
  msg: 'That needs to be a number of minutes above zero.',
  seq: 2,
  nodeId: 't1',
};
const failure: Signal = { kind: 'failure', msg: 'That did NOT save.', seq: 1, nodeId: null };

describe('SignalBar — a notice is not dressed as a breakage', () => {
  it('shows the notice text', () => {
    bar(notice);
    expect(screen.getByText('Add the end date, then save.')).toBeTruthy();
  });

  /** Marked as its own kind, so the surface (and these tests) can tell the two bars apart. */
  it('marks a notice as a notice', () => {
    const { container } = bar(notice);
    expect(container.querySelector('[data-signal="notice"]')).toBeTruthy();
  });

  it('does not render a notice as the failure bar', () => {
    const { container } = bar(notice);
    expect(container.querySelector('[data-signal="failure"]')).toBeNull();
  });

  /**
   * A screen reader should NOT interrupt for a notice — `role="status"` announces politely at
   * the next pause, `role="alert"` cuts in. Nothing is wrong; she is being told what is next.
   */
  it('announces a notice politely rather than interrupting', () => {
    bar(notice);
    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('still renders a real failure as the failure bar', () => {
    const { container } = bar(failure);
    expect(container.querySelector('[data-signal="failure"]')).toBeTruthy();
    expect(screen.getByRole('alert')).toBeTruthy();
  });

  it('lets her dismiss a notice', () => {
    bar(notice);
    expect(screen.getByLabelText('dismiss')).toBeTruthy();
  });
});

/**
 * ── THE 2026-07-20 FIX, RENDERED ────────────────────────────────────────────
 * A refusal used to travel as a success with no node and render NOWHERE — so a refused save and
 * a successful one looked identical on screen. These assert the two halves of what she asked
 * for: she can READ it, and it goes away by itself once read.
 */
describe('SignalBar — a refusal is read, then leaves', () => {
  it('puts the refusal on screen where she can read it', () => {
    bar(refusal);
    expect(screen.getByText('That needs to be a number of minutes above zero.')).toBeTruthy();
  });

  /** Not the failure bar: nothing broke, and nothing of hers was lost. */
  it('does not dress a refusal as a breakage', () => {
    const { container } = bar(refusal);
    expect(container.querySelector('[data-signal="notice"]')).toBeTruthy();
    expect(screen.getByRole('status')).toBeTruthy();
  });

  /**
   * It fades on its own after long enough to read a sentence — and NOT before. Both bounds are
   * asserted: an autofade that fires too early is the 900ms success timing all over again, which
   * is the thing she cannot read.
   */
  it('dismisses itself after a readable dwell, and not before', () => {
    vi.useFakeTimers();
    try {
      const onDismiss = vi.fn();
      render(<SignalBar T={T} sig={refusal} onDismiss={onDismiss} />);
      vi.advanceTimersByTime(3500);
      expect(onDismiss).not.toHaveBeenCalled();
      vi.advanceTimersByTime(2500);
      expect(onDismiss).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  /** The period notice keeps the opposite promise: nothing on screen carries it, so it stays. */
  it('leaves a holding notice up until she dismisses it herself', () => {
    vi.useFakeTimers();
    try {
      const onDismiss = vi.fn();
      render(<SignalBar T={T} sig={notice} onDismiss={onDismiss} />);
      vi.advanceTimersByTime(60000);
      expect(onDismiss).not.toHaveBeenCalled();
      expect(screen.getByText('Add the end date, then save.')).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });
});
