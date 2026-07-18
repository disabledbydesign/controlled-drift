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
 * Records go in as `kind='write_failed'`, `before` = the value that was intended, `after` = null.
 *
 * Flagged rather than decided unilaterally: if write failures turn out to be common enough to
 * need their own query surface, the argument for a dedicated channel gets made THEN, on
 * evidence, not now on speculation.
 *
 * ── ⚠ WHAT IS AND IS NOT WIRED ───────────────────────────────────────────────
 * Track A makes NO network calls (plan §"Out of scope for Track A"), so there is no endpoint to
 * post to and `corrections_log` is Python on the server side. What exists here is therefore:
 *   - a real client-side record (`recent()`), which the console and a test can read, and
 *   - `console.error`, so a failure is visible in a dev session without any wiring at all, and
 *   - ONE named seam, `setFailureSink`, for Track B to hand in the poster.
 * The seam is left explicit rather than the requirement dropped. Nothing here silently pretends
 * a server-side write happened.
 */

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

/** Track B hands in the real poster here. Null means "not wired yet", which is the truth today. */
let sink: ((rec: FailureRecord) => void) | null = null;

/**
 * Install the server-side poster. Called by Track B once `POST /api/log/correction` exists;
 * until then nothing calls it and `logFailure` records locally only.
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
  if (sink) sink(rec);
  return rec;
}

/** Every failure recorded this session, oldest first. */
export function recent(): readonly FailureRecord[] {
  return records;
}

/** Test hook — the module holds process-wide state, so a suite has to be able to reset it. */
export function _resetFailureLog(): void {
  records.length = 0;
  sink = null;
}
