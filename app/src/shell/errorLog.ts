/**
 * Where a failure GOES, as distinct from where it is shown.
 *
 * June, 2026-07-18: *"What matters more is error logging if something fails."* Displaying an
 * error is not recording it — a message that fades (or that she dismisses without reading) has
 * left no trace, and the whole point is that a failed write is diagnosable afterwards.
 *
 * ── which log, and why not a new one ─────────────────────────────────────────
 * The repo rule is explicit (`docs/handoff_2026-07-17_surface_rebuild.md` §5): *"Do not add a
 * thirteenth log. Route new signals through an existing one (`corrections_log` takes `kind,
 * before, after`)."* I read all twelve `scripts/*_log.py` names and the two closest bodies.
 * Honest answer: **none of the twelve is an error log.** They record June's behaviour and the
 * system's proposals — surfacing history, completions, chunk sizes, reactivations, her own
 * words. A failed write is a fact about the software, not about her.
 *
 * `corrections_log.py` is nevertheless the right destination, because the repo has already
 * NAMED it the catch-all for signals without a home, and its shape fits without distortion:
 * `log_correction(kind, before, after, *, object_id=None, object_type=None, ...)`
 * (`scripts/corrections_log.py:73`). A failed write is a divergence between what the system
 * reported and what actually persisted, which is the family of thing that log already carries.
 * Records go in as `kind='write_failed'`, `after` = null (nothing persisted — literally true),
 * and `before` = `{msg, intended}`. ⚠ The message rides INSIDE `before` because
 * `log_correction` has no parameter for it, and the message is the diagnostic half — a record
 * saying a write failed without saying WHICH one is not worth keeping. Wrapping it was
 * preferred to widening a module every other caller shares.
 *
 * ⚠ `field` is never set on these records. `corrections_log.resolve_authored_by` treats any
 * non-'authorship' record for an (object_id, field) pair as June having overwritten that field,
 * so stamping a field on a write that FAILED would tell the learning loop she authored a value
 * she never managed to save. See the route comment in `server.py` for the full account.
 *
 * Flagged rather than decided unilaterally: if write failures turn out to be common enough to
 * need their own query surface, the argument for a dedicated channel gets made THEN, on
 * evidence, not now on speculation.
 *
 * ── ⚠ WHAT IS AND IS NOT WIRED (updated 2026-07-18, Task 5) ──────────────────
 * WIRED as of this commit. `POST /api/log/correction` exists (`server.py`), `postFailure` below
 * posts to it, and `installFailureSink()` is called from `main.tsx`. So a failure now reaches
 * three places: the in-memory `recent()` trail, `console.error`, and the durable log on disk.
 *
 * STILL NOT TRUE, and not pretended to be: delivery is not guaranteed. The post is
 * fire-and-forget with no retry and no offline queue, so a failure that happens while the
 * server is unreachable reaches the console and the in-memory trail only. That is the honest
 * boundary of this seam; see `postFailure` for why it must stay quiet when it cannot deliver.
 */

import { apiSend } from '../api/client.ts';

/** One recorded failure. Mirrors `log_correction`'s parameter names so the Track B post is a
 *  rename-free pass-through. */
export interface FailureRecord {
  /** `corrections_log`'s `kind`. */
  kind: string;
  /** ISO timestamp, client clock. */
  ts: string;
  /** June-facing sentence — the same text the bar showed. */
  msg: string;
  /** The object the failure was about, when there is one. */
  objectId: string | null;
  /** What was intended — `corrections_log`'s `before`. */
  before: unknown;
}

/** How many records are kept in memory. Enough to read a session's failures; not a store. */
const LIMIT = 50;

const records: FailureRecord[] = [];

/** The server-side poster. Null until `installFailureSink()` runs, and in tests that do not
 *  install one — `logFailure` then records locally only, which is still a real record. */
let sink: ((rec: FailureRecord) => void) | null = null;

