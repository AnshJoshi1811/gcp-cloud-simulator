import colors from 'tailwindcss/colors';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm paper neutrals instead of the cool slate-grey every SaaS
        // dashboard reaches for by default. This replaces Tailwind's `gray`
        // wholesale, so every existing gray-* utility across the app shifts
        // in one place rather than needing a page-by-page rewrite.
        gray: colors.stone,
        // A deep signal-teal replaces the stock "Google blue" the console
        // was cloned in. Distinct from both the GCP console it emulates and
        // the generic indigo/terracotta defaults. Every blue-* utility
        // already used throughout the app picks this up automatically.
        blue: {
          50: '#EFFBFA',
          100: '#D7F3F1',
          200: '#AFE6E2',
          300: '#7DD4CE',
          400: '#4AB8B1',
          500: '#2A9D96',
          600: '#15807A',
          700: '#0F6560',
          800: '#0D4F4B',
          900: '#0A3B38',
        },
        primary: {
          DEFAULT: '#15807A',
          hover: '#0F6560',
          light: '#EFFBFA',
        },
        secondary: {
          DEFAULT: '#63635C',
          light: '#F0F0ED',
        },
        success: '#1e8e3e',
        warning: '#b45309',
        error: '#d93025',
        info: '#15807A',
        // The dark instrument rail (sidebar, console chrome) — a deliberate
        // near-black with a faint warm undertone, not a tinted #111 or pure
        // #000, and not reused as body text color.
        rail: {
          DEFAULT: '#181611',
          hover: '#242018',
          border: '#322D22',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
