import { useEffect, useState } from 'react';
import { reflectFields } from '../../api/focus.ts';
import type { ReflectItem, ReflectPayload } from '../../api/focus.ts';
import { fieldsFromForm } from '../../model/index.ts';
import type { FocusForm } from '../../model/index.ts';
import { FEditor } from './FEditor.tsx';
import type { FEditorKey } from './FEditor.tsx';
import type { FocusCtx } from './types.ts';

/**
 * THE VERIFICATION SURFACE — what the model made of her words, itemised, each line fixable.
 *
 * ── this is a wire-in, not a new design ─────────────────────────────────────
 * `POST /api/focus/reflect` was built, specified and unreachable: `reflectFields` in
 * `api/focus.ts` had NO CALLER anywhere in the app. Its docstring
 * (`scripts/focus_period_adapter.py:223`) already describes this screen exactly — a compressed
 * `summary`, an itemised `items` list she can verify and fix one field at a time, and
 * `blocking` so the UI holds the save until a required field is filled in. Every item carries an
 * `edit` hint naming which deterministic editor to open, so a fix needs no re-speaking and no
 * second model call. The shape below is transcribed from that payload, not invented.
 *
 * June, 2026-07-19: "i want to see what the LLM does with my words, and edit as needed."
 *
 * ── WHY NOTHING HERE IS COMPOSED CLIENT-SIDE ────────────────────────────────
 * The screen this replaces was headed "Here's what I heard" and read back two HARDCODED dates
 * with her sentence cut at the first comma — no model had ever run (`formFromDraft`, deleted in
 * 87185ba). Every value on this screen is a `display` string the SERVER produced. There is no
 * local fallback and none may be added: when the read-back cannot be loaded, this says so. A
 * summary the client made up under a heading claiming comprehension is the exact defect the
 * deletion removed, and it would come back the moment someone adds a "sensible default" here.
 *
 * The template lives in Python for the same reason — one source for the wording she checks.
 *
 * ── `blocking` IS NOT AN ERROR ──────────────────────────────────────────────
 * A missing end date means she has not filled it in yet. It does not travel the error channel,
 * is not logged as breakage, and is not phrased as something having gone wrong. See the
 * three-outcome header in `api/focus.ts`: `needs` is its own outcome precisely so this case
 * cannot be collapsed into a failure.
 *
 * ── SPOKEN REVISION IS RETIRED, NOT DEFERRED ────────────────────────────────
 * There is deliberately no "say it again" control. June, 2026-07-19: "i dont know if we need to
 * revise by voice anymore. Now that i can just edit in text." `/api/focus/edit` and
 * `startFocusEdit` are therefore unwired; do not add a button for them.
 */

/**
 * Which deterministic editor an item opens.
 *
 * ⚠ KEYED BY `item.key`, NOT BY `item.edit`. The hint names the KIND of control ('daterange',
 * 'projects', 'select', 'text', 'dates'), and two different items share a kind: `dates` and
 * `availability` are both 'daterange', `foreground` and `paused` are both 'projects'. The kind
 * alone therefore cannot say WHICH field to open, so the key does — and the hint is what says
 * the control must not be a text box. Both are used; neither is sufficient alone.
 *
 * `reactivate_tasks` is absent on purpose: it is not a period field but an INSTRUCTION carried
 * alongside one, and it is rendered as removable names below rather than through an editor.
 */
const EDITOR_FOR: Readonly<Record<string, FEditorKey>> = {
  foreground: 'front',
  paused: 'paused',
  dates: 'dates',
  availability: 'availability',
  days_off: 'daysOff',
  output_format: 'output',
  intent: 'intent',
  workday_start: 'workday',
  workday_end: 'workday',
};

export interface FocusReflectProps {
  ctx: FocusCtx;
  form: FocusForm;
  setF: <K extends keyof FocusForm>(k: K, v: FocusForm[K]) => void;
  /** Confirm and write. Only ever called when `blocking` is empty. */
  onSave: () => void;
}

