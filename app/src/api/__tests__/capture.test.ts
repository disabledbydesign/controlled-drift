/**
 * Tests for the capture seam.
 *
 * These pin the three things `docs/api_contract_v2.md` flags as easy to wire wrong, and that a
 * naive port gets wrong silently rather than loudly. The shapes below are the server's real
 * ones (`server.py` `/api/capture`, `_start_generation`), not invented payloads.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { startCapture } from '../capture.ts';

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as unknown as Response);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('startCapture — the 202 that is not a success', () => {
  /**
   * THE HAZARD. `_start_generation` returns `started:false` when another generation already
   * holds the single global lock, and the route answers that as **202** — a 2xx. A client that
   * checks only `res.ok` reads it as "my capture is running" and polls forever for a job that
   * was never created, while her text sits there looking submitted.
   */
  it('reports a busy server as BUSY, not as started', async () => {
    vi.stubGlobal('fetch', respond(202, { state: 'running', started: false }));
    expect(await startCapture('something')).toEqual({ kind: 'busy' });
  });

  it('reports a real start as started', async () => {
    vi.stubGlobal('fetch', respond(202, { state: 'running', started: true }));
    expect(await startCapture('something')).toEqual({ kind: 'started' });
  });

  /**
   * Busy must NOT travel down the failure channel. The project's rule is that a refusal is not
   * a failure and must not be reported in the register of something having gone wrong — so the
   * two are distinct variants here rather than one error string the caller has to sniff.
   */
  it('keeps busy and failed as different answers', async () => {
    vi.stubGlobal('fetch', respond(500, { error: 'the weeder fell over' }));
    const res = await startCapture('something');
    expect(res.kind).toBe('failed');
    expect(res).not.toEqual({ kind: 'busy' });
  });

  it('carries the serversentence through, so the failure can say what broke', async () => {
    vi.stubGlobal('fetch', respond(400, { error: 'capture needs text' }));
    expect(await startCapture('x')).toEqual({ kind: 'failed', error: 'capture needs text' });
  });
});
