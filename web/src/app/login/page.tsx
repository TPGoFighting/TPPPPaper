'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import BrandMark from '@/components/BrandMark';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('请填写账号和密码');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/login', { username, password }, { auth: false });
      setLoading(false);
      router.push('/admin');
    } catch (err) {
      setLoading(false);
      setError(err instanceof Error ? err.message : '登录失败');
    }
  };

  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[var(--color-bg-page)] px-4 py-8">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <BrandMark />
        </div>

        {/* 登录卡片 */}
        <div className="pixel-corners bg-[var(--color-bg)] shadow-md border border-[var(--color-border-light)] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-[var(--color-text-primary)] mb-1">
            欢迎回来
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] mb-6">
            登录以管理你的试卷资料
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 邮箱 */}
            <div>
              <label htmlFor="username" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
                管理员账号
              </label>
              <div className="relative">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  autoComplete="username"
                  className="tp-input pl-10 pr-3 py-2.5 text-sm placeholder:text-[var(--color-text-tertiary)]"
                />
              </div>
            </div>

            {/* 密码 */}
            <div>
              <label htmlFor="password" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
                密码
              </label>
              <div className="relative">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                  autoComplete="current-password"
                  className="tp-input pl-10 pr-11 py-2.5 text-sm placeholder:text-[var(--color-text-tertiary)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors"
                  aria-label="显示或隐藏密码"
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-error-text)] bg-[var(--color-error-bg)] rounded-[var(--radius-sm)]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="tp-button-primary w-full px-5 py-2.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg
                    className="animate-spin"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </button>
          </form>

          {/* 分隔线 */}
          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-[var(--color-border-light)]" />
            <span className="text-xs text-[var(--color-text-tertiary)]">或</span>
            <div className="flex-1 h-px bg-[var(--color-border-light)]" />
          </div>

          {/* 返回首页 */}
          <Link
            href="/"
            className="block text-center text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
          >
            返回首页
          </Link>
        </div>

        <p className="text-center text-xs text-[var(--color-text-tertiary)] mt-6">
          TPaper · AI 试卷转换工具
        </p>
      </div>
    </div>
  );
}
