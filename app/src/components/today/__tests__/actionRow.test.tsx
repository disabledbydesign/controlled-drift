/**
 * THE TODAY ACTION ROW — which button asks the server for what, and what she sees while it runs.
 *
 * Four of these buttons used to be `flash()` and nothing else: "Regenerating plan…", "Trimmed to
 * one small win", "Showing quick wins" and "Let's break it down" all described a plan change
 * that never happened. The wire-in is `useAppState.regenerate`, tested for its 202-and-poll
 * behaviour in `shell/__tests__/regenerate.test.tsx`; what is tested HERE is that each button
 * asks for the right thing, and that the row shows work in progress rather than looking idle.
 *
 * Every assertion is POSITIVE — it names the request that must be issued. "Did not call flash"
 * would pass against a button wired to nothing at all.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit or renders accumulate
 * and every `getByText` finds several.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { TodayPanel } from '../TodayPanel.tsx';
import { ctxWith } from './ctxFactory.tsx';

afterEach(cleanup);

describe('each generation button asks the server for what it says', () => {
  it('“↻ Fresh plan” asks for a fresh generation', () => {
    const { ctx, regenerate } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText('↻ Fresh plan'));

    expect(regenerate).toHaveBeenCalledWith({ kind: 'refresh' }, '↻ Fresh plan');
  });

  /**
   * ⚠ The ids are the SERVER's — `plan_store._DEFAULT_ACTIONS['presets']`, confirmed against her
   * live `~/.controlled-drift/actions.json`. An id the server does not hold answers 400
   * (`server.py:927`), so this test is the thing standing between a typo and a dead button.
   */
  it.each([
    ['Low energy today', 'low-energy'],
    ['Quick wins only', 'quick-wins'],
    ['I’m stuck', 'stuck'],
  ])('“%s” asks for the %s preset', (label, presetId) => {
    const { ctx, regenerate } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText(label));

    expect(regenerate).toHaveBeenCalledWith({ kind: 'preset', presetId }, label);
  });

  it('“Add something” still navigates to the Add tab and starts no generation', () => {
    const { ctx, regenerate, goTab } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText('Add something'));

    expect(goTab).toHaveBeenCalledWith('add');
    expect(regenerate).not.toHaveBeenCalled();
  });
});

describe('the row shows the work in progress', () => {
  it('the button that started it says it is regenerating', () => {
    const { ctx } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    // POSITIVE: the in-progress wording is on screen, and the resting label is not.
    expect(screen.getByText('Regenerating…')).toBeTruthy();
    expect(screen.queryByText('↻ Fresh plan')).toBeNull();
  });

  it('a running control cannot be tapped again', () => {
    const { ctx, regenerate } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText('Regenerating…'));

    expect(screen.getByText('Regenerating…').hasAttribute('disabled')).toBe(true);
    expect(regenerate).not.toHaveBeenCalled();
  });

  /**
   * The server takes one generation at a time (`_gen_lock`, `server.py:272`) and answers a
   * second with `started:false`. Holding the other controls means she never sends a request
   * that was never going to run.
   */
  it('the other generation controls are held until it settles', () => {
    const { ctx, regenerate } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    const preset = screen.getByText('Low energy today');
    expect(preset.hasAttribute('disabled')).toBe(true);
    fireEvent.click(preset);
    expect(regenerate).not.toHaveBeenCalled();
  });

  it('“Add something” stays live while a generation runs', () => {
    const { ctx, goTab } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    const add = screen.getByText('Add something');
    expect(add.hasAttribute('disabled')).toBe(false);
    fireEvent.click(add);
    expect(goTab).toHaveBeenCalledWith('add');
  });

  it('nothing is held when no generation is running', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    expect(screen.getByText('↻ Fresh plan').hasAttribute('disabled')).toBe(false);
    expect(screen.getByText('Low energy today').hasAttribute('disabled')).toBe(false);
    expect(screen.queryByText('Regenerating…')).toBeNull();
  });
});
