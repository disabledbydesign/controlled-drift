/**
 * Orphan-bucket fixture — objects that exist but hang off nothing.
 *
 * ⚠ NOT FROM v4. Every other file in this directory is a verbatim transcription of the mockup,
 * and this one is not: v4's `seed()` has no orphans at all — every fixture node has a parent
 * (noted in `docs/api_contract_v2.md:668`). That is precisely why the buckets had to be built
 * rather than ported. Kept in its own file so the "byte-identical to the mockup" guarantee over
 * `tree.ts`, `plan.ts`, `periods.ts` and `schema.ts` stays intact and checkable.
 *
 * ── THE REAL SOURCE IS THE ENDPOINT, NOT THIS FILE ───────────────────────────
 * `GET /api/tree` returns `orphans` as four keyed buckets, each `{label, nodes}`
 * (`scripts/api_tree.py:295-310`, read 2026-07-18). Track A runs on fixtures and makes no
 * network calls, so this exists to make the buckets visible and testable NOW; Track B replaces
 * it wholesale. The four keys and the four `label` strings below are copied from that endpoint
 * exactly — the labels are June-facing and were kept verbatim from the surface being retired, so
 * neither this file nor the components may reword them.
 *
 * ── the contents are illustrative; the counts are not the live ones ──────────
 * June's live space has TWELVE unparented objects — 3 tasks and 9 recurring items, among them
 * Shower, Go on a walk, Therapy and Text friends. Those four real names are used here so the
 * fixture shows the actual shape of the problem (mostly recurring self-care that belongs to no
 * project). The rest is not invented detail about her data: two generic tasks and one project
 * stand in for the remainder, and `parentless_workstreams` is left EMPTY on purpose — it is the
 * demonstration that a bucket with nothing in it renders nothing at all.
 */

import type { Node } from './types.ts';

/** One bucket as the endpoint shapes it. */
export interface OrphanBucketFixture {
  key: string;
  label: string;
  nodes: Node[];
}

const rec = (id: string, title: string, vals: Node['vals']): Node => ({
  id,
  level: 'RECURRING',
  type: 'Recurring',
  title,
  vals,
  children: [],
});

const task = (id: string, title: string, vals: Node['vals']): Node => ({
  id,
  level: 'TASK',
  type: 'Task',
  title,
  vals,
  children: [],
});

export const seedOrphans: OrphanBucketFixture[] = [
  {
    key: 'projects_without_goal',
    label: '⚠ NO GOAL YET — projects not linked to a goal',
    nodes: [
      {
        id: 'o-p-readinggroup',
        level: 'PROJECT',
        type: 'Project',
        title: 'Reading group',
        vals: { engagement: 'Open', status: 'Active', side: 'Fun / hobby' },
        children: [],
      },
    ],
  },
  {
    key: 'orphan_tasks',
    label: '⚠ NO PROJECT — orphan tasks',
    nodes: [
      task('o-t-1', 'Renew library card', { status: 'Ready', duration: 15 }),
      task('o-t-2', 'Find the box with the winter clothes', { status: 'Ready' }),
      task('o-t-3', 'Reply to the landlord', {
        status: 'Blocked',
        access: 'Requires-talking-to-a-person',
      }),
    ],
  },
  {
    key: 'orphan_recurring',
    label: '⚠ NO PROJECT — orphan recurring items',
    nodes: [
      rec('o-r-shower', 'Shower', { count: 1, unit: 'day' }),
      rec('o-r-walk', 'Go on a walk', { count: 1, unit: 'day', side: 'Wellbeing' }),
      rec('o-r-therapy', 'Therapy', { count: 1, unit: 'week', dow: 'Tue' }),
      rec('o-r-friends', 'Text friends', {
        unit: 'as_needed',
        access: 'Requires-talking-to-a-person',
      }),
    ],
  },
  {
    // Empty on purpose — see the header. A bucket with no nodes must render NOTHING, not an
    // empty heading, because a standing "0 here" line is the count line June declined.
    key: 'parentless_workstreams',
    label: '⚙ Workstreams with no parent project',
    nodes: [],
  },
];
