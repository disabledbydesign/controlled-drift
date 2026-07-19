# Shape-Driven Plan Rendering Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A fragmented (priority-shape) day renders as the numbered list v4 designed for it, with work blocks appearing as numbered rows that expand to their arcs — instead of every task landing inside one undifferentiated container.

**Architecture:** Three small frontend changes, no data-shape change and no backend change. (1) The Today view derives its rendering from `plan.shape`, which the app already receives and currently ignores. (2) `PriorityList` keeps the `PlanItem` it already fetches instead of discarding it for a graph lookup, so it can branch on `kind === 'block'` and render the arc. (3) The reason a day is a list comes from the server's existing `header` field rather than a hardcoded sentence.

**Tech Stack:** React 19 + Vite 8 + TypeScript (`app/`), vitest.

---

## ⚠ REVISION 2026-07-18 — read this before anything else

**The first draft of this plan was wrong in three compounding ways.** All four critic-swarm reviewers found the same defects independently. Recording them because the corrections below only make sense against them, and because the *method* failure is the reusable lesson.

1. **It proposed rebuilding backend work that already ships.** The claim "Python does not enrich priority-shape items with block/arc structure" was FALSE. `plan_generate.py` calls `_group_block_project_items` on priority items, and the live payload carries `block: true`, `project_id`, `chunk_min`, `absorbed_ids`, and a six-step `arc` whose every step has a real, resolving task id. `adapt.ts:151` already maps all of it.
   **Root cause of the error:** the payload was checked for a field named `kind` — the *app-side* name — against the *wire* payload, which spells it `block`. Every item returned `None` and that silence was reported as a finding. §9.1 of `BUILD_DOC.md` names exactly this: state HOW you checked and whether the method could have missed.

2. **It proposed splitting priority items out of `plan.blocks` into a new `Plan.items`.** That would have blanked the Today tab on a real priority day (`workItems` iterates `plan.blocks` and nothing else) AND silently killed every arc checkbox (`toggleArcStep` addresses steps as `plan.blocks[bandIndex].items[itemIndex].arc[stepIndex]` and returns a no-op on a miss). Both with a fully green suite.
   **The correction: DO NOT TOUCH THE DATA SHAPE.** The single container band is a container, not a label — `adapt.ts` says so. Keeping it is what makes arc addressing work.

3. **It hardcoded a June-facing sentence explaining why the day was a list.** `resolve_output_shape` reaches `priority` by more than one path, and her currently active period sets `Output format` to `"Priority list"` explicitly — she CHOSE the list. The sentence would have been false on the day it shipped, while citing spec guard #6 about telling her why. The server already sends the true per-day reason in `header`, and nothing renders it.

**The check that would have caught all three** is one `curl` of `/api/plan` read against `PriorityList.tsx`, before writing tasks rather than after.

---

## Global Constraints

- Branch `feat/overlay-actionable`. Commit only files this plan names — another thread owns `docs/`.
- **No metaphors in any June-facing string.** Literal words only. Agent-facing comments exempt.
- **Inline style objects stay inline.** Do NOT convert v4's inline styles to CSS classes or variables.
- No silent failures — raise, never bare `assert`, never proceed as if a failed step succeeded.
- **A test is unverified until you have watched it fail.** Every task includes a mutation check.
- `vite.config` sets `globals: false` — component tests MUST call `afterEach(cleanup)` explicitly.
- Do NOT restart the server. It runs under launchd with `CD_BIND=0.0.0.0`, which is what lets her phone reach it; a second manual copy binds localhost-only and breaks that.
- Do NOT add clock times to a priority plan. `AI_LAYER_SPEC.md:233` — a clock schedule cannot express "a couple of hours, whenever they come", and forcing one is an instance of her own output-format-bias finding. Generating times would be fabricating data.

## Background an implementer needs

**The two shapes.** `scripts/focus_period.py::resolve_output_shape` returns `'clock'` or `'priority'`: an explicit `Output format` wins; on `Auto` it is `priority` if today is inside the availability window. ⚠ The backend writes the word **`"clock"`**; `adapt.ts` normalizes it to `'schedule'`. Those are the same shape under two names — do not "fix" one to match the other without following both call sites.

