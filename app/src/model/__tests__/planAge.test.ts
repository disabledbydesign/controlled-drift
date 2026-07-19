/**
 * The plan-age line — "how old is what I am looking at, in words I can act on".
 *
 * WHY THIS EXISTS. The morning generation can fail. When it does, yesterday's plan is what is
 * on screen, and without this line it reads as today's. June's whole system exists so her
 * commitments live outside her head; a plan that silently presents yesterday as today is the
 * system lying about the one thing she relies on it for.
 *
 * The wording is TRANSCRIBED from `docs/overlay_daily.html` `renderPlanAge()` (~2409) — the
 * surface she used for months and tuned to herself — not composed here.
 *
 * These assert the TRUTH CONDITION: given a plan built at time T, what must she see. Not that
 * some element exists, and not that a wrong string is absent.
 */

import { describe, expect, it } from 'vitest';
import { planAgeText } from '../plan.ts';

/** Local-time construction, because the server sends a naive local ISO with no zone suffix. */
const at = (y: number, m: number, d: number, h: number, min: number) => new Date(y, m - 1, d, h, min);

describe('planAgeText', () => {
  it('says nothing at all when there is no timestamp to report', () => {
    const now = at(2026, 7, 19, 14, 0);
    expect(planAgeText('', now)).toBe('');
    expect(planAgeText(undefined, now)).toBe('');
  });

  it('says nothing rather than "Invalid Date" when the timestamp is unparseable', () => {
    expect(planAgeText('not-a-date', at(2026, 7, 19, 14, 0))).toBe('');
  });

  // ── built today: an honest fact, and NO call to regenerate ────────────────
  it('reports a plan built this morning, with no staleness notice', () => {
    const built = at(2026, 7, 19, 9, 2);
    expect(planAgeText(built.toISOString(), at(2026, 7, 19, 14, 0))).toBe(
      'built this morning at 9:02 AM',
    );
  });

  it('names the part of the day from the build hour, not the current hour', () => {
    const now = at(2026, 7, 19, 22, 0); // evening now …
    expect(planAgeText(at(2026, 7, 19, 9, 2).toISOString(), now)).toContain('this morning');
    expect(planAgeText(at(2026, 7, 19, 13, 30).toISOString(), now)).toContain('this afternoon');
    expect(planAgeText(at(2026, 7, 19, 19, 45).toISOString(), now)).toContain('this evening');
  });

  // ── the case this whole line was built for ───────────────────────────────
  it('reports a plan left over from yesterday AND how to get today’s', () => {
    const built = at(2026, 7, 18, 19, 42); // the brief's example
    expect(planAgeText(built.toISOString(), at(2026, 7, 19, 8, 0))).toBe(
      'built yesterday evening at 7:42 PM — tap Fresh plan for today’s',
    );
  });

  it('gives an unambiguous date for anything older than yesterday', () => {
    const built = at(2026, 7, 15, 9, 2);
    expect(planAgeText(built.toISOString(), at(2026, 7, 19, 8, 0))).toBe(
      'built Jul 15 at 9:02 AM — tap Fresh plan for today’s',
    );
  });

  /*
   * Staleness is CALENDAR DAYS, not elapsed hours — the thing she needs to know is "is this
   * today's plan", and a plan built at 11pm is stale at 1am despite being two hours old.
   */
  it('counts staleness in calendar days, not elapsed hours', () => {
    const built = at(2026, 7, 18, 23, 30);
    expect(planAgeText(built.toISOString(), at(2026, 7, 19, 1, 0))).toContain('built yesterday');
    // …and a plan built 20 hours ago on the SAME day is not stale.
    const sameDay = at(2026, 7, 19, 0, 30);
    expect(planAgeText(sameDay.toISOString(), at(2026, 7, 19, 20, 30))).not.toContain('tap Fresh');
  });

  it('offers the way to refresh on every stale plan and on no fresh one', () => {
    const now = at(2026, 7, 19, 12, 0);
    expect(planAgeText(at(2026, 7, 19, 9, 0).toISOString(), now)).not.toContain('Fresh plan');
    expect(planAgeText(at(2026, 7, 18, 9, 0).toISOString(), now)).toContain(
      'tap Fresh plan for today’s',
    );
    expect(planAgeText(at(2026, 7, 1, 9, 0).toISOString(), now)).toContain(
      'tap Fresh plan for today’s',
    );
  });

  /*
   * Hard accessibility rule (global CLAUDE.md): no metaphors in any June-facing string.
   * Every word here is literal — built, yesterday, morning, tap.
   */
  it('states the age in literal words, never a metaphor', () => {
    const text = planAgeText(at(2026, 7, 18, 19, 42).toISOString(), at(2026, 7, 19, 8, 0));
    expect(text).toMatch(/^built /);
    for (const metaphor of ['stale', 'fresh out', 'aging', 'old news', 'yesterday’s news']) {
      expect(text.toLowerCase()).not.toContain(metaphor);
    }
  });
});
