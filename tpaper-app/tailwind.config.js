/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'Noto Sans SC', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'Roboto Mono', 'Consolas', 'monospace'],
      },
      colors: {
        // 映射 CSS 变量到 Tailwind 颜色，便于在 className 中使用
        primary: {
          DEFAULT: 'var(--color-primary)',
          light: 'var(--color-primary-light)',
          lighter: 'var(--color-primary-lighter)',
          dark: 'var(--color-primary-dark)',
          50: 'var(--color-primary-50)',
          100: 'var(--color-primary-100)',
          200: 'var(--color-primary-200)',
          300: 'var(--color-primary-300)',
          400: 'var(--color-primary-400)',
          500: 'var(--color-primary-500)',
          600: 'var(--color-primary-600)',
          700: 'var(--color-primary-700)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          light: 'var(--color-secondary-light)',
          lighter: 'var(--color-secondary-lighter)',
          dark: 'var(--color-secondary-dark)',
        },
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        float: 'var(--shadow-float)',
        card: 'var(--shadow-card)',
      },
      transitionTimingFunction: {
        md3: 'cubic-bezier(0.2, 0, 0, 1)',
      },
    },
  },
  plugins: [],
}
