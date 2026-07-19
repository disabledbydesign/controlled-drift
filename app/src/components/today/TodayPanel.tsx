import { alpha } from '@tokens';
import { bevel } from '../atoms/index.ts';
import { Band } from './Band.tsx';
import { FocusSlot } from './FocusSlot.tsx';
import { PriorityList } from './PriorityList.tsx';
import type { TodayCtx } from './types.ts';

export interface TodayPanelProps {
  ctx: TodayCtx;
}

/**
 * v4 `todayPanel()` (~977) — the whole Today tab, top to bottom.
 *
 * Order, all v4's: focus slot · woven frame · shape switch · the plan itself · the pointer to
 * self-directed work on the Map · the regeneration action row · the free-text ask box.
 *
 * ── spec §14 deltas ─────────────────────────────────────────────────────────
 * · **Woven frame always expanded** — rendered unconditionally. ⚠ Already true in v4: the
 *   state bag declares `wovenOpen:false` (v4:79) but `todayPanel` never reads it. Verified by
 *   grep — `wovenOpen` has exactly one occurrence in the whole mockup, its declaration.
 * · **No plan-age line.** ⚠ Also already true in v4: `plan.generated` ("Built this morning at
 *   9:02.") is in the fixture and read by nothing. Verified by grep — zero occurrences of
 *   `.generated` outside the fixture. It stays in the payload for staleness logic.
 * · **"Life admin & household" preset** is present in the action row — v4 already had it.
 *
 * ── the shape switch ────────────────────────────────────────────────────────
 * `View: Schedule · Priority` writes `todayShape`, which picks between the clock bands and
 * the flat ranked list. Per spec §17 a focus period can force either shape; that override is
 * the Focus editor's (`components/focus`) and does not appear here.
 *
 * ── the action row (WIRED 2026-07-18) ───────────────────────────────────────
 * Four of these buttons said a plan had changed when nothing had happened: "Regenerating plan…",
 * "Trimmed to one small win", "Showing quick wins", "Let's break it down" were `flash()` and
 * nothing else. They now call the endpoints that already implemented them —
 * `/api/refresh` for a fresh plan, `/api/negotiate {preset_id}` for the presets.
 *
 * ⚠ THE PRESET IDS ARE QUOTED, NEVER COMPOSED. They come from `plan_store._DEFAULT_ACTIONS`
 * (`low-energy`, `quick-wins`, `stuck`, plus a UI-only `add`) merged with her own
 * `~/.controlled-drift/actions.json` — which was read live and holds exactly the first three.
 * An id the server does not hold answers 400 (`server.py:927`).
 *
 * ⚠ "Life admin & household" IS STILL UNWIRED AND STILL CLAIMS SUCCESS. There is no preset id
 * for it anywhere — not in `_DEFAULT_ACTIONS`, not in her live `actions.json`, not in v4. The
 * button is a label with no backend, and picking an id or writing its instruction text would be
 * inventing the thing this thread is removing. It needs either a preset June authors or the
 * honest-refusal path (plan Task 6). Reported, deliberately not guessed.
 *
 * ── what she sees while it runs ─────────────────────────────────────────────
 * Generation takes tens of seconds. The button that started it reads `Regenerating…` with a
 * pulsing dot; every other generation button is held at v4's not-tappable-right-now treatment
 * until it settles. Neither `signals.ts` nor the colour gallery (4a/4c/5a/5c) has an
 * in-progress state — this is DERIVED, from the dot the hardware action button already carries
 * and the `ringpulse` keyframe already in `index.html`. See `act()`.
 *
 * v4's hex-alpha suffixes are transcribed as `alpha()` at the same values:
 * 2b=.169 · 0f=.059 · 80=.502 · 33=.2 · 22=.133 · 70=.439 · 2e=.18 · 66=.4 · 0d=.051.
 */
