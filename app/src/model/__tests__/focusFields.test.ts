// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * The focus form <-> wire-fields translation.
 *
 * The app's form is camelCase (`FocusForm`, from the v4 mockup); the three write routes read a
 * flat snake_case dict (`focus_period_adapter.period_to_fields`). These two names for the same
 * field are where a wire-in silently drops data: a key the server does not recognise is not an
 * error, it is a field that quietly does not save.
 *
 * The direction of truth is `api/adapt.ts` `periodFromLive`, which is the READ mapping already
 * shipped and tested. `fieldsFromForm` must be its inverse, key for key — verified below by
 * round-tripping rather than by restating the same table twice.
 *
 * ⚠ `daysOn` is a STRING in the app ('Mon, Tue') and a LIST on the wire. `periodFromLive` does
 * `list(p.days_on).join(', ')`; the inverse has to split it back or a days-on edit never lands.
 */

import { describe, expect, it } from 'vitest';
import { fieldsFromForm, formFromFields } from '../periods.ts';
import type { FocusForm } from '../periods.ts';

const FORM: FocusForm = {
  name: 'Jobs week',
  start: '2026-07-20',
  end: '2026-07-26',
  intent: 'jobs first this week, caregiving Saturday',
  front: ['Job search', 'Controlled Drift'],
  note: 'free after 3 most days',
  availStart: '2026-07-21',
  availEnd: '2026-07-24',
  daysOff: ['2026-07-25'],
  daysOn: 'Mon, Tue',
  output: 'Priority list',
  workdayStart: '09:00',
  workdayEnd: '17:00',
  paused: ['Reading group'],
  reactivate: ['Dishes'],
};

