import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import pkg from './package.json' with { type: 'json' };

export default defineConfig({
  plugins: [tailwindcss(), svelte()],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  server: {
    // during development the PocketBase backend runs on :8090
    proxy: { '/api': 'http://127.0.0.1:8090' },
  },
  build: { outDir: 'dist', emptyOutDir: true },
});
