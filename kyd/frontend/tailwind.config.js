/** Palette taken from the DataWorkflows.ai logo: navy #092a52, blue #008cea–#00a2fd, cyan #00bcff, teal #00ccc7.
 *  Colors are CSS variables (src/index.css) so the same classes render the dark and light themes. */
const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const scale = (name, steps = STEPS) => Object.fromEntries(steps.map(k => [k, `rgb(var(--${name}-${k}) / <alpha-value>)`]));

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // surfaces: the logo's navy, darkened for page backgrounds
        premium: scale('premium', [600, 700, 800, 900, 950]),
        // primary accent: the logo's blue-to-cyan; secondary accent: the logo's teal
        cyan: scale('cyan'),
        emerald: scale('emerald'),
        slate: scale('slate'),
        amber: scale('amber'),
        red: scale('red'),
        rose: scale('rose'),
        sky: scale('sky'),
        orange: scale('orange'),
      },
    },
  },
  plugins: [],
};
