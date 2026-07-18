/**
 * Behaviour tests for the focus-period editor (Task 9).
 *
 * These pin the things this port is most likely to get quietly wrong:
 *   1. every spec §17 field renders, including `Workday start` — the one with no backing
 *      property on the live type, and so the one nothing else would catch
 *   2. the PAUSED picker is filtered to pausable projects and the FOREGROUND picker is not
 *   3. Intent survives the round trip byte-for-byte — spec §14/§17, never reworded
 *   4. Back discards the draft silently (v4's behaviour, deliberately preserved)
 *   5. `saveFocus` writes back to the right period in edit mode and appends in author mode
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, within } from '@testing-library/react';
import { formFromPeriod, formFromDraft, saveFocus } from '../../../model/index.ts';
import type { FocusForm } from '../../../model/index.ts';
import { FocusPanel } from '../FocusPanel.tsx';
import { FocusOverlay } from '../FocusOverlay.tsx';
import { focusCtxWith, freshPeriods } from './harness.ts';

afterEach(cleanup);

function periodNamed(id: string) {
  const p = freshPeriods().find((x) => x.id === id);
  if (!p) throw new Error('no fixture period ' + id);
  return p;
}

const NOW = periodNamed('fp-now');

// ── the list ────────────────────────────────────────────────────────────────

describe('FocusPanel — the period list', () => {
  it('renders both sections, the badges and each period', () => {
    const { ctx } = focusCtxWith();
    render(<FocusPanel ctx={ctx} />);
    expect(screen.getByText('Current focus period')).toBeTruthy();
    expect(screen.getByText('coming up')).toBeTruthy();
    expect(screen.getByText('Now')).toBeTruthy();
    expect(screen.getByText('Next')).toBeTruthy();
    expect(screen.getByText(NOW.name)).toBeTruthy();
    expect(screen.getByText('Recovery + admin catch-up')).toBeTruthy();
  });

  it('shows the intent verbatim — no rewording, no truncation', () => {
    const { ctx } = focusCtxWith();
    render(<FocusPanel ctx={ctx} />);
    expect(screen.getByText(NOW.intent)).toBeTruthy();
  });

  it('shows the front chips, the struck-through paused chips and the plan shape', () => {
    const { ctx } = focusCtxWith();
    render(<FocusPanel ctx={ctx} />);
    expect(screen.getByText('Academic positions')).toBeTruthy();
    expect(screen.getByText('Build Controlled Drift')).toBeTruthy();
    expect(screen.getByText('plan: Priority list')).toBeTruthy();
    // v4 renders the availability window and the workday bounds as two small captions.
    expect(screen.getByText(/^free /)).toBeTruthy();
    expect(screen.getByText('day 09:00–17:00')).toBeTruthy();
  });

  it('falls back to plain lines when a section is empty', () => {
    const { ctx } = focusCtxWith({}, []);
    render(<FocusPanel ctx={ctx} />);
    expect(screen.getByText('No focus period set for today.')).toBeTruthy();
    expect(screen.getByText('Nothing scheduled yet.')).toBeTruthy();
  });

  it('Edit opens the edit view with a form copied off that period', () => {
    const { ctx, openEditor } = focusCtxWith();
    render(<FocusPanel ctx={ctx} />);
    fireEvent.click(screen.getAllByText('Edit')[0]!);
    expect(openEditor).toHaveBeenCalledWith('edit', 'fp-now', formFromPeriod(NOW));
  });

  it('+ Add a period opens the author flow with NO form', () => {
    const { ctx, openEditor } = focusCtxWith();
    render(<FocusPanel ctx={ctx} />);
    fireEvent.click(screen.getByText('+ Add a period'));
    expect(openEditor).toHaveBeenCalledWith('author', null, null);
  });
});

// ── the form: spec §17 coverage ─────────────────────────────────────────────

describe('the edit form covers every spec §17 field', () => {
  function renderForm(over: Partial<FocusForm> = {}) {
    const { ctx, up, applyPeriods, closeEditor } = focusCtxWith({
      focusView: 'edit',
      focusEditId: 'fp-now',
      focusReflect: { ...formFromPeriod(NOW), ...over },
    });
    const r = render(<FocusOverlay ctx={ctx} open />);
    return { ...r, ctx, up, applyPeriods, closeEditor };
  }

  it('renders all eleven §17 labels', () => {
    renderForm();
    for (const label of [
      'Name',
      'Start',
      'End',
      'Intent — your words',
      'Free from',
      'Free to',
      'Plan shape',
      'Starts', // workday start — see the no-backing-property test below
      'Ends',
      'Days off',
      'Foreground — worked first',
      'Paused — off this period',
    ]) {
      expect(screen.getByText(label), label).toBeTruthy();
    }
    // the availability NOTE — the field AI_LAYER_SPEC.md §2 calls the anti-flattening path
    expect(screen.getByPlaceholderText('what this window means')).toBeTruthy();
  });

  it('offers exactly the three plan-shape overrides, with the current one selected', () => {
    renderForm();
    for (const o of ['Auto', 'Clock schedule', 'Priority list']) {
      expect(screen.getByText(o), o).toBeTruthy();
    }
  });

  it('renders Workday start even though no backing property exists yet', () => {
    // Spec §17 flags `workday_start` as NEW; AI_LAYER_SPEC.md §2 records the live type as
    // carrying only `Workday end`. The CONTROL must exist and round-trip regardless — this
    // test is what stops it being quietly dropped as "not a real field".
    const { up } = renderForm();
    const start = document.querySelectorAll('input[type="time"]')[0] as HTMLInputElement;
    expect(start.value).toBe('09:00');
    fireEvent.change(start, { target: { value: '07:30' } });
    expect(up).toHaveBeenCalledWith({
      focusReflect: expect.objectContaining({ workdayStart: '07:30' }),
    });
  });

  it('days off lists the period dates and offers the weekly-default fallback when empty', () => {
    renderForm();
    expect(screen.getByText('Overrides the system’s weekly days-off just for this period.')).toBeTruthy();
    cleanup();
    renderForm({ daysOff: [] });
    expect(screen.getByText('Weekends (system default)')).toBeTruthy();
  });

  it('the save button label follows the view', () => {
    renderForm();
    expect(screen.getByText('Save changes')).toBeTruthy();
    expect(screen.getByText('Edit focus period')).toBeTruthy();
  });
});

// ── intent is never reworded ────────────────────────────────────────────────

describe('intent is the user’s own words', () => {
  it('binds the textarea straight to the value with no transform', () => {
    const { ctx, up } = focusCtxWith({
      focusView: 'edit',
      focusEditId: 'fp-now',
      focusReflect: formFromPeriod(NOW),
    });
    render(<FocusOverlay ctx={ctx} open />);
    const ta = screen.getByDisplayValue(NOW.intent);
    const messy = '  Jobs FIRST.  caregiving sat.\n\nno deep focus.   ';
    fireEvent.change(ta, { target: { value: messy } });
    expect(up).toHaveBeenCalledWith({
      focusReflect: expect.objectContaining({ intent: messy }),
    });
  });

  it('the author flow carries the draft into intent unchanged', () => {
    const messy = '  jobs first,  caregiving from sat.  ';
    expect(formFromDraft(messy).intent).toBe(messy);
  });

  it('saveFocus writes intent through untouched', () => {
    const form = { ...formFromPeriod(NOW), intent: '  odd   spacing.  ' };
    const r = saveFocus(freshPeriods(), 'edit', 'fp-now', form);
    expect(r.periods.find((p) => p.id === 'fp-now')!.intent).toBe('  odd   spacing.  ');
  });
});

// ── the two project pickers ─────────────────────────────────────────────────

describe('the paused picker is filtered to pausable projects', () => {
  /** The picker list is the scroller after the search input; both pickers share the markup. */
  function pickerFor(placeholder: string): HTMLElement {
    const input = screen.getByPlaceholderText(placeholder);
    const list = input.nextElementSibling as HTMLElement;
    if (!list) throw new Error('picker list not found for ' + placeholder);
    return list;
  }

  function renderForm() {
    const { ctx } = focusCtxWith({
      focusView: 'edit',
      focusEditId: 'fp-now',
      focusReflect: formFromPeriod(NOW),
    });
    return render(<FocusOverlay ctx={ctx} open />);
  }

  it('drops Backburner/Done engagement and Parked/Inactive status from PAUSED only', () => {
    renderForm();
    const front = pickerFor('Search projects…');
    const paused = pickerFor('Search projects to pause…');

    // Every option the paused list offers is also in the front list; the reverse is not true.
    // A SELECTED row prefixes its label with the check glyph inside the box span, so the
    // button's textContent reads "✓Crafts". Stripped so the two lists compare on title alone.
    const names = (el: HTMLElement) =>
      Array.from(el.querySelectorAll('button')).map((b) =>
        (b.textContent ?? '').replace('✓', '').trim(),
      );
    const frontNames = names(front);
    const pausedNames = names(paused);
    expect(pausedNames.length).toBeGreaterThan(0);
    expect(frontNames.length).toBeGreaterThan(pausedNames.length);
    for (const n of pausedNames) expect(frontNames).toContain(n);
  });

  it('the excluded ones are exactly the non-pausable projects in the fixture', () => {
    const { ctx } = focusCtxWith();
    // Which goal children the filter should hold out, computed from the fixture itself so a
    // fixture change moves the expectation rather than breaking the assertion silently.
    const excluded = ctx.graph.roots.flatMap((g) =>
      g.children
        .filter(
          (c) =>
            ['PROJECT', 'SUBPROJECT', 'WORKSTREAM'].includes(c.level) &&
            (['Backburner', 'Done'].includes(String(c.vals.engagement)) ||
              ['Parked', 'Inactive'].includes(String(c.vals.status))),
        )
        .map((c) => c.title),
    );
    expect(excluded.length).toBeGreaterThan(0);

    renderForm();
    const paused = pickerFor('Search projects to pause…');
    for (const title of excluded) {
      expect(within(paused).queryByText(title), title).toBeNull();
    }
    const front = pickerFor('Search projects…');
    for (const title of excluded) {
      expect(within(front).getByText(title), title).toBeTruthy();
    }
  });

  it('shows the current selection as removable chips', () => {
    renderForm();
    // `front` and `paused` from the fixture both surface as chips above their picker.
    expect(screen.getAllByText('Academic positions').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Crafts').length).toBeGreaterThan(0);
  });
});

