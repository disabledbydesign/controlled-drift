/**
 * THE VERIFICATION SURFACE — she sees what the model made of her words, and can fix it.
 *
 * ── why this screen exists, and what it replaced ─────────────────────────────
 * `POST /api/focus/reflect` has been built, specified and reachable for some time, and NOTHING
 * CALLED IT: `reflectFields` in `api/focus.ts` had no caller anywhere in the app. So after the
 * structure step ran, June dropped straight into an editable form with no itemised statement of
 * what the model had actually understood.
 *
 * The screen before that was worse: headed "Here's what I heard", it read back two HARDCODED
 * dates and her own sentence cut at the first comma, with no model having run at all
 * (`formFromDraft`, deleted in 87185ba). So the bar here is not a reassuring summary. It is:
 * show her exactly what the server produced, and let her change it.
 *
 * ⚠ EVERY DISPLAYED VALUE IN THESE TESTS COMES OFF THE SERVER PAYLOAD. Nothing is composed
 * client-side — that is the whole property under test, and the reason the assertions check the
 * server's own `display` strings (`Mon Jul 20`, `weekends (default)`) rather than anything this
 * app could have formatted itself.
 *
 * ⚠ `blocking` IS NOT AN ERROR. A missing end date means she has not filled it in yet. It must
 * not travel the error channel, must not be logged as breakage, and must not address her as
 * though something went wrong. See `api/focus.ts`'s three-outcome header.
 *
 * The payloads below were captured from the LIVE endpoint on 2026-07-19 (`curl -X POST
 * localhost:5050/api/focus/reflect`), not written from the docstring.
 *
 * `vite.config` sets `globals: false` — `afterEach(cleanup)` is explicit or renders accumulate.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { FocusReflect } from '../FocusReflect.tsx';
import { focusCtxWith, BASE_AUTHORED_FORM } from './harness.ts';

vi.mock('../../../api/focus.ts', async () => {
  const real = await vi.importActual<typeof import('../../../api/focus.ts')>(
    '../../../api/focus.ts',
  );
  return { ...real, reflectFields: vi.fn() };
});

import { reflectFields } from '../../../api/focus.ts';

const reflectMock = vi.mocked(reflectFields);

/** The live payload, verbatim from the running server. */
const PAYLOAD = {
  summary: 'Jobs week',
  items: [
    { key: 'foreground', label: 'In front', edit: 'projects', display: 'Job search' },
    { key: 'dates', label: 'Dates', edit: 'daterange', display: 'Mon Jul 20' },
    { key: 'availability', label: 'Availability window', edit: 'daterange', display: 'none' },
    { key: 'days_off', label: 'Days off', edit: 'dates', display: 'weekends (default)' },
    { key: 'output_format', label: 'Plan shape', edit: 'select', display: 'Auto' },
    { key: 'intent', label: 'Intent', edit: 'text', display: 'jobs first' },
    { key: 'paused', label: 'Paused', edit: 'projects', display: 'Reading' },
    { key: 'workday_end', label: 'Working until', edit: 'text', display: '18:00' },
    { key: 'reactivate_tasks', label: 'Reopening', edit: 'text', display: 'dishes, recycling' },
  ],
  blocking: [] as string[],
};

function ok(payload: unknown = PAYLOAD) {
  return { ok: true as const, status: 200, data: payload };
}

afterEach(cleanup);
beforeEach(() => {
  reflectMock.mockReset();
  reflectMock.mockResolvedValue(ok() as never);
});

function form(over: Partial<typeof BASE_AUTHORED_FORM> = {}) {
  return { ...BASE_AUTHORED_FORM, ...over };
}

function mount(over: Partial<typeof BASE_AUTHORED_FORM> = {}, onSave = vi.fn()) {
  const { ctx } = focusCtxWith();
  const setF = vi.fn();
  render(<FocusReflect ctx={ctx} form={form(over)} setF={setF} onSave={onSave} />);
  return { ctx, setF, onSave };
}

