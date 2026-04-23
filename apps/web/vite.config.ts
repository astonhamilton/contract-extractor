import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/corpus/summary": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/corpus/documents": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/threads": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/turns": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/stats": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
