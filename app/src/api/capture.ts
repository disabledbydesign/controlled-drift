/**
 * The CAPTURE flow — the Add tab's real write path.
 *
 * ── why this file exists ─────────────────────────────────────────────────────
 * The Add tab shipped running a client-side MOCK (`model/mutations.ts` `capture()`), ported from
 * the v4 design mockup, which files the whole typed string as ONE plain Task under a hardcoded
 * project id and does no weeding at all. That was a documented Track A deferral ("no network
 * calls in this track") — but the plan written to close Track A's deferrals,
 * `docs/superpowers/plans/2026-07-18-persistence-seam.md`, never lists the Add tab, so the
 * follow-up never happened. June: "It should work like the real weeder. We already had it
 * working in the old UI, so i just want the same thing."
 *
 * The behaviour ported here is `docs/overlay_daily.html`'s (the old surface, which drove this
 * correctly), against the contract at `docs/api_contract_v2.md` §2.6/§6.
 *
 * ── the shape of the flow, and the three things that make it easy to get wrong ─
 *
 *   1. `POST /api/capture` answers **202 `{state:'running', started:bool}`**.
 *      `started:false` is NOT an error — it means a generation was already in flight (one global
 *      lock, `server.py:_start_generation`). The contract says so explicitly
 *      (api_contract_v2 §:414): "The UI must not surface it as a failure." A caller that only
 *      checks `res.ok` will poll forever for a job that never started.
 *
 *   2. **The result never comes back from the POST.** The worker's return value is discarded
 *      (`capture_generate.py`). The client polls `GET /api/status` and then reads the RECEIPT
 *      from `GET /api/session?stream=capture`. Reading created objects off the capture response
 *      is not a thing that can work.
 *
 *   3. `/api/status` is the **shared** generation status — the same one plan generation and
 *      `/api/refresh` use. There is no per-capture job id. (api_contract_v2 §:410 flags this as
 *      "easy to wire wrong"; focus authoring polls a DIFFERENT endpoint, `/api/focus/status`.)
 *
 * ── what does NOT surface as a failure ───────────────────────────────────────
 * `started:false` (busy) and a weed that skipped a duplicate are both ordinary outcomes. The
 * project's rule is that a refusal is not a failure and must not be reported in the register of
 * something having gone wrong. What MUST surface is `result_summary`, because `failed[]` and
 * `skipped[]` never reach the client any other way — dropping it re-creates a silent-failure
 * path, which BUILD_DOC §5.1 forbids.
 */

import { apiGet, apiSend } from './client.ts';
import type { ApiResult } from './client.ts';

/** v4/overlay poll cadence: every 3s, up to 60 tries (~3 minutes) before giving up. */
export const POLL_MS = 3000;
export const POLL_TRIES = 60;

export type CaptureStart =
  | { kind: 'started' }
  /** A generation was already running. Ordinary, not an error — say so in her register. */
  | { kind: 'busy' }
  | { kind: 'failed'; error: string };

/** `POST /api/capture` — kicks off the weed. Returns immediately; the work is asynchronous. */
export async function startCapture(text: string): Promise<CaptureStart> {
  const res = await apiSend<{ state?: string; started?: boolean }>('POST', '/api/capture', {
    text,
  });
  if (!res.ok) return { kind: 'failed', error: res.error };
  // ⚠ `started === false` arrives on a 2xx. Checking `res.ok` alone reads it as success and
  // polls for a run that does not exist.
  if (res.data.started === false) return { kind: 'busy' };
  return { kind: 'started' };
}

export type GenStatus = { state: 'idle' | 'running' | 'error'; error?: string };

export function getStatus(): Promise<ApiResult<GenStatus>> {
  return apiGet<GenStatus>('/api/status');
}

/** One created object, as the session receipt records it (`capture_generate.py`). */
export interface CreatedItem {
  id: string;
  type: string;
  name: string;
  project?: string | null;
  /** 'Today' | 'Thu Jul 16' | 'Parked' | null — already display-formatted by the resolver. */
  when_label?: string | null;
  is_today?: boolean;
  /** Projects only: Open / Steady / Backburner. */
  engagement?: string | null;
  alignment_reasoning?: string | null;
  dedup_note?: string | null;
}

export interface WeedEntry {
  ts?: string;
  intent: string;
  raw_input?: string;
  created?: CreatedItem[];
  /** "added 3, skipped 1" — the ONLY channel by which skips and failures reach her. */
  result_summary?: string;
  target_id?: string;
}

export function getCaptureSession(): Promise<ApiResult<{ entries: WeedEntry[] }>> {
  return apiGet<{ entries: WeedEntry[] }>('/api/session?stream=capture');
}

/**
 * `POST /api/capture/undo` — archives a just-captured object and marks the undo in the session
 * log. Synchronous (no LLM, no generation lock).
 *
 * ⚠ Known backend gap, carried not hidden (api_contract_v2 §:570): the server confirms this
 * write from the HTTP status alone and never re-fetches to prove the object is gone — the one
 * write path whose "ok" rests on acknowledgment rather than observed state. Not fixed here
 * (different file, different change); recorded so it is not mistaken for proven.
 */
export function undoCaptured(id: string): Promise<ApiResult<{ undone?: boolean }>> {
  return apiSend<{ undone?: boolean }>('POST', '/api/capture/undo', { id });
}

/** The when-chip's three positions, in the order tapping cycles them. */
export const WHEN_TOKENS = ['today', 'tomorrow', 'someday'] as const;
export type WhenToken = (typeof WHEN_TOKENS)[number];

/**
 * `POST /api/task/reschedule`.
 *
 * ⚠ Sends a resolver TOKEN, never the rendered label. The server re-anchors the token to a real
 * date (`when_resolve`), which is what keeps "tomorrow" meaning tomorrow rather than whatever
 * day the label was minted on. Sending the display string would hand date arithmetic to the
 * client and drift.
 */
export function rescheduleCaptured(
  id: string,
  when: WhenToken,
): Promise<ApiResult<{ when_label?: string | null; is_today?: boolean }>> {
  return apiSend<{ when_label?: string | null; is_today?: boolean }>(
    'POST',
    '/api/task/reschedule',
    { id, when },
  );
}

/** `POST /api/project/engagement` — the tap-to-change chip on a captured Project. */
export function setCapturedEngagement(
  id: string,
  from: string,
  to: string,
): Promise<ApiResult<{ engagement?: string }>> {
  return apiSend<{ engagement?: string }>('POST', '/api/project/engagement', {
    id,
    old: from,
    new: to,
  });
}
