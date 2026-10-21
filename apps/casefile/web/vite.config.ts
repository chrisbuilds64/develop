import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The surface is static files served by the core (ADR-014). In development, /api goes to the core on 8400.
export default defineConfig({
  base: process.env.VITE_BASE || "/",
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8400" } },
  build: { outDir: "dist", sourcemap: false },
});
