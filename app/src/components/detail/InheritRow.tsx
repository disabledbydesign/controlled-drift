import { useState } from 'react';
import type { ReactNode } from 'react';
import { alpha } from '@tokens';
import { clearVal, effective, isOwnValue, setVal } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import type { DetailCtx } from './types.ts';

export interface InheritRowProps {
  ctx: DetailCtx;
  n: ModelNode;
  /** The value key, v4's `vk`. */
  vk: string;
  label: string;
  hint?: string | null;
  /** v4's `buildEditor` — the control to show when the node has its OWN value. */
  editor: ReactNode;
}

/**
 * v4 `inheritRow(n,vk,label,hint,buildEditor)` (~488).
 *
 * ══ REVISED 2026-07-18 (June, this session) ═════════════════════════════════
 * Supersedes the presentation rule recorded below and in
 * `docs/handoff_2026-07-17_surface_rebuild.md:54` ("the inherit control is TWO states"). That
 * entry sits under "Load-bearing decisions — do not quietly reverse", so this is NOT quiet:
 * June asked for the change directly after hitting a save failure on this control —
 *
 *   "it would be easier to just make the UI display the editor either way, but greyed out if
 *    inheriting (but in a way that still renders it visible what those selections its
 *    inheriting are)... So the statuses should be: Inherit from parent, nothing selected, or
 *    1+ selected (custom, not inherited)."
 *
 * What changed, and what did NOT:
 *   · CHANGED — presentation. The dashed box no longer REPLACES the editor. The editor is
 *     always rendered; while inheriting it is shown non-interactive, populated with the
 *     inherited selections (`Field.tsx` builds it from the effective value), so she can see
 *     what she is actually getting before deciding to diverge.
 *   · CHANGED — `Custom` now PRE-LOADS the inherited value instead of writing empty. The old
 *     behaviour wrote `''` the instant she clicked, which for a multi_select is a delete, so
 *     the save failed its own read-back ("wrote [], read back: absent") and nothing was saved.
 *     Pre-loading also matches the spec's framing: "inherit-the-shared-default,
 *     override-when-it-differs" (backend spec §4).
 *   · UNCHANGED — the DATA model. Key absent = inherit, key present = set here. `Inherit`
 *     still REMOVES the key rather than emptying it. That is spec §4 and is untouched.
 *
 * ── THE THIRD STATUS IS NOT STORABLE FOR EVERY FIELD ────────────────────────
 * Her three statuses are inherit / set-here-empty / set-here-with-values. Verified live
 * 2026-07-18 against her real space (scratch objects, archived after): whether "set here,
 * deliberately empty" survives a round-trip depends on the property's FORMAT.
 *
 *     access     multi_select   writing [] DELETES the property — set-here-empty is
 *                               indistinguishable from never-set. NOT storable.
 *     affective  text           '' reads back as present. Storable.
 *     blockMin   number         no empty; 0 is a real value. NOT storable.
 *
 * So for `access` the middle status cannot persist, and this control must not offer a state
 * the store cannot hold — it would report saved and come back inheriting on reload. Deselecting
 * the last option is therefore treated as a return to inheriting for a multi_select, and said
 * plainly. That is the same honest limit `scripts/resolve.py` already records for checkboxes
 * ("A checkbox therefore has no tri-state — ... that is a property of the storage").
 * ⚠ OPEN, June's call: adding a real "none of these" option to the Access conditions list would
 * make the middle status storable. That is a schema write, which is human-gated.
 *
 * ── superseded note, kept for the record ────────────────────────────────────
 * ── TWO STATES, not three (June, 2026-07-18) ────────────────────────────────
 * A field is either INHERITED from an ancestor, or SET HERE. That is the whole model, and the
 * `Inherit | Custom` segments already carry it.
 *
 * **An empty value on a SET field is a normal, valid shape — not a special case.** June:
 * "Selecting no options is a valid shape (if leaving the house isn't checked, it doesn't
 * involve leaving the house)." So `Custom` with nothing checked simply means none of the
 * options apply. It needs no explanation and gets none.
 *
 * ⚠ An earlier pass added a line reading "Set here as none — not inherited." under that case,
 * describing it as an honest third state. It was REMOVED: v4 has no such text (its inheritRow
 * renders exactly two branches — the dashed box, or the editor), and it editorialised an
 * ordinary state as if it were unusual.
 *
 * The underlying DATA model still has the distinction that backend spec §4 turns on, and the
 * segments are what express it:
 *   · key ABSENT   → inheriting. `Inherit` lit. Dashed box naming the ancestor, or
 *                    "Nothing to inherit from a parent yet".
 *   · key PRESENT  → set here. `Custom` lit, editor shown — whether the value is empty or not.
 *
 * `Inherit` calls `clearVal`, which DELETES the key. It must never write '' — that would set
 * the field here and silently stop the ancestor walk.
 */
