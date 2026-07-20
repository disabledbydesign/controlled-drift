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

describe('an id-less row is a break EVEN WHEN it is not flagged interstitial', () => {
  // The real payload does NOT flag meals/fillers interstitial: live 2026-07-20, both "Lunch" and
  // "Rest — stand up, stretch, move" arrive `interstitial:false` with no id. Read as `kind:'task'`
  // with id '' they hit `TaskRow`'s `node(idx,'') === null` guard and render NOTHING — a silent gap
  // in the schedule. A row with no addressable id has nothing to check off; it is a break.
  it('converts an id-less Lunch that is not flagged interstitial', () => {
    const row = oneRow({ task: 'Lunch', time: '12:30', interstitial: false });
    expect(row).toEqual({ kind: 'break', time: '12:30', task: 'Lunch' });
  });

  it('converts an id-less model-authored filler that is not flagged interstitial', () => {
    const row = oneRow({ task: 'Rest — stand up, stretch, move', time: '17:00' });
    expect(row.kind).toBe('break');
  });
});

describe('an interstitial row with no id is a genuine anchor', () => {
  it('converts Lunch to a break, which is what has nothing to address', () => {
    const row = oneRow({ task: 'Lunch', time: '12:30', interstitial: true });
    expect(row).toEqual({ kind: 'break', time: '12:30', task: 'Lunch' });
  });

  it('treats a blank id as no id, not as an id', () => {
    // `''` is a real shape on this wire. NOTE: this row is NOT a block, so it does not by itself
    // distinguish `||` from `??` anywhere in `usableId` — both operators leave it a break. The
    // fixture that actually separates them is the blank-id BLOCK below.
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

  /**
   * THE FIXTURE THAT SEPARATES `||` FROM `??`, and the reason it had to be written: the change
   * that introduced `||` was described as pinned by tests and was not. Every other block fixture
   * here OMITS `id`, and `undefined ?? x` and `undefined || x` both give `x` — so reverting the
   * operator left the whole suite green.
   *
   * A blank id is a real shape on this wire, and `'' ?? p` is `''` — a block whose id resolved to
   * the empty string is the uncheckoffable ghost row again. Only `||` reaches `project_id` here.
   */
  it('resolves a block’s id from project_id even when id arrives BLANK, not just absent', () => {
    const row = oneRow({
      task: 'Work on IOP and recovery',
      block: true,
      id: '',
      project_id: 'bafyreihsi3mak',
      chunk_min: 25,
    });
    expect(row).toMatchObject({ kind: 'block', id: 'bafyreihsi3mak' });
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

  it('makes an id-less row a break, and never carries its project’s id onto it', () => {
    // An id-less row that carries only its PARENT project's id has nothing of its own to
    // address, so it is a break (which renders) rather than a task with id '' (which hit
    // TaskRow's null-node guard and vanished — the schedule gap fixed 2026-07-20). The security
    // property the earlier fix guarded still holds, more strongly: a break has no `id` field at
    // all, so the parent's id cannot leak onto the row.
    const row = oneRow({ task: 'Rest or light activity', project_id: 'bafyrei-household' });
    expect(row.kind).toBe('break');
    expect('id' in row).toBe(false);
  });

  /**
   * `block_project` DOES NOT MEAN "this row is a block". `plan_generate.py:726-735` sets it on
   * ORDINARY TASK rows and `continue`s past every row where `block` is true, so `block_project`
   * being set implies `block` is falsy and `project_id` is the row's PARENT PROJECT.
   *
   * `usableId` used to gate its `project_id` fallback on `block || block_project`, which made a
   * task row answer with its PARENT's id.
   *
   * ⚠ MEASURED, NOT ASSUMED: this particular row does NOT change under that gate, because the
   * task branch of `conv` reads `it.id ?? ''` directly and never calls `usableId`. Mutating the
   * gate back leaves this test green — it is kept as a positive statement of the rule, and as the
   * guard that catches a future change routing the task branch through `usableId`. The fixture
   * that DOES bite is the interstitial one below; see its note.
   */
  it('never lets block_project address an id-less row as its parent project', () => {
    const row = oneRow({
      task: 'Draft the cover letter',
      block_project: true,
      project_id: 'bafyrei-parent-project',
      duration_min: 30,
    });
    // block_project does not make usableId return the parent (that gate was removed), so this
    // id-less row is a break — and a break carries no `id`, so the parent's id cannot reach the
    // wire. The rule the earlier fix stated ("not addressable as its parent") holds; the row now
    // renders instead of vanishing.
    expect(row.kind).toBe('break');
    expect('id' in row).toBe(false);
  });

  /**
   * THE ROW THE WRONG GATE ACTUALLY CHANGED, and the only one — verified by mutation, not read
   * off the code. `usableId` is consulted in exactly two places: the `interstitial && !usableId`
   * test, and the block branch's own `id`. So a `block_project` row is affected only when it is
   * ALSO interstitial: the parent's id made `usableId` non-empty, the break test failed, and a
   * fixed anchor ("Rest or light activity") was converted to a task row instead — a row with no
   * id, which `PriorityList` then filters out entirely. She loses the anchor from her day.
   */
  it('keeps a block_project row a BREAK when it is a short id-less anchor', () => {
    // The parent's id must not rescue an anchor into looking addressable.
    const row = oneRow({
      task: 'Rest or light activity',
      interstitial: true,
      block_project: true,
      project_id: 'bafyrei-parent-project',
    });
    expect(row).toEqual({ kind: 'break', time: '', task: 'Rest or light activity' });
  });
});
