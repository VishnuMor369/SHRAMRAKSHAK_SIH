/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        safety: {
          green: '#10B981',
          emerald: '#059669',
          amber: '#F59E0B',
          red: '#EF4444',
          crimson: '#DC2626',
          dark: '#0F172A',
          slate: '#1E293B',
          light: '#F8FAFC'
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
      }
    },
  },
  plugins: [],
}
