import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        cs: {
          navy: "#1b213c",      // dark navy used for text / headings
          mint: "#e6faf4",      // light mint background (banner)
          accent: "#00395c",    // link / accent color similar to schedule page
        },
      },
      fontFamily: {
        sans: ["Lato", "sans-serif"],
        heading: ["Merriweather", "serif"],
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: '100%',
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
} satisfies Config;
