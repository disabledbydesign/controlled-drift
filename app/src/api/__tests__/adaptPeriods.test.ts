// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * Tests for the focus-period wire→app adapter.
 *
 * The payloads below are shapes that came off the RUNNING `/api/periods` on 2026-07-18, not
 * invented ones. That matters here more than anywhere: the bug this adapter exists to close was
 * the Focus tab rendering `seedPeriods` — invented weeks — as though they were June's own
 * commitments. A test written against the fixture would have been testing the fabrication.
 *
 * The two conventions disagree on almost every name, so the first test pins the WHOLE mapping in
 * one assertion: a rename on either side fails it, rather than a field quietly arriving
 * `undefined` and rendering blank.
 */

import { describe, expect, it } from 'vitest';
import { periodFromLive, periodsFromLive } from '../adapt.ts';
import type { LivePeriod, PeriodsResponse } from '../adapt.ts';

/**
 * Every call below pins `today` explicitly. `periodFromLive` defaults it to the real clock, and
 * a suite that let it default would quietly change meaning as the calendar moves — these
 * fixtures are dated, so "is this period over?" has a different answer next month.
 */
const TODAY = '2026-07-18';

/** One real period, trimmed — "Week of Jun 29", as the live endpoint sends it. */
const REAL: LivePeriod = {
  id: 'bafyreiahoidmgbpiqdeeswy2biir6giyeferstznkj5ue6tehxsueda2pi',
  active: false,
  name: 'Week of Jun 29 — recover, jobs, caregiving',
  start_date: '2026-06-29',
  end_date: '2026-07-06',
  intent: 'Coming off the SSRC sprint: ~2 days rest/recovery first, then jobs.',
  // ⚠ Deliberately DIFFERENT from start_date/end_date. The live period had
  // `availability_end === end_date`, and a fixture that copies that coincidence cannot tell an
  // adapter reading the wrong one — a mutation swapping them passed until these were split.
  availability_start: '2026-07-03',
  availability_end: '2026-07-05',
  availability_note: "Caregiving for my girlfriend's daughter after surgery.",
  days_off: ['2026-07-05'],
  days_on: ['2026-07-04', '2026-07-06'],
  output_format: 'Priority list',
  workday_start: '09:00',
  workday_end: '17:00',
  foreground_projects: ['Academic positions', 'Industry positions'],
  paused_projects: ['Crafts'],
};

