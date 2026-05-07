import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 内网穿透（如 SakuraFrp / frp-cat.com）时浏览器 Host 非 localhost，需显式放行
    allowedHosts: ["frp-cat.com", ".frp-cat.com"],
    proxy: {
      "/api-pipeline": {
        target: "http://127.0.0.1:8008",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-pipeline/, ""),
      },
    },
  },
});
