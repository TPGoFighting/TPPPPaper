import { Link } from 'react-router-dom'

export default function Logo({ height = 28 }: { height?: number }) {
  return (
    <Link
      to="/"
      className="flex items-center gap-1 select-none"
      aria-label="TPaper 首页"
      style={{ height }}
    >
      <svg
        width={height}
        height={height}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="32" height="32" rx="8" fill="url(#tp-logo-grad)" />
        <path
          d="M9 11.5h14M16 11.5v11M12.5 22.5h7"
          stroke="#fff"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <defs>
          <linearGradient
            id="tp-logo-grad"
            x1="0"
            y1="0"
            x2="32"
            y2="32"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#1a73e8" />
            <stop offset="1" stopColor="#34a853" />
          </linearGradient>
        </defs>
      </svg>
      <span
        className="text-2xl font-bold tracking-tight"
        style={{ color: 'var(--color-text-primary)' }}
      >
        TPaper
      </span>
    </Link>
  )
}
