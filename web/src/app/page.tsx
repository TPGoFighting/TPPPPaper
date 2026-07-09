import Link from 'next/link';
import BrandMark from '@/components/BrandMark';

export default function HomePage() {
  return (
    <main className="min-h-[100dvh] overflow-hidden px-4 py-6">
      <div className="mx-auto flex min-h-[calc(100dvh-48px)] max-w-6xl flex-col">
        <header className="flex items-center justify-between">
          <BrandMark />
          <Link
            href="/login"
            className="tp-button-secondary px-4 py-2 text-sm"
          >
            登录
          </Link>
        </header>

        <section className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[1fr_420px]">
          <div className="anim-fade-in">
            <span className="pixel-corners inline-flex border border-[var(--color-primary)] bg-[var(--color-primary-50)] px-3 py-1 font-mono text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-primary)]">
              AI PAPER ENGINE
            </span>
            <h1 className="mt-7 max-w-3xl text-5xl font-black leading-[0.98] text-[var(--color-text-primary)] md:text-7xl">
              TPaper
              <span className="block bg-[var(--gradient-text)] bg-clip-text text-transparent">
                turns papers into live pages.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-[var(--color-text-secondary)] md:text-lg">
              上传 PDF、Word 或图片资料，后端解析、生成题目结构，再发布成可交互网页。黑白底色、红色动势、网格界面，给传统试卷一个更酷的工作台。
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/admin"
                className="tp-button-primary px-6 py-3 text-sm"
              >
                进入管理后台
              </Link>
              <Link
                href="/admin/upload"
                className="tp-button-secondary px-6 py-3 text-sm"
              >
                上传资料
              </Link>
            </div>
          </div>

          <div className="pixel-corners border border-[var(--color-border-light)] bg-black/50 p-5 shadow-[var(--shadow-float)]">
            <div className="grid grid-cols-4 gap-2">
              {Array.from({ length: 24 }).map((_, index) => (
                <span
                  key={index}
                  className={`aspect-square border ${
                    index % 7 === 0
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary)] shadow-[var(--shadow-glow-primary)]'
                      : index % 5 === 0
                        ? 'border-[var(--color-secondary)] bg-[var(--color-secondary)]/20'
                        : 'border-[var(--color-border)] bg-[var(--color-bg-elevated)]'
                  }`}
                />
              ))}
            </div>
            <div className="mt-5 border border-[var(--color-border)] bg-[var(--color-bg)] p-4">
              <div className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--color-primary)]">
                pipeline
              </div>
              <div className="mt-3 grid gap-2 text-sm text-[var(--color-text-secondary)]">
                <span>01 upload source</span>
                <span>02 parse with LongCat</span>
                <span>03 review draft</span>
                <span>04 publish interactive page</span>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-3 pb-8 text-xs text-[var(--color-text-tertiary)] sm:grid-cols-3">
          <span className="border-t border-[var(--color-border)] pt-3">FastAPI backend</span>
          <span className="border-t border-[var(--color-border)] pt-3">SQLite/Postgres ready</span>
          <span className="border-t border-[var(--color-border)] pt-3">Pixel grid UI</span>
        </div>
      </div>
    </main>
  );
}