**What a box is, in the design.** v4's `band()` (mockup line 1064) makes each time band a card in the hardware theme (border, 2px blue left accent, `r.card` radius, panel background, bevel) and a hairline-separated section in celestial. So a clock day shows one box per band. A priority day has no bands, which is why everything currently lands in one.

**What a priority day should look like.** v4's `priorityList()` (mockup line 1024) is NOT boxes: numbered rows (`1.` `2.`), a 15px rose checkbox, the title with a project prefix, ▲▼ reorder buttons, each row separated by a hairline. `app/src/components/today/PriorityList.tsx` already implements this faithfully.

**What v4 does NOT answer, and June has now decided.** v4's priority list has no handling for work blocks — its fixture data was always clock-shaped, so a block inside a numbered list never came up. It would render the block as a plain numbered row titled from the graph node, with no arc. **June's decision (2026-07-18): a block is a numbered row that expands to its arc.** That is what Task 3 builds.

**What a block is.** Per `docs/display_grain_design.md` §REVISION 2026-07-14: a rendering layer over real, still-selected tasks. Arc steps carry real task ids and check off through the normal path. A previous build made the block a synthetic *selection* unit; it matched the design doc, passed 599 tests, severed real tasks from id-resolution, and had to be reverted. Do not reintroduce that frame.

---

## File Structure

| File | Responsibility after this plan |
|---|---|
| `app/src/fixtures/types.ts` | `Plan.shape` narrowed from `string` to a union so a wrong value cannot typecheck. |
| `app/src/api/adapt.ts` | Carries the server's `header` through to `Plan`. No change to the block/arc mapping — it is already correct. |
| `app/src/model/plan.ts` | Gains an addressed variant of `workItems` returning each item with its band/item index, so a consumer can drive `toggleArcStep`. |
| `app/src/components/today/TodayPanel.tsx` | Derives the view from `plan.shape`; offers the toggle only on a clock plan; renders `plan.header` as the reason. |
| `app/src/components/today/PriorityList.tsx` | Renders a block as a numbered row that expands to its arc; stops marking a Project done. |

---

### Task 1: Narrow `Plan.shape`, and carry the server's real reason

**Files:**
- Modify: `app/src/fixtures/types.ts:196`, `app/src/api/adapt.ts`
- Test: `app/src/api/__tests__/adaptShape.test.ts` (create)

**Interfaces:**
- Produces: `Plan.shape: 'priority' | 'schedule'` and `Plan.header: string`.

**Context:** `shape` is typed `string`, so `P.shape === 'schedule'` typechecks against any value and a mismatch fails silently and permanently. `header` is on the wire (`plan_generate.py:361` — "one line naming what today's shape is and why"), is absent from `LivePlan`, and has zero consumers in `app/src`.

- [ ] **Step 1: Write the failing test**

```ts
// app/src/api/__tests__/adaptShape.test.ts
import { describe, expect, it } from 'vitest';
import { planFromLive } from '../adapt.ts';
import type { LivePlan } from '../adapt.ts';

const LIVE_PRIORITY = {
  shape: 'priority',
  header: "Today's fragmented—start at the top when you get a window.",
  woven_frame: 'w',
  items: [{ project: 'household', task: 'Do the dishes', id: 'bafy-dishes' }],
} as unknown as LivePlan;

describe('planFromLive — shape and reason', () => {
  it('carries the server-generated header, which is the only honest reason for the shape', () => {
    // resolve_output_shape reaches 'priority' by more than one path — an explicit
    // "Priority list" setting OR Auto-plus-availability-window — so the app CANNOT
    // derive the reason locally without sometimes asserting a cause that is not the cause.
    expect(planFromLive(LIVE_PRIORITY).header).toBe(
      "Today's fragmented—start at the top when you get a window.",
    );
  });

  it('keeps priority items inside the container band, where arc addressing works', () => {
    const p = planFromLive(LIVE_PRIORITY);
    expect(p.shape).toBe('priority');
    expect(p.blocks.length).toBe(1);            // the container band — NOT a label she reads
    expect(p.blocks[0]!.items.length).toBe(1);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd app && npx vitest run src/api/__tests__/adaptShape.test.ts`
Expected: FAIL — `header` is undefined.

- [ ] **Step 3: Narrow the type and add `header`**

