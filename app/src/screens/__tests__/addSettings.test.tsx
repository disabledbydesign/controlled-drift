/**
 * Behaviour tests for Task 8 — the Add/Log tab and Settings.
 *
 * These pin what the port is most likely to get quietly wrong:
 *   1. capture files a real TASK into the graph through the pure mutation, and the receipt
 *      the user sees is built from what actually landed (not from the raw input)
 *   2. capture is a no-op on blank/whitespace input — v4's `if(!t)return` guard
 *   3. the receipt's "edit" button routes to the created task's id
 *   4. the log tag is selectable and sticky, and the Log button clears the box
 *   5. ⚠ the log text and tag are DISCARDED — nothing carries them anywhere. Ported from v4
 *      as-is and pinned here so the gap is visible rather than assumed fixed.
 *   6. Settings drives the SHARED theme setter — a second `useTheme()` would fork it
 *   7. the backend radio and the hobby switch both write the bag
 *   8. the removed footer theme switcher does not come back: the theme control is reachable
 *      only from Settings
 *
 * `vite.config` sets `globals: false`, so Testing Library's automatic cleanup never registers.
 * `afterEach(cleanup)` is explicit or renders accumulate and every `getByText` finds several.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { seed, seedStrategies } from '../../fixtures/index.ts';
import { CAPTURE_PROJECT_ID, capture, index, node } from '../../model/index.ts';
import type { Graph, MutationResult } from '../../model/index.ts';
import { AddScreen } from '../AddScreen.tsx';
import type { AddCtx, AddUi } from '../AddScreen.tsx';
import { SettingsScreen } from '../SettingsScreen.tsx';
import type { SettingsCtx, SettingsUi } from '../SettingsScreen.tsx';

afterEach(cleanup);

function freshGraph(): Graph {
  return {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
  };
}

const BASE_ADD_UI: AddUi = { addText: '', logText: '', logTag: 'The day', receipt: [] };

function addCtx(over: Omit<Partial<AddCtx>, 'ui'> & { ui?: Partial<AddUi> } = {}): AddCtx {
  const graph = over.graph ?? freshGraph();
  return {
    T: themes.celestial,
    graph,
    idx: index(graph),
    ui: { ...BASE_ADD_UI, ...over.ui },
    up: over.up ?? vi.fn(),
    apply: over.apply ?? vi.fn(),
    openDetail: over.openDetail ?? vi.fn(),
    flash: over.flash ?? vi.fn(),
  };
}

// ── the model mutation ───────────────────────────────────────────────────────

describe('capture() mutation', () => {
  it('files a Ready TASK under the capture project and reports where it went', () => {
    const g = freshGraph();
    const res = capture(g, '  call the surgeon  ', CAPTURE_PROJECT_ID, () => 'capfix');

    expect(res.graph).not.toBe(g); // a new reference is the re-render signal
    expect(res.toast).toBe('Sorted into Build Controlled Drift');
    expect(res.ui).toEqual({ addText: '' });

    const created = node(index(res.graph), 'capfix');
    expect(created).toBeDefined();
    expect(created?.title).toBe('call the surgeon'); // trimmed, per v4
    expect(created?.level).toBe('TASK');
    expect(created?.type).toBe('Task');
    expect(created?.vals).toEqual({ status: 'Ready' });
    expect(created?._new).toBe(true);

    // it is a CHILD of the destination project, not a root
    const parent = node(index(res.graph), CAPTURE_PROJECT_ID);
    expect(parent?.children.some((c) => c.id === 'capfix')).toBe(true);

    // the original graph is untouched — structural sharing, not in-place mutation
    expect(node(index(g), 'capfix')).toBeUndefined();
  });

  it('no-ops on blank input, returning the SAME graph reference (v4 `if(!t)return`)', () => {
    const g = freshGraph();
    for (const blank of ['', '   ', '\n\t ']) {
      const res = capture(g, blank);
      expect(res.graph).toBe(g);
      expect(res.node).toBeNull();
      expect(res.toast).toBeNull();
    }
  });

  it('no-ops rather than throwing when the destination project is missing', () => {
    const g = freshGraph();
    const res = capture(g, 'something', 'no-such-project');
    expect(res.graph).toBe(g);
    expect(res.node).toBeNull();
  });
});

// ── the Add tab ──────────────────────────────────────────────────────────────

describe('AddScreen — capture', () => {
  it('typing writes the bag and tapping + Add applies the mutation and prepends a receipt', () => {
    const up = vi.fn();
    const apply = vi.fn();
    const { rerender } = render(<AddScreen ctx={addCtx({ up, apply })} />);

    fireEvent.change(screen.getByPlaceholderText(/call the surgeon/), {
      target: { value: 'book the dentist' },
    });
    expect(up).toHaveBeenCalledWith({ addText: 'book the dentist' });

    // re-render with the text in the bag, as the real `up` would
    const ctx = addCtx({ up, apply, ui: { addText: 'book the dentist' } });
    rerender(<AddScreen ctx={ctx} />);
    fireEvent.click(screen.getByText('+ Add'));

    const res = apply.mock.calls[0]?.[0] as MutationResult;
    expect(res.toast).toBe('Sorted into Build Controlled Drift');
    expect(res.node?.title).toBe('book the dentist');

    // the receipt is composed from what LANDED, and prepended (v4:1140)
    const receiptPatch = up.mock.calls.at(-1)?.[0] as Partial<AddUi>;
    expect(receiptPatch.receipt).toEqual([
      { id: res.node?.id, text: 'book the dentist', project: 'Build Controlled Drift' },
    ]);
  });

  it('+ Add does nothing at all when the box is empty', () => {
    const up = vi.fn();
    const apply = vi.fn();
    render(<AddScreen ctx={addCtx({ up, apply })} />);
    fireEvent.click(screen.getByText('+ Add'));
    expect(apply).not.toHaveBeenCalled();
    expect(up).not.toHaveBeenCalled();
  });

  it('shows the empty-state line until something is captured, then the receipt row', () => {
    render(<AddScreen ctx={addCtx()} />);
    expect(screen.getByText(/Nothing yet today/)).toBeTruthy();
    cleanup();

    render(
      <AddScreen
        ctx={addCtx({
          ui: { receipt: [{ id: 'cap1', text: 'book the dentist', project: 'Build Controlled Drift' }] },
        })}
      />,
    );
    expect(screen.queryByText(/Nothing yet today/)).toBeNull();
    expect(screen.getByText('book the dentist')).toBeTruthy();
    expect(screen.getByText('Build Controlled Drift')).toBeTruthy();
  });

  it("the receipt's edit button opens the created task", () => {
    const openDetail = vi.fn();
    render(
      <AddScreen
        ctx={addCtx({
          openDetail,
          ui: { receipt: [{ id: 'cap1', text: 'book the dentist', project: 'P' }] },
        })}
      />,
    );
    fireEvent.click(screen.getByText('edit'));
    expect(openDetail).toHaveBeenCalledWith('cap1');
  });
});

// ── the Log side ─────────────────────────────────────────────────────────────

describe('AddScreen — log', () => {
  it('offers both day/issue tags and selecting one writes the bag', () => {
    const up = vi.fn();
    render(<AddScreen ctx={addCtx({ up })} />);
    expect(screen.getByText('The day')).toBeTruthy();
    expect(screen.getByText('Friction')).toBeTruthy();

    fireEvent.click(screen.getByText('Friction'));
    expect(up).toHaveBeenCalledWith({ logTag: 'Friction' });
  });

  it('marks the selected tag differently from the unselected one', () => {
    // jsdom normalises hex to `rgb(...)`, so compare the two rendered styles rather than
    // asserting a literal token value.
    render(<AddScreen ctx={addCtx({ ui: { logTag: 'Friction' } })} />);
    const friction = screen.getByText('Friction').getAttribute('style');
    const day = screen.getByText('The day').getAttribute('style');
    expect(friction).not.toBe(day);
    // v4: selected gets the rose border, unselected the plain one.
    expect(friction).toContain('rgb(242, 166, 200)'); // celestial `rose` #f2a6c8
    expect(day).not.toContain('rgb(242, 166, 200)');
  });

  it('Log clears the box and flashes; with an empty box it does nothing', () => {
    const up = vi.fn();
    const flash = vi.fn();
    render(<AddScreen ctx={addCtx({ up, flash })} />);
    fireEvent.click(screen.getByText('Log'));
    expect(flash).not.toHaveBeenCalled();
    expect(up).not.toHaveBeenCalled();
    cleanup();

    render(<AddScreen ctx={addCtx({ up, flash, ui: { logText: 'migraine, rested' } })} />);
    fireEvent.click(screen.getByText('Log'));
    expect(flash).toHaveBeenCalledWith('Logged');
    expect(up).toHaveBeenCalledWith({ logText: '' });
  });

  it('⚠ FLAGGED v4 BEHAVIOUR: the log text and tag are discarded, not stored anywhere', () => {
    // Pinned deliberately. v4's Log handler is `flash('Logged'); up({logText:''})` and nothing
    // else — no list, no store, and the tag never reaches the message. The real backend
    // appends to signal_log.jsonl; Track A makes no network calls, so this drop stands.
    // If a store is ever added, this test fails and the flag gets revisited on purpose.
    const up = vi.fn();
    const flash = vi.fn();
    const apply = vi.fn();
    render(
      <AddScreen ctx={addCtx({ up, flash, apply, ui: { logText: 'a friction', logTag: 'Friction' } })} />,
    );
    fireEvent.click(screen.getByText('Log'));

    expect(apply).not.toHaveBeenCalled();
    expect(flash).toHaveBeenCalledWith('Logged'); // NOT 'Logged · Friction'
    expect(up.mock.calls).toEqual([[{ logText: '' }]]); // the only write is the clear
  });
});

// ── Settings ─────────────────────────────────────────────────────────────────

const BASE_SETTINGS_UI: SettingsUi = { backend: 'claude', hobby: true };

function settingsCtx(
  over: Omit<Partial<SettingsCtx>, 'ui'> & { ui?: Partial<SettingsUi> } = {},
): SettingsCtx {
  return {
    T: over.T ?? themes.celestial,
    name: over.name ?? 'celestial',
    setTheme: over.setTheme ?? vi.fn(),
    ui: { ...BASE_SETTINGS_UI, ...over.ui },
    up: over.up ?? vi.fn(),
  };
}

describe('SettingsScreen', () => {
  it('offers both themes and tapping one calls the SHARED setter from props', () => {
    const setTheme = vi.fn();
    render(<SettingsScreen ctx={settingsCtx({ setTheme })} />);
    expect(screen.getByText('Celestial')).toBeTruthy();
    expect(screen.getByText('Hardware')).toBeTruthy();

    fireEvent.click(screen.getByText('Hardware'));
    expect(setTheme).toHaveBeenCalledWith('hardware');
  });

  it('marks the active theme card, and the mark follows the `name` prop', () => {
    render(<SettingsScreen ctx={settingsCtx({ name: 'celestial' })} />);
    const cel = screen.getByText('Celestial').closest('button');
    const hw = screen.getByText('Hardware').closest('button');
    expect(cel?.getAttribute('style')).toContain('box-shadow');
    expect(hw?.getAttribute('style')).not.toBe(cel?.getAttribute('style'));
    cleanup();

    render(<SettingsScreen ctx={settingsCtx({ name: 'hardware', T: themes.hardware })} />);
    const hw2 = screen.getByText('Hardware').closest('button');
    const cel2 = screen.getByText('Celestial').closest('button');
    // hardware `rose` #f593c1, as jsdom serialises it
    expect(hw2?.getAttribute('style')).toContain('rgb(245, 147, 193)');
    expect(cel2?.getAttribute('style')).not.toContain('rgb(245, 147, 193)');
  });

  it('preserves the isHW SHAPE fork on the theme dot: square in hardware, round in celestial', () => {
    const dotOf = (label: string) =>
      screen.getByText(label).parentElement?.firstElementChild?.getAttribute('style') ?? '';

    render(<SettingsScreen ctx={settingsCtx({ T: themes.celestial })} />);
    expect(dotOf('Celestial')).toContain('border-radius: 50%');
    cleanup();

    render(<SettingsScreen ctx={settingsCtx({ T: themes.hardware, name: 'hardware' })} />);
    expect(dotOf('Celestial')).toContain('border-radius: 2px');
  });

  it('the backend picker writes the bag and shows the current choice as selected', () => {
    const up = vi.fn();
    render(<SettingsScreen ctx={settingsCtx({ up })} />);
    expect(screen.getByText('Claude subscription')).toBeTruthy();
    expect(screen.getByText('Local model')).toBeTruthy();
    expect(screen.getByText('Open-source API')).toBeTruthy();

    fireEvent.click(screen.getByText('Local model'));
    expect(up).toHaveBeenCalledWith({ backend: 'local' });
  });

  it('the plan-content toggle reflects and flips `hobby`', () => {
    const up = vi.fn();
    const { rerender } = render(<SettingsScreen ctx={settingsCtx({ up })} />);
    fireEvent.click(screen.getByText('Include creative / hobby work'));
    expect(up).toHaveBeenCalledWith({ hobby: false });

    rerender(<SettingsScreen ctx={settingsCtx({ up, ui: { hobby: false } })} />);
    fireEvent.click(screen.getByText('Include creative / hobby work'));
    expect(up).toHaveBeenLastCalledWith({ hobby: true });
  });
});