/**
 * Install a server-side poster. Production hands in `postFailure` via `installFailureSink()`;
 * tests hand in their own to observe what a failure carries.
 */
export function setFailureSink(next: ((rec: FailureRecord) => void) | null): void {
  sink = next;
}

/** Record a failure. Always local; also remote once the sink is installed. */
export function logFailure(
  msg: string,
  opts: { kind?: string; objectId?: string | null; before?: unknown } = {},
): FailureRecord {
  const rec: FailureRecord = {
    kind: opts.kind ?? 'write_failed',
    ts: new Date().toISOString(),
    msg,
    objectId: opts.objectId ?? null,
    before: opts.before ?? null,
  };
  records.push(rec);
  if (records.length > LIMIT) records.shift();
  // Deliberately `console.error` and not `warn`: a failed write is an error, and this is the
  // only channel that exists before Track B wires the sink.
  console.error('[controlled-drift] ' + rec.kind + ': ' + msg, rec);
  // ⚠ GUARDED, and this is the load-bearing line of the file. `logFailure` is called from
  // `fail()`, which is called from `rollback()`, which runs inside an UNAWAITED `performWrite`
  // promise. A sink that threw would throw straight back out through all three and reject that
  // promise — turning a failure the system successfully REPORTED into an unhandled rejection,
  // which is strictly worse than the problem the sink exists to solve. Nothing a sink does may
  // change what `logFailure` does for its caller.
  if (sink) {
    try {
      sink(rec);
    } catch (e) {
      // console only. Calling `fail()` here would re-enter `logFailure` and recurse forever.
      console.error('[controlled-drift] the failure sink itself threw', e);
    }
  }
  return rec;
}

/** Every failure recorded this session, oldest first. */
export function recent(): readonly FailureRecord[] {
  return records;
}

/**
 * The real poster — `POST /api/log/correction`, which appends through `corrections_log` on the
 * server so a failed write outlives the tab.
 *
 * ── three properties, all deliberate ─────────────────────────────────────────
 * 1. FIRE-AND-FORGET. It returns void and awaits nothing. `logFailure` is synchronous and sits
 *    on a rollback path; making it wait on the network would delay the rollback for the sake of
 *    bookkeeping.
 * 2. IT NEVER THROWS. `apiSend` already reports failure as a VALUE rather than a rejection
 *    (see `api/client.ts`), so the `.then` rejection arm and the outer `try` are belt-and-braces
 *    against a synchronous throw before the promise exists — but the guarantee has to hold here
 *    as well as at the call site, not only there.
 * 3. IT NEVER CALLS `fail()`. A poster that reported its own failure through the app's failure
 *    channel would re-enter `logFailure`, post again, fail again, and recurse without bound. So
 *    a failure to record a failure is CONSOLE ONLY. That is a real limit and worth naming: if
 *    the server is unreachable, the durable log does not get the record, and only the in-memory
 *    trail and the console have it. Retry/queueing is not built, and is not pretended to be.
 */
function postFailure(rec: FailureRecord): void {
  try {
    void apiSend('POST', '/api/log/correction', {
      kind: rec.kind,
      msg: rec.msg,
      objectId: rec.objectId,
      before: rec.before,
      ts: rec.ts,
    }).then(
      (res) => {
        if (!res.ok) {
          console.error('[controlled-drift] failure not recorded on the server: ' + res.error, rec);
        }
      },
      (e) => {
        console.error('[controlled-drift] failure not recorded on the server', e, rec);
      },
    );
  } catch (e) {
    console.error('[controlled-drift] failure not recorded on the server', e, rec);
  }
}

/**
 * Wire the poster in. Called once at startup from `main.tsx` — the production caller
 * `setFailureSink` did not have until now.
 */
export function installFailureSink(): void {
  setFailureSink(postFailure);
}

/** Test hook — the module holds process-wide state, so a suite has to be able to reset it. */
export function _resetFailureLog(): void {
  records.length = 0;
  sink = null;
}
