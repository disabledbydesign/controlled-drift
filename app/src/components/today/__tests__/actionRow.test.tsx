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
   * (`server.py:1017`), so this test is the thing standing between a typo and a dead button.
   *
   * The LABELS are no longer written here. They come from `ctx.presets`, which is her own file
   * read through `GET /api/actions` — see the block below for why.
   */
  it.each([
    ['Low energy today', 'low-energy'],
    ['Quick wins first', 'quick-wins'],
    ["I'm stuck", 'stuck'],
    // Wired 2026-07-18. This one used to `flash()` a claim with no backend behind it; the preset
    // now exists and was confirmed live (202 + a reordered plan).
    ['Life admin & household', 'life-admin'],
  ])('“%s” asks for the %s preset', (label, presetId) => {
    const { ctx, regenerate } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText(label));

    expect(regenerate).toHaveBeenCalledWith({ kind: 'preset', presetId }, label);
  });
});

/*
 * THE BUTTON LABELS ARE HERS, NOT THE APP'S.
 *
 * These four labels were hardcoded in `TodayPanel`, and had already drifted from what she
 * stores: her `quick-wins` preset reads "Quick wins first"; the button read "Quick wins only".
 * She was asked which was correct and the question was withdrawn — it is the wrong question.
 * Editing the string would leave the drift free to reappear on her next edit. The button
 * reading its label from her file is what removes the class.
 *
 * ⚠ Every assertion below holds LABEL and ID apart. The label is display and hers to change;
 * the id is the wire contract and must survive her changing it.
 */
describe('the action row renders her own presets', () => {
  const mine = [
    { id: 'low-energy', label: 'Low energy today' },
    { id: 'quick-wins', label: 'Quick wins first' },
  ];

  it('shows the labels her file holds, not any the app carries', () => {
    const { ctx } = ctxWith({}, undefined, null, false, mine);
    render(<TodayPanel ctx={ctx} />);
    expect(screen.getByText('Quick wins first')).toBeTruthy();
  });

  it('follows her file when she renames a button, keeping the id it dispatches on', () => {
    const renamed = [{ id: 'quick-wins', label: 'Short things first' }];
    const { ctx, regenerate } = ctxWith({}, undefined, null, false, renamed);
    render(<TodayPanel ctx={ctx} />);

    fireEvent.click(screen.getByText('Short things first'));

    // Her word on screen; the server's id on the wire.
    expect(regenerate).toHaveBeenCalledWith(
      { kind: 'preset', presetId: 'quick-wins' },
      'Short things first',
    );
  });

  it('grows and shrinks with her file — a preset she adds gets a button', () => {
    const withNew = [...mine, { id: 'errands', label: 'Errands only' }];
    const { ctx } = ctxWith({}, undefined, null, false, withNew);
    render(<TodayPanel ctx={ctx} />);

    const row = screen.getByText('↻ Fresh plan').parentElement!;
    expect([...row.querySelectorAll('button')].map((b) => b.textContent)).toEqual([
      '↻ Fresh plan',
      'Low energy today',
      'Quick wins first',
      'Errands only',
      'Move this later',
    ]);
  });

  /*
   * When her presets could not be read, the row shows the controls that need no file and
   * NOTHING ELSE. A remembered set of labels would be the defect returning: a button claiming
   * to be hers while standing for a preset the server may no longer hold.
   */
  it('offers no preset buttons at all when her file could not be read', () => {
    const { ctx } = ctxWith({}, undefined, null, false, []);
    render(<TodayPanel ctx={ctx} />);

    const row = screen.getByText('↻ Fresh plan').parentElement!;
    expect([...row.querySelectorAll('button')].map((b) => b.textContent)).toEqual([
      '↻ Fresh plan',
      'Move this later',
    ]);
  });

  /**
   * "Add something" was removed from this row on June's direction (2026-07-18) — it is navigation
   * among plan actions, and the tab bar already reaches the Add tab.
   *
   * The assertion is positive about the row's CONTENTS: these five are what the row offers. A bare
   * `queryByText('Add something') === null` would also pass against a row that rendered nothing at
   * all, which is the failure this test has to be able to see.
   */
  it('the action row offers exactly the six plan actions, and no Add button', () => {
    const { ctx } = ctxWith();
    const { container } = render(<TodayPanel ctx={ctx} />);

    const row = screen.getByText('↻ Fresh plan').parentElement!;
    const labels = [...row.querySelectorAll('button')].map((b) => b.textContent);
    // The four in the middle are her file's, in her file's order — see the preset block below.
    expect(labels).toEqual([
      '↻ Fresh plan',
      'Low energy today',
      'Quick wins first',
      "I'm stuck",
      'Life admin & household',
      'Move this later',
    ]);
    // And the label is nowhere else on the Today tab either.
    expect(container.textContent).not.toContain('Add something');
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

  /**
   * The hold is on the GENERATION controls only. "Move this later" starts no generation, so the
   * server's one-at-a-time lock has nothing to do with it and it stays tappable.
   */
  it('“Move this later” stays live while a generation runs', () => {
    const { ctx, notice } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    const move = screen.getByText('Move this later');
    expect(move.hasAttribute('disabled')).toBe(false);
    fireEvent.click(move);
    /**
     * Through `notice`, not `flash`. This button's ONLY job is to say this sentence, and through
     * `flash` the sentence rendered nowhere — so the button was a control that visibly did
     * nothing at all, while this test passed.
     */
    expect(notice).toHaveBeenCalledWith('Pick an item to move');
  });

  it('“Life admin & household” is held with the other generation controls', () => {
    const { ctx, regenerate } = ctxWith({}, undefined, '↻ Fresh plan');
    render(<TodayPanel ctx={ctx} />);

    const preset = screen.getByText('Life admin & household');
    expect(preset.hasAttribute('disabled')).toBe(true);
    fireEvent.click(preset);
    expect(regenerate).not.toHaveBeenCalled();
  });

  it('nothing is held when no generation is running', () => {
    const { ctx } = ctxWith();
    render(<TodayPanel ctx={ctx} />);

    expect(screen.getByText('↻ Fresh plan').hasAttribute('disabled')).toBe(false);
    expect(screen.getByText('Low energy today').hasAttribute('disabled')).toBe(false);
    expect(screen.queryByText('Regenerating…')).toBeNull();
  });
});
