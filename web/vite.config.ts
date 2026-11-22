/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the backend runs on its own port. Vite passes every /api
// request on to it, so the browser only ever talks to one address (no CORS).
// In production nginx does the same job (see nginx.conf).
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    // The charts library is most of the code: its own file, cached separately
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  server: {
    port: 5173,
    proxy: { "/api": { target: apiUrl, ws: true } }, // ws: the live updates too
  },
  preview: {
    port: 4173,
    proxy: { "/api": { target: apiUrl, ws: true } },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
