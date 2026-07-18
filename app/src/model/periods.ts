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
 * v4:893 — the form the author flow hands to the reflect-back view.
 *
 * ⚠ v4 hardcodes `start:'2026-07-21', end:'2026-07-27'` and derives the name by cutting the
 * draft at the first `.`/`,`/newline and capping it at 48 chars. Both are MOCKUP STAND-INS for
 * the LLM structuring pass described in `AI_LAYER_SPEC.md` §2 ("she *says it*, the AI
 * structures it into these fields and reflects it back"). Ported verbatim so the flow is
 * drivable; Track B replaces the body of this function, not its shape.
 *
 * The intent is carried through UNCHANGED (`intent: draft`) — spec §14/§17: intent is the
 * user's own words and is never reworded. There is no transform here and none may be added.
 */
export function formFromDraft(draft: string): FocusForm {
  const first = draft.split(/[.,\n]/)[0] ?? '';
  return {
    name: first.slice(0, 48),
    start: '2026-07-21',
    end: '2026-07-27',
    intent: draft,
    front: [],
    note: '',
    availStart: '',
    availEnd: '',
    daysOff: [],
    daysOn: '',
    output: 'Auto',
    workdayStart: '',
    workdayEnd: '',
    paused: [],
  };
}

/** v4:923 — a new period's id: `'fp'+Math.random().toString(36).slice(2,6)`. */
function newPeriodId(): string {
  return 'fp' + Math.random().toString(36).slice(2, 6);
}

/**
 * v4 `saveFocus(view)` (920), as a pure function.
 *
 * `edit` writes the form back onto the period `editId` names; anything else (v4's `else`
 * branch, reached from `view==='author'`) appends a NEW period with `when:'upcoming'`.
 *
 * ⚠ Two v4 behaviours preserved as-is rather than tidied:
 *   1. In edit mode, if no period matches `editId`, v4 still flashes "Focus period updated"
 *      and closes. Nothing was written. Same here.
 *   2. The new period keeps `name: f.name || 'New focus period'`, but the EDIT branch has no
 *      such fallback — editing a name to empty stores an empty name.
 */
export function saveFocus(
  periods: readonly Period[],
  view: 'edit' | 'author',
  editId: string | null,
  form: FocusForm,
): PeriodResult {
  // v4:921-922 build `front`/`paused`/`extra` from the form. The comma-string fallbacks v4
  // wraps these in (`(f.front||'').split(',')…`) are unreachable: both producers of a form —
  // `formFromPeriod` and `formFromDraft` — supply arrays, and `FocusForm` types them as
  // arrays. Dropped rather than ported dead.
  const extra = {
    front: form.front.slice(),
    note: form.note || '',
    availStart: form.availStart || '',
    availEnd: form.availEnd || '',
    daysOff: form.daysOff.slice(),
    daysOn: form.daysOn || '',
    output: form.output || 'Auto',
    workdayStart: form.workdayStart || '',
    workdayEnd: form.workdayEnd || '',
    paused: form.paused.slice(),
  };

  if (view === 'edit') {
    return {
      periods: periods.map((p) =>
        p.id === editId
          ? { ...p, name: form.name, start: form.start, end: form.end, intent: form.intent, ...extra }
          : p,
      ),
      toast: 'Focus period updated',
    };
  }

  return {
    periods: [
      ...periods,
      {
        id: newPeriodId(),
        when: 'upcoming',
        name: form.name || 'New focus period',
        start: form.start,
        end: form.end,
        intent: form.intent,
        ...extra,
      },
    ],
    toast: 'Focus period saved',
  };
}