export function FocusReflect({ ctx, form, setF, onSave }: FocusReflectProps) {
  const { T } = ctx;
  const C = T.c;
  const [payload, setPayload] = useState<ReflectPayload | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [openKey, setOpenKey] = useState<string | null>(null);

  // Re-asked whenever the fields change, so a per-field fix is reflected back by the SERVER
  // rather than patched locally — the endpoint is synchronous and runs no model, which is what
  // makes that affordable. `JSON.stringify` is the dependency because `fieldsFromForm` builds a
  // fresh object every render and an object identity would re-fire this forever.
  const wire = JSON.stringify(fieldsFromForm(form));
  useEffect(() => {
    let dropped = false;
    void (async () => {
      const res = await reflectFields(JSON.parse(wire) as Record<string, unknown>);
      if (dropped) return;
      if (!res.ok) {
        // NO client-composed fallback. See the header.
        setUnreadable(true);
        return;
      }
      setUnreadable(false);
      setPayload(res.data);
    })();
    return () => {
      dropped = true;
    };
  }, [wire]);

  const page = { padding: '14px', background: T.pane, minHeight: '100%' };

  /**
   * The screen's own label. Safe to show before the payload lands because it is not a claim
   * about content — unlike the summary and the items, which are the server's and appear only
   * once the server has sent them.
   */
  const overline = (
    <div style={{ fontSize: '11.5px', color: C.roseDim, marginBottom: '3px' }}>
      What it made of what you wrote
    </div>
  );

  if (unreadable && !payload) {
    return (
      <div style={page}>
        {overline}
        <div style={{ fontSize: '12.5px', color: C.rose, lineHeight: 1.5 }}>
          The read-back could not be loaded, so there is nothing to check here yet. Your words
          were structured — nothing has been saved. Try again in a moment.
        </div>
      </div>
    );
  }
  if (!payload) {
    return (
      <div style={page}>
        {overline}
        <div style={{ fontSize: '12.5px', color: C.roseDim }}>Reading it back…</div>
      </div>
    );
  }

  const blocking = payload.blocking ?? [];
  const held = blocking.length > 0;

  const reactivateNames = form.reactivate ?? [];

  /** One line: what the server understood, and a control to change it. */
  const row = (item: ReflectItem) => {
    const which = EDITOR_FOR[item.key];
    const open = openKey === item.key;
    return (
      <div key={item.key} style={{ borderTop: '1px solid ' + C.roseBorder, padding: '9px 0' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '9px' }}>
          <span
            style={{
              fontSize: '10px',
              color: C.roseDim,
              textTransform: 'uppercase',
              letterSpacing: '.06em',
              flex: '0 0 34%',
            }}
          >
            {item.label}
          </span>
          <span style={{ flex: 1, minWidth: 0, fontSize: '12.5px', color: C.text, lineHeight: 1.4 }}>
            {item.display}
          </span>
          {which ? (
            <button
              onClick={() => setOpenKey(open ? null : item.key)}
              aria-label={'change ' + item.label}
              style={{
                background: 'none',
                border: '1px solid ' + C.roseBorder,
                borderRadius: T.r.ctl,
                color: C.roseDim,
                fontSize: '11px',
                fontFamily: 'inherit',
                padding: '3px 10px',
                cursor: 'pointer',
                flex: '0 0 auto',
              }}
            >
              {open ? 'Done' : 'Change'}
            </button>
          ) : null}
        </div>

        {/* The as-needed tasks the server will turn back on. Shown by NAME so a wrong match is
            visible, and removable so she can drop one before anything is written — until now
            the instruction round-tripped and the write honoured it (4451927) with nothing on
            screen saying which task had been picked. */}
        {item.key === 'reactivate_tasks' ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '7px' }}>
            {reactivateNames.map((n) => (
              <span
                key={n}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px',
                  color: C.text,
                  background: C.roseBg,
                  border: '1px solid ' + C.roseBorder,
                  borderRadius: T.r.card,
                  padding: '3px 6px 3px 10px',
                }}
              >
                {n}
                <button
                  onClick={() => setF('reactivate', reactivateNames.filter((x) => x !== n))}
                  aria-label={'do not reopen ' + n}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: C.roseDim,
                    fontSize: '13px',
                    fontFamily: 'inherit',
                    lineHeight: 1,
                    padding: '0 2px',
                    cursor: 'pointer',
                  }}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {open && which ? (
          <div style={{ marginTop: '9px' }}>
            <FEditor ctx={ctx} which={which} form={form} setF={setF} />
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div style={page}>
      {overline}
      <div
        style={{
          fontSize: '14px',
          fontWeight: 700,
          color: C.rose,
          marginBottom: '4px',
          lineHeight: 1.3,
        }}
      >
        {payload.summary}
      </div>
      <div style={{ fontSize: '11.5px', color: C.roseDim, marginBottom: '8px', lineHeight: 1.4 }}>
        Change anything that is not right, then save.
      </div>

      <div>{payload.items.map(row)}</div>

      {/* Not an error state. Names the field she has not filled in yet, in that register. */}
      {held ? (
        <div
          data-testid="focus-reflect-blocking"
          style={{
            fontSize: '12px',
            color: C.gold,
            background: C.goldDim,
            border: '1px solid ' + C.gold,
            borderRadius: T.r.field,
            padding: '9px 11px',
            marginTop: '12px',
            lineHeight: 1.45,
          }}
        >
          {'A focus period still needs ' + blocking.join(' and ') + '. Fill that in and it will save.'}
        </div>
      ) : null}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '14px' }}>
        <button
          onClick={() => {
            // ⚠ UNREACHABLE WHILE `disabled` IS SET, AND KEPT ANYWAY. React fires no handler on
            // a disabled button, so no test can cover this line — deleting it leaves the suite
            // green, which mutation-testing confirmed. It stays so that a later change dropping
            // `disabled` (for a styling reason, say) cannot quietly begin saving a period that
            // is still missing a required field. The `disabled` state is what the tests assert.
            if (held) return;
            onSave();
          }}
          disabled={held}
          style={{
            background: held ? C.surface : C.gold,
            border: '1px solid ' + (held ? C.roseBorder : C.gold),
            borderRadius: T.r.field,
            color: held ? C.dimmer : C.bg,
            fontSize: '13px',
            fontWeight: 700,
            fontFamily: 'inherit',
            padding: '9px 18px',
            cursor: held ? 'default' : 'pointer',
          }}
        >
          Looks right — save
        </button>
      </div>
    </div>
  );
}