describe('fieldsFromForm — every field she edits reaches the wire', () => {
  it('maps each form key to the server key the write routes read', () => {
    expect(fieldsFromForm(FORM)).toEqual({
      name: 'Jobs week',
      start_date: '2026-07-20',
      end_date: '2026-07-26',
      intent: 'jobs first this week, caregiving Saturday',
      foreground_projects: ['Job search', 'Controlled Drift'],
      availability_note: 'free after 3 most days',
      availability_start: '2026-07-21',
      availability_end: '2026-07-24',
      days_off: ['2026-07-25'],
      days_on: ['Mon', 'Tue'],
      output_format: 'Priority list',
      workday_start: '09:00',
      workday_end: '17:00',
      paused_projects: ['Reading group'],
      reactivate_tasks: ['Dishes'],
    });
  });

  /**
   * The regression that matters most: a field present in the form but absent from the wire dict
   * is data loss that looks exactly like a successful save. Named positively — every one of the
   * fifteen editable fields must appear.
   *
   * ⚠ WAS FOURTEEN, AND THAT LOCKED A REAL GAP IN. `reactivate_tasks` was in neither direction of
   * the translation, so the whole as-needed reactivation feature — built, reviewed and
   * live-verified in a prior session — was unreachable from this editor: she says "keep the
   * dishes going", the structure step returns it, the form drops it, the write omits it, the
   * server reactivates nothing, and she is told the period saved. A success message over a
   * partly-discarded write. The count in this test is a guard, so it moves when the field list
   * moves — it must never be the reason a dropped field stays dropped.
   */
  it('emits all fifteen editable fields, so none is silently dropped', () => {
    const keys = Object.keys(fieldsFromForm(FORM)).sort();
    expect(keys).toEqual(
      [
        'availability_end',
        'availability_note',
        'availability_start',
        'days_off',
        'days_on',
        'end_date',
        'foreground_projects',
        'intent',
        'name',
        'output_format',
        'paused_projects',
        'reactivate_tasks',
        'start_date',
        'workday_end',
        'workday_start',
      ].sort(),
    );
  });

  /**
   * The named failure the drop caused, asserted directly rather than only through the key list:
   * the tasks she asked to pick back up must reach the wire under the key `server.py`'s
   * `_reactivate_named_tasks` reads (`fields.get("reactivate_tasks")`).
   */
  it('carries the tasks she asked to pick back up through to the wire', () => {
    expect(fieldsFromForm({ ...FORM, reactivate: ['Dishes', 'Clean the fridge'] }).reactivate_tasks)
      .toEqual(['Dishes', 'Clean the fridge']);
  });

  it('sends an empty list when she named no task to pick back up, never omitting the key', () => {
    const out = fieldsFromForm({ ...FORM, reactivate: [] });
    expect(out.reactivate_tasks).toEqual([]);
    expect(Object.prototype.hasOwnProperty.call(out, 'reactivate_tasks')).toBe(true);
  });

  it('copies the reactivate list rather than aliasing the form array', () => {
    expect(fieldsFromForm(FORM).reactivate_tasks).not.toBe(FORM.reactivate);
  });

  /**
   * FINDING 5 — the §14/§17 guarantee, restored on the side that can still break it.
   *
   * The retired test asserted `formFromDraft(messy).intent === messy`. The client no longer
   * BUILDS the intent (the server's structure step does), but the client still SENDS it, and
   * this translation is the last place a trim, a case-fold or a truncation could be introduced
   * between the box she typed in and the write. Her words go out byte for byte.
   */
  it('sends her intent byte for byte, with no trimming or rewording', () => {
    const messy = '  Jobs FIRST.  caregiving sat.\n\nno deep focus.   ';
    expect(fieldsFromForm({ ...FORM, intent: messy }).intent).toBe(messy);
  });

  it('reads her intent back byte for byte, with no trimming or rewording', () => {
    const messy = '  Jobs FIRST.  caregiving sat.\n\nno deep focus.   ';
    expect(formFromFields({ intent: messy }).intent).toBe(messy);
  });

  it('splits the days-on string into the list the wire carries', () => {
    expect(fieldsFromForm({ ...FORM, daysOn: 'Mon, Wed, Fri' }).days_on).toEqual([
      'Mon',
      'Wed',
      'Fri',
    ]);
  });

  it('sends an empty days-on as an empty list, not as a list holding one empty string', () => {
    expect(fieldsFromForm({ ...FORM, daysOn: '' }).days_on).toEqual([]);
  });

  it('copies the lists rather than aliasing the form arrays', () => {
    const out = fieldsFromForm(FORM);
    expect(out.foreground_projects).not.toBe(FORM.front);
    expect(out.days_off).not.toBe(FORM.daysOff);
  });
});

describe('formFromFields — the structure step’s answer becomes the form she checks', () => {
  it('maps each server key back to the form key the editor renders', () => {
    expect(formFromFields(fieldsFromForm(FORM))).toEqual(FORM);
  });

  /** The round trip is the real assertion: read mapping and write mapping agree, key for key. */
  it('round-trips a form unchanged', () => {
    expect(formFromFields(fieldsFromForm(FORM))).toEqual(FORM);
  });

  it('fills a period the model left incomplete with blanks, never with invented values', () => {
    const out = formFromFields({ name: 'Half a week' });
    expect(out.name).toBe('Half a week');
    expect(out.start).toBe('');
    expect(out.end).toBe('');
    expect(out.front).toEqual([]);
    expect(out.daysOn).toBe('');
    expect(out.reactivate).toEqual([]);
  });

  /**
   * The read half of the same drop. The structure step emits `reactivate_tasks`
   * (`focus_period_generate.py`) and the reflect-back renders it as the "Reopening" line she
   * checks — so the form she confirms has to be holding it, or Save writes a period without the
   * thing she just read back and approved.
   */
  it('keeps the tasks the structure step said to pick back up', () => {
    expect(formFromFields({ reactivate_tasks: ['Dishes'] }).reactivate).toEqual(['Dishes']);
  });

  /**
   * `output_format` is one of three exact select values on the server. A period the model left
   * without one shows Auto — the same default `to_write_properties` applies.
   */
  it('defaults the plan shape to Auto when the model named none', () => {
    expect(formFromFields({}).output).toBe('Auto');
  });
});