import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./context/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#5A3825", dark: "#43291A", soft: "#EFE6E0", mid: "#8A6450" },
        ink: { DEFAULT: "#26211E", soft: "#5E5650", faint: "#8B837D" },
        surface: { DEFAULT: "#F6F4F2", deep: "#ECE8E4" },
        line: "#E4DED8",
        ok: { DEFAULT: "#2F6B3F", soft: "#E6F0E8" },
        warn: { DEFAULT: "#8A5A00", soft: "#F8EEDB" },
        bad: { DEFAULT: "#9B2C2C", soft: "#F7E4E2" },
      },
      fontFamily: {
        sans: ['"Public Sans"', '"Segoe UI"', "system-ui", "-apple-system", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
      borderRadius: { md: "6px", lg: "8px" },
    },
  },
  plugins: [],
};
export default config;
