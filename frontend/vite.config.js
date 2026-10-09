import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const BACKEND = process.env.VITE_BACKEND_ORIGIN ?? 'http://127.0.0.1:8000';

// Only /api is proxied. Everything else is a client-side route and must fall
// through to index.html, so the browser never receives API JSON at /appointments.
// This mirrors production, where Nginx/Ingress send /api/* to the backend and
// everything else to the static frontend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
  preview: {
    host: true,
    port: 3000,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
});