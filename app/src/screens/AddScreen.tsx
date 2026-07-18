import type { Theme } from '@tokens';
import { Placeholder } from './Placeholder.tsx';

/** Placeholder until Task 8 ports `addLogTab()` (~1108). */
export function AddScreen({ T }: { T: Theme }) {
  return <Placeholder T={T} name="Add/Log" />;
}