In `app/src/fixtures/types.ts`, replace `shape: string;` in `interface Plan`:

```ts
  /**
   * ⚠ Narrowed from `string` 2026-07-18. As a bare string, `shape === 'schedule'` typechecked
   * against any value, so a wire-word change or a typo would silently render every plan — clock
   * plans included — through the wrong branch, permanently and with no error.
   *
   * NOTE the two names for one shape: the backend writes `"clock"` (`plan_generate.py:1398`);
   * `adapt.ts` normalizes it to `'schedule'`. Follow both call sites before changing either.
   */
  shape: 'priority' | 'schedule';
  /**
   * The server's one-line statement of what today's shape is and why (`plan_generate.py:361`).
   * The ONLY honest source for that reason: `resolve_output_shape` reaches `priority` by more
   * than one path, so anything the client composes locally would assert a cause it cannot know.
   */
  header: string;
```

- [ ] **Step 4: Carry `header` through the adapter**

Add `header?: string` to `LivePlan`, and `header: str(live.header)` to the returned `Plan`. Missing becomes `''`, never `undefined`.

- [ ] **Step 5: Run and watch it pass.** Fix any fixture that now needs `header: ''`; do NOT weaken the type to optional.

- [ ] **Step 6: Mutation-check.** Drop the `header` mapping — the first test must fail. Change the adapter to return `blocks: []` for priority — the second must fail. Restore both.

- [ ] **Step 7: Full suite + typecheck**

Run: `cd app && npx tsc --noEmit && npx vitest run`

- [ ] **Step 8: Commit**

```bash
git add app/src/fixtures/types.ts app/src/api/adapt.ts app/src/api/__tests__/adaptShape.test.ts
git commit -m "fix(surface): narrow the plan shape type and carry the server's own reason"
```

---

### Task 2: An addressed item list, so a consumer can drive arc check-off

**Files:**
- Modify: `app/src/model/plan.ts`
- Test: `app/src/model/__tests__/` — match the existing filename convention in that folder

**Interfaces:**
- Produces: `export function addressedWorkItems(plan: Plan): AddressedItem[]` where `AddressedItem = { item: PlanItem; bandIndex: number; itemIndex: number }`. Breaks are excluded, exactly as `workItems` excludes them.

**Why this exists:** `PriorityList` currently reduces its items to bare ids and re-derives each row from the graph, so it cannot see `kind`, `arc`, or `chunk_min`. `ArcStep` needs `(bandIndex, itemIndex, stepIndex)` to address a step — and the reorderable `priOrder` means a row's position in the list is NOT its position in the band. The address must travel with the item.

`workItems` stays as it is; other callers depend on it.

- [ ] **Step 1: Write the failing test** — a plan with two bands returns each non-break item with the band and item index at which it actually sits, and those indices resolve back to the same item via `plan.blocks[bandIndex].items[itemIndex]`.

- [ ] **Step 2: Run it and watch it fail.**

- [ ] **Step 3: Implement**

```ts
export interface AddressedItem {
  item: PlanItem;
  bandIndex: number;
  itemIndex: number;
}

/**
 * `workItems`, but each item keeps the address `toggleArcStep` needs.
 *
 * The list a consumer renders can be reordered (`priOrder`), so a row's position on screen is
 * not its position in the plan. Passing the on-screen index to `toggleArcStep` would address a
 * different step — or none, which that function answers with a SILENT no-op.
 */
export function addressedWorkItems(plan: Plan): AddressedItem[] {
  const out: AddressedItem[] = [];
  plan.blocks.forEach((b, bandIndex) => {
    b.items.forEach((item, itemIndex) => {
      if (item.kind !== 'break') out.push({ item, bandIndex, itemIndex });
    });
  });
  return out;
}
```

- [ ] **Step 4: Run and watch it pass.**

- [ ] **Step 5: Mutation-check.** Return the on-screen index as `itemIndex` (i.e. a running counter instead of the per-band index) — the round-trip assertion must fail. Restore.

- [ ] **Step 6: Full suite + typecheck, then commit**

```bash
git add app/src/model/plan.ts app/src/model/__tests__/
git commit -m "feat(surface): items carry the address arc check-off needs"
```

---

### Task 3: A block in the priority list is a numbered row that expands to its arc

