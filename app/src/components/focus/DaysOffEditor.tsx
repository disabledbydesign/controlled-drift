import type { FocusForm } from '../../model/index.ts';
import { fmtDate } from './fmtDate.ts';
import type { FocusCtx } from './types.ts';

export interface DaysOffEditorProps {
  ctx: FocusCtx;
  form: FocusForm;
  setF: <K extends keyof FocusForm>(k: K, v: FocusForm[K]) => void;
}

/**
 * v4 `daysOffEditor(form,setF)` (866).
 *
 * A chip per date (tap to remove), a date input + Add button, and a one-line explanation.
 * The empty state says "Weekends (system default)" — spec §17: `days_off` is a per-period
 * OVERRIDE of the system's weekly days-off, not a new global setting.
 *
 * Add is guarded by `v && arr.indexOf(v)<0` — an empty date or a duplicate is a no-op — and
 * the list is `.sort()`ed, so the chips stay in date order however they were entered.
 * `focusNewOff` is cleared only on a successful add, so a rejected duplicate leaves the date
 * in the input.
 *
 * ⚠ NOT PRESENT here: `days_on` (v4 carries `form.daysOn` through save but renders no control
 * for it). Backend spec §17 calls `days_on` "stubbed in the UI but not yet a committed field
 * — leave OPEN", while `AI_LAYER_SPEC.md` §2's recovery note records it as live on the type
 * and populated on 4 of 7 objects. Not reconciled, and not this task's call: the value passes
 * through the form unchanged either way.
 *
 * ⚠ v4's `Array.isArray(form.daysOff) ? … : (form.daysOff||'').split(',')` string fallback is
 * dropped — `FocusForm.daysOff` is `string[]` and both form producers supply an array, so the
 * string arm is unreachable. See `model/periods.ts`.
 */
export function DaysOffEditor({ ctx, form, setF }: DaysOffEditorProps) {
  const { T, ui, up } = ctx;
  const C = T.c;
  const arr = form.daysOff;

  const add = () => {
    const v = ui.focusNewOff;
    if (v && arr.indexOf(v) < 0) {
      setF('daysOff', [...arr, v].sort());
      up({ focusNewOff: '' });
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
        {arr.length ? (
          arr.map((d, i) => (
            <button
              key={i}
              onClick={() => setF('daysOff', arr.filter((_, j) => j !== i))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                color: C.text,
                background: C.roseDim,
                border: '1px solid ' + C.roseBorder,
                borderRadius: T.r.card,
                padding: '3px 7px 3px 10px',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              {fmtDate(d)}
              <span style={{ color: C.rose, fontSize: '13px' }}>×</span>
            </button>
          ))
        ) : (
          <span style={{ fontSize: '11px', color: C.roseDim }}>Weekends (system default)</span>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="date"
          value={ui.focusNewOff}
          onChange={(e) => up({ focusNewOff: e.target.value })}
          style={{
            flex: 1,
            background: C.surface,
            border: '1px solid ' + C.roseBorder,
            borderRadius: T.r.field,
            color: C.text,
            fontSize: '13px',
            fontFamily: 'inherit',
            padding: '8px 10px',
            colorScheme: 'dark',
            boxSizing: 'border-box',
          }}
        />
        <button
          onClick={add}
          style={{
            background: C.goldDim,
            border: '1px solid ' + C.gold,
            borderRadius: T.r.field,
            color: C.gold,
            fontSize: '12px',
            fontFamily: 'inherit',
            padding: '0 14px',
            cursor: 'pointer',
          }}
        >
          Add
        </button>
      </div>

      <div style={{ fontSize: '10.5px', color: C.dimmer, marginTop: '7px', lineHeight: 1.4 }}>
        Overrides the system’s weekly days-off just for this period.
      </div>
    </div>
  );
}
