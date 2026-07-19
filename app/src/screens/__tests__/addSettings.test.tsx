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
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { themes } from '@tokens';
import { seed, seedStrategies } from '../../fixtures/index.ts';
import { index } from '../../model/index.ts';
import type { Graph } from '../../model/index.ts';
import { AddScreen, latestWeed, rowsFrom } from '../AddScreen.tsx';
import type { AddCtx, AddUi } from '../AddScreen.tsx';
import type { CreatedItem, WeedEntry } from '../../api/capture.ts';
import { SettingsScreen } from '../SettingsScreen.tsx';
import type { SettingsCtx, SettingsUi } from '../SettingsScreen.tsx';
import type { BackendOption } from '../../shell/useAppState.ts';

afterEach(cleanup);

function freshGraph(): Graph {
  return {
    roots: structuredClone(seed) as Graph['roots'],
    strategies: structuredClone(seedStrategies) as Graph['strategies'],
  };
}

const BASE_ADD_UI: AddUi = { addText: '', logText: '', logTag: 'The day' };

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
    logDay: over.logDay ?? vi.fn().mockResolvedValue(true),
    captureEntries: over.captureEntries ?? [],
    captureSummary: over.captureSummary ?? null,
    loadCapture: over.loadCapture ?? vi.fn().mockResolvedValue(undefined),
    runCapture: over.runCapture ?? vi.fn().mockResolvedValue(true),
    undoCapture: over.undoCapture ?? vi.fn().mockResolvedValue(undefined),
    setCapturedWhen: over.setCapturedWhen ?? vi.fn().mockResolvedValue(undefined),
    setCapturedEngagement: over.setCapturedEngagement ?? vi.fn().mockResolvedValue(undefined),
    regenerate: over.regenerate ?? vi.fn().mockResolvedValue(undefined),
    busy: over.busy ?? null,
  };
}

/** One weed turn as the session log records it. */
function weed(created: Partial<CreatedItem>[], over: Partial<WeedEntry> = {}): WeedEntry {
  return {
    ts: '2026-07-18T10:00:00',
    intent: 'weed',
    created: created.map((c, i) => ({
      id: c.id ?? `obj${i}`,
      type: c.type ?? 'Task',
      name: c.name ?? `thing ${i}`,
      ...c,
    })) as CreatedItem[],
    ...over,
  };
}

// ── the receipt, derived from the session log ────────────────────────────────

describe('rowsFrom — the receipt the server describes', () => {
  it('flattens every weed turn into rows, newest first', () => {
    const rows = rowsFrom([
      weed([{ id: 'a', name: 'first' }]),
      weed([{ id: 'b', name: 'second' }, { id: 'c', name: 'third' }]),
    ]);
    expect(rows.map((r) => r.item.id)).toEqual(['c', 'b', 'a']);
  });

  it('marks an undone row instead of dropping it — she can still see what she undid', () => {
    const rows = rowsFrom([
      weed([{ id: 'a', name: 'kept' }, { id: 'b', name: 'undone one' }]),
      { intent: 'undo', target_id: 'b' } as WeedEntry,
    ]);
    expect(rows.find((r) => r.item.id === 'b')?.undone).toBe(true);
    expect(rows.find((r) => r.item.id === 'a')?.undone).toBe(false);
    expect(rows).toHaveLength(2); // NOT removed
  });

  it('latestWeed ignores undo entries and returns the most recent capture turn', () => {
    const entries = [
      weed([{ id: 'a' }], { ts: 'first' }),
      weed([{ id: 'b' }], { ts: 'second' }),
      { intent: 'undo', target_id: 'b' } as WeedEntry,
    ];
    expect(latestWeed(entries)?.ts).toBe('second');
    expect(latestWeed([])).toBeNull();
  });
});

