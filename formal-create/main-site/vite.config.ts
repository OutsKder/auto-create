import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api-pipeline": {
        target: "http://127.0.0.1:8008",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-pipeline/, ""),
      },
    },
  },
});
