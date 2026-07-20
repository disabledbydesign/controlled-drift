// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

/**
 * The failure log's SINK — where a failed write goes once it has been recorded locally.
 *
 * `signals.test.ts` already covers the in-memory trail (`recent()`, the default `kind`, that a
 * record happens with no sink installed). This file covers the seam that was wired in Task 5:
 * the sink is really called, and — the load-bearing one — a sink that throws cannot damage the
 * caller that is already handling a failure.
 *
 * Why that one matters most: `logFailure` is called from `fail()`, from `rollback()`, inside an
 * UNAWAITED `performWrite` promise. Before the guard, a throwing sink threw back out through all
 * three and rejected that promise — converting a failure the system had successfully REPORTED
 * into an unhandled rejection. The bug the error log would have introduced is worse than the one
 * it exists to fix, so it gets a test that fails the moment the guard is removed.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logFailure, recent, setFailureSink, _resetFailureLog } from '../errorLog.ts';

beforeEach(() => {
  _resetFailureLog();
  // `logFailure` writes to console.error by design; silence it so a passing run is quiet.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  _resetFailureLog();
  vi.restoreAllMocks();
});

describe('the installed sink', () => {
  it('receives the failure record on a real failure', () => {
    const sink = vi.fn();
    setFailureSink(sink);

    logFailure('Not moved. The server did not answer.', {
      objectId: 'task-1',
      before: { move: 'task-1' },
    });

    expect(sink).toHaveBeenCalledTimes(1);
    const rec = sink.mock.calls[0]![0];
    expect(rec.msg).toBe('Not moved. The server did not answer.');
    expect(rec.kind).toBe('write_failed');
    expect(rec.objectId).toBe('task-1');
    expect(rec.before).toEqual({ move: 'task-1' });
    expect(typeof rec.ts).toBe('string');
  });
});

describe('a sink that throws', () => {
  it('does NOT propagate out of logFailure — the caller is already handling a failure', () => {
    setFailureSink(() => {
      throw new Error('the poster blew up');
    });

    // The assertion is on the RETURN, not merely on the absence of a throw: `logFailure`
    // must complete its whole contract, not just avoid crashing.
    const rec = logFailure('Not saved.', { objectId: 'task-1' });

    expect(rec.msg).toBe('Not saved.');
    expect(rec.objectId).toBe('task-1');
  });

  it('still leaves the local record behind, so the trail survives a broken poster', () => {
    setFailureSink(() => {
      throw new Error('the poster blew up');
    });

    logFailure('Not saved.');

    expect(recent()).toHaveLength(1);
    expect(recent()[0]!.msg).toBe('Not saved.');
  });

  it('reports its own breakage to the console instead of back into the failure channel', () => {
    // A poster that reported ITS failure through `fail()` would re-enter `logFailure` and
    // recurse without bound. Console only is the fix, so assert the console got it.
    setFailureSink(() => {
      throw new Error('the poster blew up');
    });

    logFailure('Not saved.');

    const said = (console.error as unknown as ReturnType<typeof vi.fn>).mock.calls
      .map((c: unknown[]) => String(c[0]))
      .join('\n');
    expect(said).toContain('the failure sink itself threw');
  });

  it('does not stop the NEXT failure from being recorded and posted', () => {
    const sink = vi.fn(() => {
      throw new Error('the poster blew up');
    });
    setFailureSink(sink);

    logFailure('first');
    logFailure('second');

    expect(sink).toHaveBeenCalledTimes(2);
    expect(recent().map((r) => r.msg)).toEqual(['first', 'second']);
  });
});