import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

const backend = process.env.INTERFACES_BACKEND ?? "http://localhost:8000";

export default defineConfig({
  plugins: [preact()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/ws": { target: backend.replace(/^http/, "ws"), ws: true },
    },
  },
});
