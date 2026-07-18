import type { Theme } from '@tokens';
import type { GraphIndex } from '../model/index.ts';
import { Placeholder } from './Placeholder.tsx';

/** Placeholder until Task 4 renders the real tree here and Task 6 adds the map controls. */
export function MapScreen({ T, idx }: { T: Theme; idx: GraphIndex }) {
  return <Placeholder T={T} name="Map" note={`${idx.byId.size} objects indexed`} />;
}