**Files:**
- Modify: `app/src/components/today/PriorityList.tsx`
- Modify: `app/src/components/today/__tests__/` — extract the existing ctx factory (see Step 0)
- Test: `app/src/components/today/__tests__/priorityBlock.test.tsx` (create)

**June's decision (2026-07-18):** a block is a numbered row that expands to its arc. Collapsed by default — on a fragmented day the point is a short scannable list.

**⚠ READ `WorkBlock.tsx` BEFORE WRITING ANYTHING.** It already implements exactly this behaviour for the schedule view: collapse via `ctx.ui.blocksOpen[entryKey]`, arc rendered through `ArcStep` with `bandIndex`/`itemIndex`/`stepIndex`, and a check wired to `ctx.ui.chunked[entryKey]`. **Two independent reviewers refused the previous version of this task for instructing a hand-rebuild of that component.** You are not writing new block behaviour; you are giving the existing behaviour a numbered-row skin. Anything you cannot reuse directly, state why in a comment.

**The checkbox writes `chunked`, not `toggleDone`.** This is not a free choice — `docs/display_grain_design.md` §REVISION 2026-07-14 §B: "The block *header* still carries the project-level 'did a chunk today' check." `WorkBlock.tsx:73` implements it. The previous version of this task said only "do NOT wire it to `toggleDone`" and never said what to wire, which would have shipped an inert checkbox on her main path.

**Use the SAME state keys as the schedule view** — `entryKey = bandIndex + '-' + itemIndex` (`Band.tsx:112`). Keying by row id instead would give the same block two independent expand-and-chunk states that silently diverge when she flips the toggle.

**The project prefix must not stutter.** A plain row renders `proj.title + ' · ' + n.title`. For the block, the plan phrasing is `"Work on IOP and recovery"` and `nearestProject` resolves to `"IOP and recovery"` — so the naive path renders **"IOP and recovery · Work on IOP and recovery"**. Render NO project prefix on a block row; the plan phrasing already names the thread.

- [ ] **Step 0: Extract the shared test factory (its own commit)**

`today.test.tsx` has a module-local, non-exported helper `ctxWith(ui, plan)` (~line 79). Move it to `app/src/components/today/__tests__/ctxFactory.tsx`, export it, and import it in `today.test.tsx`. Change nothing about its behaviour. Run the suite — it must stay green at its current count. Commit separately so a later reviewer can see this was a move, not a rewrite.

- [ ] **Step 1: Write the failing tests**

⚠ Every assertion below is POSITIVE — it names what must be true. An earlier draft asserted only that a wrong write did NOT happen, which passes just as well against a checkbox wired to nothing.

```tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { PriorityList } from '../PriorityList.tsx';
import { ctxWith } from './ctxFactory.tsx';
afterEach(cleanup);   // vite.config sets globals:false — auto-cleanup never registers

// Build a priority-shaped plan whose single container band holds one block with a 2-step arc.
// Mirror the LIVE payload shape: block id absent, project_id set, arc steps carrying real ids.

describe('PriorityList — a block row', () => {
  it('renders the plan phrasing, with no project prefix stuttering in front of it', () => {
    render(<PriorityList ctx={blockCtx()} />);
    expect(screen.getByText('Work on IOP and recovery')).toBeTruthy();
    expect(screen.queryByText(/IOP and recovery · Work on/)).toBeNull();
  });

  it('is collapsed until tapped, then shows its arc steps', () => {
    const up = vi.fn();
    render(<PriorityList ctx={blockCtx({ up })} />);
    expect(screen.queryByText('Read chapter 2')).toBeNull();
    fireEvent.click(screen.getByText('Work on IOP and recovery'));
    // The open-state write must use the band/item address, NOT the row id.
    expect(up).toHaveBeenCalledWith({ blocksOpen: expect.objectContaining({ '0-0': true }) });
  });

  it('checking it records a chunk — a POSITIVE assertion, so an inert box fails', () => {
    const up = vi.fn();
    render(<PriorityList ctx={blockCtx({ up })} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(up).toHaveBeenCalledWith({ chunked: expect.objectContaining({ '0-0': true }) });
  });

  it('does NOT mark the underlying project done', () => {
    const apply = vi.fn();
    render(<PriorityList ctx={blockCtx({ apply })} />);
    fireEvent.click(screen.getAllByLabelText('mark done')[0]!);
    expect(apply).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run and watch all four fail.**

- [ ] **Step 3: Give `PriorityList` the plan item and the address**

It already calls `workItems(ctx.plan)` and then discards the items for a graph lookup. Build a lookup from row id to `{ item, bandIndex, itemIndex }` by walking `ctx.plan.blocks`, so a row can reach both its `PlanItem` and its address. Keep the existing `priOrder` behaviour and id-keyed ordering exactly as they are.

- [ ] **Step 4: Branch on the block kind**

When the entry's item has `kind === 'block'`: render the same numbered row shell as a task row (same padding, same hairline, same numbered gutter), with the title from `item.task`, no project prefix, the checkbox writing `ctx.ui.chunked[entryKey]`, and the title tapping `ctx.ui.blocksOpen[entryKey]`. When open, map the arc through the imported `ArcStep` passing `bandIndex`, `itemIndex` and `stepIndex`.

A block with an empty or absent `arc` renders as a bare row with no expander — `display_grain_design.md` decision 4 (a container project with no discrete tasks is a bare did-a-chunk block).

- [ ] **Step 5: Run and watch all four pass.**

- [ ] **Step 6: Mutation-check each**

Key `blocksOpen` by row id → the address assertion fails. Render `n.title` → the phrasing assertion fails. Add the project prefix → the stutter assertion fails. Wire the checkbox to `toggleDone` → the chunk and the no-apply assertions both fail. Remove the checkbox handler entirely → the chunk assertion fails (this is the one the old test could not catch). Restore after each.

- [ ] **Step 7: Full suite + typecheck, then commit**

```bash
git add app/src/components/today/PriorityList.tsx app/src/components/today/__tests__/
git commit -m "feat(surface): a block in the priority list opens to its arc"
```

---

### Task 4: The view follows the plan's shape

**Files:**
- Modify: `app/src/components/today/TodayPanel.tsx:44`; the segment ROW is at `:164-179` (`:46` is the `seg` helper's definition, not the row)
- Test: `app/src/components/today/__tests__/shapeRender.test.tsx` (extend)

**Context:** `TodayPanel.tsx:44` reads `ctx.ui.todayShape || 'schedule'` — a mockup default, whose fixture was always clock-shaped. The plan's own shape is never consulted. This is the single true defect the original plan found.

⚠ **The existing test at `today.test.tsx:116` will NOT catch a regression here** — its fixture is `seedPlan`, whose `shape` is `'schedule'`, so it keeps passing through the old path regardless. Do not treat it as coverage.

- [ ] **Step 1: Write the failing test** — a `shape: 'priority'` plan renders the priority list even when `ui.todayShape` is `'schedule'`; a `shape: 'schedule'` plan still offers both toggle segments.

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Derive the view from the plan**

```tsx
  // The SERVER decides the shape from her focus period (focus_period.resolve_output_shape).
  // The app used to ignore that and default to the mockup's 'schedule', which is how a
  // priority plan ended up rendered through one unlabelled container band.
  // A clock plan CAN render either way — `workItems` flattens bands into a ranked list — so
  // the toggle is real there and only there. A priority plan has no clock times to show, and
  // inventing them is the fabrication this whole surface is being cleaned of.
  const canToggle = P.shape === 'schedule';
  const shape = canToggle ? ctx.ui.todayShape || 'schedule' : 'priority';
```

- [ ] **Step 4: Show the server's reason instead of a dead control**

```tsx
      {canToggle ? (
        <>
          {seg('schedule', 'Schedule')}
          {seg('priority', 'Priority')}
        </>
      ) : P.header ? (
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.45 }}>{P.header}</div>
      ) : null}
