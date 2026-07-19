/**
 * Pure helpers over the FOCUS PERIODS — v4's `this.periods` array.
 *
 * Same seam as `model/plan.ts`: focus periods are not part of the object `Graph` (they
 * reference projects by TITLE, not by id — see `fixtures/periods.ts`), so they get their own
 * state-in / new-state-out mutation rather than being forced through `mutations.ts`.
 *
 * v4 mutated the period in place (`p.name=f.name; Object.assign(p,extra)`) and called
 * `bump()`; that cannot work under React reference equality, so the equivalent here rebuilds
 * the array and the one changed period, sharing every untouched entry.
 */

import type { Period } from '../fixtures/index.ts';

/** What a period mutation returns. Mirrors `PlanResult`. */
export interface PeriodResult {
  periods: Period[];
  toast: string | null;
}

/**
 * The focus-period edit form — v4's `st.focusReflect`.
 *
 * Every field of `Period` except `id` and `when`, which the form never carries: v4's
 * `openEdit` (814-816) copies exactly these fifteen keys out of the period, and the author
 * flow's "Structure this →" (v4:893) builds the same fifteen from scratch.
 */
export interface FocusForm {
  name: string;
  start: string;
  end: string;
  intent: string;
  front: string[];
  note: string;
  availStart: string;
  availEnd: string;
  daysOff: string[];
  daysOn: string;
  output: string;
  workdayStart: string;
  workdayEnd: string;
  paused: string[];
}

/** v4:816 `openEdit` — the period → form copy, with every list `.slice()`d. */
export function formFromPeriod(p: Period): FocusForm {
  return {
    name: p.name,
    start: p.start,
    end: p.end,
    intent: p.intent,
    front: (p.front || []).slice(),
    note: p.note || '',
    availStart: p.availStart || '',
    availEnd: p.availEnd || '',
    daysOff: (p.daysOff || []).slice(),
    daysOn: p.daysOn || '',
    output: p.output || 'Auto',
    workdayStart: p.workdayStart || '',
    workdayEnd: p.workdayEnd || '',
    paused: (p.paused || []).slice(),
  };
}

/**
 * The form <-> WIRE-FIELDS translation.
 *
 * ── what replaced `formFromDraft`, and why it had to go ──────────────────────
 * v4's `formFromDraft` built the reflect-back form on the client: it hardcoded
 * `start:'2026-07-21', end:'2026-07-27'` and derived the name by cutting her draft at the first
 * `.`/`,`/newline. The screen it fed is headed "Here's what I heard" and tells her "It reads
 * back what it heard for you to check." No model had run. The surface was claiming a
 * comprehension that never happened, and the dates it showed her were two constants.
 *
 * `POST /api/focus/author` is what actually structures her words (`AI_LAYER_SPEC.md` §2: she
 * says it, the AI structures it into these fields and reflects it back). The structured answer
 * comes back as the server's flat snake_case dict, so the client's job is no longer to invent a
 * form but to TRANSLATE one. That is `formFromFields`; `fieldsFromForm` is the way back.
 *
 * Intent is still carried through UNCHANGED in both directions — spec §14/§17: intent is her own
 * words and is never reworded. There is no transform here and none may be added.
 *
 * ⚠ `daysOn` is a STRING here and a LIST on the wire, mirroring `adapt.ts` `periodFromLive`
 * (`list(p.days_on).join(', ')`). Both directions handle the seam; `focusFields.test.ts`
 * round-trips them against each other rather than trusting the table twice.
 */

/** A wire-side field dict — the server's own key names. */
type Fields = Record<string, unknown>;

function str(v: unknown): string {
  return v === null || v === undefined ? '' : String(v);
}

function list(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => str(x)) : [];
}

/** The form as the three write routes read it. Every editable field, or it does not save. */
export function fieldsFromForm(form: FocusForm): Fields {
  return {
    name: form.name,
    start_date: form.start,
    end_date: form.end,
    intent: form.intent,
    foreground_projects: form.front.slice(),
    availability_note: form.note || '',
    availability_start: form.availStart || '',
    availability_end: form.availEnd || '',
    days_off: form.daysOff.slice(),
    // '' must become [], never [''] — an empty string entry writes a blank day and reads back
    // as a day she never named.
    days_on: form.daysOn
      .split(',')
      .map((d) => d.trim())
      .filter((d) => d.length > 0),
    output_format: form.output || 'Auto',
    workday_start: form.workdayStart || '',
    workday_end: form.workdayEnd || '',
    paused_projects: form.paused.slice(),
  };
}

/** The structure step's answer as the form June checks field by field. */
export function formFromFields(fields: Fields): FocusForm {
  const f = fields || {};
  return {
    name: str(f.name),
    start: str(f.start_date),
    end: str(f.end_date),
    intent: str(f.intent),
    front: list(f.foreground_projects),
    note: str(f.availability_note),
    availStart: str(f.availability_start),
    availEnd: str(f.availability_end),
    daysOff: list(f.days_off),
    daysOn: list(f.days_on).join(', '),
    output: str(f.output_format) || 'Auto',
    workdayStart: str(f.workday_start),
    workdayEnd: str(f.workday_end),
    paused: list(f.paused_projects),
  };
}

/**
 * ⚠ `saveFocus` WAS HERE AND IS GONE. It rebuilt the periods array locally and returned a toast
 * ("Focus period updated" / "Focus period saved"). Nothing left the browser, so every field June
 * edited — name, dates, intent, availability window, note, plan shape, workday hours, days off,
 * foreground and paused projects — was gone on reload, under a message saying it had saved.
 *
 * The write now goes to `POST /api/focus/commit` (new) or `POST /api/focus/update` (edit in
 * place) through `shell/useAppState.ts` `saveFocusPeriod`, and the confirmation waits for the
 * server, which re-fetches and verifies every written field before answering ok.
 *
 * It is deleted rather than left unused on purpose: an exported function with exactly the right
 * name and shape is an invitation to wire the editor back to it.
 *
 * `PeriodResult` stays — `applyPeriods` still takes one — but nothing produces one now.
 */
