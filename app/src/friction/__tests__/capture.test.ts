import { describe, it, expect, vi, beforeEach } from 'vitest';

const domToPng = vi.fn();
// jsdom cannot rasterise anything, so the library is mocked. What we test here is OUR logic:
// the descriptor walk, and that a capture failure degrades to null instead of throwing.
vi.mock('modern-screenshot', () => ({ domToPng: (...a: unknown[]) => domToPng(...a) }));

import { describeTarget, snapshot } from '../capture.ts';

beforeEach(() => {
  domToPng.mockReset();
  document.body.innerHTML = '';
});

describe('describeTarget', () => {
  it('is null for no element', () => {
    expect(describeTarget(null)).toBeNull();
  });

  it('reads the tag, the accessible label and a text snippet', () => {
    document.body.innerHTML = `<button aria-label="Move this back">Not today</button>`;
    const t = describeTarget(document.querySelector('button'));
    expect(t).toMatchObject({ tag: 'button', label: 'Move this back', text: 'Not today' });
  });

  it('falls back to the text when there is no aria-label', () => {
    document.body.innerHTML = `<div>Cancel food stamps</div>`;
    expect(describeTarget(document.querySelector('div'))!.label).toBe('Cancel food stamps');
  });

  it('truncates a long text snippet', () => {
    document.body.innerHTML = `<div>${'x'.repeat(400)}</div>`;
    expect(describeTarget(document.querySelector('div'))!.text.length).toBeLessThanOrEqual(200);
  });

  it('collects data-* attributes from the element and its ancestors', () => {
    document.body.innerHTML =
      `<section data-desk-col="map"><span data-signal="row"><em>hi</em></span></section>`;
    const t = describeTarget(document.querySelector('em'));
    expect(t!.data).toEqual({ 'desk-col': 'map', signal: 'row' });
  });

  it('records the element chain outward, so a mis-hit still lands somewhere useful', () => {
    document.body.innerHTML = `<li aria-label="Cancel food stamps"><span><i></i></span></li>`;
    const chain = describeTarget(document.querySelector('i'))!.chain;
    expect(chain[0]!.tag).toBe('i');
    expect(chain.map((c) => c.tag)).toContain('li');
    expect(chain.find((c) => c.tag === 'li')!.label).toBe('Cancel food stamps');
  });

  it('caps the chain rather than walking the whole document', () => {
    document.body.innerHTML = '<a><b><i><u><s><em><q>x</q></em></s></u></i></b></a>';
    expect(describeTarget(document.querySelector('q'))!.chain.length).toBeLessThanOrEqual(5);
  });

  it('lets a nearer data attribute win over an ancestor with the same name', () => {
    document.body.innerHTML = `<section data-signal="outer"><span data-signal="inner"><em>hi</em></span></section>`;
    expect(describeTarget(document.querySelector('em'))!.data.signal).toBe('inner');
  });
});

describe('snapshot', () => {
  it('returns the data URL the renderer produced', async () => {
    domToPng.mockResolvedValue('data:image/png;base64,AAAA');
    expect(await snapshot(document.body)).toBe('data:image/png;base64,AAAA');
  });

  it('resolves null rather than throwing when the renderer fails', async () => {
    domToPng.mockRejectedValue(new Error('tainted canvas'));
    expect(await snapshot(document.body)).toBeNull();
  });

  it('resolves null when the renderer returns something that is not a png data URL', async () => {
    domToPng.mockResolvedValue('');
    expect(await snapshot(document.body)).toBeNull();
  });

  it('skips nodes marked as capture chrome', async () => {
    domToPng.mockResolvedValue('data:image/png;base64,AAAA');
    await snapshot(document.body);
    const opts = domToPng.mock.calls[0]![1] as { filter: (n: Node) => boolean };
    const chrome = document.createElement('div');
    chrome.setAttribute('data-cd-capture-chrome', '');
    expect(opts.filter(chrome)).toBe(false);
    expect(opts.filter(document.createElement('p'))).toBe(true);
  });
});
