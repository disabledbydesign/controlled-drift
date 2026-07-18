import { formFromDraft, saveFocus } from '../../model/index.ts';
import type { FocusForm } from '../../model/index.ts';
import { FEditor } from './FEditor.tsx';
import { FField, FSub, inputStyle } from './fields.tsx';

import type { FocusCtx } from './types.ts';

export interface FocusEditorProps {
  ctx: FocusCtx;
  /** v4:813 — `st.focusView==='author' ? 'author' : 'edit'`. */
  view: 'edit' | 'author';
}

/**
 * v4 `focusEditor(view)` (887) — the two screens behind the `__focus__` detail route.
 *
 * ── SCREEN 1: author, before structuring (v4:890) ────────────────────────────
 * Reached only when `view==='author'` AND there is no form yet. One textarea: "What focus
 * period do you want to set up? Say it in your own words." — `AI_LAYER_SPEC.md` §2, "How June
 * authors it": she says it, the system structures it and reflects it back, she confirms or
 * edits. **She never fills a form.** "Structure this →" builds the form (see
 * `model/periods.ts` `formFromDraft`, and the stand-in warning on it) and falls through to
 * screen 2.
 *
 * ── SCREEN 2: the form (v4:896) ──────────────────────────────────────────────
 * Same markup for `edit` and for the author flow's reflect-back; only the heading, the
 * subheading and the save-button label differ. Sections in v4's order: Name · Period ·
 * Intent · When you're free · Plan overrides (shape, workday, days off) · Projects
 * (foreground, paused).
 *
 * ⚠ BACK DISCARDS THE DRAFT, SILENTLY — PORTED AS-IS, NOT FIXED.
 * `docs/ux_consistency_review_2026-07-17.md` finding #4: everywhere else in this surface an
 * edit commits as you type, but here `‹ Back` clears `focusReflect` and nothing is written —
 * no warning, no confirm, no autosave. The plan's Task 9 is explicit that this is June's call
 * post-port, so the inconsistency is preserved exactly and flagged here rather than repaired.
 *
 * ⚠ `daysOffDisp` (v4:895) is computed in v4 and then never rendered — its only possible
 * consumer was `fRow`, which has no call site (see `fields.tsx`). NOT PORTED.
 */
export function FocusEditor({ ctx, view }: FocusEditorProps) {
  const { T, ui, up, periods, applyPeriods, closeEditor } = ctx;
  const C = T.c;
  const form = ui.focusReflect;

  const back = (
    <button
      onClick={closeEditor}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        background: 'none',
        border: 'none',
        color: C.rose,
        fontSize: '12px',
        fontFamily: 'inherit',
        padding: 0,
        cursor: 'pointer',
        marginBottom: '12px',
      }}
    >
      ‹ Back
    </button>
  );

  const page = {
    padding: '14px',
    background: T.pane,
    backdropFilter: T.paneBlur,
    WebkitBackdropFilter: T.paneBlur,
    minHeight: '100%',
  };

  // v4:889 — the author screen's own input style. Identical to `fEditor`'s except that it
  // carries no `colorScheme` (there is no date/time control on this screen).
  const inp = inputStyle(T);

  if (view === 'author' && !form) {
    const structure = () => {
      const d = ui.focusDraft.trim();
      if (!d) return;
      up({ focusReflect: formFromDraft(d) });
    };
    return (
      <div style={page}>
        {back}
        <div style={{ fontSize: '13px', color: C.rose, marginBottom: '10px', lineHeight: 1.4 }}>
          What focus period do you want to set up? Say it in your own words.
        </div>
        <textarea
          value={ui.focusDraft}
          placeholder="e.g. jobs first this week, caregiving starts Saturday, Sunday off, working late Monday…"
          onChange={(e) => up({ focusDraft: e.target.value })}
          style={{ ...inp, minHeight: '88px', resize: 'none', lineHeight: 1.45 }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '9px' }}>
          <button
            onClick={structure}
            style={{
              background: C.goldDim,
              border: '1px solid ' + C.gold,
              borderRadius: T.r.field,
              color: C.gold,
              fontSize: '13px',
              fontFamily: 'inherit',
              padding: '8px 16px',
              cursor: 'pointer',
            }}
          >
            Structure this →
          </button>
        </div>
        <div style={{ fontSize: '11px', color: C.roseDim, marginTop: '10px', lineHeight: 1.4 }}>
          It reads back what it heard for you to check — it won’t reword your intent.
        </div>
      </div>
    );
  }

  // v4:896 falls straight through to the form with `form` still possibly null when
  // `view==='edit'` — every edit route sets `focusReflect`, so it cannot happen, but the type
  // has to be narrowed. Renders nothing rather than a half-form.
  if (!form) return null;

  const setF = <K extends keyof FocusForm>(k: K, v: FocusForm[K]) =>
    up({ focusReflect: { ...form, [k]: v } });

  const onSave = () => {
    applyPeriods(saveFocus(periods, view, ui.focusEditId, form));
    closeEditor();
  };

  return (
    <div style={page}>
      {back}
      <div style={{ fontSize: '13px', fontWeight: 700, color: C.rose, marginBottom: '4px' }}>
        {view === 'edit' ? 'Edit focus period' : 'Here’s what I heard'}
      </div>
      <div style={{ fontSize: '11.5px', color: C.roseDim, marginBottom: '10px', lineHeight: 1.4 }}>
        {view === 'edit' ? 'All fields are editable below.' : 'Check each field, then save.'}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '13px' }}>
        <FField T={T} label="Name">
          <FEditor ctx={ctx} which="name" form={form} setF={setF} />
        </FField>

        <FSub T={T}>Period</FSub>
        <FEditor ctx={ctx} which="dates" form={form} setF={setF} />

        <FField T={T} label="Intent — your words">
          <FEditor ctx={ctx} which="intent" form={form} setF={setF} />
        </FField>

        <FSub T={T}>When you’re free</FSub>
        <FEditor ctx={ctx} which="availability" form={form} setF={setF} />

        <FSub T={T}>Plan overrides</FSub>
        <FField T={T} label="Plan shape">
          <FEditor ctx={ctx} which="output" form={form} setF={setF} />
        </FField>
        <FEditor ctx={ctx} which="workday" form={form} setF={setF} />
        <FField T={T} label="Days off">
          <FEditor ctx={ctx} which="daysOff" form={form} setF={setF} />
        </FField>

        <FSub T={T}>Projects</FSub>
        <FField T={T} label="Foreground — worked first">
          <FEditor ctx={ctx} which="front" form={form} setF={setF} />
        </FField>
        <FField T={T} label="Paused — off this period">
          <FEditor ctx={ctx} which="paused" form={form} setF={setF} />
        </FField>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '14px' }}>
        <button
          onClick={onSave}
          style={{
            background: C.gold,
            border: '1px solid ' + C.gold,
            borderRadius: T.r.field,
            color: C.bg,
            fontSize: '13px',
            fontWeight: 700,
            fontFamily: 'inherit',
            padding: '9px 18px',
            cursor: 'pointer',
          }}
        >
          {view === 'edit' ? 'Save changes' : 'Looks right — save'}
        </button>
      </div>
    </div>
  );
}
