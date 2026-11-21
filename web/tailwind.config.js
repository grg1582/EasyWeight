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
        "accent-ink": v("accent-ink"),
        danger: v("danger"),
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
