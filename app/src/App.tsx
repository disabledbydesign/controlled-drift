import { useMemo } from 'react';
import { chipBorder, chipFill, typeRamp } from '@tokens';
import { useTheme } from './theme/useTheme';
import { starfield } from './theme/starfield';

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

export function App() {
  const { name, theme: T, setTheme, isHW } = useTheme();
  const C = T.c;
  const E = T.effects;

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
        background: `${isHW ? '' : sky + ','}${E.ambient},${C.bg}`,
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
