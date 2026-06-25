/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './*.html',
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
      },
    },
  },
  plugins: [],
}
