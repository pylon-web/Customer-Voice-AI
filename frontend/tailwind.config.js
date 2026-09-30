/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        c1: {
          red: {
            DEFAULT: '#D03027',
            light: '#FCE8E7',
            hover: '#B81D24',
            dark: '#91161C',
          },
          navy: {
            DEFAULT: '#004879',
            dark: '#0B2341',
            darker: '#071527',
            deep: '#040E1B',
            light: '#0076BE',
          },
          blue: {
            DEFAULT: '#004879',
            accent: '#0099D8',
            hover: '#00629B',
          },
          slate: {
            bg: '#06101E',
            card: '#0B1E36',
            cardHover: '#0F2644',
            border: '#1B365D',
            borderHover: '#2A4E80',
          },
          gold: '#C29B38',
          bronze: '#A35C2B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', '-apple-system', 'BlinkMacSystemFont', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
