import type { FocusForm, ModelNode } from '../../model/index.ts';
import type { FocusCtx } from './types.ts';

/** v4:876 — the three levels the picker offers. A GOAL is a group header, never selectable. */
const PICKABLE = new Set(['PROJECT', 'SUBPROJECT', 'WORKSTREAM']);

/**
 * v4:876 `pausable(n)` — the PAUSED-list filter, and the one piece of real domain logic in
 * this picker:
 *
 *   !['Backburner','Done'].includes(n.vals.engagement) && !['Parked','Inactive'].includes(n.vals.status)
 *
 * Spec §17: "Paused is filtered to 'pausable' projects in the picker: only those that would
 * normally populate the plan (not Backburner/Done engagement, not Parked/Inactive status)."
 * The reason is that pausing something already excluded from the plan is a no-op the user
 * cannot see the effect of — the list would offer choices that do nothing.
 *
 * The FOREGROUND list is deliberately NOT filtered: foregrounding is exactly how a
 * Backburner or Parked project gets pulled back into the plan for a period (`AI_LAYER_SPEC.md`
 * §2, `foreground_projects`: "overriding their enduring `engagement`").
 */
function pausable(n: ModelNode): boolean {
  const eng = n.vals.engagement;
  const status = n.vals.status;
  return (
    !(typeof eng === 'string' && ['Backburner', 'Done'].includes(eng)) &&
    !(typeof status === 'string' && ['Parked', 'Inactive'].includes(status))
  );
}

export interface FocusProjectPickerProps {
  ctx: FocusCtx;
  form: FocusForm;
  setF: <K extends keyof FocusForm>(k: K, v: FocusForm[K]) => void;
  /** v4's `key` argument (874) — which of the two project lists this picker edits. */
  field: 'front' | 'paused';
}

/**
 * v4 `focusFrontPicker(form,setF,key)` (874) — the shared Foreground / Paused project picker.
 *
 * Selected chips on top (tap to deselect), a search box, then a scrolling list grouped by
 * GOAL with a checkbox per project.
 *
 * ⚠ Selection is by project TITLE, not id — v4 stores `c.title` into the list and matches
 * with `sel.includes(c.title)`, and `fixtures/periods.ts` records the same. Two projects with
 * the same title under different goals are therefore indistinguishable here. Ported as-is;
 * `AI_LAYER_SPEC.md` §2 specifies the real fields as objects-relations that "drive real
 * selection by id", so the id form is Track B's, not a fix to make in the mockup port.
 *
 * ⚠ The group list walks `graph.roots[].children` only — one level below each goal. A
 * SUBPROJECT or WORKSTREAM nested deeper than that is not offered. That is v4's traversal
 * (`this.data.map(g => g.children.filter(…))`, 878), unchanged.
 */
export function FocusProjectPicker({ ctx, form, setF, field }: FocusProjectPickerProps) {
  const { T, graph, ui, up } = ctx;
  const C = T.c;

  const sel = form[field];
  const toggle = (t: string) =>
    setF(field, sel.includes(t) ? sel.filter((x) => x !== t) : [...sel, t]);

  const q = (field === 'front' ? ui.focusPickFront : ui.focusPickPaused).toLowerCase();
  const setQ = (v: string) =>
    up(field === 'front' ? { focusPickFront: v } : { focusPickPaused: v });

  // v4:878 — the search matches the project title OR its goal's title, so typing a goal name
  // narrows to everything under it.
  const groups = graph.roots
    .map((g) => ({
      g,
      kids: g.children.filter(
        (c) =>
          PICKABLE.has(c.level) &&
          (field !== 'paused' || pausable(c)) &&
          (!q || c.title.toLowerCase().includes(q) || g.title.toLowerCase().includes(q)),
      ),
    }))
    .filter((x) => x.kids.length);

  return (
    <div>
      {sel.length ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
          {sel.map((f, i) => (
            <button
              key={i}
              onClick={() => toggle(f)}
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
              {f}
              <span style={{ color: C.rose, fontSize: '13px', lineHeight: 1 }}>×</span>
            </button>
          ))}
        </div>
      ) : null}

      <input
        value={field === 'front' ? ui.focusPickFront : ui.focusPickPaused}
        placeholder={field === 'paused' ? 'Search projects to pause…' : 'Search projects…'}
        onChange={(e) => setQ(e.target.value)}
        style={{
          width: '100%',
          background: C.bg,
          border: '1px solid ' + C.roseBorder,
          borderRadius: T.r.field,
          color: C.text,
          fontSize: '13px',
          fontFamily: 'inherit',
          padding: '8px 11px',
          outline: 'none',
          boxSizing: 'border-box',
          marginBottom: '8px',
        }}
      />

      <div
        style={{
          maxHeight: '188px',
          overflowY: 'auto',
          border: '1px solid ' + C.roseBorder,
          borderRadius: T.r.field,
          background: C.surface,
        }}
      >
        {groups.length ? (
          groups.map((x, gi) => (
            <div key={gi}>
              <div
                style={{
                  fontSize: '10px',
                  color: C.dimmer,
                  textTransform: 'uppercase',
                  letterSpacing: '.06em',
                  padding: '8px 11px 4px',
                  background: C.bg,
                }}
              >
                {x.g.title}
              </div>
              {x.kids.map((c, i) => {
                const on = sel.includes(c.title);
                return (
                  <button
                    key={i}
                    onClick={() => toggle(c.title)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '9px',
                      width: '100%',
                      textAlign: 'left',
                      background: on ? C.roseDim : 'none',
                      border: 'none',
                      borderBottom: '1px solid ' + C.roseBorder,
                      color: on ? C.text : C.dim,
                      fontSize: '12.5px',
                      fontFamily: 'inherit',
                      padding: '8px 11px',
                      cursor: 'pointer',
                    }}
                  >
                    {/* v4's own checkbox, hardcoded at 4px radius — it does NOT use the
                        `taskCheck` atom and does NOT fork on theme. Kept verbatim. */}
                    <span
                      style={{
                        width: '15px',
                        height: '15px',
                        flex: '0 0 auto',
                        borderRadius: '4px',
                        border: '1.5px solid ' + (on ? C.rose : C.dimmer),
                        background: on ? C.rose : 'none',
                        position: 'relative',
                      }}
                    >
                      {on ? (
                        <span
                          style={{
                            position: 'absolute',
                            inset: 0,
                            fontSize: '10px',
                            lineHeight: '13px',
                            textAlign: 'center',
                            color: C.bg,
                          }}
                        >
                          ✓
                        </span>
                      ) : null}
                    </span>
                    {c.title}
                  </button>
                );
              })}
            </div>
          ))
        ) : (
          <div
            style={{ fontSize: '12px', color: C.dimmer, padding: '14px', textAlign: 'center' }}
          >
            No matches
          </div>
        )}
      </div>
    </div>
  );
}
