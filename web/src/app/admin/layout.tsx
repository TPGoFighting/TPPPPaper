'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import BrandMark from '@/components/BrandMark';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-[100dvh] bg-[var(--color-bg-page)]">
      <Navbar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <header
          className="sticky top-0 z-30 backdrop-blur-[var(--nav-blur)] border-b md:hidden"
          style={{
            background: 'color-mix(in srgb, var(--color-bg) 88%, transparent)',
            borderColor: 'var(--color-border-light)',
          }}
        >
          <div className="flex items-center justify-between h-[var(--nav-height)] px-4">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="打开菜单"
              className="inline-flex items-center justify-center w-10 h-10 rounded-[var(--radius-sm)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <BrandMark href="/admin" compact />
            <div className="w-10" />
          </div>
        </header>

        {/* 主内容 */}
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
