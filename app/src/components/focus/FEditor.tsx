import type { FocusForm } from '../../model/index.ts';
import { DaysOffEditor } from './DaysOffEditor.tsx';
import { FocusProjectPicker } from './FocusProjectPicker.tsx';
import { FSubLabel, FTwo, inputStyle } from './fields.tsx';
import type { FocusCtx } from './types.ts';

/** v4:858 — the three `output_format` values, hardcoded in the mockup. */
const OUTPUT_OPTIONS = ['Auto', 'Clock schedule', 'Priority list'] as const;

/** The `key` argument of v4's `fEditor` (850) — one per editable group, not one per field. */
export type FEditorKey =
  | 'name'
  | 'dates'
  | 'intent'
  | 'availability'
  | 'output'
  | 'workday'
  | 'daysOff'
  | 'front'
  | 'paused';

export interface FEditorProps {
  ctx: FocusCtx;
  which: FEditorKey;
  form: FocusForm;
  setF: <K extends keyof FocusForm>(k: K, v: FocusForm[K]) => void;
}

/**
 * v4 `fEditor(key,form,setF)` (850) — the control for one field group.
 *
 * Nine branches, dispatched on `key`. v4 ends with `return null` for an unrecognised key;
 * `FEditorKey` is a closed union here, so the fall-through is a compile error instead — the
 * same "make the wrong thing impossible" move as the derived index in `useAppState`.
 *
 * ── SPEC §17 COVERAGE ────────────────────────────────────────────────────────
 * All eleven §17 fields render:
 *   Name · Period start/end · Intent · Availability window (start + end + note) ·
 *   Plan-shape override · Workday start + end · Days off · Foreground · Paused.
 *
 * ⚠ `Workday start` HAS NO BACKING PROPERTY. `docs/review_reorganize_backend_spec.md` §17
 * flags `workday_start` as NEW, and `AI_LAYER_SPEC.md` §2's recovery note records that the
 * live Anytype Focus Period type carries only `Workday end` and that the scheduler's
 * day-bounds logic is still end-only. The control below is real and its value round-trips
 * through the form and `saveFocus`, but there is nothing on the object to persist it to yet —
 * Track B has to add the property before this field means anything.
 */
export function FEditor({ ctx, which, form, setF }: FEditorProps) {
  const { T } = ctx;
  const C = T.c;
  const inp = inputStyle(T, 'dark');

  const dateI = (k: 'start' | 'end' | 'availStart' | 'availEnd') => (
    <input type="date" value={form[k]} onChange={(e) => setF(k, e.target.value)} style={inp} />
  );
  const timeI = (k: 'workdayStart' | 'workdayEnd') => (
    <input type="time" value={form[k]} onChange={(e) => setF(k, e.target.value)} style={inp} />
  );

  switch (which) {
    case 'name':
      return (
        <input value={form.name} onChange={(e) => setF('name', e.target.value)} style={inp} />
      );

    case 'dates':
      return (
        <FTwo
          a={
            <FSubLabel T={T} label="Start">
              {dateI('start')}
            </FSubLabel>
          }
          b={
            <FSubLabel T={T} label="End">
              {dateI('end')}
            </FSubLabel>
          }
        />
      );

    // Intent is June's own words. Spec §14/§17 and AI_LAYER_SPEC.md §2: "Read by the LLM as
    // framing, never reworded by the generator." A plain textarea bound straight to the value —
    // no normalisation, no trim, no transform, and none may be added.
    case 'intent':
      return (
        <textarea
          value={form.intent}
          onChange={(e) => setF('intent', e.target.value)}
          style={{ ...inp, minHeight: '80px', resize: 'none', lineHeight: 1.45 }}
        />
      );

    // Spec §17: a NARROWER free window inside the period; empty = the whole period. The note
    // is the situated meaning of that window and is what the planner actually reads —
    // AI_LAYER_SPEC.md §2 calls it "the anti-flattening path", never compressed into the dates.
    case 'availability':
      return (
        <div>
          <FTwo
            a={
              <FSubLabel T={T} label="Free from">
                {dateI('availStart')}
              </FSubLabel>
            }
            b={
              <FSubLabel T={T} label="Free to">
                {dateI('availEnd')}
              </FSubLabel>
            }
          />
          <div style={{ fontSize: '11px', color: C.roseDim, margin: '7px 0' }}>
            A narrower window when you’re only partly free (e.g. caregiving). Leave blank to use
            the whole period.
          </div>
          <textarea
            value={form.note}
            placeholder="what this window means"
            onChange={(e) => setF('note', e.target.value)}
            style={{ ...inp, minHeight: '50px', resize: 'none', lineHeight: 1.45 }}
          />
        </div>
      );

    // Spec §17 plan-shape override → §14's `shape`. `Auto` lets the generator decide.
    case 'output':
      return (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {OUTPUT_OPTIONS.map((o) => {
            const on = (form.output || 'Auto') === o;
            return (
              <button
                key={o}
                onClick={() => setF('output', o)}
                style={{
                  background: on ? C.roseDim : C.surface,
                  border: '1px solid ' + (on ? C.rose : C.roseBorder),
                  borderRadius: T.r.field,
                  color: on ? C.text : C.dim,
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  padding: '6px 11px',
                  cursor: 'pointer',
                }}
              >
                {o}
              </button>
            );
          })}
        </div>
      );

    // ⚠ "Starts" has no backing property on the live type — see the header note.
    case 'workday':
      return (
        <FTwo
          a={
            <FSubLabel T={T} label="Starts">
              {timeI('workdayStart')}
            </FSubLabel>
          }
          b={
            <FSubLabel T={T} label="Ends">
              {timeI('workdayEnd')}
            </FSubLabel>
          }
        />
      );

    case 'daysOff':
      return <DaysOffEditor ctx={ctx} form={form} setF={setF} />;

    case 'front':
      return <FocusProjectPicker ctx={ctx} form={form} setF={setF} field="front" />;

    case 'paused':
      return <FocusProjectPicker ctx={ctx} form={form} setF={setF} field="paused" />;
  }
}