// ── back discards, deliberately ─────────────────────────────────────────────

describe('Back discards the draft silently — v4 behaviour, deliberately preserved', () => {
  it('closes without saving and without confirming', () => {
    const { ctx, applyPeriods, closeEditor } = focusCtxWith({
      focusView: 'edit',
      focusEditId: 'fp-now',
      focusReflect: { ...formFromPeriod(NOW), name: 'a name the user typed but never saved' },
    });
    render(<FocusOverlay ctx={ctx} open />);
    fireEvent.click(screen.getByText('‹ Back'));
    expect(closeEditor).toHaveBeenCalledTimes(1);
    // The flagged inconsistency: nothing is written, and nothing warns.
    expect(applyPeriods).not.toHaveBeenCalled();
    expect(screen.queryByText(/discard|unsaved|are you sure/i)).toBeNull();
  });
});

// ── the author flow ─────────────────────────────────────────────────────────

describe('the author flow', () => {
  it('asks for June’s own words and promises not to reword them', () => {
    const { ctx } = focusCtxWith({ focusView: 'author', focusReflect: null });
    render(<FocusOverlay ctx={ctx} open />);
    expect(
      screen.getByText('What focus period do you want to set up? Say it in your own words.'),
    ).toBeTruthy();
    expect(screen.getByText(/won’t reword your intent/)).toBeTruthy();
    // The form is NOT shown until the draft has been structured.
    expect(screen.queryByText('Days off')).toBeNull();
  });

  it('“Structure this →” is a no-op on an empty draft', () => {
    const { ctx, up } = focusCtxWith({ focusView: 'author', focusReflect: null, focusDraft: '   ' });
    render(<FocusOverlay ctx={ctx} open />);
    fireEvent.click(screen.getByText('Structure this →'));
    expect(up).not.toHaveBeenCalled();
  });

  it('structures a draft into a form and reflects it back', () => {
    const { ctx, up } = focusCtxWith({
      focusView: 'author',
      focusReflect: null,
      focusDraft: 'jobs first this week, caregiving from Saturday',
    });
    render(<FocusOverlay ctx={ctx} open />);
    fireEvent.click(screen.getByText('Structure this →'));
    expect(up).toHaveBeenCalledWith({
      focusReflect: formFromDraft('jobs first this week, caregiving from Saturday'),
    });
  });

  it('the reflect-back screen uses the confirm wording, not the edit wording', () => {
    const { ctx } = focusCtxWith({
      focusView: 'author',
      focusReflect: formFromDraft('jobs first this week'),
    });
    render(<FocusOverlay ctx={ctx} open />);
    expect(screen.getByText('Here’s what I heard')).toBeTruthy();
    expect(screen.getByText('Looks right — save')).toBeTruthy();
  });
});