describe('periodFromLive', () => {
  it('maps every snake_case wire field onto the app name that carries it', () => {
    expect(periodFromLive(REAL, TODAY)).toEqual({
      id: 'bafyreiahoidmgbpiqdeeswy2biir6giyeferstznkj5ue6tehxsueda2pi',
      // ended 2026-07-06, twelve days before TODAY
      when: 'past',
      name: 'Week of Jun 29 — recover, jobs, caregiving',
      start: '2026-06-29',
      end: '2026-07-06',
      intent: 'Coming off the SSRC sprint: ~2 days rest/recovery first, then jobs.',
      front: ['Academic positions', 'Industry positions'],
      note: "Caregiving for my girlfriend's daughter after surgery.",
      availStart: '2026-07-03',
      availEnd: '2026-07-05',
      daysOff: ['2026-07-05'],
      daysOn: '2026-07-04, 2026-07-06',
      output: 'Priority list',
      workdayStart: '09:00',
      workdayEnd: '17:00',
      paused: ['Crafts'],
    });
  });

  it('does not confuse the two availability ends, nor availability with the period dates', () => {
    const p = periodFromLive(REAL);
    expect([p.start, p.end]).toEqual(['2026-06-29', '2026-07-06']);
    expect([p.availStart, p.availEnd]).toEqual(['2026-07-03', '2026-07-05']);
  });

  it('does not confuse the projects in front with the paused ones', () => {
    const p = periodFromLive({
      foreground_projects: ['In front'],
      paused_projects: ['Paused'],
    });
    expect(p.front).toEqual(['In front']);
    expect(p.paused).toEqual(['Paused']);
  });

  it('carries the availability note into `note`, which is the only free-text field beside intent', () => {
    const p = periodFromLive({ availability_note: 'keep the weekend light', intent: 'jobs first' });
    expect(p.note).toBe('keep the weekend light');
    expect(p.intent).toBe('jobs first');
  });

  it('turns `active` into when:now — the flag survives the crossing', () => {
    expect(periodFromLive({ ...REAL, active: true }, TODAY).when).toBe('now');
    // absent is not active: a payload without the flag must not promote a period to "now"
    expect(periodFromLive({ name: 'x' }, TODAY).when).not.toBe('now');
  });

  it('`active` beats the dates — the server owns the window rule, not this mapping', () => {
    // Her real "Week of Jul 14" has start === end === a date already behind us, yet the server
    // can still mark a period active. Re-deriving "is it current?" here from the dates would put
    // that rule in two places and let them disagree.
    expect(periodFromLive({ ...REAL, active: true, end_date: '2026-01-01' }, TODAY).when).toBe(
      'now',
    );
  });

  it('separates ENDED periods from ones still ahead — six of her seven have already ended', () => {
    // Before `'past'` existed, every one of these landed under "coming up" badged "Next".
    expect(periodFromLive({ ...REAL, end_date: '2026-07-06' }, TODAY).when).toBe('past');
    expect(periodFromLive({ ...REAL, end_date: '2026-08-30' }, TODAY).when).toBe('upcoming');
  });

  it('a period ending TODAY has not ended', () => {
    // The boundary is the reason `today` is a parameter. Off by one here files the period she is
    // living in right now under "earlier".
    expect(periodFromLive({ ...REAL, end_date: TODAY }, TODAY).when).toBe('upcoming');
  });

  it('no end date stays visible rather than being guessed into the past', () => {
    // A period that cannot be shown to have ended must not be filed away; the failure directions
    // are not symmetric — one hides real work, the other shows one extra card.
    expect(periodFromLive({ ...REAL, end_date: null }, TODAY).when).toBe('upcoming');
    expect(periodFromLive({ name: 'x' }, TODAY).when).toBe('upcoming');
  });

  it('joins the days-on ARRAY into the string the form binds to a text input', () => {
    expect(periodFromLive({ days_on: ['2026-07-04'] }).daysOn).toBe('2026-07-04');
    expect(periodFromLive({ days_on: [] }).daysOn).toBe('');
  });

  it('gives every field an empty value rather than undefined when the wire omits it', () => {
    const p = periodFromLive({});
    // `output` is the one deliberate default — the select must never render blank.
    expect(p).toEqual({
      id: '',
      when: 'upcoming',
      name: '',
      start: '',
      end: '',
      intent: '',
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
    });
    for (const [key, value] of Object.entries(p)) {
      expect(value, `${key} is undefined`).toBeDefined();
    }
  });

  it('treats an explicit null the same as an absent field — the server sends null workday times', () => {
    const p = periodFromLive({
      name: null,
      start_date: null,
      workday_start: null,
      workday_end: null,
      days_off: null,
      foreground_projects: null,
      paused_projects: null,
      output_format: null,
    });
    expect(p.name).toBe('');
    expect(p.start).toBe('');
    expect(p.workdayStart).toBe('');
    expect(p.workdayEnd).toBe('');
    expect(p.daysOff).toEqual([]);
    expect(p.front).toEqual([]);
    expect(p.paused).toEqual([]);
    expect(p.output).toBe('Auto');
  });
});

describe('periodsFromLive', () => {
  it('keeps the order the server sorted (earliest start first) and adapts each entry', () => {
    const res: PeriodsResponse = {
      periods: [
        { ...REAL, id: 'a', name: 'first', start_date: '2026-06-29' },
        { ...REAL, id: 'b', name: 'second', start_date: '2026-07-14', active: true },
      ],
    };
    const out = periodsFromLive(res, TODAY);
    expect(out.map((p) => p.name)).toEqual(['first', 'second']);
    expect(out.map((p) => p.when)).toEqual(['past', 'now']);
  });

  it('dates the whole list against ONE day, so a list mapped across midnight stays consistent', () => {
    // `periodFromLive` defaults `today` per call. If the list resolved it per entry instead of
    // once, a map running as the clock rolls over would date its first entries yesterday and its
    // last ones today — and a period ending at that boundary would flip mid-list.
    const res: PeriodsResponse = {
      periods: [
        { ...REAL, id: 'a', end_date: '2026-07-17' },
        { ...REAL, id: 'b', end_date: '2026-07-17' },
      ],
    };
    expect(periodsFromLive(res, '2026-07-17').map((p) => p.when)).toEqual([
      'upcoming',
      'upcoming',
    ]);
    expect(periodsFromLive(res, '2026-07-18').map((p) => p.when)).toEqual(['past', 'past']);
  });

  it('reads a payload with no periods array as NO periods, never as a crash', () => {
    expect(periodsFromLive({} as PeriodsResponse)).toEqual([]);
    expect(periodsFromLive({ periods: [] })).toEqual([]);
  });
});