```

⚠ Render `P.header` **verbatim**. Do NOT compose a local explanation — the client cannot know which path produced the shape, and a confident wrong reason is worse than none. If `header` is empty, show nothing.

⚠ **The row's first child is an uppercase "View" label with `marginRight:'auto'` (`:166-175`).** Replacing only the segments leaves that label heading a sentence with no control under it. Hide the label too when `canToggle` is false.

⚠ **Three statements of the same fact would stack.** Today's live payload has `woven_frame` = "Today is all about supporting your girlfriend's move—household and logistics come first…", the new `header` = "Today's fragmented—start at the top when you get a window. Household and moving prep come first…", and `PriorityList.tsx:71` = "No clock times — a ranked to-do list to pull from." `TodayPanel:159` already renders the woven frame in the rose card. Cut `PriorityList`'s line when the header is shown, so she reads the point once. Say what you cut in the commit message.

⚠ `header` is unbounded LLM output going into a June-facing surface bound by the no-metaphors access rule. Nothing constrains tomorrow's. Render it verbatim (composing locally is the fabrication this replaced) and record the exposure in the commit message as a known gap.

- [ ] **Step 5: Run and watch it pass.**

- [ ] **Step 6: Mutation-check.** Restore `ctx.ui.todayShape || 'schedule'` — the test must fail. Restore.

- [ ] **Step 7: Full suite + typecheck, then commit**

```bash
git add app/src/components/today/TodayPanel.tsx app/src/components/today/__tests__/
git commit -m "fix(surface): the plan's own shape decides how it renders"
```

---

### Task 5: Integration and live-verify — REQUIRED, not a test

**Not done when tests pass. Done when June's real plan renders correctly in the running app.**

- [ ] **Step 1: Build the bundle.** `app/dist` is gitignored and port 5050 serves the BUILT bundle, so source changes are invisible there until this runs.

```bash
cd app && npx vite build
```

- [ ] **Step 2: Record the real payload**

```bash
curl -s http://localhost:5050/api/plan | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['shape'], '| header:', (d.get('header') or '')[:60]); [print(' ', i.get('task','')[:40], '| block:', bool(i.get('block')), '| arc:', len(i.get('arc') or [])) for i in (d.get('items') or [])]"
```

If today's shape is `clock`, the priority path cannot be verified against real data — **say so plainly** rather than implying success, and verify the clock path live plus the priority path against fixtures.

- [ ] **Step 3: Drive the real app**

```bash
agent-browser open "http://localhost:5050/app/"
```

⚠ `agent-browser screenshot` HANGS INDEFINITELY — do not call it. Use DOM/text reads, or `cd app && node scripts/shot.mjs "today" celestial`.

State each as observed or not:
1. Rows render as separate numbered rows with hairline separators — not one undifferentiated container.
2. No clock times anywhere on a priority day.
3. The Schedule/Priority toggle is not offered as a dead control; the server's `header` line is shown instead.
4. The block renders as ONE collapsed numbered row reading "Work on IOP and recovery".
5. Tapping it reveals its arc steps.

- [ ] **Step 4: Confirm the arc actually functions**

Tap an arc step and confirm the **"here" marker moves to the next step** — the rose rail, wash and glow shift. This is in-session state change, not persistence (persistence is the seam plan's). `toggleArcStep` answers a bad address with a SILENT no-op, so a checkbox that renders proves nothing. **This step is what catches a dead control.**

- [ ] **Step 5: Reconcile payload against screen**

Every item in the payload appears exactly once on screen, and no row appears that is not in the payload. ⚠ A task listed in the block's `absorbed_ids` legitimately appears once *as an arc step* and NOT as its own row — that is correct, not a ghost.

- [ ] **Step 6: Report honestly**, including anything unverified. Do NOT mark done on a green suite.

- [ ] **Step 7: Commit any fixes the live run surfaced.**

---

## After this plan

1. **Cross-family review** — `~/.claude/skills/requesting-code-review/github_models_review.py`. Non-Claude family. ⚠ ~8k cap: chunk per file, sending a file and its tests together or the reviewer false-flags "no tests." If it errors, fall back to a Claude review **with a visible note that the cross-family pass was skipped and why**.
2. **June drives the surface** and reacts.
3. **Then the persistence seam plan.** Arc-step and block check-off persistence land there — which is why Task 5 Step 4 checks state change only.

**Deliberately out of scope, recorded so it is not lost:**
- `still_here` has 28 computed entries and renders nowhere, including time-sensitive items. Marked open as contract §6 Q5.
- The two-names-for-one-shape mismatch (`"clock"` on the wire, `'schedule'` in the app) is documented in Task 1 but not unified.
- Adding a `shape_reason` to the payload would be better than `header` for this specific job. `header` is honest and already exists; a dedicated field is the cleaner eventual answer.