// ── saveFocus ───────────────────────────────────────────────────────────────

describe('saveFocus', () => {
  it('writes back to the named period and leaves the others alone', () => {
    const before = freshPeriods();
    const form: FocusForm = {
      ...formFromPeriod(NOW),
      name: 'Renamed',
      workdayStart: '07:00',
      daysOff: ['2026-07-19', '2026-07-20'],
      paused: ['Crafts'],
    };
    const r = saveFocus(before, 'edit', 'fp-now', form);
    const after = r.periods.find((p) => p.id === 'fp-now')!;
    expect(after.name).toBe('Renamed');
    expect(after.workdayStart).toBe('07:00');
    expect(after.daysOff).toEqual(['2026-07-19', '2026-07-20']);
    expect(after.paused).toEqual(['Crafts']);
    expect(after.when).toBe('now'); // `when` is not a form field and must survive
    expect(r.periods.find((p) => p.id === 'fp-next')).toEqual(before[1]);
    expect(r.toast).toBe('Focus period updated');
    // pure: the input array is untouched
    expect(before.find((p) => p.id === 'fp-now')!.name).toBe(NOW.name);
  });

  it('appends a new upcoming period in author mode', () => {
    const before = freshPeriods();
    const r = saveFocus(before, 'author', null, formFromDraft('a lighter fortnight'));
    expect(r.periods.length).toBe(before.length + 1);
    const added = r.periods[r.periods.length - 1]!;
    expect(added.when).toBe('upcoming');
    expect(added.intent).toBe('a lighter fortnight');
    expect(added.id).not.toBe('');
    expect(r.toast).toBe('Focus period saved');
  });

  it('falls back to a placeholder name only on the author path', () => {
    const blank = { ...formFromDraft('x'), name: '' };
    expect(saveFocus(freshPeriods(), 'author', null, blank).periods.at(-1)!.name).toBe(
      'New focus period',
    );
    // ⚠ v4 has no such fallback on the edit path — an emptied name stays empty. Pinned so the
    // asymmetry is a decision, not an accident.
    const edited = saveFocus(freshPeriods(), 'edit', 'fp-now', { ...formFromPeriod(NOW), name: '' });
    expect(edited.periods.find((p) => p.id === 'fp-now')!.name).toBe('');
  });

  it('lists and the arrays inside them are copies, not shared references', () => {
    const before = freshPeriods();
    const form = formFromPeriod(NOW);
    const r = saveFocus(before, 'edit', 'fp-now', form);
    const after = r.periods.find((p) => p.id === 'fp-now')!;
    expect(after.front).not.toBe(form.front);
    expect(after.daysOff).not.toBe(form.daysOff);
    expect(after.paused).not.toBe(form.paused);
  });
});

