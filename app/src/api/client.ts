/**
 * The network seam. Every request the surface makes goes through this file.
 *
 * ── why one file ─────────────────────────────────────────────────────────────
 * `docs/api_contract_v2.md` §0 records that the v4 mockup has exactly ONE declared network
 * seam in 1179 lines — a commented-out `fetch('/api/schema')` — and that "the frontend track's
 * first structural job is therefore to introduce the data layer the mockup does not have."
 * This is that layer. Nothing else in `app/src` calls `fetch`.
 *
 * ── same-origin, and why there is no base URL setting ────────────────────────
 * The built bundle is served by `scripts/server.py` at `/app/` (its `_serve_app`), so `/api/...`
 * is same-origin in production. In dev, `vite.config.ts` proxies `/api` to `127.0.0.1:5050`, so
 * it is same-origin there too. That is deliberate and is why commit d9eb4bb could refuse to add
 * CORS: the browser never talks cross-origin, so there is no preflight to answer.
 *
 * ── failure is a value, not an exception ─────────────────────────────────────
 * Every function returns `{ok:true, data}` or `{ok:false, error}`. A rejected promise would let
 * a caller forget a `catch` and lose the failure silently, which is the one outcome
 * `docs/BUILD_DOC.md` §5.1 forbids ("no silent failures"). The server already answers write
 * failures in the contract's `{ok:false, error}` envelope, including a read-back that could not
 * prove the write (`server.py:_run_write`) — so a 500 here is a REAL not-saved, not a transport
 * hiccup to be smoothed over.
 */

/** What a request produced. `error` is a sentence fit to show June, not a stack. */
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

/** Requests hang rather than fail when Anytype is asleep; a live tree read takes ~2s. */
const TIMEOUT_MS = 30_000;

function message(e: unknown): string {
  if (e instanceof DOMException && e.name === 'AbortError') {
    return 'the server did not answer in time';
  }
  if (e instanceof TypeError) return 'could not reach the server';
  return e instanceof Error ? e.message : String(e);
}

/**
 * One request. The server's own `{error}` / `{ok:false,error}` body is preferred over an
 * invented "HTTP 500" string, because that body is what says WHICH field did not save.
 */
async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(path, {
      ...init,
      signal: ctl.signal,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    });
    const text = await res.text();
    let body: unknown = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      // `/api/map` still answers text/plain on failure (contract §3.2) and a 404 fallthrough is
      // JSON — but a non-JSON body must not read as a parse crash. Report what arrived.
      return { ok: false, error: text.slice(0, 200) || `HTTP ${res.status}` };
    }
    const rec = (body ?? {}) as Record<string, unknown>;
    if (!res.ok || rec['ok'] === false) {
      const err = typeof rec['error'] === 'string' ? rec['error'] : `HTTP ${res.status}`;
      return { ok: false, error: err };
    }
    return { ok: true, data: body as T };
  } catch (e) {
    return { ok: false, error: message(e) };
  } finally {
    clearTimeout(timer);
  }
}

export function apiGet<T>(path: string): Promise<ApiResult<T>> {
  return request<T>(path);
}

export function apiSend<T>(
  method: 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<ApiResult<T>> {
  return request<T>(path, {
    method,
    ...(body === undefined ? null : { body: JSON.stringify(body) }),
  });
}
