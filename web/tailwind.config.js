/** @type {import('tailwindcss').Config} */

// Colors come from CSS variables (src/index.css), which switch for dark mode,
// so components use one set of names: bg-surface, text-ink, text-muted...
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: v("page"),
        surface: v("surface"),
        line: v("line"),
        ink: v("ink"),
        muted: v("muted"),
        faint: v("faint"),
        accent: v("accent"),
        "accent-strong": v("accent-strong"),
        "accent-ink": v("accent-ink"),
        danger: v("danger"),
        success: v("success"),
      },
      fontFamily: {
        // Self-hosted (@fontsource-variable/inter, imported in main.tsx)
        sans: ["Inter Variable", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.04)",
        "card-hover": "0 2px 8px rgb(0 0 0 / 0.06)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "none" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out both",
      },
    },
  },
  plugins: [],
};