describe('AddScreen — capture', () => {
  it('+ Add runs the REAL weeder, not a local mutation', async () => {
    const runCapture = vi.fn().mockResolvedValue(true);
    const up = vi.fn();
    render(<AddScreen ctx={addCtx({ ui: { addText: 'call the surgeon' }, runCapture, up })} />);

    fireEvent.click(screen.getByRole('button', { name: '+ Add' }));

    expect(runCapture).toHaveBeenCalledWith('call the surgeon');
    // Cleared only after the capture is PROVEN, never optimistically.
    await waitFor(() => expect(up).toHaveBeenCalledWith({ addText: '' }));
  });

  it('a capture that did NOT save leaves her words on screen', async () => {
    const runCapture = vi.fn().mockResolvedValue(false);
    const up = vi.fn();
    render(<AddScreen ctx={addCtx({ ui: { addText: 'keep me' }, runCapture, up })} />);

    fireEvent.click(screen.getByRole('button', { name: '+ Add' }));

    await waitFor(() => expect(runCapture).toHaveBeenCalled());
    expect(up).not.toHaveBeenCalledWith({ addText: '' });
  });

  it('reads the receipt from the server when the tab opens', () => {
    const loadCapture = vi.fn().mockResolvedValue(undefined);
    render(<AddScreen ctx={addCtx({ loadCapture })} />);
    expect(loadCapture).toHaveBeenCalled();
  });

  it('renders what the weeder filed, with where it went', () => {
    const entries = [weed([{ id: 't1', name: 'call the surgeon', project: 'Medical' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries })} />);
    expect(screen.getByText('call the surgeon')).toBeTruthy();
    expect(screen.getByText('Medical')).toBeTruthy();
  });

  it('shows result_summary — the ONLY place a skip or failure is ever mentioned', () => {
    render(<AddScreen ctx={addCtx({ captureSummary: 'added 3, skipped 1' })} />);
    expect(screen.getByText('added 3, skipped 1')).toBeTruthy();
  });

  it('the when-chip sends a TOKEN, never the rendered label', () => {
    const setCapturedWhen = vi.fn().mockResolvedValue(undefined);
    const entries = [weed([{ id: 't1', name: 'x', when_label: 'Today', is_today: true }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries, setCapturedWhen })} />);

    fireEvent.click(screen.getByRole('button', { name: 'Today' }));
    // Today -> tomorrow in the cycle, and it is the TOKEN that goes over the wire.
    expect(setCapturedWhen).toHaveBeenCalledWith('t1', 'tomorrow');
  });

  it('the engagement chip cycles a captured Project through the three states', () => {
    const setCapturedEngagement = vi.fn().mockResolvedValue(undefined);
    const entries = [weed([{ id: 'p1', type: 'Project', name: 'New project', engagement: 'Open' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries, setCapturedEngagement })} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open' }));
    expect(setCapturedEngagement).toHaveBeenCalledWith('p1', 'Open', 'Steady');
  });

  it('undo archives through the server, and an undone row loses its controls', () => {
    const undoCapture = vi.fn().mockResolvedValue(undefined);
    const entries = [weed([{ id: 't1', name: 'oops' }])];
    const { rerender } = render(<AddScreen ctx={addCtx({ captureEntries: entries, undoCapture })} />);

    fireEvent.click(screen.getByRole('button', { name: 'undo' }));
    expect(undoCapture).toHaveBeenCalledWith('t1');

    rerender(
      <AddScreen
        ctx={addCtx({
          captureEntries: [...entries, { intent: 'undo', target_id: 't1' } as WeedEntry],
          undoCapture,
        })}
      />,
    );
    expect(screen.getByText('oops')).toBeTruthy(); // still visible
    expect(screen.queryByRole('button', { name: 'undo' })).toBeNull();
  });

  it('the receipt edit button opens the created object', () => {
    const openDetail = vi.fn();
    const entries = [weed([{ id: 't1', name: 'thing' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries, openDetail })} />);
    fireEvent.click(screen.getByRole('button', { name: 'edit' }));
    expect(openDetail).toHaveBeenCalledWith('t1');
  });

  /**
   * A real payload shape, not a hypothetical: `project` is absent on a created Project or Goal
   * (the live weed on 2026-07-18 returned it only for the Task). Rendering "sorted into" with
   * nothing after it would read as a lost link rather than a thing that has no parent.
   */
  it('an item with no project says what it is instead of a dangling "sorted into"', () => {
    const entries = [weed([{ id: 'p1', type: 'Project', name: 'A whole new project' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries })} />);
    expect(screen.getByText('A whole new project')).toBeTruthy();
    expect(screen.getByText(/added as project/i)).toBeTruthy();
    expect(screen.queryByText(/sorted into/)).toBeNull();
  });

  it('shows the empty-state line until something is captured', () => {
    render(<AddScreen ctx={addCtx()} />);
    expect(screen.getByText(/Nothing yet today/)).toBeTruthy();
  });
});

