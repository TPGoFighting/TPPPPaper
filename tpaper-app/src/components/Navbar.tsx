import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'

const navItems = [
  { to: '/admin', label: '管理首页', end: false },
  { to: '/upload', label: '上传资料', end: false },
  { to: '/models', label: '模型配置', end: false },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = window.location

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  const handleLogout = async () => {
    try {
      await logout()
    } catch {
      /* ignore */
    }
    navigate('/login')
  }

  return (
    <header
      className="sticky top-0 z-50 backdrop-blur-[var(--nav-blur)] border-b"
      style={{
        background: 'color-mix(in srgb, var(--color-bg) 88%, transparent)',
        borderColor: 'var(--color-border-light)',
      }}
    >
      <nav className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 flex items-center justify-between h-[var(--nav-height)]">
        <Logo />

        <div className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-link text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-[var(--color-text-primary)] nav-link-active'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-primary)]'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {user ? (
            <button
              type="button"
              onClick={handleLogout}
              className="hidden md:inline-flex items-center px-4 sm:px-5 py-2 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
            >
              登出
            </button>
          ) : (
            <NavLink
              to="/login"
              className="hidden md:inline-flex items-center px-4 sm:px-5 py-2 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
            >
              登录
            </NavLink>
          )}

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="切换菜单"
            aria-expanded={open}
            className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-[var(--radius-sm)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {open ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </nav>

      <div
        className={`md:hidden overflow-hidden transition-[max-height] duration-300 ease-md3 ${
          open ? 'max-h-96' : 'max-h-0'
        }`}
        style={{ background: 'var(--color-bg)' }}
      >
        <div className="px-4 py-3 flex flex-col gap-1 border-t border-[var(--color-border-light)]">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `px-3 py-3 min-h-[44px] flex items-center rounded-[var(--radius-sm)] text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-[var(--color-primary)] bg-[var(--color-primary-50)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          {user ? (
            <button
              type="button"
              onClick={handleLogout}
              className="px-3 py-3 min-h-[44px] flex items-center text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] rounded-[var(--radius-sm)] text-left"
            >
              登出
            </button>
          ) : (
            <NavLink
              to="/login"
              className="px-3 py-3 min-h-[44px] flex items-center text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-bg-hover)] rounded-[var(--radius-sm)]"
            >
              登录
            </NavLink>
          )}
        </div>
      </div>
    </header>
  )
}
