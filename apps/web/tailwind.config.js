/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#FFF9F1",
          100: "#FDEBD0",
          200: "#FCD9C0",
          500: "#F97316",
          600: "#E54416",
          700: "#C73D0F",
        },
      },
    },
  },
  plugins: [],
};
