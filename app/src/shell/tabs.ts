/**
 * The six tabs.
 *
 * v4's `appTabs()` (~949) renders FIVE buttons — Today, Add/Log, Map, Routines, Strategies.
 * Settings is the sixth destination but deliberately not a tab: `appHeader()` (~940) reaches
 * it from the gear, and `renderShell()` (~929) hides the tab bar entirely while it is open.
 * That fork is preserved here: `TAB_BAR` is what the bar renders, `AppTab` is the full set.
 */

export type AppTab = 'today' | 'add' | 'map' | 'routines' | 'strategies' | 'settings';

/** Labels are v4's verbatim. */
export const TAB_BAR: ReadonlyArray<{ id: AppTab; label: string }> = [
  { id: 'today', label: 'Today' },
  { id: 'add', label: 'Add/Log' },
  { id: 'map', label: 'Map' },
  { id: 'routines', label: 'Routines' },
  { id: 'strategies', label: 'Strategies' },
];

/**
 * Order used to decide the navigation direction.
 *
 * v4 derives direction from tree DEPTH (`treeBody` ~642: deeper = 'fwd', shallower = 'back')
 * and there is no tab-level animation, because v4 re-renders the whole shell imperatively.
 * The same grammar — later enters from the right, earlier from the left — is applied to tab
 * changes here, with settings pinned last so opening it reads as going forward and closing it
 * as coming back.
 */
const ORDER: readonly AppTab[] = ['today', 'add', 'map', 'routines', 'strategies', 'settings'];

export type NavDir = 'fwd' | 'back';

export function navDir(from: AppTab, to: AppTab): NavDir {
  return ORDER.indexOf(to) < ORDER.indexOf(from) ? 'back' : 'fwd';
}

/** v4 `this.NAV` (~61). */
export const NAV = '.26s cubic-bezier(.4,0,.2,1)';

/** The animation shorthand for a panel entering in the given direction. */
export function navAnimation(dir: NavDir): string {
  return `${dir === 'back' ? 'navback' : 'navfwd'} ${NAV}`;
}
