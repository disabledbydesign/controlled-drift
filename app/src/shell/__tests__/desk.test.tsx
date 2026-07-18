/**
 * Behaviour tests for the DESKTOP render path (Task 10).
 *
 * These pin the five things this task is most likely to get quietly wrong:
 *   1. the phone/desktop choice is a WIDTH breakpoint, and the state survives crossing it
 *   2. the Map is a Finder COLUMN BROWSER — `deskPath.length + 1` columns, and drilling from
 *      column k truncates the path to k rather than appending to the end
 *   3. `dnd:true` is actually ON here (v4:747 is the only call site in the mockup), so a row
 *      re-parents on drop — and an INVALID drop is a SILENT no-op, which is v4's shape and is
 *      pinned so a later change cannot quietly alter it without a failing test
 *   4. the divider drag writes `widths` and clamps to v4's 220–700
 *   5. the same components render on both paths — Routines loses only its `MapControls`
 *      chrome (the desktop toolbar carries it), not its own filter chips
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup, within, act } from '@testing-library/react';
import { themes } from '@tokens';
import { Surface, DESKTOP_MIN_WIDTH } from '../Surface.tsx';

afterEach(cleanup);

const T = themes.celestial;

/**
 * jsdom has no `matchMedia`. This stub answers the ONE query `Surface` asks, from a width we
 * control, and keeps the listener so a test can move the viewport across the breakpoint
 * mid-session — which is the only way to check that state survives the swap.
 */
let listeners: Array<(e: MediaQueryListEvent) => void> = [];
let width = 420;

function setWidth(next: number) {
  const wasWide = width >= DESKTOP_MIN_WIDTH;
  width = next;
  const isWide = next >= DESKTOP_MIN_WIDTH;
  if (wasWide !== isWide) {
    // `act` because the listener drives a React state update; without it the swap is queued
    // and the very next assertion still sees the old shell.
    act(() => listeners.forEach((l) => l({ matches: isWide } as MediaQueryListEvent)));
  }
}

beforeEach(() => {
  listeners = [];
  width = 420;
  vi.stubGlobal(
    'matchMedia',
    (q: string) =>
      ({
        media: q,
        get matches() {
          return width >= DESKTOP_MIN_WIDTH;
        },
        addEventListener: (_: string, l: (e: MediaQueryListEvent) => void) => listeners.push(l),
        removeEventListener: (_: string, l: (e: MediaQueryListEvent) => void) => {
          listeners = listeners.filter((x) => x !== l);
        },
      }) as unknown as MediaQueryList,
  );
});

function mount() {
  return render(<Surface T={T} name="celestial" setTheme={() => {}} />);
}

/** The desktop Map's columns carry `data-desk-col`; nothing on the phone path does. */
const cols = (c: HTMLElement) => [...c.querySelectorAll('[data-desk-col]')] as HTMLElement[];
const handles = (c: HTMLElement) => [...c.querySelectorAll('[data-drag-handle]')] as HTMLElement[];

function goMap(container: HTMLElement) {
  fireEvent.click(screen.getByRole('button', { name: 'Map' }));
  return container;
}

/** The draggable element is the row's inner line, not the wrapper. */
function rowIn(container: HTMLElement, col: number, title: string): HTMLElement {
  const panel = container.querySelector(`[data-desk-col="${col}"]`) as HTMLElement;
  const label = within(panel).getByText(title);
  let el: HTMLElement | null = label;
  while (el && el.parentElement !== panel) el = el.parentElement;
  if (!el) throw new Error(`row "${title}" not found in column ${col}`);
  return el;
}

/**
 * A `dataTransfer` good enough for the handlers under test: they call `setData` and assign
 * `effectAllowed` / `dropEffect`. jsdom supplies none of it.
 */
function dt() {
  return { setData: vi.fn(), getData: vi.fn(), effectAllowed: '', dropEffect: '' };
}

