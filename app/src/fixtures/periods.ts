/**
 * Focus-period fixture — verbatim transcription of `seedPeriods()`
 * from design/mockups/review-reorganize-mobile-v4.html, ~lines 805–812.
 *
 * `front` and `paused` hold project TITLES, not ids, in v4.
 */

import type { Period } from './types.ts';

export const seedPeriods: Period[] = [
  {
    id: 'fp-now',
    when: 'now',
    name: 'Job-search sprint · caregiving from Sat',
    start: '2026-07-14',
    end: '2026-07-20',
    intent:
      'Jobs first this week — applications and outreach before anything else. Caregiving starts Saturday, so Thu/Fri are the real work days. Sunday off.',
    front: ['Academic positions', 'Publishing papers'],
    note: 'Low bandwidth after Sat — keep the weekend light.',
    availStart: '2026-07-18',
    availEnd: '2026-07-20',
    daysOff: ['2026-07-20'],
    daysOn: '',
    output: 'Priority list',
    workdayStart: '09:00',
    workdayEnd: '17:00',
    paused: ['Build Controlled Drift', 'Crafts'],
  },
  {
    id: 'fp-next',
    when: 'upcoming',
    name: 'Recovery + admin catch-up',
    start: '2026-07-21',
    end: '2026-07-27',
    intent:
      'Lighter week to recover from caregiving. Clear the admin backlog; take on nothing new.',
    front: ['Household', 'Self-care'],
    note: '',
    availStart: '',
    availEnd: '',
    daysOff: [],
    daysOn: '',
    output: 'Auto',
    workdayStart: '',
    workdayEnd: '',
    paused: [],
  },
];
