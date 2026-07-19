/**
 * Task 4 — the rendered view follows the PLAN's shape, not a mockup default.
 *
 * `TodayPanel` used to read `ctx.ui.todayShape || 'schedule'` and never consult `plan.shape`.
 * v4's fixture was always clock-shaped, so the default was invisible in tests and shipped a
 * real fragmented day into the clock-schedule branch.
 *
 * ⚠ `today.test.tsx`'s toggle test does NOT cover this: its fixture is `seedPlan`, whose
 * `shape` is `'schedule'`, so it keeps passing through the old path either way.
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never
 * registers — `afterEach(cleanup)` is explicit or renders accumulate and `getByText` finds
 * several.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { Plan } from '../../../fixtures/index.ts';
import { TodayPanel } from '../TodayPanel.tsx';
import { ctxWith, freshPlan } from './ctxFactory.tsx';

afterEach(cleanup);

/** The seed plan re-shaped as the server sends a fragmented day: no bands, a real header. */
function priorityPlan(header = "Today's fragmented — start at the top when you get a window."): Plan {
  const p = freshPlan();
  p.shape = 'priority';
  p.header = header;
  return p;
}

describe('Task 4 — the plan decides the shape', () => {
  it('renders the priority list on a priority plan even when the stored view is Schedule', () => {
    // The defect exactly: stored UI says 'schedule', the plan says 'priority'. The plan wins.
    const { ctx } = ctxWith({ todayShape: 'schedule' }, priorityPlan());
    render(<TodayPanel ctx={ctx} />);
    // Positive markers of the priority list: a numbered gutter and its reorder controls.
    expect(screen.getByText('1.')).toBeTruthy();
    expect(screen.getByText('2.')).toBeTruthy();
    expect(screen.getAllByText('▲').length).toBeGreaterThan(0);
    // And positively NOT the clock view: no band card headings, no clock times.
    expect(screen.queryByText('Morning')).toBeNull();
    expect(screen.queryByText('9:00 – 12:00')).toBeNull();
  });

  it('still offers both toggle segments on a schedule plan', () => {
    const { ctx } = ctxWith(); // seedPlan — shape 'schedule'
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('View')).toBeTruthy();
    expect(screen.getByText('Schedule')).toBeTruthy();
    expect(screen.getByText('Priority')).toBeTruthy();
    // The clock view is what a schedule plan renders by default.
    expect(screen.getByText('Morning')).toBeTruthy();
  });

  it("shows the server's own header line, and drops the View label that headed the control", () => {
    const reason = "Today's fragmented — start at the top when you get a window.";
    const { ctx } = ctxWith({}, priorityPlan(reason));
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText(reason)).toBeTruthy();
    // The label heads a control. With the segments gone it would head a sentence.
    expect(screen.queryByText('View')).toBeNull();
    expect(screen.queryByText('Schedule')).toBeNull();
    expect(screen.queryByText('Priority')).toBeNull();
  });

  it('states the point once — the list drops its own lead line while the header is shown', () => {
    const { ctx } = ctxWith({}, priorityPlan());
    render(<TodayPanel ctx={ctx} />);
    expect(screen.queryByText(/No clock times/)).toBeNull();
    // The list itself is still there — the line went, not the view.
    expect(screen.getByText('1.')).toBeTruthy();
  });

  it('renders no reason line at all when the header is empty, and keeps the list lead', () => {
    const { ctx } = ctxWith({}, priorityPlan(''));
    const { container } = render(<TodayPanel ctx={ctx} />);
    // Nothing is composed locally to fill the gap: the row that would have held the reason
    // holds nothing.
    const row = container.querySelector('div[style*="padding: 6px 14px 2px"]');
    expect(row).toBeTruthy();
    expect(row!.textContent).toBe('');
    // With no header above it, the list's own lead is the only statement — so it stays.
    expect(screen.getByText(/No clock times/)).toBeTruthy();
  });
});
