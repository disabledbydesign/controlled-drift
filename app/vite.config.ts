// vitest/config re-exports Vite's defineConfig with the `test` key typed in.
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

const REPO = resolve(__dirname, '..');

// The Python server (scripts/server.py) owns /api and still serves the OLD overlay at "/".
// The new surface is mounted at /app/ so both can run side by side until June judges the
// new one better — she uses the old one daily and a big-bang swap puts the cost on her.
export default defineConfig({
  base: '/app/',
  plugins: [react()],

  resolve: {
    alias: {
      // Canonical design tokens live in design/tokens/ — reconciled from color-system.html,
      // which is the look June actually tuned against. Aliased rather than copied so there
      // is exactly one source and no drift between design record and running code.
      '@tokens': resolve(REPO, 'design/tokens/tokens.ts'),
      '@': resolve(__dirname, 'src'),
    },
  },

  server: {
    port: 5173,
    fs: {
      // Allow reading design/tokens/, which sits outside this app's root.
      allow: [REPO],
    },
    proxy: {
      // Closes the CORS gap without touching server.py: in dev the browser only ever
      // talks to :5173, and Vite forwards /api to the Python server same-origin.
      '/api': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: false,
      },
    },
  },

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },

  test: {
    // jsdom is the DEFAULT because most tests here are component tests: a new component
    // test is then correct with no ceremony, and the failure mode of forgetting is a
    // passing test rather than a confusing "document is not defined".
    //
    // The 18 pure model/API/logic files opt OUT explicitly with a `@vitest-environment node`
    // docblock. That is not a micro-optimisation. Building a jsdom for a file that never
    // touches the DOM is pure contention: measured on this 8-core machine, environment
    // setup cost MORE than running the tests (47.97s env vs 54.02s tests unloaded; 237s env
    // vs 204s tests under load). Those wasted setups are what pushed ordinary tests past
    // their timeout whenever another agent was building or running the backend suite.
    environment: 'jsdom',

    // Deliberate: component tests call `afterEach(cleanup)` explicitly. Turning globals on
    // would silently change every test file's assumptions.
    globals: false,

    // Cap file-level parallelism below the core count. Vitest's default sizes the pool to
    // the machine, which is right for a machine running only the suite — but this suite
    // routinely runs while agents run builds and the Python suite. Leaving headroom means
    // the suite degrades (runs slower) under load instead of failing (timing out).
    // (Vitest 4 replaced `poolOptions.forks.maxForks` with a top-level `maxWorkers`;
    // the old key is silently ignored, so it must not be reintroduced.)
    pool: 'forks',
    maxWorkers: 6,

    // Backstop only — NOT the fix. The fix is the two settings above, which remove the
    // contention that made tests slow. This timeout exists because the suite shares a
    // machine with work it cannot see or control, and a test that would pass in 200ms
    // should not be failed for losing a scheduling race. It is sized so that a genuine
    // hang still fails the run in reasonable time rather than hanging CI.
    testTimeout: 20_000,
    hookTimeout: 20_000,
  },
});
