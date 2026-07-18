import type { Theme } from '@tokens';
import type { Graph } from '../model/index.ts';
import { Placeholder } from './Placeholder.tsx';

/** Placeholder until Task 6 ports `strategiesBody()` (~651). */
export function StrategiesScreen({ T, graph }: { T: Theme; graph: Graph }) {
  return <Placeholder T={T} name="Strategies" note={`${graph.strategies.length} strategies`} />;
}
