import { useEffect, useState } from 'react';
import { useTheme } from './theme/useTheme.ts';
import { AppShell } from './shell/AppShell.tsx';
import { CheckPage } from './CheckPage.tsx';

/**
 * Entry point.
 *
 * The app is the shell. The token acceptance page — the surface June compares against
 * `design/mockups/color-system.html` §5a/§5c — is NOT deleted; it moves to `/check`, because
 * it stays the fidelity reference for the whole port and every later task needs it reachable.
 *
 * Routing is a hash check, not a router dependency: there are exactly two destinations and
 * the app itself is a single-screen shell with its own tab state. Both `#/check` and a
 * `/check` path suffix work, so the route survives being served from `/app/` by the Python
 * server later (Task 12) as well as by the Vite dev server now.
 *
 * `useTheme` is called HERE and only here. It owns a `useState`; a second call anywhere in
 * the tree would fork the theme, so `T` is passed down as a prop from this one call.
 */
function isCheckRoute(): boolean {
  const { hash, pathname } = window.location;
  return hash.replace(/^#/, '').replace(/\/$/, '') === '/check' || /\/check\/?$/.test(pathname);
}

export function App() {
  const { name, theme: T, setTheme } = useTheme();
  const [check, setCheck] = useState(isCheckRoute);

  useEffect(() => {
    const onNav = () => setCheck(isCheckRoute());
    window.addEventListener('hashchange', onNav);
    window.addEventListener('popstate', onNav);
    return () => {
      window.removeEventListener('hashchange', onNav);
      window.removeEventListener('popstate', onNav);
    };
  }, []);

  if (check) return <CheckPage />;
  return <AppShell T={T} name={name} setTheme={setTheme} />;
}
