/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // LegalLens brand palette
        ink: {
          DEFAULT: "#1a1f2e",   // near-black for text
          soft: "#374151",      // secondary text
          muted: "#6b7280",     // captions
        },
        parchment: {
          DEFAULT: "#faf9f7",   // page background
          warm: "#f3f0eb",      // card background
          border: "#e5e0d8",    // borders
        },
        brand: {
          DEFAULT: "#1e40af",   // deep judicial blue
          light: "#dbeafe",     // blue tint bg
          dark: "#1e3a8a",
        },
        verdict: {
          green: "#065f46",     // positive
          red: "#991b1b",       // negative
          amber: "#92400e",     // caution
        },
      },
      fontFamily: {
        display: ["'Playfair Display'", "Georgia", "serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)",
        citation: "inset 3px 0 0 #1e40af",
      },
    },
  },
  plugins: [],
};
