/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Inter"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          "system-ui",
          "sans-serif",
        ],
        mono: [
          '"JetBrains Mono"',
          '"Fira Code"',
          '"SF Mono"',
          "ui-monospace",
          "monospace",
        ],
      },
      colors: {
        // 飞书中性色系 (Feishu Neutral)
        ink: {
          50: "#fafafa",
          100: "#f4f5f7",
          200: "#e5e7eb",
          300: "#d1d5db",
          400: "#9ca3af",
          500: "#6b7280",
          600: "#4b5563",
          700: "#374151",
          800: "#1f2937",
          900: "#111827",
          950: "#0a0a0f",
        },
        // 织界主色 (Weave Brand)
        weave: {
          50: "#eef4ff",
          100: "#dbe6ff",
          200: "#bfd2ff",
          300: "#93b2ff",
          400: "#6087ff",
          500: "#3b5fff",
          600: "#2540f5",
          700: "#1d31dc",
          800: "#1b2bb0",
          900: "#1d2b8b",
        },
        // AI 辉光（极客风用）
        glow: {
          cyan: "#22d3ee",
          violet: "#8b5cf6",
          pink: "#ec4899",
        },
      },
      boxShadow: {
        // 飞书骨架
        "feishu-card": "0 1px 2px 0 rgba(17, 24, 39, 0.04), 0 1px 3px 0 rgba(17, 24, 39, 0.06)",
        "feishu-hover": "0 4px 8px -2px rgba(17, 24, 39, 0.08), 0 2px 4px -2px rgba(17, 24, 39, 0.06)",
        // 苹果质感
        "apple-glass": "0 8px 32px 0 rgba(17, 24, 39, 0.08), inset 0 1px 0 0 rgba(255, 255, 255, 0.5)",
        "apple-modal": "0 25px 50px -12px rgba(17, 24, 39, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.5) inset",
        // AI 辉光
        "glow-sm": "0 0 20px 0 rgba(59, 95, 255, 0.15)",
        "glow-md": "0 0 40px 0 rgba(59, 95, 255, 0.25)",
      },
      backgroundImage: {
        "grid-light":
          "linear-gradient(to right, rgba(17,24,39,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(17,24,39,0.04) 1px, transparent 1px)",
        "grid-dark":
          "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        "grid-24": "24px 24px",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1)",
        shimmer: "shimmer 2.5s linear infinite",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        float: "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
    },
  },
  plugins: [],
};
