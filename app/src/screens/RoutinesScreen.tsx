import type { Theme } from '@tokens';
import type { GraphIndex } from '../model/index.ts';
import { Placeholder } from './Placeholder.tsx';

/** Placeholder until Task 6 ports `recurringBody()` (~677). */
export function RoutinesScreen({ T, idx }: { T: Theme; idx: GraphIndex }) {
  let n = 0;
  for (const obj of idx.byId.values()) if (obj.level === 'RECURRING') n += 1;
  return <Placeholder T={T} name="Routines" note={`${n} recurring objects`} />;
}
