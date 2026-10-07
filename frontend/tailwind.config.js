/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        spreego: {
          canvas: '#0B0D13',
          surface: '#12151E',
          elevated: '#1A1F2C',
          border: '#232938',
          'border-whisper': 'rgba(255, 255, 255, 0.08)',
          violet: '#7C3AED',
          'violet-light': '#8B5CF6',
          'violet-dark': '#6D28D9',
          champagne: '#F5D061',
          'champagne-light': '#FBE698',
          'text-primary': '#F9FAFB',
          'text-secondary': '#94A3B8',
          'text-tertiary': '#64748B',
          emerald: '#10B981',
          rose: '#EF4444',
        },
      },
      fontFamily: {
        display: ['Outfit', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        sans: ['Geist Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        card: '0 8px 32px 0 rgba(0, 0, 0, 0.36)',
        'violet-glow': '0 4px 20px -2px rgba(124, 58, 237, 0.35)',
        'champagne-glow': '0 4px 20px -2px rgba(245, 208, 97, 0.35)',
      },
      animation: {
        'spin-slow': 'spin 6s linear infinite',
      },
    },
  },
  plugins: [],
};