describe('it shows what the SERVER produced', () => {
  it('asks the server for the read-back, sending the structured fields', async () => {
    mount();
    await waitFor(() => expect(reflectMock).toHaveBeenCalledTimes(1));
    // The server's own key names, not the app's camelCase form keys.
    expect(reflectMock.mock.calls[0]![0]).toMatchObject({ name: 'Job search week' });
  });

  it("renders the server's summary", async () => {
    mount();
    expect(await screen.findByText('Jobs week')).toBeTruthy();
  });

  it('renders every item the payload carried, with its label', async () => {
    mount();
    await screen.findByText('Jobs week');
    for (const it of PAYLOAD.items) {
      expect(screen.getByText(it.label)).toBeTruthy();
    }
  });

  /**
   * The anti-fabrication assertion. `Mon Jul 20` is the SERVER's formatting of a date the model
   * produced; nothing in this app formats a date that way. If this passes while the network is
   * stubbed out, the screen is composing its own read-back again.
   */
  it("shows the server's own formatted values, not values it composed", async () => {
    mount();
    expect(await screen.findByText('Mon Jul 20')).toBeTruthy();
    expect(screen.getByText('weekends (default)')).toBeTruthy();
    expect(screen.getByText('18:00')).toBeTruthy();
  });

  it('re-asks the server after she changes a field, so the read-back stays the server’s', async () => {
    const { ctx } = focusCtxWith();
    const setF = vi.fn();
    const { rerender } = render(
      <FocusReflect ctx={ctx} form={form()} setF={setF} onSave={vi.fn()} />,
    );
    await waitFor(() => expect(reflectMock).toHaveBeenCalledTimes(1));

    rerender(
      <FocusReflect ctx={ctx} form={form({ intent: 'caregiving first' })} setF={setF} onSave={vi.fn()} />,
    );

    await waitFor(() => expect(reflectMock).toHaveBeenCalledTimes(2));
    expect(reflectMock.mock.calls[1]![0]).toMatchObject({ intent: 'caregiving first' });
  });

  /**
   * NO CLIENT-SIDE FALLBACK. If the read-back cannot be loaded, the screen says so. It must not
   * render a summary it made up — that is precisely what was deleted in 87185ba.
   */
  it('says the read-back could not be loaded rather than inventing one', async () => {
    reflectMock.mockResolvedValue({ ok: false, status: 500, error: 'server said no' } as never);
    mount();
    expect(await screen.findByText(/could not be loaded/i)).toBeTruthy();
    expect(screen.queryByText('Jobs week')).toBeNull();
  });
});

describe('each item opens its own editor — not a text box for everything', () => {
  it('opens the DATE controls for the dates item', async () => {
    const { ctx } = focusCtxWith();
    render(<FocusReflect ctx={ctx} form={form()} setF={vi.fn()} onSave={vi.fn()} />);
    await screen.findByText('Mon Jul 20');

    fireEvent.click(screen.getByLabelText('change Dates'));

    expect(screen.getByText('Start')).toBeTruthy();
    expect(screen.getByText('End')).toBeTruthy();
  });

  it('opens the PLAN-SHAPE choices for the output item, not a text box', async () => {
    const { ctx } = focusCtxWith();
    render(<FocusReflect ctx={ctx} form={form()} setF={vi.fn()} onSave={vi.fn()} />);
    await screen.findByText('Jobs week');

    fireEvent.click(screen.getByLabelText('change Plan shape'));

    expect(screen.getByText('Clock schedule')).toBeTruthy();
    expect(screen.getByText('Priority list')).toBeTruthy();
  });

  it('writes a per-field fix back through setF', async () => {
    const { ctx } = focusCtxWith();
    const setF = vi.fn();
    render(<FocusReflect ctx={ctx} form={form()} setF={setF} onSave={vi.fn()} />);
    await screen.findByText('Jobs week');

    fireEvent.click(screen.getByLabelText('change Plan shape'));
    fireEvent.click(screen.getByText('Priority list'));

    expect(setF).toHaveBeenCalledWith('output', 'Priority list');
  });

  it('opens ONE editor at a time', async () => {
    const { ctx } = focusCtxWith();
    render(<FocusReflect ctx={ctx} form={form()} setF={vi.fn()} onSave={vi.fn()} />);
    await screen.findByText('Jobs week');

    fireEvent.click(screen.getByLabelText('change Dates'));
    fireEvent.click(screen.getByLabelText('change Plan shape'));

    expect(screen.queryByText('Start')).toBeNull();
    expect(screen.getByText('Clock schedule')).toBeTruthy();
  });
});

