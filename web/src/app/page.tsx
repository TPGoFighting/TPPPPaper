import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-[100dvh] flex items-center justify-center bg-[var(--color-bg-page)] px-4">
      <div className="max-w-2xl w-full text-center anim-fade-in">
        <span className="inline-block px-3 py-1 text-xs font-semibold tracking-wide text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-full)] mb-6">
          AI 驱动
        </span>
        <h1 className="text-4xl md:text-5xl font-bold leading-[var(--leading-tight)] tracking-tight text-[var(--color-text-primary)]">
          让你的试卷
          <br />
          <span className="text-[var(--color-primary)]">活起来</span>
        </h1>
        <p className="mt-5 text-base md:text-lg text-[var(--color-text-secondary)] max-w-lg mx-auto leading-relaxed">
          上传 PDF、Word 等格式的试卷或复习资料，AI 自动转换为可交互的网页
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/admin"
            className="inline-flex items-center px-6 py-3 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
          >
            进入管理后台
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center px-6 py-3 text-sm font-semibold text-[var(--color-primary)] border border-[var(--color-border)] rounded-[var(--radius-full)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            登录
          </Link>
        </div>
      </div>
    </main>
  );
}