export function TodayPanel({ ctx }: TodayPanelProps) {
  const C = ctx.T.c;
  const hw = ctx.T.mode === 'hardware';
  const P = ctx.plan;
  // The SERVER decides the shape from her focus period (focus_period.resolve_output_shape).
  // The app used to ignore that and default to the mockup's 'schedule', which is how a
  // priority plan ended up rendered through one unlabelled container band.
  // A clock plan CAN render either way — `workItems` flattens bands into a ranked list — so
  // the toggle is real there and only there. A priority plan has no clock times to show, and
  // inventing them is the fabrication this whole surface is being cleaned of.
  const canToggle = P.shape === 'schedule';
  const shape = canToggle ? ctx.ui.todayShape || 'schedule' : 'priority';
  // The server's own one-line reason. Rendered VERBATIM and never composed here: the client
  // cannot know which path produced the shape (explicit "Priority list" setting vs. an
  // availability window), so any locally written sentence would sometimes assert a cause that
  // is not the cause. Empty header → no line at all.
  const reason = !canToggle && P.header ? P.header : '';

  const seg = (id: 'schedule' | 'priority', label: string) => {
    const on = shape === id;
    return (
      <button
        key={id}
        onClick={() => ctx.up({ todayShape: id })}
        style={{
          background: 'none',
          border: 'none',
          color: on ? C.sig : C.dimmer,
          fontSize: '11px',
          fontWeight: on ? 600 : 500,
          fontFamily: 'inherit',
          padding: '1px 2px',
          cursor: 'pointer',
          borderBottom: '1.5px solid ' + (on ? C.sig : 'transparent'),
        }}
      >
        {label}
      </button>
    );
  };

  /**
   * `gated` marks a button that STARTS A GENERATION — so it can show that it is working, and so
   * a second tap cannot stack a request the server would refuse anyway (`_gen_lock`,
   * `server.py:272`). "Add something" is navigation and stays live throughout.
   */
  const act = (label: string, primary: boolean, onClick: () => void, gated = false) => {
    const running = gated && ctx.generating === label;
    const held = gated && ctx.generating !== null && !running;
    const stl: React.CSSProperties = hw
      ? {
          background: primary
            ? `linear-gradient(180deg,${alpha(C.rose, 0.169)},${alpha(C.rose, 0.059)})`
            : 'linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.01))',
          border: '1px solid ' + (primary ? alpha(C.rose, 0.502) : 'rgba(255,255,255,.12)'),
          borderRadius: ctx.T.r.ctl,
          color: primary ? C.rose : C.dim,
          fontFamily: ctx.T.mono,
          fontSize: '10.5px',
          letterSpacing: '.04em',
          textTransform: 'uppercase',
          padding: '6px 11px',
          cursor: 'pointer',
          lineHeight: 1,
          boxShadow: primary
            ? `0 0 14px ${alpha(C.rose, 0.2)}, inset 0 1px 0 rgba(255,255,255,.13)`
            : 'inset 0 1px 0 rgba(255,255,255,.07)',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
        }
      : {
          background: primary
            ? `radial-gradient(1.2px 1.2px at 22% 32%,rgba(255,255,255,.55),transparent 60%),${alpha(C.rose, 0.133)}`
            : 'rgba(255,255,255,.05)',
          border: '1px solid ' + (primary ? alpha(C.rose, 0.439) : 'rgba(255,255,255,.1)'),
          borderRadius: ctx.T.r.chip,
          color: primary ? C.rose : C.dim,
          fontSize: '12px',
          padding: '6px 13px',
          cursor: 'pointer',
          fontFamily: 'inherit',
          lineHeight: 1,
          boxShadow: primary ? `0 0 16px ${alpha(C.rose, 0.18)}` : 'none',
        };
    // The dot is v4's own — the action row's primary hardware button already carries one (5px,
    // round, accent-coloured, 6px glow), transcribed just below. While a generation runs it also
    // appears on the celestial button and on the non-primary presets, in that button's OWN text
    // colour, so no new colour value enters either theme.
    const dotColor = primary ? C.rose : C.dim;
    const dot = (pulsing: boolean) => (
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          background: pulsing ? dotColor : C.rose,
          boxShadow: '0 0 6px ' + (pulsing ? dotColor : C.rose),
          flex: '0 0 auto',
          // `ringpulse` is defined in `app/index.html` and, before this, used by nothing —
          // `.5 → 0` opacity with a 1.06 scale. `alternate` makes it a pulse rather than a
          // single fade-out. See the header note on why this is derived and not transcribed.
          ...(pulsing ? { animation: 'ringpulse 1.1s ease-in-out infinite alternate' } : null),
        }}
      />
    );
    return (
      <button
        key={label}
        onClick={onClick}
        disabled={running || held}
        style={{
          ...stl,
          // v4's own not-tappable-right-now treatment: `opacity:.5` from the blocked type button
          // (v4:533), `cursor:'default'` from the disabled desktop back button (v4:723).
          ...(held ? { opacity: 0.5, cursor: 'default' } : null),
          ...(running ? { cursor: 'default' } : null),
          // The celestial button is not a flex container in its resting state; the running dot
          // needs it to be one, exactly as the hardware button already is.
          ...(running && !hw
            ? { display: 'inline-flex', alignItems: 'center', gap: '6px' }
            : null),
        }}
      >
        {running ? dot(true) : primary && hw ? dot(false) : null}
        {running ? 'Regenerating…' : label}
      </button>
    );
  };

  return (
    <div>
      <FocusSlot ctx={ctx} />

      {/* The woven frame — the one narrative the surface keeps (spec §14). */}
      <div
        style={{
          margin: '12px 14px 2px',
          padding: '11px 14px',
          border: '1px solid ' + C.roseBorder,
          borderLeft: hw ? '2px solid ' + C.rose : '1px solid ' + C.roseBorder,
          borderRadius: ctx.T.r.card,
          background: hw
            ? C.roseBg
            : 'radial-gradient(1.2px 1.2px at 18% 30%,rgba(255,255,255,.4),transparent 60%),' +
              'radial-gradient(1px 1px at 74% 66%,rgba(255,255,255,.3),transparent 60%),' +
              C.roseBg,
          backdropFilter: ctx.T.blur,
          WebkitBackdropFilter: ctx.T.blur,
          boxShadow: hw ? bevel(ctx.T) : `0 0 22px -8px ${alpha(C.rose, 0.4)}`,
        }}
      >
        <div
          style={{
            fontFamily: ctx.T.mono,
            fontSize: '9px',
            letterSpacing: '.12em',
            textTransform: 'uppercase',
            color: C.roseDim,
            marginBottom: '4px',
          }}
        >
          {hw ? '// today' : '✦ today'}
        </div>
        <div style={{ fontSize: '13px', color: C.rose, lineHeight: 1.55, opacity: 0.95 }}>
          {P.woven}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '6px 14px 2px' }}>
        {canToggle ? (
          <>
            {/* The label heads the control. With no control under it, it would head a
                sentence instead — so it goes when the segments go. */}
            <span
              style={{
                fontSize: '10px',
                color: C.dimmer,
                textTransform: 'uppercase',
                letterSpacing: '.08em',
                marginRight: 'auto',
              }}
            >
              View
            </span>
            {seg('schedule', 'Schedule')}
            <span style={{ color: C.dimmer, fontSize: '10px' }}>·</span>
            {seg('priority', 'Priority')}
          </>
        ) : reason ? (
          <div style={{ fontSize: '11px', color: C.dimmer, lineHeight: 1.45 }}>{reason}</div>
        ) : null}
      </div>

      {shape === 'priority' ? (
        <div style={{ borderBottom: '1px solid ' + C.border, padding: '4px 0' }}>
          <PriorityList ctx={ctx} reasonShown={!!reason} />
        </div>
      ) : (
        <div style={{ borderBottom: '1px solid ' + C.border }}>
          {P.blocks.map((b, bi) => (
            <Band key={'b' + bi} ctx={ctx} band={b} bandIndex={bi} />
          ))}
        </div>
      )}

      <div
        onClick={() => ctx.goTab('map')}
        style={{
          margin: '10px 14px 0',
          padding: '11px 13px',
          border: '1px solid ' + C.roseBorder,
          borderRadius: ctx.T.r.field,
          background: C.roseBg,
          cursor: 'pointer',
        }}
      >
        <span style={{ display: 'block', fontSize: '12px', color: C.dim, lineHeight: 1.45 }}>
          Creative and self-directed work isn’t scheduled — it’s yours to choose.
        </span>
        <span style={{ display: 'block', fontSize: '12px', color: C.rose, marginTop: '4px' }}>
          Open the Map to pick a thread ›
        </span>
      </div>

      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid ' + C.border,
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
        }}
      >
        {act('↻ Fresh plan', true, () => ctx.regenerate({ kind: 'refresh' }, '↻ Fresh plan'), true)}
        {act(
          'Low energy today',
          false,
          () => ctx.regenerate({ kind: 'preset', presetId: 'low-energy' }, 'Low energy today'),
          true,
        )}
        {act(
          'Quick wins only',
          false,
          () => ctx.regenerate({ kind: 'preset', presetId: 'quick-wins' }, 'Quick wins only'),
          true,
        )}
        {act('Life admin & household', false, () =>
          ctx.flash('Prioritizing life admin + household'),
        )}
        {act(
          'I’m stuck',
          false,
          () => ctx.regenerate({ kind: 'preset', presetId: 'stuck' }, 'I’m stuck'),
          true,
        )}
        {act('Add something', false, () => ctx.goTab('add'))}
        {act('Move this later', false, () => ctx.flash('Pick an item to move'))}
      </div>

      <div style={{ padding: '10px 14px 18px' }}>
        <div
          style={{
            fontFamily: hw ? ctx.T.mono : 'inherit',
            fontSize: '10px',
            color: C.dimmer,
            textTransform: 'uppercase',
            letterSpacing: '.08em',
            marginBottom: '6px',
          }}
        >
          {hw ? '// tell me what you need' : 'or tell me what you need'}
        </div>
        <div style={{ display: 'flex', gap: '7px', alignItems: 'flex-end' }}>
          <textarea
            value={ctx.ui.ask}
            placeholder={
              hw
                ? '>_ 30 min, need to stay horizontal…'
                : 'e.g. I only have 30 min and need to stay horizontal…'
            }
            onChange={(e) => ctx.up({ ask: e.target.value })}
            style={{
              flex: 1,
              background: C.inkBg,
              border: '1px solid ' + C.inkBorder,
              borderRadius: ctx.T.r.field,
              color: C.text,
              fontSize: '13px',
              fontFamily: hw ? ctx.T.mono : 'inherit',
              padding: '8px 11px',
              resize: 'none',
              minHeight: '150px',
              lineHeight: 1.45,
              outline: 'none',
              boxShadow: hw ? 'inset 0 1px 3px rgba(0,0,0,.4)' : 'none',
            }}
          />
          <button
            onClick={() => {
              if (ctx.ui.ask.trim()) {
                ctx.flash('Sent');
                ctx.up({ ask: '' });
              }
            }}
            style={{
              background: hw
                ? `linear-gradient(180deg,${alpha(C.sig, 0.169)},${alpha(C.sig, 0.051)})`
                : alpha(C.rose, 0.133),
              border: '1px solid ' + (hw ? alpha(C.sig, 0.502) : alpha(C.rose, 0.4)),
              borderRadius: ctx.T.r.field,
              color: hw ? C.sig : C.rose,
              fontFamily: hw ? ctx.T.mono : 'inherit',
              fontSize: hw ? '10.5px' : '12px',
              letterSpacing: hw ? '.04em' : 'normal',
              textTransform: hw ? 'uppercase' : 'none',
              padding: '0 13px',
              cursor: 'pointer',
              height: '36px',
              whiteSpace: 'nowrap',
              boxShadow: hw ? 'inset 0 1px 0 rgba(255,255,255,.12)' : 'none',
            }}
          >
            {hw ? 'EXEC ⏎' : '✦ Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
