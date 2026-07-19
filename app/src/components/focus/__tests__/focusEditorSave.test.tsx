/**
 * THE TWO CONTROLS ON THE FOCUS EDITOR, AND WHAT THEY MUST ACTUALLY CALL.
 *
 * Both were wired to nothing that leaves the browser:
 *
 *   "Structure this →"  ran `formFromDraft`, a client-side stand-in with two hardcoded dates,
 *                       and then showed its output under the heading "Here's what I heard".
 *   "Save changes"      ran `saveFocus`, a pure local state change, and raised
 *                       "Focus period updated" over nothing. Every field died on reload.
 *
 * These tests drive the rendered buttons and assert on the calls that must go out, POSITIVELY.
 * A test that only asserted "no wrong write happened" would pass against a button wired to
 * nothing at all — which is the exact state this file exists to leave behind.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { themes } from '@tokens';
import { FocusEditor } from '../FocusEditor.tsx';
import type { FocusCtx, FocusUi } from '../types.ts';
import type { FocusForm } from '../../../model/index.ts';

afterEach(cleanup);

const FORM: FocusForm = {
  name: 'Jobs week',
  start: '2026-07-20',
  end: '2026-07-26',
  intent: 'jobs first this week',
  front: [],
  note: '',
  availStart: '',
  availEnd: '',
  daysOff: [],
  daysOn: '',
  output: 'Auto',
  workdayStart: '',
  workdayEnd: '',
  paused: [],
};

const UI: FocusUi = {
  focusView: 'edit',
  focusEditId: 'fp-1',
  focusReflect: FORM,
  focusDraft: '',
  focusNewOff: '',
  focusPickFront: '',
  focusPickPaused: '',
};

function ctxWith(ui: Partial<FocusUi>, overrides: Partial<FocusCtx> = {}) {
  const saveFocusPeriod = vi.fn().mockResolvedValue(true);
  const authorFocus = vi.fn().mockResolvedValue(FORM);
  const closeEditor = vi.fn();
  const up = vi.fn();
  const ctx = {
    T: themes.celestial,
    graph: { roots: [], strategies: [], orphans: {} },
    periods: [],
    ui: { ...UI, ...ui },
    up,
    applyPeriods: vi.fn(),
    openEditor: vi.fn(),
    closeEditor,
    saveFocusPeriod,
    authorFocus,
    ...overrides,
  } as unknown as FocusCtx;
  return { ctx, saveFocusPeriod, authorFocus, closeEditor, up };
}

describe('Save changes writes the period to the server', () => {
  it('calls the write with the edited period’s id and the whole form', async () => {
    const { ctx, saveFocusPeriod } = ctxWith({ focusView: 'edit', focusEditId: 'fp-1' });
    render(<FocusEditor ctx={ctx} view="edit" />);

    fireEvent.click(screen.getByText('Save changes'));

    await waitFor(() => expect(saveFocusPeriod).toHaveBeenCalledWith('edit', 'fp-1', FORM));
  });

  it('closes the editor once the write has landed', async () => {
    const { ctx, closeEditor } = ctxWith({ focusView: 'edit' });
    render(<FocusEditor ctx={ctx} view="edit" />);

    fireEvent.click(screen.getByText('Save changes'));

    await waitFor(() => expect(closeEditor).toHaveBeenCalled());
  });

  /**
   * THE ONE THAT MATTERS MOST. When the server refuses ("you have not put an end date in yet")
   * the editor must STAY OPEN holding her work. Closing would discard the whole form — the
   * refusal notice would name a field on a screen she can no longer reach.
   */
  it('keeps the editor open, holding her work, when the write did not land', async () => {
    const saveFocusPeriod = vi.fn().mockResolvedValue(false);
    const { ctx, closeEditor } = ctxWith({ focusView: 'edit' }, { saveFocusPeriod } as never);
    render(<FocusEditor ctx={ctx} view="edit" />);

    fireEvent.click(screen.getByText('Save changes'));

    await waitFor(() => expect(saveFocusPeriod).toHaveBeenCalled());
    expect(closeEditor).not.toHaveBeenCalled();
    // Positive form: her form is still on screen.
    expect(screen.getByDisplayValue('Jobs week')).toBeTruthy();
  });

  it('sends a NEW period down the author path, with no period id', async () => {
    const { ctx, saveFocusPeriod } = ctxWith({ focusView: 'author', focusEditId: null });
    render(<FocusEditor ctx={ctx} view="author" />);

    fireEvent.click(screen.getByText('Looks right — save'));

    await waitFor(() => expect(saveFocusPeriod).toHaveBeenCalledWith('author', null, FORM));
  });
});

describe('Structure this sends her words to the model', () => {
  it('hands the draft to the structure step', async () => {
    const { ctx, authorFocus } = ctxWith({
      focusView: 'author',
      focusReflect: null,
      focusDraft: 'jobs first this week, caregiving from Saturday',
    });
    render(<FocusEditor ctx={ctx} view="author" />);

    fireEvent.click(screen.getByText('Structure this →'));

    await waitFor(() =>
      expect(authorFocus).toHaveBeenCalledWith('jobs first this week, caregiving from Saturday'),
    );
  });

  it('shows her the form the model produced', async () => {
    const { ctx, up } = ctxWith({
      focusView: 'author',
      focusReflect: null,
      focusDraft: 'jobs first this week',
    });
    render(<FocusEditor ctx={ctx} view="author" />);

    fireEvent.click(screen.getByText('Structure this →'));

    await waitFor(() => expect(up).toHaveBeenCalledWith({ focusReflect: FORM }));
  });

  /**
   * When nothing came back, the "Here's what I heard" screen must NOT open. A form of blanks —
   * or worse, one the client filled in itself — under that heading is the fabrication this whole
   * change removes.
   */
  it('does not open the read-back screen when the model produced nothing', async () => {
    const authorFocus = vi.fn().mockResolvedValue(null);
    const { ctx, up } = ctxWith(
      { focusView: 'author', focusReflect: null, focusDraft: 'jobs first' },
      { authorFocus } as never,
    );
    render(<FocusEditor ctx={ctx} view="author" />);

    fireEvent.click(screen.getByText('Structure this →'));

    await waitFor(() => expect(authorFocus).toHaveBeenCalled());
    expect(up).not.toHaveBeenCalledWith(expect.objectContaining({ focusReflect: expect.anything() }));
    // Positive form: she is still on the screen with her words, able to try again.
    expect(screen.getByText('Structure this →')).toBeTruthy();
  });

  it('does not call the model for an empty draft', async () => {
    const { ctx, authorFocus } = ctxWith({
      focusView: 'author',
      focusReflect: null,
      focusDraft: '   ',
    });
    render(<FocusEditor ctx={ctx} view="author" />);

    fireEvent.click(screen.getByText('Structure this →'));

    expect(authorFocus).not.toHaveBeenCalled();
  });
});
