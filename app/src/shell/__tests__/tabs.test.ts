// @vitest-environment node
// Pure logic — no DOM. Opting out of jsdom keeps 53 environment setups from
// contending for 8 cores, which is what made the suite time out under load.

import { describe, expect, it } from 'vitest';
import { navAnimation, navDir, TAB_BAR } from '../tabs.ts';

/**
 * Behaviour, not existence: the two things the shell's routing can get wrong silently are
 * (a) putting Settings in the tab bar, and (b) animating a backward move as a forward one,
 * which reads as the app moving deeper when it is coming back.
 */
describe('tab bar', () => {
  it('renders five tabs — Settings is reached from the gear, not the bar', () => {
    expect(TAB_BAR.map((t) => t.id)).toEqual(['today', 'add', 'map', 'routines', 'strategies']);
    expect(TAB_BAR.some((t) => (t.id as string) === 'settings')).toBe(false);
  });

  it('uses v4 labels verbatim', () => {
    expect(TAB_BAR.map((t) => t.label)).toEqual([
      'Today',
      'Add/Log',
      'Map',
      'Routines',
      'Strategies',
    ]);
  });
});

describe('navigation direction', () => {
  it('moving later in the bar is forward', () => {
    expect(navDir('today', 'map')).toBe('fwd');
    expect(navDir('map', 'strategies')).toBe('fwd');
  });

  it('moving earlier in the bar is back', () => {
    expect(navDir('strategies', 'today')).toBe('back');
    expect(navDir('map', 'add')).toBe('back');
  });

  it('opening settings reads as forward and leaving it as back', () => {
    expect(navDir('today', 'settings')).toBe('fwd');
    expect(navDir('settings', 'today')).toBe('back');
  });

  it('names the keyframes that index.html defines', () => {
    expect(navAnimation('fwd')).toContain('navfwd');
    expect(navAnimation('back')).toContain('navback');
    expect(navAnimation('fwd')).toContain('.26s cubic-bezier(.4,0,.2,1)');
  });
});