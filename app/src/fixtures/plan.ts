/**
 * Daily-plan fixture — verbatim transcription of `seedPlan()`
 * from design/mockups/review-reorganize-mobile-v4.html, ~lines 785–802.
 *
 * Note the two item grains: `kind:'task'` is a real checkoffable task id;
 * `kind:'block'` is an ongoing-work block rendered over a real node id, whose
 * `arc` steps carry the real task id on the 'here' step. `kind:'break'` has no
 * id at all.
 */

import type { Plan } from './types.ts';

export const seedPlan: Plan = {
  date: 'Wed Jul 16',
  /*
   * EMPTY ON PURPOSE. v4's fixture carried the sentence "Built this morning at 9:02."; the
   * field now holds a real ISO timestamp, and this seed plan has no real generation behind it.
   *
   * ⚠ Load-bearing, not tidiness: `useAppState` clones this seed as the app's INITIAL plan,
   * before the real `/api/plan` fetch lands. Any timestamp here would be shown to June as a
   * fact about her plan for the moment the app is opening — either a false "built this
   * morning" or a false staleness notice. Empty renders no age line at all, and the real
   * timestamp replaces it as soon as the payload arrives.
   */
  generated: '',
  shape: 'schedule',
  // v4's fixture predates the server's `header` line and has no equivalent of it. Empty rather
  // than invented — a made-up reason in the fixture is exactly what the real one replaces.
  header: '',
  woven:
    'Two threads carry today: the scholarly work that’s nearly closed out, and keeping the material floor intact. The papers that just need finishing go first while focus is high; job-search outreach takes the lower-stakes afternoon. Creative and build work isn’t scheduled — it’s on the Map when you want it.',
  blocks: [
    {
      label: 'Morning',
      time: '9:00 – 12:00',
      framing: 'Freshest energy goes to the writing that’s nearly done.',
      items: [
        {
          kind: 'block',
          id: 'l3pdzq',
          task: 'Work on the reviewer response',
          time: '9:00 – 10:30',
          chunkMin: 90,
          why: 'already accepted — this reply is all that’s left to close it',
          arc: [
            { text: 'Re-read reviewer 2’s objection on sampling', state: 'done' },
            { text: 'Draft the rebuttal paragraph', state: 'here', id: 'l3pdzq' },
            { text: 'Fold in the two supporting citations', state: 'ahead' },
            { text: 'Read once for tone, then send to the editor', state: 'ahead' },
          ],
        },
        {
          kind: 'task',
          id: 'kt4i6q',
          time: '10:30 – 12:00',
          durationMin: 90,
          why: 'scattered across two repos; consolidating unblocks the rest',
          description:
            'Research data and code live in two repos — pull them into one place so the analysis can run.',
          heldBack: ['Re-run the bias metrics', 'Write the data-availability note'],
        },
      ],
    },
    {
      label: 'Midday',
      time: '12:00 – 1:00',
      framing: 'A real stop, not a quick break.',
      items: [{ kind: 'break', time: '12:00', task: 'Lunch' }],
    },
    {
      label: 'Afternoon',
      time: '12:30 – 3:30',
      framing: 'Post-lunch for outreach — lower stakes, still forward motion.',
      items: [
        {
          kind: 'task',
          id: 'ieshky',
          time: '12:30 – 2:00',
          durationMin: 90,
          why: 'strongest job lead — keeps material survival moving',
          description:
            'EdTech-focused recruiter, employer-paid. Send the intro note and attach the CV.',
        },
        {
          kind: 'task',
          id: 'fwjisq',
          time: '2:00 – 2:30',
          durationMin: 30,
          why: 'a quick sweep keeps the thread alive',
        },
        {
          kind: 'block',
          id: '4r3464',
          task: 'Work on the autograder bias paper',
          time: '2:30 – 3:30',
          chunkMin: 60,
          why: 'a steady chunk keeps it from going cold',
        },
      ],
    },
  ],
};
