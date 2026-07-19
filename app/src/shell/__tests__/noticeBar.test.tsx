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

const notice: Signal = { kind: 'notice', msg: 'Add the end date, then save.', seq: 1, nodeId: null };
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
