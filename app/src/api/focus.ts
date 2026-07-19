/**
 * The FOCUS PERIOD write path — authoring, reflect-back, commit, spoken edit, update.
 *
 * ── why this file exists ─────────────────────────────────────────────────────
 * Five endpoints were live and unreachable. `saveFocus` (`model/periods.ts`) was a pure local
 * state change: every field June edited — name, dates, intent, availability window, note, plan
 * shape, workday hours, days off, foreground and paused projects — was gone on reload, under a
 * toast reading "Focus period updated". This is the wire-in.
 *
 * ── THE REFUSAL CONVENTION, AND WHY IT IS HANDLED HERE AND NOT IN `client.ts` ──
 * `/api/focus/commit` (`server.py:1371`) and `/api/focus/update` (`:1451`) answer a REFUSED
 * write with **HTTP 200** and a body of `{"blocked":[...]}` — a list of plain field labels from
 * `focus_period_adapter.missing_required`, e.g. `['end date']`. `client.ts`'s `request()` treats
 * any 200 without `ok:false` as success, so a refusal would raise a success toast over a period
 * that was never written.
 *
 * That convention is this endpoint family's private one. Teaching the shared client to look for
 * `blocked` would impose one family's protocol on all traffic, so the translation lives here.
 *
 * ── THREE OUTCOMES, NOT TWO ──────────────────────────────────────────────────
 * `FocusWrite` is a three-way union on purpose:
 *
 *   saved  — the server wrote it AND proved it by re-fetching (both routes read back before
 *            answering, and 500 rather than claim a write they could not confirm).
 *   needs  — she has not filled a required field in yet. **This is not a failure.** It must not
 *            travel the error channel, must not be logged as breakage, and must not address her
 *            in the register of something having gone wrong. It names the field instead.
 *   failed — the request actually broke (network, server, an unknown project name at 400).
 *
 * Collapsing any two of these is the defect this seam exists to prevent. `capture.ts`'s
 * busy/failed split is the same rule applied to the same problem.
 */

import { apiGet, apiSend } from './client.ts';
import type { ApiResult } from './client.ts';

/** The authoring poll cadence — the structure step is an LLM call (~30s). */
export const FOCUS_POLL_MS = 3000;
export const FOCUS_POLL_TRIES = 60;

/**
 * The flat, snake_case field dict the three write routes read and the generate step emits.
 * Keys are the server's (`focus_period_adapter.period_to_fields`), never the app's camelCase
 * form keys — `model/periods.ts` owns the translation between the two.
 */
export type FocusFields = Record<string, unknown>;

/** What a focus write produced. See the three-outcomes note above. */
export type FocusWrite =
  | { kind: 'saved'; id: string; name: string }
  /** She has not filled these in yet. `missing` holds plain labels: `['end date']`. */
  | { kind: 'needs'; missing: string[] }
  | { kind: 'failed'; error: string };

/**
 * Translate one commit/update response into an outcome.
 *
 * ⚠ The `blocked` check runs BEFORE the success return, because the refusal arrives on a 200
 * that `client.ts` has already classified as `ok`. Checking `res.ok` alone reads a refusal as a
 * saved period.
 */
function writeOutcome(res: ApiResult<{ ok?: boolean; id?: string; name?: string; blocked?: unknown }>): FocusWrite {
  if (!res.ok) return { kind: 'failed', error: res.error };
  const blocked = res.data?.blocked;
  if (Array.isArray(blocked) && blocked.length > 0) {
    return { kind: 'needs', missing: blocked.map((b) => String(b)) };
  }
  return { kind: 'saved', id: String(res.data?.id ?? ''), name: String(res.data?.name ?? '') };
}

/** `POST /api/focus/commit` — confirm a NEW period and write it. */
export async function commitFocus(fields: FocusFields, rawText: string): Promise<FocusWrite> {
  return writeOutcome(
    await apiSend('POST', '/api/focus/commit', { fields, raw_text: rawText }),
  );
}

/**
 * `POST /api/focus/update` — confirm an edit and UPDATE THE EXISTING object in place.
 *
 * The id is required by the server (400 without it), which is why it is a separate parameter
 * rather than something hopefully present inside `fields`.
 */
export async function updateFocus(
  id: string,
  fields: FocusFields,
  rawText: string,
): Promise<FocusWrite> {
  return writeOutcome(
    await apiSend('POST', '/api/focus/update', { id, fields, raw_text: rawText }),
  );
}

/** Starting an async structure step. `busy` is ordinary, not an error. */
export type FocusStart =
  | { kind: 'started' }
  /** A generation already holds the single shared lock. Say "one thing at a time," not "failed". */
  | { kind: 'busy' }
  | { kind: 'failed'; error: string };

async function startJob(path: string, text: string): Promise<FocusStart> {
  const res = await apiSend<{ state?: string; started?: boolean }>('POST', path, { text });
  if (!res.ok) return { kind: 'failed', error: res.error };
  // ⚠ `started:false` arrives on a 202 — a 2xx. `res.ok` alone reads it as running.
  if (res.data?.started === false) return { kind: 'busy' };
  return { kind: 'started' };
}

/**
 * `POST /api/focus/author` — hand June's own words to the structure step.
 *
 * This is what `formFromDraft`'s hardcoded dates were standing in for. The result does NOT come
 * back from this call: poll `focusStatus()`, then read `focusResult()`.
 */
export function startAuthor(text: string): Promise<FocusStart> {
  return startJob('/api/focus/author', text);
}

/**
 * `POST /api/focus/edit` — a broad SPOKEN revision of the active period. Same async shape as
 * authoring; the result carries `original` as well, so the reflect-back can mark what changed.
 */
export function startFocusEdit(text: string): Promise<FocusStart> {
  return startJob('/api/focus/edit', text);
}

/** `GET /api/focus/status` — the authoring poller. Focus has its OWN status route, not `/api/status`. */
export type FocusStatus = { state?: string; error?: string; result_ready?: boolean };

export function focusStatus(): Promise<ApiResult<FocusStatus>> {
  return apiGet<FocusStatus>('/api/focus/status');
}

/** One line of the deterministic read-back June checks field by field. */
export interface ReflectItem {
  key: string;
  label: string;
  edit: string;
  display: string;
  /** Edit route only: whether this field changed against the period's previous state. */
  changed?: boolean;
}

export interface ReflectPayload {
  summary: string;
  items: ReflectItem[];
  blocking?: string[];
}

/** `GET /api/focus/result` — the structured fields plus the reflect-back, once the job lands. */
export interface FocusResult {
  empty?: boolean;
  raw_text?: string;
  fields?: FocusFields;
  /** Edit route only: the period's state before the revision. */
  original?: FocusFields;
  /** Edit route only: the id to update in place. */
  id?: string;
  reflect?: ReflectPayload;
}

export function focusResult(): Promise<ApiResult<FocusResult>> {
  return apiGet<FocusResult>('/api/focus/result');
}

/**
 * `POST /api/focus/reflect` — re-render the read-back after a per-field fix. Synchronous, NO LLM.
 *
 * The template lives in Python so the wording June checks has ONE source. This is also what
 * makes the "Here's what I heard" screen honest: it shows what the structure step actually
 * produced instead of a summary the client made up.
 */
export function reflectFields(
  fields: FocusFields,
  original?: FocusFields,
): Promise<ApiResult<ReflectPayload>> {
  return apiSend<ReflectPayload>('POST', '/api/focus/reflect', {
    fields,
    ...(original === undefined ? null : { original }),
  });
}
