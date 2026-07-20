/**
 * The AUTHOR flow now ends on the verification surface, not on a bare form.
 *
 * `FocusEditor`'s author path used to drop her straight into the same editable form the edit
 * route shows, headed "Here's what I heard" — a heading that had already outlived the thing that
 * made it a lie (`formFromDraft`'s hardcoded dates, deleted in 87185ba) but still gave her no
 * itemised statement of what the model actually understood. `POST /api/focus/reflect` produces
 * exactly that statement and nothing called it.
 *
 * ⚠ THE EDIT ROUTE IS UNCHANGED. Opening an existing period is not a read-back of anything a
 * model just did — there is no comprehension to check — so it keeps the full form.
 *
 * ⚠ NO SPOKEN-REVISION CONTROL. June retired it on 2026-07-19 ("Now that i can just edit in
 * text"). One test below asserts positively that no such control appears, because an unwired
 * button that looks live is worse than an absent one.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { FocusEditor } from '../FocusEditor.tsx';
import { focusCtxWith, BASE_AUTHORED_FORM } from './harness.ts';

vi.mock('../../../api/focus.ts', async () => {
  const real = await vi.importActual<typeof import('../../../api/focus.ts')>(
    '../../../api/focus.ts',
  );
  return { ...real, reflectFields: vi.fn() };
});

import { reflectFields } from '../../../api/focus.ts';

const reflectMock = vi.mocked(reflectFields);

const PAYLOAD = {
  summary: 'Job search week',
  items: [
    { key: 'dates', label: 'Dates', edit: 'daterange', display: 'Mon Aug 3 – Sun Aug 9' },
    { key: 'intent', label: 'Intent', edit: 'text', display: 'jobs first this week' },
  ],
  blocking: [] as string[],
};

afterEach(cleanup);
beforeEach(() => {
  reflectMock.mockReset();
  reflectMock.mockResolvedValue({ ok: true, status: 200, data: PAYLOAD } as never);
});

describe('the author flow lands on the read-back', () => {
  it('shows the SERVER’s itemised read-back once the structure step has produced a form', async () => {
    const { ctx } = focusCtxWith({ focusReflect: { ...BASE_AUTHORED_FORM } });
    render(<FocusEditor ctx={ctx} view="author" />);

    expect(await screen.findByText('Mon Aug 3 – Sun Aug 9')).toBeTruthy();
    expect(reflectMock).toHaveBeenCalled();
  });

  it('saves through the same writer the form used, so the write path is unchanged', async () => {
    const { ctx, saveFocusPeriod } = focusCtxWith({ focusReflect: { ...BASE_AUTHORED_FORM } });
    render(<FocusEditor ctx={ctx} view="author" />);
    await screen.findByText('Job search week');

    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(saveFocusPeriod).toHaveBeenCalledTimes(1));
    expect(saveFocusPeriod.mock.calls[0]![0]).toBe('author');
  });

  it('offers a way to reach the fields the read-back does not itemise, such as the name', async () => {
    const { ctx } = focusCtxWith({ focusReflect: { ...BASE_AUTHORED_FORM } });
    render(<FocusEditor ctx={ctx} view="author" />);
    await screen.findByText('Job search week');

    fireEvent.click(screen.getByRole('button', { name: /every field/i }));

    expect(screen.getByText('Name')).toBeTruthy();
  });

  /** Retired, not deferred — see the header. */
  it('offers NO spoken-revision control', async () => {
    const { ctx } = focusCtxWith({ focusReflect: { ...BASE_AUTHORED_FORM } });
    render(<FocusEditor ctx={ctx} view="author" />);
    await screen.findByText('Job search week');

    expect(screen.queryByText(/say it again|revise by voice|re-record/i)).toBeNull();
  });
});

describe('the edit route is untouched', () => {
  it('still shows the full form, and asks for no read-back', async () => {
    const { ctx } = focusCtxWith({ focusReflect: { ...BASE_AUTHORED_FORM } });
    render(<FocusEditor ctx={ctx} view="edit" />);

    expect(screen.getByText('Edit focus period')).toBeTruthy();
    expect(screen.getByText('Name')).toBeTruthy();
    expect(reflectMock).not.toHaveBeenCalled();
  });
});
