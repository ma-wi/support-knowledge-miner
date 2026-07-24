import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_SKM_API_BASE_URL ?? "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
});
