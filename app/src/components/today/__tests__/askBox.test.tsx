/**
 * THE "TELL ME WHAT YOU NEED" BOX — the one control on this surface that holds words she WROTE.
 *
 * It used to `flash('Sent')` and then `up({ask:''})`. Nothing read `ui.ask`: a 150px textarea
 * prompting "I only have 30 min and need to stay horizontal" invited a considered sentence, told
 * her it had gone, and deleted it. Same shape as the Friction-log drop fixed the day before, in
 * the box that invites the most words.
 *
 * It now goes to `/api/negotiate` as `message` — the free-text half of the endpoint the presets
 * already use (`server.py:973`) — through the same `regenerate` seam and the same 202-and-poll
 * wait, and the box empties on a confirmed generation and on nothing else.
 *
 * ── what is tested WHERE, and why it is split ───────────────────────────────
 * These tests own the CALLER's half: the right request goes out with her text in it, and her
 * text survives every answer except a proven success. That `regenerate` itself resolves `false`
 * and puts a readable failure on screen — the "she is told it did not send" half — is the seam's
 * own behaviour and is tested against the real fetch path in `shell/__tests__/regenerate.test.ts`
 * ("resolves false and says it did not send"). Asserting it a second time here, against a spy,
 * would only be asserting the spy.
 *
 * Every assertion below is POSITIVE about what the box must contain afterwards, not merely that
 * something did not happen — the textarea is driven by real state through `AskHarness`, so
 * "her text is still there" is read off the element rather than inferred from an uncalled spy.
 *
 * `vite.config` sets `globals: false`, so `afterEach(cleanup)` is explicit.
 */

import { useState } from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { TodayPanel } from '../TodayPanel.tsx';
import { ctxWith } from './ctxFactory.tsx';

afterEach(cleanup);

const PLACEHOLDER = 'e.g. I only have 30 min and need to stay horizontal…';
const HER_TEXT = 'I only have 30 min and need to stay horizontal';

/**
 * The panel with a REAL `ask` value behind it.
 *
 * `ctxWith`'s `up` is a spy, so a panel mounted straight from it can never show the box changing
 * — the textarea would hold its initial value whatever the handler did, and a test asserting
 * "her text is still there" would pass against code that cleared it. This feeds `up({ask})` back
 * into the value, which is what the running app does, so the assertion is about the box.
 */
function renderAsk(initial: string, sendResult: boolean) {
  const base = ctxWith({ ask: initial });
  base.regenerate.mockResolvedValue(sendResult);

  function AskHarness() {
    const [ask, setAsk] = useState(initial);
    const ctx = {
      ...base.ctx,
      ui: { ...base.ctx.ui, ask },
      up: (patch: Partial<typeof base.ctx.ui>) => {
        base.up(patch);
        if (patch.ask !== undefined) setAsk(patch.ask);
      },
    };
    return <TodayPanel ctx={ctx} />;
  }

  render(<AskHarness />);
  return { ...base, box: () => screen.getByPlaceholderText(PLACEHOLDER) as HTMLTextAreaElement };
}

describe('sending what she wrote', () => {
  it('asks the server to re-plan around her message, carrying her words', async () => {
    const { regenerate } = renderAsk(HER_TEXT, true);

    fireEvent.click(screen.getByText('✦ Send'));

    await waitFor(() =>
      expect(regenerate).toHaveBeenCalledWith({ kind: 'message', message: HER_TEXT }, 'Your message'),
    );
  });

  it('sends the trimmed text, not the surrounding whitespace', async () => {
    const { regenerate } = renderAsk(`  ${HER_TEXT}\n`, true);

    fireEvent.click(screen.getByText('✦ Send'));

    await waitFor(() =>
      expect(regenerate).toHaveBeenCalledWith({ kind: 'message', message: HER_TEXT }, 'Your message'),
    );
  });

  it('empties the box once the server has confirmed a new plan', async () => {
    const { box } = renderAsk(HER_TEXT, true);

    fireEvent.click(screen.getByText('✦ Send'));

    await waitFor(() => expect(box().value).toBe(''));
  });

  /**
   * ⚠ THE ONE THAT MATTERS. A send that did not land leaves the box holding exactly what she
   * typed, ready to send again — she never has to retype a sentence the software swallowed.
   * `regenerate` has already put a readable failure on screen by this point; see the header.
   */
  it('keeps every word she wrote when the send did not land', async () => {
    const { box, regenerate } = renderAsk(HER_TEXT, false);

    fireEvent.click(screen.getByText('✦ Send'));

    await waitFor(() => expect(regenerate).toHaveBeenCalled());
    expect(box().value).toBe(HER_TEXT);
  });

  /**
   * An empty box has nothing to send and claims nothing. Positive: the box is still empty and no
   * request went out, so a stray tap cannot start a generation on a blank message — which
   * `/api/negotiate` would answer 400 (`server.py:1000`).
   */
  it('sends nothing at all when the box is empty', async () => {
    const { box, regenerate } = renderAsk('   ', false);

    fireEvent.click(screen.getByText('✦ Send'));

    await waitFor(() => expect(box().value).toBe('   '));
    expect(regenerate).not.toHaveBeenCalled();
  });
});
