import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Brand neon palette — refined medical
        neon: {
          green: '#4ADE80',
          'green-bright': '#6FF09A',
          cyan: '#4FC8F0',
          'cyan-bright': '#7AD9FF',
          teal: '#2DD4BF',
        },
        surface: {
          1: '#11151E',
          2: '#181D28',
          3: '#1C2230',
          4: '#232A38',
          5: '#2A3142',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl: 'calc(var(--radius) + 4px)',
        '2xl': 'calc(var(--radius) + 8px)',
      },
      boxShadow: {
        'neon': '0 0 18px -4px rgba(74, 222, 128, 0.50), 0 0 36px -8px rgba(74, 222, 128, 0.30)',
        'neon-cyan': '0 0 18px -4px rgba(79, 200, 240, 0.50), 0 0 36px -8px rgba(79, 200, 240, 0.30)',
        'neon-soft': '0 0 18px -6px rgba(74, 222, 128, 0.45)',
        'neon-cyan-soft': '0 0 18px -6px rgba(79, 200, 240, 0.45)',
        'glow-card': '0 18px 40px -18px rgba(0, 0, 0, 0.65), 0 0 28px -12px rgba(74, 222, 128, 0.30)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(110deg, #4ADE80 0%, #2DD4BF 50%, #4FC8F0 100%)',
        'brand-gradient-bright': 'linear-gradient(110deg, #6FF09A 0%, #2DD4BF 50%, #7AD9FF 100%)',
        'grid-dark':
          'linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid-48': '48px 48px',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '.6' },
        },
        'pulse-glow': {
          '0%, 100%': {
            boxShadow:
              '0 0 16px rgba(74, 222, 128, 0.30), 0 0 28px rgba(74, 222, 128, 0.15)',
          },
          '50%': {
            boxShadow:
              '0 0 22px rgba(74, 222, 128, 0.50), 0 0 40px rgba(74, 222, 128, 0.28)',
          },
        },
        'shimmer': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        float: 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse-slow 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
        shimmer: 'shimmer 2.4s linear infinite',
        'fade-in': 'fade-in 0.4s ease-out',
      },
    },
  },
  plugins: [],
}
export default config
