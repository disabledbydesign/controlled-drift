import type { Theme } from '@tokens';
import type { Plan } from '../fixtures/index.ts';
import { Placeholder } from './Placeholder.tsx';

/** Placeholder until Task 7 ports `todayPanel()` (~977) and everything under it. */
export function TodayScreen({ T, plan }: { T: Theme; plan: Plan }) {
  return <Placeholder T={T} name="Today" note={`${plan.date} · ${plan.blocks.length} blocks`} />;
}
