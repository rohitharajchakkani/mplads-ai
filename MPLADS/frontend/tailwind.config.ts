import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15263a",
        navy: "#12355b",
        blue: {
          50: "#edf5fb",
          100: "#d8e9f7",
          200: "#b8d7ed",
          DEFAULT: "#1769aa",
          700: "#12558d",
        },
        mist: "#f4f7fa",
        line: "#d7e0e8",
        sage: "#23755d",
        civic: {
          saffron: "#d97706",
          green: "#18794e",
          pale: "#f8fafc",
        },
      },
      boxShadow: {
        panel: "0 16px 44px rgba(20, 50, 80, 0.10)",
        elevated: "0 8px 28px rgba(20, 50, 80, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
