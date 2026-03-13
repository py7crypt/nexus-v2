/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Use these via className="font-display" or className="font-body"
        // Fonts are loaded via vite.config.js HTML injection — no @import needed
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        body:    ['Poppins', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#1E73FF',
          dark:    '#1558cc',
          light:   '#e8f0ff',
        },
        cat: {
          tech:          '#1E73FF',
          science:       '#7C3AED',
          business:      '#059669',
          health:        '#DC2626',
          lifestyle:     '#D97706',
          travel:        '#0891B2',
          entertainment: '#DB2777',
        },
      },
    },
  },
  plugins: [],
}