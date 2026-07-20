// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * `interstitial` MEANS SHORT, NOT "a break" — and reading it as "a break" deleted a real chore.
 *
 * The LLM prompt's JSON rule 3 tells the model to flag real tasks of 15 minutes or less as
 * interstitial too, so the backend's own test has two halves: `interstitial AND no id`
 * (`scripts/plan_generate.py:1338`, with its own comment naming the 2026-07-13 silent-drop this
 * caused there). `adapt.ts` implemented only the first half, and on 2026-07-20 June's real
 * Priority list lost "Do the dishes" — a recurring chore with a real Anytype id — because the
 * adapter classified it as a rest break. A break renders no checkbox and cannot be checked off,
 * so the row was gone with nothing to say it had been dropped.
 *
 * WHAT THESE PIN DOWN, all asserted POSITIVELY (each names what the row MUST become, and what
 * id it MUST carry — an assertion that it merely "is not a break" would also pass against a
 * build that dropped the row some other way):
 *   1. interstitial + an id  → `kind:'task'`, id intact
 *   2. interstitial + no id  → `kind:'break'` (Lunch, Rest — genuinely not addressable)
 *   3. a BLOCK's id lives in `project_id`, and that counts as having an id
 *   4. `project_id` on a NON-block row is its parent project and must NOT be read as its own id
 */

import { describe, expect, it } from 'vitest';
import { planFromLive } from '../adapt.ts';
import type { LivePlan } from '../adapt.ts';

/** The single converted row of a one-row priority plan. */
function oneRow(item: Record<string, unknown>) {
  const plan = planFromLive({ shape: 'priority', items: [item] } as unknown as LivePlan);
  return plan.blocks[0]!.items[0]!;
}

describe('an interstitial row that carries an id is a real short task', () => {
  it('converts "Do the dishes" to a checkable task row with its Anytype id', () => {
    const row = oneRow({
      id: 'bafyreie47nri7dishes',
      task: 'Do the dishes',
      interstitial: true,
      duration_min: 10,
      project: 'household',
    });

    expect(row.kind).toBe('task');
    expect(row).toMatchObject({
      kind: 'task',
      id: 'bafyreie47nri7dishes',
      task: 'Do the dishes',
      durationMin: 10,
    });
  });

  it('keeps it in the list the Priority view reads, so it is still rendered at all', () => {
    const plan = planFromLive({
      shape: 'priority',
      items: [
        { id: 'bafy-a', task: 'Answer the email', interstitial: false },
        { id: 'bafy-dishes', task: 'Do the dishes', interstitial: true },
        { task: 'Lunch', interstitial: true },
      ],
    } as unknown as LivePlan);

    const rows = plan.blocks[0]!.items;
    const ids = rows.filter((r) => r.kind === 'task').map((r) => r.id);
    expect(ids).toEqual(['bafy-a', 'bafy-dishes']);
    expect(rows.map((r) => r.kind)).toEqual(['task', 'task', 'break']);
  });
});

describe('an interstitial row with no id is a genuine anchor', () => {
  it('converts Lunch to a break, which is what has nothing to address', () => {
    const row = oneRow({ task: 'Lunch', time: '12:30', interstitial: true });
    expect(row).toEqual({ kind: 'break', time: '12:30', task: 'Lunch' });
  });

  it('treats a blank id as no id, not as an id', () => {
    // `''` is a real shape on this wire and `??` would have let it through as an "id".
    const row = oneRow({ id: '', task: 'Rest or light activity', interstitial: true });
    expect(row.kind).toBe('break');
  });
});

describe('a block carries its id in project_id', () => {
  it('counts project_id as having an id, so an interstitial block stays a block', () => {
    const row = oneRow({
      task: 'Work on IOP and recovery',
      block: true,
      project_id: 'bafyreihsi3mak',
      chunk_min: 25,
      interstitial: true,
    });

    expect(row).toMatchObject({
      kind: 'block',
      id: 'bafyreihsi3mak',
      task: 'Work on IOP and recovery',
      chunkMin: 25,
    });
  });

  it('still resolves an ordinary block’s id from project_id', () => {
    const row = oneRow({
      task: 'Work on the job search',
      block: true,
      project_id: 'bafyreic3jgl5z',
      chunk_min: 45,
    });
    expect(row).toMatchObject({ kind: 'block', id: 'bafyreic3jgl5z' });
  });
});

describe('project_id on a NON-block row is the parent project, not the row', () => {
  /**
   * `plan_generate.py:734` sets `project_id` on ordinary task rows to their PARENT project's id.
   * An id-less anchor that happens to carry one must therefore still be a break: reading the
   * project's id as the row's own would address the wrong Anytype object entirely.
   */
  it('does not let a parent project’s id rescue an id-less anchor', () => {
    const row = oneRow({ task: 'Lunch', interstitial: true, project_id: 'bafyrei-household' });
    expect(row).toEqual({ kind: 'break', time: '', task: 'Lunch' });
  });

  it('gives an id-less ordinary task an empty id rather than its project’s', () => {
    const row = oneRow({ task: 'Rest or light activity', project_id: 'bafyrei-household' });
    expect(row).toMatchObject({ kind: 'task', id: '' });
  });
});