export function InheritRow({ ctx, n, vk, label, hint, editor }: InheritRowProps) {
  const { T, graph, idx, apply } = ctx;
  const C = T.c;
  const id = n.id;

  const noOwnValue = !isOwnValue(n, vk);
  const eff = effective(idx, n, vk);

  /**
   * "She pressed Custom, but there was nothing to copy down yet."
   *
   * Local, and deliberately not in the shared UI bag: nothing outside this control reads it and
   * it must die with the pane. Identity is React's job — `Field.tsx` gives this component a
   * `key` of `id + vk`, so switching object or field MOUNTS A NEW ROW and this resets to false
   * on its own. An earlier version compared a stored `id + ' ' + vk` string instead; the compare
   * went true while the rendered output stayed in the inheriting branch, so the hand-rolled
   * identity was replaced by the framework's.
   *
   * This exists because the state it represents is NOT STORABLE for every field. For a
   * multi_select, "set here, nothing selected" and "unset" are the same bytes (verified live),
   * so there is nowhere to persist "she chose to diverge but has not picked anything yet". The
   * alternative — writing an empty value on the click — is precisely the bug she hit: for a
   * multi_select that write DELETES the property and fails its own read-back.
   *
   * So the opened-but-not-yet-written state lives here, for as long as the pane is open. Her
   * first selection writes through the normal path and makes it real.
   */
  const [opened, setOpened] = useState(false);

  const inheriting = noOwnValue && !opened;

  // v4: `disp = v => (v===''||v==null) ? 'none set' : (''+v).replace(/-/g,' ')`
  const disp = (v: unknown): string =>
    v === '' || v === null || v === undefined ? 'none set' : String(v).replace(/-/g, ' ');

  const seg = (txt: string, on: boolean, onClick: () => void) => (
    <button
      key={txt}
      onClick={onClick}
      style={{
        fontSize: '11px',
        fontWeight: 600,
        padding: '4px 11px',
        borderRadius: T.r.ctl,
        cursor: 'pointer',
        fontFamily: 'inherit',
        border: '1px solid ' + (on ? C.blue : C.border),
        // v4: `C.blue+'22'` — 0x22/255 = .133
        background: on ? alpha(C.blue, 0.133) : C.panel,
        color: on ? C.blue : C.dim,
      }}
    >
      {txt}
    </button>
  );

  // v4's `n.vals[vk]` read for the Custom branch.
  const own = n.vals[vk];

  /**
   * The editor, always rendered. While inheriting it is shown but not operable.
   *
   * DERIVED, not transcribed — the gallery has no precedent for an inheriting/disabled field
   * (searched `design/mockups/color-system.html` regions 4a/4c/5a/5c, the only trusted ones).
   * Derived from two things already in the system, introducing no new colour or radius:
   *   · `C.disabled` — the existing token for an inactive control, gallery L60/L153, defined in
   *     BOTH themes, so this forks with the theme rather than hardcoding a grey.
   *   · the dashed border this branch already used, kept as the signal that the value is not
   *     this object's own. `Detail.test.tsx:90` treats that dash as load-bearing, and it stays.
   * `pointerEvents:'none'` is what makes it non-operable; `inert` would be better but is not in
   * this React version's typings. The children keep their own inline colours (inline styles do
   * not cascade), so the wrapper carries the dimming — hence opacity rather than a colour swap.
   */
  const shownEditor = inheriting ? (
    <div
      aria-disabled="true"
      style={{
        pointerEvents: 'none',
        opacity: 0.55,
        padding: '9px 11px',
        background: C.panel,
        border: '1px dashed ' + C.border,
        borderRadius: T.r.field,
      }}
    >
      {editor}
    </div>
  ) : (
    editor
  );

  // The provenance line: which ancestor this is coming from, and what it resolves to. Replaces
  // the sentence the dashed box used to carry, now that the box holds the editor instead.
  const source = inheriting ? (
    <div style={{ fontSize: '11px', color: C.dim, marginTop: '6px', lineHeight: 1.4 }}>
      {eff.from
        ? 'Inheriting from ' + eff.from + ' — ' + disp(eff.val)
        : 'Nothing to inherit from a parent yet'}
    </div>
  ) : null;

  const body = (
    <>
      {shownEditor}
      {source}
    </>
  );

  return (
    <div style={{ marginBottom: '14px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          marginBottom: '7px',
        }}
      >
        <label
          style={{
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '.04em',
            textTransform: 'uppercase',
            color: C.dim,
          }}
        >
          {label}
        </label>
        <div style={{ display: 'flex', gap: '4px', flex: '0 0 auto' }}>
          {seg('Inherit', inheriting, () => {
            // Backing out of an editor she opened but never wrote to: just close it. There is
            // nothing stored to remove, and sending a clear would be a write for a field she
            // never actually changed.
            if (opened) {
              setOpened(false);
              return;
            }
            apply(clearVal(graph, id, vk));
          })}
          {/*
            PRE-LOAD the inherited value rather than writing empty (June, 2026-07-18). The old
            code wrote `(… ) || ''`, and for a multi_select `''` coerces to `[]`, which Anytype
            stores by DELETING the property — so the write failed its own read-back and she got
            "Could not save access — it is NOT saved." Starting from the inherited value gives
            the first write something real to persist, and gives her the shared default to edit
            down from, which is what spec §4 describes ("inherit-the-shared-default,
            override-when-it-differs").

            No-op when already Custom: re-clicking must not overwrite what she has set.
          */}
          {seg('Custom', !inheriting, () => {
            if (!inheriting) return;
            // Copy the inherited value down so the first write has something real to persist,
            // and so she edits DOWN from the shared default (spec §4's
            // "inherit-the-shared-default, override-when-it-differs").
            //
            // With NOTHING to inherit there is nothing to copy, and writing an empty value is
            // the bug: for a multi_select it deletes the property and fails its own read-back.
            // So open the editor and write nothing — her first selection is the first write.
            const seed = eff.val ?? own;
            const emptySeed =
              seed == null || seed === '' || (Array.isArray(seed) && seed.length === 0);
            if (emptySeed) setOpened(true);
            else apply(setVal(graph, id, vk, seed));
          })}
        </div>
      </div>
      {body}
      {hint ? (
        <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.4, marginTop: '6px' }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}
