import { alpha, themes } from '@tokens';
import type { Theme, ThemeName } from '@tokens';
import { bevel, glow, Switch } from '../components/atoms/index.ts';
import type { BackendId, BackendOption } from '../shell/useAppState.ts';

/**
 * Settings — v4 `settingsPanel()` (1152) and `themeSection()` (1144).
 *
 * Reached from the header gear, never from the tab bar (see `shell/tabs.ts`). `themeSection`
 * has exactly one caller (`settingsPanel`, v4:1158), so both live here.
 *
 * ── theme state ─────────────────────────────────────────────────────────────
 * `name` and `setTheme` arrive as props, threaded down from the one `useTheme()` call in
 * `App.tsx`. This screen does NOT call `useTheme()`: that hook owns a `useState`, so a second
 * caller would hold an independent copy and the switch here would move only that copy while
 * the rest of the surface stayed put. Same rule stated in `components/atoms/index.ts` and
 * `shell/AppShell.tsx`.
 *
 * Persistence is `useTheme`'s existing `localStorage` effect on `cd_theme` — nothing is added
 * here for it, which is why the choice survives a reload.
 *
 * ── the backend list is READ, never hardcoded (Task 10) ─────────────────────
 * v4's three static rows (`claude | local | api`) do not match what `scripts/server.py` accepts
 * (`mistral | openrouter | claude | local`) — `api` does not exist there and `mistral`, June's
 * decided production default, was missing. Neither control reached the server at all before this
 * task, so a wrong option produced no visible error. `ctx.options` is `GET /api/settings`'s own
 * list (`plan_generate.backend_descriptor`, computed server-side) — this screen renders it, it
 * does not invent it.
 */

/** The slice of the UI bag Settings reads. `UiState` satisfies it structurally. */
export interface SettingsUi {
  backend: BackendId;
  hobby: boolean;
}

export interface SettingsCtx {
  T: Theme;
  name: ThemeName;
  setTheme: (n: ThemeName) => void;
  ui: SettingsUi;
  /** The real backend list from the server. Empty until it has loaded (or if the read failed). */
  options: BackendOption[];
  /** `POST /api/settings` — writes `backend` or `hobby` (translated to `include_hobby_block`). */
  save: (patch: Partial<SettingsUi>) => void;
}

export function SettingsScreen({ ctx }: { ctx: SettingsCtx }) {
  const { T, ui } = ctx;
  const C = T.c;
  const be = ui.backend;
  const hobby = ui.hobby;

  /** One radio row per backend option the server actually offers. */
  const opt = (o: BackendOption) => {
    const on = be === o.id;
    const detail = o.model ? `${o.mechanism} · ${o.model}` : o.mechanism;
    return (
      <button
        key={o.id}
        onClick={() => ctx.save({ backend: o.id })}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '9px',
          padding: '10px 0',
          cursor: 'pointer',
          background: 'none',
          border: 'none',
          borderBottom: '1px solid ' + C.hair,
          width: '100%',
          textAlign: 'left',
          fontFamily: 'inherit',
        }}
      >
        <span
          style={{
            width: '14px',
            height: '14px',
            borderRadius: '50%',
            border: '1.5px solid ' + (on ? C.gold : C.dimmer),
            flex: '0 0 auto',
            marginTop: '1px',
            position: 'relative',
          }}
        >
          {on ? (
            <span
              style={{
                position: 'absolute',
                inset: '2.5px',
                borderRadius: '50%',
                background: C.gold,
              }}
            />
          ) : null}
        </span>
        <div>
          <div style={{ fontSize: '13px', color: on ? C.text : C.dim }}>{o.label}</div>
          <div
            style={{
              fontSize: '11px',
              color: C.dimmer,
              fontFamily: T.mono,
              marginTop: '2px',
              lineHeight: 1.35,
            }}
          >
            {detail}
          </div>
        </div>
      </button>
    );
  };

  return (
    <div>
      <ThemeSection ctx={ctx} />

      <div style={{ padding: '13px 14px' }}>
        <div style={EYEBROW(C.dimmer)}>which model writes your plans</div>
        {ctx.options.map(opt)}
      </div>

      <div style={{ padding: '13px 14px', borderTop: '1px solid ' + C.border }}>
        <div style={EYEBROW(C.dimmer)}>what your daily plan includes</div>
        <button
          onClick={() => ctx.save({ hobby: !hobby })}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit',
            padding: 0,
          }}
        >
          <span style={{ fontSize: '13px', color: C.text }}>Include creative / hobby work</span>
          <Switch T={T} on={hobby} col={C.gold} />
        </button>
      </div>
    </div>
  );
}

/**
 * v4 `themeSection()` (1144).
 *
 * The two cards are built from `THEMES.celestial` / `THEMES.hardware` — here, the `themes`
 * record in `design/tokens/tokens.ts`, which carries the same `label` and `tag` fields v4's
 * `buildThemes()` (134) sets (v4:153, v4:158). Order is v4's: celestial then hardware.
 *
 * ⚠ SHAPE FORK, preserved: the selected dot is a 2px SQUARE in hardware and a circle in
 * celestial (v4's `this.isHW()?'2px':'50%'`) — the geometry differs, not just the colour.
 */
function ThemeSection({ ctx }: { ctx: SettingsCtx }) {
  const { T } = ctx;
  const C = T.c;
  const hw = T.mode === 'hardware';

  const opt = (t: Theme) => {
    const on = ctx.name === t.name;
    return (
      <button
        key={t.name}
        onClick={() => ctx.setTheme(t.name)}
        style={{
          flex: 1,
          minWidth: 0,
          cursor: 'pointer',
          fontFamily: 'inherit',
          textAlign: 'left',
          padding: '11px 12px',
          borderRadius: T.r.card,
          border: '1px solid ' + (on ? C.rose : C.border),
          // v4: `on ? C.rose+'1c' : C.panel`  (0x1c = .110)
          background: on ? alpha(C.rose, 0.11) : C.panel,
          boxShadow: on ? glow(T, C.rose) : bevel(T),
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <span
            style={{
              width: '9px',
              height: '9px',
              borderRadius: hw ? '2px' : '50%',
              background: on ? C.rose : C.dimmer,
              boxShadow: on ? '0 0 8px ' + C.rose : 'none',
              flex: '0 0 auto',
            }}
          />
          <span style={{ fontSize: '13.5px', fontWeight: 700, color: on ? C.text : C.dim }}>
            {t.label}
          </span>
        </span>
        <span
          style={{
            fontSize: '10px',
            color: on ? C.rose : C.dimmer,
            fontFamily: T.mono,
            letterSpacing: '.02em',
            textTransform: 'uppercase',
            paddingLeft: '16px',
            lineHeight: 1.3,
          }}
        >
          {t.tag}
        </span>
      </button>
    );
  };

  return (
    <div style={{ padding: '13px 14px', borderBottom: '1px solid ' + C.border }}>
      <div style={{ ...EYEBROW(C.dimmer), marginBottom: '9px' }}>theme · whole-surface look</div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {opt(themes.celestial)}
        {opt(themes.hardware)}
      </div>
      <div style={{ fontSize: '10.5px', color: C.dimmer, marginTop: '8px', lineHeight: 1.45 }}>
        {'Applies across every tab, mobile and desktop — and is remembered on this device.'}
      </div>
    </div>
  );
}

/** The section eyebrow (v4:1147, 1160, 1165). */
function EYEBROW(color: string): React.CSSProperties {
  return {
    fontSize: '10px',
    color,
    textTransform: 'uppercase',
    letterSpacing: '.08em',
    marginBottom: '9px',
  };
}