describe('the phone/desktop switch', () => {
  it('renders the PHONE shell below the breakpoint and the DESKTOP shell at or above it', () => {
    setWidth(DESKTOP_MIN_WIDTH - 1);
    const a = mount();
    goMap(a.container);
    expect(cols(a.container)).toHaveLength(0);
    // The phone Map's own controls; the desktop puts search in the toolbar instead.
    expect(a.container.querySelectorAll('[data-drag-handle]')).toHaveLength(0);
    cleanup();

    setWidth(DESKTOP_MIN_WIDTH);
    const b = mount();
    goMap(b.container);
    expect(cols(b.container)).toHaveLength(1);
  });

  it('keeps the app state across the breakpoint — a resize must not re-seed the fixtures', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    expect(cols(container)).toHaveLength(2);

    // Drag a project out of Scholarly practice and onto a different goal.
    const src = rowIn(container, 1, 'Reframe paper');
    const dst = rowIn(container, 0, 'Builder practice');
    const t = dt();
    fireEvent.dragStart(src.firstElementChild!, { dataTransfer: t });
    fireEvent.dragOver(dst.firstElementChild!, { dataTransfer: t });
    fireEvent.drop(dst.firstElementChild!, { dataTransfer: t });
    expect(within(container.querySelector('[data-desk-col="1"]')!).queryByText('Reframe paper')).toBeNull();

    // Cross to the phone shell. Had each shell owned its own `useAppState`, this would
    // remount and the move would vanish.
    setWidth(420);
    expect(cols(container)).toHaveLength(0);
    fireEvent.click(screen.getByText('Builder practice'));
    expect(screen.getByText('Reframe paper')).toBeTruthy();
  });
});

describe('the Finder column browser', () => {
  it('renders one column per level, with a divider between every pair', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    expect(cols(container)).toHaveLength(1);
    // At the root there is only the detail divider; each new column adds one of its own.
    expect(handles(container).map((h) => h.dataset.dragHandle)).toEqual(['detail']);

    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    expect(cols(container)).toHaveLength(2);
    expect(handles(container).map((h) => h.dataset.dragHandle)).toEqual(['deskcol', 'detail']);
  });

  it('drilling from column k TRUNCATES the path to k — it does not append to the end', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    expect(cols(container)).toHaveLength(2);

    // Pick a DIFFERENT goal back in column 0. The second column must be replaced, not added to.
    fireEvent.click(within(rowIn(container, 0, 'Builder practice')).getByText('Builder practice'));
    expect(cols(container)).toHaveLength(2);
    expect(
      within(container.querySelector('[data-desk-col="1"]')!).queryByText('Reframe paper'),
    ).toBeNull();
  });

  it('the breadcrumb walks back out, and its back button is disabled at the root', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    const back = () => screen.getByRole('button', { name: 'back one level' });
    expect((back() as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    expect((back() as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(back());
    expect(cols(container)).toHaveLength(1);
  });

  it('tapping a LEAF opens the detail pane instead of adding a column', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    expect(screen.getByText(/Select an item to edit/)).toBeTruthy();

    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    fireEvent.click(within(rowIn(container, 1, 'Reframe paper')).getByText('Reframe paper'));
    expect(cols(container)).toHaveLength(3);

    // A TASK cannot be drilled into (v4:746 `canDrill`), so tapping it opens the editor and
    // sets `deskPath` to `slice(0, k)` — the columns to its LEFT stay, no fourth column opens.
    // Tapped in the deepest column that slice is the identity, so the count holds at 3.
    const task = 'Split Reframe and Welfare sections into separate papers';
    fireEvent.click(within(rowIn(container, 2, task)).getByText(task));
    expect(cols(container)).toHaveLength(3);
    expect(screen.queryByText(/Select an item to edit/)).toBeNull();
    expect(screen.getByRole('button', { name: 'close' })).toBeTruthy();
  });
});