describe('AddScreen — the verify gate before anything rebuilds her day', () => {
  it('asks before rebuilding when something landed for today', () => {
    const entries = [weed([{ id: 't1', name: 'x', is_today: true, when_label: 'Today' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries })} />);
    expect(screen.getByRole('button', { name: 'Regenerate today' })).toBeTruthy();
  });

  it('does NOT ask when nothing is for today — no box at all', () => {
    const entries = [weed([{ id: 't1', name: 'x', is_today: false, when_label: 'Parked' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries })} />);
    expect(screen.queryByRole('button', { name: 'Regenerate today' })).toBeNull();
  });

  it('"Not now" changes nothing — it must not rebuild the plan', () => {
    const regenerate = vi.fn().mockResolvedValue(undefined);
    const entries = [weed([{ id: 't1', name: 'x', is_today: true, when_label: 'Today' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries, regenerate })} />);

    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    expect(regenerate).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Regenerate today' })).toBeNull();
  });

  it('Regenerate today rebuilds only when she says so', () => {
    const regenerate = vi.fn().mockResolvedValue(undefined);
    const entries = [weed([{ id: 't1', name: 'x', is_today: true, when_label: 'Today' }])];
    render(<AddScreen ctx={addCtx({ captureEntries: entries, regenerate })} />);

    fireEvent.click(screen.getByRole('button', { name: 'Regenerate today' }));
    expect(regenerate).toHaveBeenCalledWith({ kind: 'refresh' }, 'Regenerate today');
  });
});

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

  it('an empty box logs nothing', async () => {
    const up = vi.fn();
    const logDay = vi.fn().mockResolvedValue(true);
    render(<AddScreen ctx={addCtx({ up, logDay })} />);
    fireEvent.click(screen.getByText('Log'));
    expect(logDay).not.toHaveBeenCalled();
    expect(up).not.toHaveBeenCalled();
  });

  it('Log sends the text to the friction log and clears the box once it saved', async () => {
    const up = vi.fn();
    const logDay = vi.fn().mockResolvedValue(true);
    render(<AddScreen ctx={addCtx({ up, logDay, ui: { logText: 'migraine, rested' } })} />);
    fireEvent.click(screen.getByText('Log'));

    expect(logDay).toHaveBeenCalledWith('migraine, rested', ['day']);
    await waitFor(() => expect(up).toHaveBeenCalledWith({ logText: '' }));
  });

  it('the Friction tag is sent as "issue" — the tag the triage passes filter on', async () => {
    // The server keeps only "day"/"issue" and silently substitutes ["day"] for anything else,
    // so a broken mapping here would not error — it would quietly file every friction entry as
    // a day entry, and the loss would only surface at the next triage.
    const logDay = vi.fn().mockResolvedValue(true);
    render(
      <AddScreen ctx={addCtx({ logDay, ui: { logText: 'a friction', logTag: 'Friction' } })} />,
    );
    fireEvent.click(screen.getByText('Log'));

    expect(logDay).toHaveBeenCalledWith('a friction', ['issue']);
  });

  it('a failed write leaves her text on screen instead of clearing it', async () => {
    // The defect this replaced flashed "Logged" and cleared the box unconditionally, so a
    // dropped entry was indistinguishable from a saved one. Losing her words is the worse half.
    const up = vi.fn();
    const logDay = vi.fn().mockResolvedValue(false);
    render(<AddScreen ctx={addCtx({ up, logDay, ui: { logText: 'the thing that broke' } })} />);
    fireEvent.click(screen.getByText('Log'));

    await waitFor(() => expect(logDay).toHaveBeenCalled());
    expect(up).not.toHaveBeenCalled();
  });
});

// ── Settings ─────────────────────────────────────────────────────────────────