// ── the overlay ─────────────────────────────────────────────────────────────

describe('FocusOverlay', () => {
  it('renders nothing when the __focus__ route is not open', () => {
    const { ctx } = focusCtxWith({ focusView: 'edit', focusReflect: formFromPeriod(NOW) });
    const { container } = render(<FocusOverlay ctx={ctx} open={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('routes focusView==="author" to the author flow and anything else to the edit form', () => {
    const { ctx } = focusCtxWith({ focusView: 'list', focusReflect: formFromPeriod(NOW) });
    render(<FocusOverlay ctx={ctx} open />);
    expect(screen.getByText('Edit focus period')).toBeTruthy();
  });

  it('saving calls the period seam and then closes', () => {
    const { ctx, applyPeriods, closeEditor } = focusCtxWith({
      focusView: 'edit',
      focusEditId: 'fp-now',
      focusReflect: { ...formFromPeriod(NOW), name: 'Saved name' },
    });
    render(<FocusOverlay ctx={ctx} open />);
    fireEvent.click(screen.getByText('Save changes'));
    expect(applyPeriods).toHaveBeenCalledTimes(1);
    const result = applyPeriods.mock.calls[0]![0];
    expect(result.periods.find((p: { id: string }) => p.id === 'fp-now').name).toBe('Saved name');
    expect(closeEditor).toHaveBeenCalledTimes(1);
  });
});
