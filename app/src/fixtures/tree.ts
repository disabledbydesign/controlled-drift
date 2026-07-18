/**
 * Object-graph fixture — verbatim transcription of `seed()` (~lines 197–266)
 * and `seedStrategies()` (~lines 267–276) from
 * design/mockups/review-reorganize-mobile-v4.html.
 *
 * Node shape in v4: {id, level, type, title, vals, children}. The mockup also
 * hangs a `parent` back-pointer on each node at runtime (`index()`, ~line 277);
 * that is derived, not fixture data, so it is not represented here.
 */

import type { Node, Strategy } from './types.ts';

export const seed: Node[] = [
  {
    id: 'kidvlq',
    level: 'GOAL',
    type: 'Goal',
    title: 'Material survival',
    vals: {
      engagement: 'Steady',
      status: 'Active',
      horizon: 'Chapter',
      reaching: 'Income and a role that fits — not one that extracts.',
    },
    children: [
      {
        id: 'notekm',
        level: 'PROJECT',
        type: 'Project',
        title: 'Moving',
        vals: { engagement: 'Open', status: 'Active', side: 'Daily life' },
        children: [],
      },
      {
        id: 'znqg2i',
        level: 'PROJECT',
        type: 'Project',
        title: 'Crafts',
        vals: {
          engagement: 'Open',
          status: 'Active',
          side: 'Fun / hobby',
          access: 'Involves-leaving-house',
          blockMin: '60',
          affective: 'Playful, low-stakes — good for making something with my hands.',
        },
        children: [
          {
            id: 'sellcase',
            level: 'SUBPROJECT',
            type: 'Project',
            title: 'Sell phone case',
            vals: { engagement: 'Open', side: 'Fun / hobby' },
            children: [
              {
                id: 'we7liy',
                level: 'TASK',
                type: 'Task',
                title: 'Put phone case for sale',
                vals: {
                  status: 'Needs Clarifying',
                  needs: true,
                  affective: 'Been delaying a long time; stuck on how to do this.',
                },
                children: [],
              },
            ],
          },
          {
            id: 'leather',
            level: 'SUBPROJECT',
            type: 'Project',
            title: 'Leatherworking',
            vals: { engagement: 'Open', side: 'Fun / hobby' },
            children: [
              {
                id: 'mbpqqy',
                level: 'TASK',
                type: 'Task',
                title: 'Start dying and cutting leather for cuff order',
                vals: { status: 'Ready' },
                children: [],
              },
              {
                id: 'zzbzqu',
                level: 'TASK',
                type: 'Task',
                title: 'Order rivets for cuff order',
                vals: { status: 'Ready', ai: true },
                children: [],
              },
            ],
          },
        ],
      },
      {
        id: 'hx6fqm',
        level: 'PROJECT',
        type: 'Project',
        title: 'Publishing papers',
        vals: { engagement: 'Open', status: 'Active', side: 'Work' },
        children: [
          {
            id: '4r3464',
            level: 'SUBPROJECT',
            type: 'Project',
            title: 'Autograder bias paper',
            vals: { engagement: 'Steady', side: 'Work' },
            children: [
              {
                id: 'kt4i6q',
                level: 'TASK',
                type: 'Task',
                title: 'Consolidate scattered OFB research data',
                vals: {
                  status: 'Active',
                  access: 'Requires-deep-thinking',
                  context: 'Research data + code scattered across two repos.',
                },
                children: [],
              },
            ],
          },
        ],
      },
      {
        id: 'xx2uay',
        level: 'PROJECT',
        type: 'Project',
        title: 'Academic positions',
        vals: { engagement: 'Open', status: 'Active', side: 'Work' },
        children: [
          {
            id: 'fwjisq',
            level: 'TASK',
            type: 'Task',
            title: 'Sweep for job search opportunities',
            vals: { status: 'Ready' },
            children: [],
          },
          {
            id: 'ieshky',
            level: 'TASK',
            type: 'Task',
            title: 'Reach out to Redfish Technology (EdTech recruiter)',
            vals: {
              status: 'Active',
              access: 'Requires-talking-to-a-person',
              context: 'Strongest lead — EdTech-focused, employer-paid, places IC level.',
            },
            children: [],
          },
        ],
      },
      {
        id: '6ixeji',
        level: 'PROJECT',
        type: 'Project',
        title: 'Stable clock-in/out income',
        vals: { engagement: 'Backburner', status: 'Active', side: 'Work' },
        children: [],
      },
    ],
  },
  {
    id: '5lcssq',
    level: 'GOAL',
    type: 'Goal',
    title: 'Scholarly practice',
    vals: { engagement: 'Open', status: 'Active', horizon: 'Ongoing' },
    children: [
      {
        id: 'exdcey',
        level: 'PROJECT',
        type: 'Project',
        title: 'AI welfare critique paper',
        vals: { engagement: 'Backburner', status: 'Active', side: 'Work' },
        children: [
          {
            id: 'tpw6bi',
            level: 'TASK',
            type: 'Task',
            title: 'Revise AI welfare critique paper',
            vals: { status: 'Active' },
            children: [],
          },
        ],
      },
      {
        id: 'ffmya4',
        level: 'PROJECT',
        type: 'Project',
        title: 'Reframe paper',
        vals: { engagement: 'Open', status: 'Active', side: 'Work' },
        children: [
          {
            id: 't6ndra',
            level: 'TASK',
            type: 'Task',
            title: 'Split Reframe and Welfare sections into separate papers',
            vals: { status: 'Active' },
            children: [],
          },
        ],
      },
      {
        id: '3cpyku',
        level: 'PROJECT',
        type: 'Project',
        title: 'Cultural Anthropology — reviewer response',
        vals: { engagement: 'Steady', status: 'Active', side: 'Work' },
        children: [
          {
            id: 'l3pdzq',
            level: 'TASK',
            type: 'Task',
            title: 'Write response to the commentary',
            vals: {
              status: 'Active',
              context: 'Already accepted; this reply is all that is left.',
            },
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: 'irv6fe',
    level: 'GOAL',
    type: 'Goal',
    title: 'Builder practice',
    vals: { engagement: 'Steady', status: 'Active', horizon: 'Ongoing' },
    children: [
      {
        id: 'mb752u',
        level: 'PROJECT',
        type: 'Project',
        title: 'Grounded Recollection (GRA)',
        vals: { engagement: 'Steady', status: 'Active', side: 'Fun / hobby' },
        children: [
          {
            id: '5h5p3u',
            level: 'WORKSTREAM',
            type: 'Project',
            title: 'Profile memory formation',
            vals: { engagement: 'Steady', status: 'Active' },
            children: [],
          },
          {
            id: '5eoewi',
            level: 'WORKSTREAM',
            type: 'Project',
            title: 'Metabolize the archive',
            vals: { engagement: 'Steady', status: 'Active' },
            children: [
              {
                id: 'uuqh3q',
                level: 'TASK',
                type: 'Task',
                title: 'Resume GRA metabolism at R2',
                vals: { status: 'Active' },
                children: [],
              },
            ],
          },
        ],
      },
      {
        id: 'vyzxdu',
        level: 'PROJECT',
        type: 'Project',
        title: 'Build Controlled Drift',
        vals: { engagement: 'Sprint', status: 'Active', side: 'Fun / hobby' },
        children: [
          {
            id: 'vqgjaa',
            level: 'WORKSTREAM',
            type: 'Project',
            title: 'Daily plan pipeline',
            vals: { engagement: 'Sprint', status: 'Active' },
            children: [
              {
                id: 'ixmgki',
                level: 'TASK',
                type: 'Task',
                title: 'Duration intelligence for task estimates',
                vals: {
                  status: 'Ready',
                  ai: true,
                  context: 'Durations are wildly off — most sit on the 30-min default.',
                },
                children: [],
              },
            ],
          },
          {
            id: 'yqguaa',
            level: 'WORKSTREAM',
            type: 'Project',
            title: 'Orientation map + arc rendering',
            vals: { engagement: 'Steady', status: 'Active' },
            children: [
              {
                id: 'ct3ca4',
                level: 'TASK',
                type: 'Task',
                title: 'Redesign the Map tab into a scannable surface',
                vals: { status: 'In Design' },
                children: [],
              },
            ],
          },
        ],
      },
    ],
  },
  {
    id: '2jyuzm',
    level: 'GOAL',
    type: 'Goal',
    title: 'Sustainable daily life',
    vals: { engagement: 'Open', status: 'Active', horizon: 'Ongoing' },
    children: [
      {
        id: 'household',
        level: 'PROJECT',
        type: 'Project',
        title: 'Household',
        vals: { engagement: 'Steady', status: 'Active', side: 'Daily life' },
        children: [
          {
            id: 'r-dishes',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Do the dishes',
            vals: { count: 1, unit: 'day', tod: '20:00' },
            children: [],
          },
          {
            id: 'r-kitchen',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Clean the kitchen',
            vals: { count: 1, unit: 'week', dow: 'Sat' },
            children: [],
          },
          {
            id: 'r-groc',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Go to the grocery store',
            vals: { unit: 'as_needed' },
            children: [],
          },
          {
            id: 'r-bills',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Pay bills',
            vals: {
              count: 1,
              unit: 'month',
              access: 'Involves-bureaucracy',
              context: 'Triggers on the first of the month.',
            },
            children: [],
          },
          {
            id: 'r-trash',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Take out the trash',
            vals: { count: 1, unit: 'week', dow: 'Tue', tod: '19:00' },
            children: [],
          },
          {
            id: 'r-plants',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Water the plants',
            vals: { count: 3, unit: 'day' },
            children: [],
          },
        ],
      },
      {
        id: 'selfcare',
        level: 'PROJECT',
        type: 'Project',
        title: 'Self-care',
        vals: { engagement: 'Open', status: 'Active', side: 'Wellbeing' },
        children: [
          {
            id: 'r-walk',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Go on a long walk',
            vals: { count: 3, unit: 'week' },
            children: [],
          },
          {
            id: 'r-meds',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Take morning meds',
            vals: { count: 1, unit: 'day', tod: '08:00' },
            children: [],
          },
          {
            id: 'r-therapy',
            level: 'RECURRING',
            type: 'Recurring',
            title: 'Therapy',
            vals: { count: 1, unit: 'week', dow: 'Wed', tod: '15:00', source: 'calendar' },
            children: [],
          },
          {
            id: 'a73bn4',
            level: 'TASK',
            type: 'Task',
            title: 'Wax',
            vals: { status: 'Ready' },
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: 'odmuqm',
    level: 'GOAL',
    type: 'Goal',
    title: 'FFS Healing and recovery',
    vals: {
      engagement: 'Backburner',
      status: 'Parked',
      horizon: 'Chapter',
      context: 'Surgery date: May 20, 2026',
    },
    children: [],
  },
];

export const seedStrategies: Strategy[] = [
  {
    id: 'strat1',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'When low energy, pick one small win and stop',
    vals: {
      when: 'Low energy',
      status: 'Active',
      directive: 'Surface a single ≤15-min task; do not stack the day.',
    },
    children: [],
  },
  {
    id: 'strat2',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'Non-Backburner project unworked ~1 month → propose Backburner',
    vals: {
      when: 'Always',
      status: 'Active',
      directive: 'Offer to move it to Backburner; log the response with a revisit interval.',
    },
    children: [],
  },
  {
    id: 'strat3',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'Steady project unsurfaced ~16 days → propose foregrounding',
    vals: {
      when: 'Always',
      status: 'Active',
      directive: 'Bring it back into view; ask before reprioritising.',
    },
    children: [],
  },
  {
    id: 'strat4',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'When overwhelmed, cut the day to three anchors',
    vals: {
      when: 'Overwhelmed',
      status: 'Active',
      directive: 'Drop everything but 3 must-dos; explicitly park the rest.',
    },
    children: [],
  },
  {
    id: 'strat5',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'On a sprint, protect one long deep-work block',
    vals: {
      when: 'Sprint',
      status: 'Active',
      directive: 'Reserve a 2-hour block for the sprint target before anything else.',
    },
    children: [],
  },
  {
    id: 'strat6',
    level: 'STRATEGY',
    type: 'Strategy',
    title: 'When stuck, rewrite the next step as one tiny action',
    vals: {
      when: 'Stuck',
      status: 'Active',
      directive: 'Renegotiate the plan down to a single 5-minute first step.',
    },
    children: [],
  },
];
