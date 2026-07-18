import { TodayPanel } from '../components/today/index.ts';
import type { TodayCtx } from '../components/today/index.ts';

/**
 * v4's Today tab. The screen is a thin mount: `TodayPanel` (v4 `todayPanel` ~977) owns the
 * whole surface, and the context is assembled in the shell, where the state actually lives.
 */
export function TodayScreen({ ctx }: { ctx: TodayCtx }) {
  return <TodayPanel ctx={ctx} />;
}
