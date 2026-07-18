import type { Theme } from '@tokens';

export interface PlaceholderProps {
  T: Theme;
  /** The tab's own name — the point is that the shell says which tab you are on. */
  name: string;
  /** One short line of real, checkable state. Optional. */
  note?: string;
}

/**
 * A tab that has no content yet.
 *
 * This exists so the shell is verifiable on its own, before Tasks 4–9 fill the tabs in. Each
 * one names itself, so switching tabs is observable rather than inferred from a highlight.
 * Where a `note` is given it reports live state read out of the running model layer, which is
 * what shows the data path is actually connected and not just imported.
 */
export function Placeholder({ T, name, note }: PlaceholderProps) {
  const C = T.c;
  const hw = T.mode === 'hardware';
  return (
    <div
      style={{
        minHeight: '260px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px',
        padding: '48px 20px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontFamily: hw ? T.mono : T.font,
          fontSize: hw ? '15px' : '19px',
          fontWeight: 600,
          letterSpacing: hw ? '.1em' : '-.01em',
          textTransform: hw ? 'uppercase' : 'none',
          color: C.text,
        }}
      >
        {name}
      </div>
      {note ? (
        <div style={{ fontFamily: T.mono, fontSize: '11px', color: C.dimmer }}>{note}</div>
      ) : null}
    </div>
  );
}