describe('drag to re-parent — the one `dnd:true` call site (v4:747)', () => {
  it('is enabled here: a movable row on the desktop Map is draggable', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    // A GOAL is a root and cannot move, so no GOAL row in column 0 is draggable...
    //
    // ⚠ NARROWED IN TASK 11. This used to assert that column 0 held no draggable rows AT ALL.
    // That stopped being true when the orphan buckets landed there: an unfiled task or project
    // sits in column 0 and IS movable — which is the point of surfacing it, since dragging it
    // onto a project is how it gets filed. Asserting per-row rather than per-column keeps the
    // original claim (goals do not move) without asserting something the buckets disprove.
    const col0 = container.querySelector('[data-desk-col="0"]') as HTMLElement;
    for (const goal of ['Material survival', 'Scholarly practice', 'Builder practice']) {
      const row = rowIn(container, 0, goal);
      expect((row.firstElementChild as HTMLElement).getAttribute('draggable')).toBeNull();
    }
    // …and the orphan rows in the same column ARE draggable, so they can be filed.
    expect(col0.querySelectorAll('[draggable="true"]').length).toBeGreaterThan(0);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    // ...but the projects under it can.
    expect(
      container.querySelectorAll('[data-desk-col="1"] [draggable="true"]').length,
    ).toBeGreaterThan(0);
  });

  it('is NOT enabled on the phone Map', () => {
    setWidth(420);
    const { container } = mount();
    goMap(container);
    expect(container.querySelectorAll('[draggable="true"]')).toHaveLength(0);
  });

  it('a valid drop re-parents the node', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));

    const src = rowIn(container, 1, 'Reframe paper');
    const dst = rowIn(container, 0, 'Builder practice');
    const t = dt();
    fireEvent.dragStart(src.firstElementChild!, { dataTransfer: t });
    fireEvent.dragOver(dst.firstElementChild!, { dataTransfer: t });
    fireEvent.drop(dst.firstElementChild!, { dataTransfer: t });

    expect(
      within(container.querySelector('[data-desk-col="1"]')!).queryByText('Reframe paper'),
    ).toBeNull();
    fireEvent.click(within(rowIn(container, 0, 'Builder practice')).getByText('Builder practice'));
    expect(
      within(container.querySelector('[data-desk-col="1"]')!).getByText('Reframe paper'),
    ).toBeTruthy();
  });

  /**
   * ⭐ REWRITTEN IN TASK 11 — and this test is the reason the rewrite is legible.
   *
   * It used to assert that an invalid drop was a SILENT no-op, with a comment saying the
   * assertion was a flag: *"when Task 11's toast lands, it should fail, and the fix is to give
   * the guard a message — not to loosen the test."* It did fail, exactly there, on the
   * `not.toMatch(/cannot/)` line. The guard now has a message, so the assertion inverts.
   *
   * The silent behaviour was v4's, and this is an AUTHORISED DIVERGENCE from it — June asked for
   * it directly on 2026-07-18, having watched the surface light a row up as a valid target and
   * then decline without a word.
   */
  it('an INVALID drop (onto its own descendant) refuses VISIBLY and says why', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Builder practice')).getByText('Builder practice'));
    fireEvent.click(within(rowIn(container, 1, 'Build Controlled Drift')).getByText('Build Controlled Drift'));

    const before = container.querySelector('[data-desk-col="1"]')!.textContent;
    const src = rowIn(container, 1, 'Build Controlled Drift');
    const child = container.querySelector('[data-desk-col="2"]')!.firstElementChild as HTMLElement;
    const line = child.firstElementChild as HTMLElement;
    const t = dt();
    fireEvent.dragStart(src.firstElementChild!, { dataTransfer: t });
    fireEvent.dragOver(line, { dataTransfer: t });

    // 1. THE HOVER STATE TELLS THE TRUTH. The valid-target look is a blue DASHED outline; a
    //    target that will refuse must not wear it. `dropEffect` is the cursor half of the same
    //    answer, given before the mouse comes up.
    expect(line.style.outline).toContain('dotted');
    expect(line.style.outline).not.toContain('dashed');
    expect(t.dropEffect).toBe('none');

    fireEvent.drop(line, { dataTransfer: t });

    // 2. Nothing moved — the guard still holds.
    expect(container.querySelector('[data-desk-col="1"]')!.textContent).toBe(before);
    // 3. …and now something SAYS so, naming both objects rather than saying "invalid".
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Not moved');
    expect(alert.textContent).toContain('Build Controlled Drift');
    expect(alert.textContent).toContain('Daily plan pipeline');
  });

  it('a valid target still wears the valid look — the refusal style is not applied everywhere', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));

    const src = rowIn(container, 1, 'Reframe paper');
    const dst = rowIn(container, 0, 'Builder practice');
    const line = dst.firstElementChild as HTMLElement;
    const t = dt();
    fireEvent.dragStart(src.firstElementChild!, { dataTransfer: t });
    fireEvent.dragOver(line, { dataTransfer: t });

    expect(line.style.outline).toContain('dashed');
    expect(t.dropEffect).toBe('move');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('the refusal message can be dismissed, and does NOT fade on its own', () => {
    vi.useFakeTimers();
    try {
      setWidth(1440);
      const { container } = mount();
      goMap(container);
      fireEvent.click(within(rowIn(container, 0, 'Builder practice')).getByText('Builder practice'));
      fireEvent.click(
        within(rowIn(container, 1, 'Build Controlled Drift')).getByText('Build Controlled Drift'),
      );
      const src = rowIn(container, 1, 'Build Controlled Drift');
      const child = container.querySelector('[data-desk-col="2"]')!.firstElementChild as HTMLElement;
      const t = dt();
      fireEvent.dragStart(src.firstElementChild!, { dataTransfer: t });
      fireEvent.drop(child.firstElementChild!, { dataTransfer: t });

      expect(screen.getByRole('alert')).toBeTruthy();
      // A failure must survive being glanced at late — it is the one signal that does not fade.
      act(() => void vi.advanceTimersByTime(20000));
      expect(screen.queryByRole('alert')).toBeTruthy();

      fireEvent.click(screen.getByRole('button', { name: 'dismiss' }));
      expect(screen.queryByRole('alert')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('the pane dividers', () => {
  it('a divider drag writes the width, and the clamp holds at v4’s 220–700', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    const detail = handles(container).find((h) => h.dataset.dragHandle === 'detail')!;
    const pane = detail.nextElementSibling as HTMLElement;
    expect(pane.style.width).toBe('400px');

    // The detail pane is on the RIGHT, so dragging its handle LEFT makes it wider. The start
    // width is v4's 480 default, not the rendered 400 — see the note in `dragHandle`.
    fireEvent.mouseDown(detail, { clientX: 1000 });
    fireEvent.mouseMove(document, { clientX: 900 });
    expect(pane.style.width).toBe('580px');

    // Past the ceiling it stops at 700, not at whatever the pointer says.
    fireEvent.mouseMove(document, { clientX: 100 });
    expect(pane.style.width).toBe('700px');
    fireEvent.mouseUp(document);

    // …and past the floor it stops at 220.
    fireEvent.mouseDown(detail, { clientX: 1000 });
    fireEvent.mouseMove(document, { clientX: 1900 });
    expect(pane.style.width).toBe('220px');
    fireEvent.mouseUp(document);
  });

  it('every Finder column shares ONE width key, so one divider resizes them all', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    fireEvent.click(within(rowIn(container, 1, 'Reframe paper')).getByText('Reframe paper'));
    expect(cols(container).map((c) => c.style.width)).toEqual(['320px', '320px', '320px']);

    const col = handles(container).find((h) => h.dataset.dragHandle === 'deskcol')!;
    fireEvent.mouseDown(col, { clientX: 500 });
    fireEvent.mouseMove(document, { clientX: 560 });
    fireEvent.mouseUp(document);
    // 340 (v4's start default) + 60 — applied to every column at once.
    expect(cols(container).map((c) => c.style.width)).toEqual(['400px', '400px', '400px']);
  });

  it('releasing the drag clears the document cursor', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    const detail = handles(container).find((h) => h.dataset.dragHandle === 'detail')!;
    fireEvent.mouseDown(detail, { clientX: 1000 });
    expect(document.body.style.cursor).toBe('col-resize');
    fireEvent.mouseUp(document);
    expect(document.body.style.cursor).toBe('');
  });
});

describe('the same components, a different arrangement', () => {
  it('Routines keeps its own filter chips but drops the phone MapControls chrome', () => {
    setWidth(1440);
    mount();
    fireEvent.click(screen.getByRole('button', { name: 'Routines' }));
    // Its own cadence chips are part of the body and survive.
    expect(screen.getByText('As needed')).toBeTruthy();
    // The phone's shared filter strip is not rendered — the desktop toolbar carries search,
    // and the toolbar only offers Filters / + New on the Map tab.
    expect(screen.queryByPlaceholderText('Filter by title…')).toBeNull();

    cleanup();
    setWidth(420);
    mount();
    fireEvent.click(screen.getByRole('button', { name: 'Routines' }));
    expect(screen.getByText('As needed')).toBeTruthy();
    expect(screen.getByPlaceholderText('Filter by title…')).toBeTruthy();
  });

  it('the detail editor DOCKS as a pane on the wide tabs and closes with the ✕ Close pill', () => {
    setWidth(1440);
    const { container } = mount();
    goMap(container);
    expect(screen.getByText(/Select an item to edit/)).toBeTruthy();

    fireEvent.click(within(rowIn(container, 0, 'Scholarly practice')).getByText('Scholarly practice'));
    // The pencil on a row opens the editor; leaves open it on tap.
    fireEvent.click(within(rowIn(container, 1, 'Reframe paper')).getByText('Reframe paper'));
    fireEvent.click(within(rowIn(container, 2, 'Split Reframe and Welfare sections into separate papers')).getByText('Split Reframe and Welfare sections into separate papers'));
    // `wide` swaps the phone's "‹ Back" for the bordered close pill (v4:587).
    expect(screen.getByRole('button', { name: 'close' })).toBeTruthy();
  });

  it('the toolbar offers search / Filters / + New on the Map tab only', () => {
    setWidth(1440);
    mount();
    expect(screen.queryByPlaceholderText('Filter by title…')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    expect(screen.getByPlaceholderText('Filter by title…')).toBeTruthy();
    expect(screen.getByText('+ New')).toBeTruthy();
  });
});
