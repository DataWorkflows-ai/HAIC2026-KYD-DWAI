/** Palette taken from the DataWorkflows.ai logo: navy #092a52, blue #008cea–#00a2fd, cyan #00bcff, teal #00ccc7. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // surfaces: the logo's navy, darkened for page backgrounds
        premium: { 950: '#050f1d', 900: '#081a30', 800: '#0d2745', 700: '#17406b', 600: '#24598f' },
        // primary accent: the logo's blue-to-cyan
        cyan: { 50: '#e6f8ff', 100: '#c7efff', 200: '#99e2ff', 300: '#5cd2ff', 400: '#00bcff', 500: '#00a2fd', 600: '#008cea', 700: '#0070c0', 800: '#005090', 900: '#003a70', 950: '#052b58' },
        // secondary accent: the logo's teal
        emerald: { 50: '#e6fbfa', 100: '#c2f5f3', 200: '#8eece9', 300: '#4fe0dc', 400: '#00ccc7', 500: '#00b3ae', 600: '#009490', 700: '#007673', 800: '#005e5c', 900: '#004d4b', 950: '#002e2d' },
      },
    },
  },
  plugins: [],
};
