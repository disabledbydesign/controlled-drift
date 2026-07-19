import { domToPng } from 'modern-screenshot';

/**
 * What June was pressing when she summoned the capture.
 *
 * Deliberately coarse and best-effort. The app is not instrumented with per-row ids (only five
 * data-* attributes exist across the whole tree), so rather than requiring an instrumentation
 * pass first, this reads whatever the DOM already says: the element kind, its accessible label,
 * a text snippet, and any data-* attributes on the way up. That is a HINT for the triage pass —
 * "she was on the Not today button" — never a claim about which object she meant.
 */
export interface PressTarget {
  tag: string;
  label: string;
  text: string;
  data: Record<string, string>;
  /**
   * The innermost element and its ancestors, outward. Recorded because June's own worry about
   * this is the right one: elements overlap, and a finger lands slightly off. The innermost hit
   * may be a padding div or the wrong sibling. The chain means a near-miss still lands somewhere
   * useful — a reader that cannot make sense of `label` can look one step out.
   */
  chain: Array<{ tag: string; label: string }>;
}

const MAX_TEXT = 200;
/** Far enough out to escape a mis-hit, short enough not to be the whole document. */
const MAX_CHAIN = 5;
/** Elements carrying this attribute are the capture UI itself and must not appear in the shot. */
export const CHROME_ATTR = 'data-cd-capture-chrome';

function snip(s: string | null | undefined): string {
  const t = (s || '').replace(/\s+/g, ' ').trim();
  return t.length > MAX_TEXT ? t.slice(0, MAX_TEXT) : t;
}

export function describeTarget(el: Element | null): PressTarget | null {
  if (!el) return null;
  const text = snip(el.textContent);
  const aria = el.getAttribute('aria-label');

  // Walk to the document root collecting data-* attributes. NEAREST WINS: the loop only fills a
  // key it has not already seen, so an inner data-signal is not overwritten by an outer one.
  const data: Record<string, string> = {};
  const chain: Array<{ tag: string; label: string }> = [];
  for (let n: Element | null = el; n; n = n.parentElement) {
    for (const a of Array.from(n.attributes)) {
      if (!a.name.startsWith('data-')) continue;
      const key = a.name.slice('data-'.length);
      if (!(key in data)) data[key] = a.value;
    }
    if (chain.length < MAX_CHAIN) {
      chain.push({
        tag: n.tagName.toLowerCase(),
        label: snip(n.getAttribute('aria-label')) || snip(n.textContent),
      });
    }
  }

  return { tag: el.tagName.toLowerCase(), label: snip(aria) || text, text, data, chain };
}

/**
 * The live screen as a PNG data URL, rendered from the DOM inside the page.
 *
 * ── why not the macOS screenshot ────────────────────────────────────────────
 * `screencapture` needs Screen Recording permission, and `desktop_app.py:156` records that it
 * returns a BLACK image without it — a failure mode that looks like a working capture. The
 * bundle is also unsigned, so the permission prompt has no stable identity to attach to. Doing
 * it in the page needs no permission at all, cannot go black, and works unchanged on June's
 * phone over the LAN, which the OS path could never have done.
 *
 * ── the honest tradeoff ─────────────────────────────────────────────────────
 * This RE-RENDERS the DOM rather than copying real pixels, so unusual CSS can come out slightly
 * wrong. If the friction being logged IS a rendering bug, the image may not show it faithfully.
 * That is why the entry also carries the view and the press target: the record stays useful even
 * when the picture is imperfect.
 *
 * NEVER throws. A failed snapshot must still leave her able to file a text-only entry — losing
 * the whole capture because the image did not render would be strictly worse than the old path.
 */
export async function snapshot(node?: HTMLElement | null): Promise<string | null> {
  const root = node || document.body;
  if (!root) return null;
  try {
    const url = await domToPng(root, {
      // The overlay is drawn before the async render finishes in some orderings; excluding it by
      // attribute is cheaper and more reliable than trying to sequence around it.
      filter: (n: Node) =>
        !(n instanceof Element && n.hasAttribute(CHROME_ATTR)),
      // 1 rather than devicePixelRatio: a 3x phone screen would produce a multi-megabyte PNG for
      // no legibility gain at the size she will actually look at it.
      scale: 1,
    });
    return typeof url === 'string' && url.startsWith('data:image/png') ? url : null;
  } catch {
    return null;
  }
}
