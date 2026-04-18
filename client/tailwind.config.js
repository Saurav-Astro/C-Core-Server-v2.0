/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      boxShadow: {
        glow: "0 0 40px rgba(52, 211, 153, 0.1)",
        surface: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      colors: {
        panel: {
          DEFAULT: "rgb(3 7 18 / <alpha-value>)",
          solid: "#030712",
        },
        brand: {
          emerald: "#10b981",
          cyan: "#06b6d4",
          blue: "#3b82f6",
          rose: "#f43f5e",
          amber: "#f59e0b",
        },
      },
      backgroundImage: {
        "soft-grid":
          "linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
