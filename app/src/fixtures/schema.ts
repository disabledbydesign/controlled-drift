/**
 * Schema fixture — verbatim transcription of `defaultSchema()`
 * from design/mockups/review-reorganize-mobile-v4.html, ~lines 90–125.
 *
 * SEMANTICS (load-bearing, from the v4 source comments):
 * The UI generates every picker, chip, dropdown and detail form from this
 * schema. Nothing downstream is hardcoded. `relations` = the tag vocabularies;
 * `controls` = the relations each level surfaces, in order; `notes` = its
 * free-text relations. Every level in the app maps to one entry here.
 *
 * SWAP SEAM: v4 ~line 131 has
 *   async loadSchema(){ this.SCHEMA = await (await fetch('/api/schema')).json(); … }
 * so this literal is exported as the *default value* of a typed constant and is
 * never inlined into logic. Pointing the app at `GET /api/schema` is a one-line
 * change at the consumer: replace `defaultSchema` with the fetched `Schema`.
 */

import type { Schema } from './types.ts';

export const defaultSchema: Schema = {
  relations: {
    goalEng: { label: 'Engagement', options: ['Backburner', 'Open', 'Steady', 'Sprint'] },
    goalStatus: { label: 'Status', options: ['Active', 'Parked', 'Achieved'] },
    horizon: {
      label: 'Horizon',
      options: ['Chapter', 'Milestone', 'Short-term', 'Medium-term', 'Long-term', 'Ongoing'],
    },
    proj: {
      label: 'Engagement',
      options: [
        'Backburner',
        'Open',
        'Steady',
        'Sprint',
        'Hyperfixation',
        'Needs Clarifying',
        'Done',
      ],
    },
    projStatus: { label: 'Status', options: ['Active', 'Parked', 'Inactive'] },
    side: { label: 'Side', options: ['Work', 'Daily life', 'Fun / hobby', 'Wellbeing'] },
    taskStatus: {
      label: 'Status',
      options: [
        'Ready',
        'Active',
        'Blocked',
        'In Design',
        'Parked',
        'Needs Clarifying',
        'Done',
      ],
    },
    access: {
      label: 'Access conditions',
      options: [
        'Requires-talking-to-a-person',
        'Can-be-done-lying-down',
        'Involves-leaving-house',
        'Requires-deep-thinking',
        'Involves-bureaucracy',
        'Induces-pain',
      ],
    },
    unit: { label: 'Frequency', options: ['day', 'week', 'month', 'as_needed'] },
    dow: { label: 'Day of week', options: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
    strategyState: {
      label: 'Applies when',
      options: ['Always', 'Low energy', 'Overwhelmed', 'Sprint', 'Stuck'],
    },
    strategyStatus: { label: 'Status', options: ['Active', 'Retired'] },
  },
  controls: {
    GOAL: [
      ['select', 'Engagement', 'engagement', 'goalEng'],
      ['select', 'Goal status', 'status', 'goalStatus'],
      ['select', 'Horizon', 'horizon', 'horizon'],
    ],
    PROJECT: [
      ['select', 'Engagement', 'engagement', 'proj'],
      ['select', 'Project status', 'status', 'projStatus'],
      ['select', 'Side', 'side', 'side'],
      ['date', 'Deadline', 'deadline'],
      ['number', 'Typical block (min)', 'blockMin', null, null],
      [
        'multi',
        'Access conditions',
        'access',
        'access',
        'Block-level default — tasks inherit unless they set their own.',
      ],
    ],
    SUBPROJECT: [
      ['select', 'Engagement', 'engagement', 'proj'],
      ['select', 'Project status', 'status', 'projStatus'],
      ['select', 'Side', 'side', 'side'],
      ['number', 'Typical block (min)', 'blockMin', null, null],
      [
        'multi',
        'Access conditions',
        'access',
        'access',
        'Block-level default — tasks inherit unless they set their own.',
      ],
    ],
    WORKSTREAM: [
      ['select', 'Engagement', 'engagement', 'proj'],
      ['select', 'Status', 'status', 'projStatus'],
      ['number', 'Typical block (min)', 'blockMin', null, null],
      [
        'multi',
        'Access conditions',
        'access',
        'access',
        'Block-level default — tasks inherit unless they set their own.',
      ],
    ],
    TASK: [
      ['select', 'Task status', 'status', 'taskStatus'],
      ['date', 'Due date', 'due', null, 'Deadline — drives urgency and ordering in the plan.'],
      [
        'date',
        'Scheduled',
        'scheduled',
        null,
        'The day your plan has placed it (usually set when you schedule or move it).',
      ],
      ['number', 'Duration (min)', 'duration'],
      ['toggle', 'AI Autonomous', 'ai'],
      ['toggle', 'Needs clarifying', 'needs'],
      ['multi', 'Access conditions', 'access', 'access'],
    ],
    RECURRING: [
      ['recur', 'Repeats', 'count', 'unit'],
      ['multi', 'Day of week', 'dow', 'dow'],
      ['number', 'Day of month', 'dom'],
      ['time', 'Time of day', 'tod'],
      ['number', 'Duration (min)', 'duration'],
      ['toggle', 'AI Autonomous', 'ai'],
      ['toggle', 'Needs clarifying', 'needs'],
      ['multi', 'Access conditions', 'access', 'access'],
    ],
    STRATEGY: [
      ['select', 'Applies when', 'when', 'strategyState'],
      ['select', 'Strategy status', 'status', 'strategyStatus'],
    ],
  },
  notes: {
    GOAL: [
      ['Reaching for', 'reaching'],
      ['Resolution condition', 'resolution'],
      ['Context', 'context'],
      ['Barriers', 'barriers'],
    ],
    PROJECT: [
      ['Reaching for', 'reaching'],
      ['Description', 'description'],
      ['Context', 'context'],
      ['Affective', 'affective'],
      ['Barriers', 'barriers'],
    ],
    SUBPROJECT: [
      ['Reaching for', 'reaching'],
      ['Context', 'context'],
      ['Affective', 'affective'],
    ],
    WORKSTREAM: [
      ['Reaching for', 'reaching'],
      ['Context', 'context'],
    ],
    TASK: [
      ['Context', 'context'],
      ['Access notes', 'accessNotes'],
      ['Affective', 'affective'],
      ['Blocked on', 'blocked'],
      ['Relevant docs', 'docs'],
    ],
    RECURRING: [
      ['Context', 'context'],
      ['Access notes', 'accessNotes'],
      ['Affective', 'affective'],
      ['Blocked on', 'blocked'],
      ['Relevant docs', 'docs'],
    ],
    STRATEGY: [
      ['Directive', 'directive'],
      ['Notes', 'context'],
    ],
  },
};
