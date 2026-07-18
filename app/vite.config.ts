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

  // Component tests need a DOM. Model-layer tests are pure and unaffected.
  test: {
    environment: 'jsdom',
    globals: false,
  },
});
