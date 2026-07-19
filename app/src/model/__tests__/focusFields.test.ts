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
    });
  });

  /**
   * The regression that matters most: a field present in the form but absent from the wire dict
   * is data loss that looks exactly like a successful save. Named positively — every one of the
   * fourteen editable fields must appear.
   */
  it('emits all fourteen editable fields, so none is silently dropped', () => {
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
        'start_date',
        'workday_end',
        'workday_start',
      ].sort(),
    );
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
  });

  /**
   * `output_format` is one of three exact select values on the server. A period the model left
   * without one shows Auto — the same default `to_write_properties` applies.
   */
  it('defaults the plan shape to Auto when the model named none', () => {
    expect(formFromFields({}).output).toBe('Auto');
  });
});
