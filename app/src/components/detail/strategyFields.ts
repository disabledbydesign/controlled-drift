import type { NoteField } from '../../fixtures/index.ts';

/**
 * Strategy note fields — THE ONE PLACE THE DETAIL FORM OVERRIDES THE SCHEMA.
 *
 * ── WHY ──────────────────────────────────────────────────────────────────────
 * `docs/BUILD_DOC.md` §"Strategy — DECIDED 2026-07-18" settles this: the mockup drifted from
 * the data model, and the data model wins. June has 12 real Strategy objects. The live
 * Anytype type carries `name`, `Applies when`, `What for`, `Learning notes`, `Context`,
 * `Strategy status`. Across those 12:
 *
 *   `What for`        carries BOTH the trigger and the instruction — used on essentially all
 *   `Context`         elaboration, origin, distinctions — used on ~10 of 12
 *   `Applies when`    used on 1 of 12
 *   `Learning notes`  currently unused, but it is a real field on the type
 *
 * The mockup's schema offers `Directive` and `Notes`, and no `Learning notes` at all. Porting
 * it verbatim would print the wrong label over the field where her instructions actually live
 * and would give her nowhere to see a real field of the type. Both are hiding data, not
 * styling it, so the labels are corrected here.
 *
 * ── WHAT CHANGES AND WHAT DOES NOT ───────────────────────────────────────────
 * VALUE KEYS ARE UNCHANGED. `directive`, `context` and `status` stay exactly as the fixture
 * names them, because the fixture is the mockup's naming and translating mockup keys to live
 * Anytype field names happens at the API seam (Track B, `docs/api_contract_v2.md`), not in a
 * component. The seam mapping this anticipates:
 *
 *   fixture key      live Anytype field
 *   ───────────      ──────────────────
 *   title            name
 *   when             Applies when
 *   status           Strategy status
 *   directive        What for          ← NOT a new field; the mockup's own key, relabelled
 *   context          Context
 *   learningNotes    Learning notes    ← no mockup key existed; this one is coined here
 *
 * No `Directive` field is added — `directive` is the SAME field, shown under the name the
 * data model uses for it.
 *
 * ── HOW LONG THIS LIVES ──────────────────────────────────────────────────────
 * Until `GET /api/schema` lands (Track B, "four API gaps"). The fetched schema will carry the
 * live labels and the live field list, at which point `Detail` reads `TEXT.STRATEGY`
 * unmodified and this file is deleted. It is deliberately a thin transform over the schema's
 * own output rather than a replacement list, so a schema that gains fields keeps them.
 */

/** Mockup label → live Anytype field name, for the note fields Strategy actually has. */
const RELABEL: Record<string, string> = {
  // key      // live field name
  directive: 'What for',
  context: 'Context',
};

/** Live fields the mockup's schema has no entry for at all. */
const EXTRA: readonly NoteField[] = [['Learning notes', 'learningNotes']] as const;

export function strategyNotes(fromSchema: readonly NoteField[]): readonly NoteField[] {
  const relabelled: NoteField[] = fromSchema.map(([label, key]) => {
    const live = RELABEL[key];
    return live ? ([live, key] as NoteField) : ([label, key] as NoteField);
  });
  const have = new Set(relabelled.map(([, key]) => key));
  for (const extra of EXTRA) if (!have.has(extra[1])) relabelled.push(extra);
  return relabelled;
}
