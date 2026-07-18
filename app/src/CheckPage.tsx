import { useMemo, useState } from 'react';
import { chipBorder, chipFill, typeRamp } from '@tokens';
import { useTheme } from './theme/useTheme';
import { starfield } from './theme/starfield';
import {
  appBg,
  Badge,
  bevel,
  Chip,
  EditChip,
  glow,
  Rail,
  RoundCheck,
  Switch,
  TaskCheck,
  TopAccent,
  typeColor,
} from './components/atoms';

/**
 * Token acceptance surface.
 *
 * This is NOT the app — it is the check page. It renders the reconciled tokens so they can be
 * compared side by side against `design/mockups/color-system.html` sections 5a (celestial) and
 * 5c (hardware), which are the canonical component kits June tuned against.
 *
 * It exists because fidelity should be verified by LOOKING, not by reading hex values.
 */

const TYPES = ['GOAL', 'PROJECT', 'SUBPROJECT', 'WORKSTREAM', 'TASK', 'RECURRING', 'STRATEGY'];

export function CheckPage() {
  const { name, theme: T, setTheme, isHW } = useTheme();
  const C = T.c;
  const E = T.effects;

  // Drives the interactive atoms below, so the on/off forks can be seen switching.
  const [live, setLive] = useState(false);

  // Regenerated only when the theme changes — the seed is fixed, so the sky is stable.
  const sky = useMemo(() => starfield(), []);

  const chips: [string, string][] = [
    ['Steady', C.green],
    ['Sprint', C.rose],
    ['Open', C.amber],
    ['Work', C.purple],
    ['Blocked', C.red],
  ];

  return (
    <div
      style={{
        minHeight: '100vh',
        background: appBg(T, sky),
        color: C.text,
        fontFamily: T.font,
        padding: '40px 24px 96px',
      }}
    >
      <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <header style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div
            style={{
              fontFamily: T.mono,
              fontSize: 10,
              letterSpacing: '.14em',
              textTransform: 'uppercase',
              color: C.dimmer,
            }}
          >
            {isHW ? '// token check' : '✦ token check'}
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>
            {T.label} <span style={{ color: C.dim, fontWeight: 400, fontSize: 15 }}>— {T.tag}</span>
          </div>

          {/* The check page is a route now (App.tsx), so it needs a way back to the app. */}
          <a
            href="#/"
            style={{ fontFamily: T.mono, fontSize: 10, color: C.dimmest, textDecoration: 'none' }}
          >
            ‹ back to the app
          </a>

          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            {(['celestial', 'hardware'] as const).map((n) => (
              <button
                key={n}
                onClick={() => setTheme(n)}
                style={{
                  cursor: 'pointer',
                  padding: '7px 16px',
                  fontFamily: isHW ? T.mono : T.font,
                  fontSize: 12,
                  textTransform: isHW ? 'uppercase' : 'none',
                  letterSpacing: isHW ? '.1em' : 0,
                  color: n === name ? C.on : C.dim,
                  background: n === name ? C.rose : 'transparent',
                  border: `1px solid ${n === name ? C.rose : C.border}`,
                  borderRadius: T.r.chip,
                  boxShadow: n === name ? E.glowSm(C.rose) : 'none',
                }}
              >
                {n}
              </button>
            ))}
          </div>
        </header>

        <Section title="Object types · structure ramp + kinds" T={T}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14 }}>
            {TYPES.map((t) => {
              const col = typeRamp[name][t] ?? C.dim;
              return (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: isHW ? '2px' : '50%',
                      background: col,
                      boxShadow: E.glowSm(col),
                      display: 'inline-block',
                    }}
                  />
                  <span style={{ fontSize: 12, color: C.dim, fontFamily: isHW ? T.mono : T.font }}>
                    {isHW ? t : t.charAt(0) + t.slice(1).toLowerCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>

        <Section title="Status chips" T={T}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {chips.map(([label, col]) => (
              <span
                key={label}
                style={{
                  fontSize: 11.5,
                  color: col,
                  background: chipFill(col, name),
                  border: chipBorder(col),
                  borderRadius: T.r.chip,
                  padding: '4px 12px',
                  fontFamily: isHW ? T.mono : T.font,
                  textTransform: isHW ? 'uppercase' : 'none',
                  letterSpacing: isHW ? '.08em' : 0,
                }}
              >
                {label}
              </span>
            ))}
          </div>
        </Section>

        <Section title="Checkboxes · completion green is NOT task colour" T={T}>
          <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
            {[false, true].map((done) => (
              <span
                key={String(done)}
                style={{
                  width: 19,
                  height: 19,
                  borderRadius: isHW ? '4px' : '50%',
                  border: `1.5px solid ${done ? C.green : C.border}`,
                  background: done ? C.green : 'transparent',
                  boxShadow: done ? E.glowSm(C.green) : E.bevelInset,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  color: C.onGreen,
                }}
              >
                {done ? '✓' : ''}
              </span>
            ))}
            <span style={{ fontSize: 12.5, color: C.dim }}>
              green = done / steady / saved, never “this is a task”
            </span>
          </div>
        </Section>

        <Section title="Surfaces" T={T}>
          <div
            style={{
              background: C.panel,
              border: `1px solid ${C.border}`,
              borderRadius: T.r.card,
              padding: 16,
              boxShadow: `${E.containerHighlight}, ${E.containerShadow}`,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: '0 0 auto 0',
                height: E.topAccentHeight,
                background: E.topAccent,
                boxShadow: E.topAccentGlow,
              }}
            />
            <div style={{ fontSize: 14.5, fontWeight: 600, marginTop: 6 }}>Scholarly writing</div>
            <div style={{ fontSize: 12.5, color: C.dim, marginTop: 4 }}>
              a panel with the top accent, container bevel and glass border
            </div>
          </div>
        </Section>

        {/* ─── Ported v4 atoms ─────────────────────────────────────────────────────
            Everything below renders the primitives in `components/atoms/`, for eyeball
            comparison against color-system.html §5a (celestial) and §5c (hardware). */}

        <Section title="Atom · TopAccent" T={T}>
          <div
            style={{
              background: C.panel,
              border: `1px solid ${C.border}`,
              borderRadius: T.r.card,
              overflow: 'hidden',
            }}
          >
            <TopAccent T={T} />
            <div style={{ padding: 14, fontSize: 12.5, color: C.dim }}>
              the gradient bar sits flush at the top edge of a panel
            </div>
          </div>
        </Section>

        <Section title="Atom · TaskCheck · size forks at 17px" T={T}>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            {([13, 15, 17, 19, 24] as const).map((s) => (
              <div key={s} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <TaskCheck T={T} done={false} col={C.rose} size={s} />
                <TaskCheck T={T} done col={C.rose} size={s} />
                <TaskCheck T={T} done col={C.green} size={s} />
                <span style={{ fontSize: 11, color: C.dimmest, fontFamily: T.mono }}>{s}</span>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Atom · Switch · two different controls, not one recoloured" T={T}>
          <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
            <Switch T={T} on={false} />
            <Switch T={T} on />
            <Switch T={T} on col={C.green} />
            <Switch T={T} on col={C.rose} />
            <button
              onClick={() => setLive((v) => !v)}
              style={{
                background: 'none',
                border: `1px solid ${C.border}`,
                borderRadius: T.r.ctl,
                color: C.dim,
                fontFamily: 'inherit',
                fontSize: 11.5,
                padding: '4px 10px',
                cursor: 'pointer',
              }}
            >
              toggle live
            </button>
            <Switch T={T} on={live} />
          </div>
        </Section>

        <Section title="Atom · Badge + Rail · colour from the gallery legend" T={T}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {TYPES.map((t) => (
              <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'stretch' }}>
                <Rail T={T} level={t} />
                <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', padding: '3px 0' }}>
                  <Badge T={T} level={t} />
                  <Badge T={T} level={t} small />
                  <span style={{ fontSize: 12.5, color: C.textSoft }}>a row at this level</span>
                  <span style={{ fontSize: 10.5, color: C.dimmest, fontFamily: T.mono }}>
                    {typeColor(T, t)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Atom · Chip · unset branch drops the hardware treatment" T={T}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            <Chip T={T} c={{ text: 'Steady', color: C.green }} />
            <Chip T={T} c={{ text: 'Open', color: C.amber }} />
            <Chip T={T} c={{ text: 'Blocked', color: C.red }} />
            <Chip T={T} c={{ text: 'Strategy', color: C.strategy }} />
            <Chip T={T} c={{ text: 'clickable', color: C.sig }} onClick={() => setLive((v) => !v)} />
            <Chip T={T} c={{ text: 'no engagement set', unset: true }} />
          </div>
        </Section>

        <Section title="Atoms · RoundCheck + EditChip · a Today row" T={T}>
          <div
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'flex-start',
              background: C.surface,
              border: `1px solid ${C.hair}`,
              borderRadius: T.r.card,
              padding: '10px 12px',
            }}
          >
            <RoundCheck T={T} done={live} onClick={() => setLive((v) => !v)} />
            <div style={{ flex: '1 1 auto', minWidth: 0 }}>
              <div style={{ fontSize: 13.5, color: C.text }}>Draft the methods section</div>
              <div style={{ fontSize: 11, color: C.dimmest, marginTop: 3 }}>takes 45m</div>
            </div>
            <EditChip T={T} onClick={() => setLive((v) => !v)} />
          </div>
        </Section>

        <Section title="Helpers · glow() and bevel()" T={T}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {[
              ['glow(sig)', glow(T, C.sig)],
              ['glow(rose)', glow(T, C.rose)],
              ['glow(green)', glow(T, C.green)],
              ['bevel()', bevel(T)],
            ].map(([label, sh]) => (
              <div
                key={label}
                style={{
                  background: C.panel,
                  border: `1px solid ${C.border}`,
                  borderRadius: T.r.ctl,
                  padding: '10px 14px',
                  fontSize: 11.5,
                  color: C.dim,
                  fontFamily: T.mono,
                  boxShadow: sh,
                }}
              >
                {label}
              </div>
            ))}
          </div>
          <div style={{ fontSize: 11.5, color: C.dimmest }}>
            bevel() is intentionally <code>none</code> in celestial — that theme does not bevel.
          </div>
        </Section>

        <div style={{ fontSize: 11.5, color: C.dimmest, lineHeight: 1.6 }}>
          Compare against <code>design/mockups/color-system.html</code> — section 5a for celestial,
          5c for hardware. Starfield: {sky.split('),radial').length} gradients built at runtime
          from ~600 bytes of code, rather than 14 kB of literal CSS in the bundle. The resulting
          string is the same size either way — what is saved is download, not memory.
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  T,
  children,
}: {
  title: string;
  T: ReturnType<typeof useTheme>['theme'];
  children: React.ReactNode;
}) {
  const isHW = T.mode === 'hardware';
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div
        style={{
          fontFamily: T.mono,
          fontSize: 10,
          letterSpacing: '.14em',
          textTransform: 'uppercase',
          color: T.c.dimmer,
        }}
      >
        {isHW ? `// ${title}` : title}
      </div>
      {children}
    </section>
  );
}