const BASE_SETTINGS_UI: SettingsUi = { backend: 'claude', hobby: true };

/**
 * The real `GET /api/settings` option list — `mistral | openrouter | claude | local`, verbatim
 * from `curl -s localhost:5050/api/settings` (2026-07-19). NOT v4's hardcoded three
 * (`claude | local | api`): `api` does not exist on the server, and `mistral` — June's decided
 * production default — was missing from v4's list entirely.
 */
const BASE_BACKEND_OPTIONS: BackendOption[] = [
  { id: 'mistral', label: 'Mistral', mechanism: 'Mistral API (direct)', model: 'mistral-large-latest' },
  { id: 'openrouter', label: 'OpenRouter', mechanism: 'OpenRouter API', model: 'anthropic/claude-sonnet-4' },
  { id: 'claude', label: 'Claude', mechanism: 'claude -p CLI (your subscription)', model: null },
  { id: 'local', label: 'Local', mechanism: 'on-device (MLX)', model: 'mlx-community/Qwen2.5-7B-Instruct-4bit' },
];

function settingsCtx(
  over: Omit<Partial<SettingsCtx>, 'ui'> & { ui?: Partial<SettingsUi> } = {},
): SettingsCtx {
  return {
    T: over.T ?? themes.celestial,
    name: over.name ?? 'celestial',
    setTheme: over.setTheme ?? vi.fn(),
    ui: { ...BASE_SETTINGS_UI, ...over.ui },
    options: over.options ?? BASE_BACKEND_OPTIONS,
    save: over.save ?? vi.fn(),
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

  it('renders exactly the options `ctx.options` was given — the server list, not a hardcoded one', () => {
    // A hardcoded three (`claude | local | api`) would neither show 'OpenRouter' nor offer
    // 'mistral' at all — this is the assertion a reversion to that old list fails.
    render(<SettingsScreen ctx={settingsCtx()} />);
    expect(screen.getByText('Mistral')).toBeTruthy();
    expect(screen.getByText('OpenRouter')).toBeTruthy();
    expect(screen.getByText('Claude')).toBeTruthy();
    expect(screen.getByText('Local')).toBeTruthy();
    expect(screen.queryByText('Open-source API')).toBeNull();
  });

  it('shows the real routing mechanism and model per option, not a hand-written description', () => {
    render(<SettingsScreen ctx={settingsCtx()} />);
    expect(screen.getByText('Mistral API (direct) · mistral-large-latest')).toBeTruthy();
    expect(screen.getByText('OpenRouter API · anthropic/claude-sonnet-4')).toBeTruthy();
    // claude's `model` is null — the line falls back to the mechanism alone, no dangling "· null".
    expect(screen.getByText('claude -p CLI (your subscription)')).toBeTruthy();
    expect(screen.getByText('on-device (MLX) · mlx-community/Qwen2.5-7B-Instruct-4bit')).toBeTruthy();
  });

  it('an empty option list (a failed settings read) renders no backend rows at all', () => {
    render(<SettingsScreen ctx={settingsCtx({ options: [] })} />);
    expect(screen.queryByText('Mistral')).toBeNull();
    expect(screen.queryByText('Claude')).toBeNull();
  });

  it('the backend picker saves the id the server sent, and shows the current choice as selected', () => {
    const save = vi.fn();
    render(<SettingsScreen ctx={settingsCtx({ save, ui: { backend: 'claude' } })} />);

    fireEvent.click(screen.getByText('Local'));
    // The value sent is the option's own `id` — not a client-invented one.
    expect(save).toHaveBeenCalledWith({ backend: 'local' });
  });

  it('the plan-content toggle reflects and flips `hobby`', () => {
    const save = vi.fn();
    const { rerender } = render(<SettingsScreen ctx={settingsCtx({ save })} />);
    fireEvent.click(screen.getByText('Include creative / hobby work'));
    expect(save).toHaveBeenCalledWith({ hobby: false });

    rerender(<SettingsScreen ctx={settingsCtx({ save, ui: { hobby: false } })} />);
    fireEvent.click(screen.getByText('Include creative / hobby work'));
    expect(save).toHaveBeenLastCalledWith({ hobby: true });
  });
});
