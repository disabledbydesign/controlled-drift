import type { Theme } from '@tokens';
import { Placeholder } from './Placeholder.tsx';

/**
 * Placeholder until Task 8 ports `settingsPanel()` (~1152) and `themeSection()` (~1144).
 * Reached from the header gear, never from the tab bar — see `shell/tabs.ts`.
 */
export function SettingsScreen({ T }: { T: Theme }) {
  return <Placeholder T={T} name="Settings" />;
}
