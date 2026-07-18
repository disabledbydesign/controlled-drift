import { useCallback, useEffect, useState } from 'react';
import { themes, type Theme, type ThemeName } from '@tokens';

/**
 * Theme selection. Client-local by default, per backend spec §18: the choice is a display
 * preference and must NEVER be written to Anytype objects or included in plan-generation
 * context. `cd_theme` is the same localStorage key v4 used, so an existing choice carries over.
 */
const KEY = 'cd_theme';
const DEFAULT: ThemeName = 'celestial';

function read(): ThemeName {
  try {
    const v = localStorage.getItem(KEY);
    if (v === 'celestial' || v === 'hardware') return v;
  } catch {
    /* private mode / storage disabled — fall through to the default */
  }
  return DEFAULT;
}

export function useTheme(): {
  name: ThemeName;
  theme: Theme;
  setTheme: (n: ThemeName) => void;
  isHW: boolean;
} {
  const [name, setName] = useState<ThemeName>(read);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, name);
    } catch {
      /* non-fatal: the theme just won't persist */
    }
  }, [name]);

  const setTheme = useCallback((n: ThemeName) => setName(n), []);

  return {
    name,
    theme: themes[name],
    setTheme,
    // v4 branched on this ~30 times for SHAPE differences (checkbox geometry, radii,
    // mono-vs-sans chrome) — not just color. Those are real forks, not a palette swap.
    isHW: name === 'hardware',
  };
}