describe('the tasks being turned back on are visible, and removable', () => {
  /**
   * When she says "keep the dishes going", the authoring step returns `reactivate_tasks` and the
   * server turns those tasks back on at write time (commit 4451927). Nothing on screen showed
   * WHICH task was picked, so a wrong match could not be seen, let alone removed, before saving.
   */
  it('names each task that will be reopened', async () => {
    mount({ reactivate: ['dishes', 'recycling'] });
    await screen.findByText('Reopening');
    expect(screen.getByText('dishes')).toBeTruthy();
    expect(screen.getByText('recycling')).toBeTruthy();
  });

  it('removes one without touching the other', async () => {
    const { ctx } = focusCtxWith();
    const setF = vi.fn();
    render(
      <FocusReflect
        ctx={ctx}
        form={form({ reactivate: ['dishes', 'recycling'] })}
        setF={setF}
        onSave={vi.fn()}
      />,
    );
    await screen.findByText('Reopening');

    fireEvent.click(screen.getByLabelText('do not reopen dishes'));

    expect(setF).toHaveBeenCalledWith('reactivate', ['recycling']);
  });
});

describe('a field she has not filled in yet holds the save — and is not an error', () => {
  const BLOCKED = { ...PAYLOAD, blocking: ['end date'] };

  it('names what is still needed', async () => {
    reflectMock.mockResolvedValue(ok(BLOCKED) as never);
    mount();
    expect(await screen.findByText(/end date/)).toBeTruthy();
  });

  it('does not save while something required is still empty', async () => {
    reflectMock.mockResolvedValue(ok(BLOCKED) as never);
    const onSave = vi.fn();
    mount({}, onSave);
    await screen.findByText(/end date/);

    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(onSave).not.toHaveBeenCalled();
  });

  /**
   * ⚠ THE TEST ABOVE ALONE IS NOT ENOUGH, and mutation is what showed it. Deleting the `if
   * (held) return` guard inside the handler left every test green, because the button is also
   * `disabled` and React fires no handler on a disabled button — so the click asserted nothing
   * about the rule. This asserts the mechanism that is actually doing the work, so removing it
   * fails here.
   *
   * The handler's own guard is deliberately kept as well. It cannot be reached through the DOM
   * while `disabled` is set, so no test can cover it; it exists so that a later change removing
   * `disabled` — for a styling reason, say — cannot quietly start saving an incomplete period.
   */
  it('the save control is not available at all while something is missing', async () => {
    reflectMock.mockResolvedValue(ok(BLOCKED) as never);
    mount();
    await screen.findByText(/end date/);

    expect(screen.getByRole('button', { name: /save/i })).toHaveProperty('disabled', true);
  });

  it('the save control IS available once nothing is missing', async () => {
    mount();
    await screen.findByText('Jobs week');

    expect(screen.getByRole('button', { name: /save/i })).toHaveProperty('disabled', false);
  });

  /**
   * The register rule, asserted positively. This is "you have not filled this in yet", never
   * "something went wrong" — and it must not carry the failure words the error channel uses.
   */
  it('says it in the not-yet-filled-in register, not the something-broke one', async () => {
    reflectMock.mockResolvedValue(ok(BLOCKED) as never);
    mount();
    const line = await screen.findByTestId('focus-reflect-blocking');
    expect(line.textContent).toMatch(/still needs/i);
    expect(line.textContent).not.toMatch(/error|failed|problem|invalid|wrong/i);
  });

  it('saves once nothing is missing', async () => {
    const onSave = vi.fn();
    mount({}, onSave);
    await screen.findByText('Jobs week');

    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
