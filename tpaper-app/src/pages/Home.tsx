import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const features = [
  {
    title: '智能解析',
    desc: 'AI 自动识别试卷中的题目、选项、答案区域，精准提取每一道题目，无需手动排版。',
  },
  {
    title: '可交互展示',
    desc: '转换后的试卷支持在线作答、实时判分、答案解析，体验远超纸质试卷。',
  },
  {
    title: '模型自定义',
    desc: '灵活配置 OpenAI 兼容模型、并发与重试策略，满足不同教学场景需求。',
  },
]

const steps = [
  { num: 1, title: '上传文件', desc: '支持 PDF、Word、图片等格式，拖拽即可上传。', color: '#1a73e8' },
  { num: 2, title: 'AI 转换', desc: 'AI 自动解析内容，生成可交互的网页试卷。', color: '#ea4335' },
  { num: 3, title: '在线使用', desc: '在线作答、查看解析、分享给同学。', color: '#34a853' },
]

export default function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/admin" replace />

  return (
    <>
      <section className="min-h-[calc(100dvh-var(--nav-height))] pt-12 pb-16 bg-[var(--color-bg-page)]">
        <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 h-full flex items-center">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-10 lg:gap-16 items-center w-full">
            <div className="lg:col-span-3">
              <span className="inline-block px-3 py-1 text-xs font-semibold tracking-wide text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-full)] mb-6">
                AI 驱动
              </span>
              <h1 className="text-4xl md:text-5xl lg:text-[3.25rem] font-bold leading-[var(--leading-tight)] tracking-tight text-[var(--color-text-primary)]">
                让你的试卷
                <br />
                <span className="text-[var(--color-primary)]">活起来</span>
              </h1>
              <p className="mt-5 text-base md:text-lg text-[var(--color-text-secondary)] max-w-lg leading-relaxed">
                上传 PDF、Word 等格式的试卷或复习资料，AI 自动转换为可交互的网页。
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  to="/login"
                  className="inline-flex items-center px-6 py-3 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
                >
                  登录开始使用
                </Link>
                <a
                  href="#features"
                  className="inline-flex items-center px-6 py-3 text-sm font-semibold text-[var(--color-primary)] border border-[var(--color-border)] rounded-[var(--radius-full)] hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  查看特性
                </a>
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="aspect-[4/3] w-full rounded-[var(--radius-lg)] shadow-[var(--shadow-lg)] bg-gradient-to-br from-[var(--color-primary-50)] to-[var(--color-success-50)] flex items-center justify-center">
                <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="8" y1="13" x2="16" y2="13" />
                  <line x1="8" y1="17" x2="13" y2="17" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-20 md:py-28 bg-[var(--color-bg)]">
        <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-[var(--color-text-primary)]">
            为什么选择 TPaper
          </h2>
          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((f) => (
              <article
                key={f.title}
                className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-md)] shadow-[var(--shadow-sm)] p-6 hover:shadow-[var(--shadow-md)] transition-shadow"
              >
                <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">{f.title}</h3>
                <p className="mt-2 text-[var(--color-text-secondary)] leading-relaxed text-sm">{f.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 md:py-28 bg-[var(--color-bg-page)]">
        <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-[var(--color-text-primary)]">
            使用流程
          </h2>
          <ol className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-6 relative list-none p-0">
            <div
              className="hidden md:block absolute top-6 left-[calc(16.67%+1rem)] right-[calc(16.67%+1rem)] border-t-2 border-dashed border-[var(--color-border)]"
              aria-hidden="true"
            />
            {steps.map((s) => (
              <li key={s.num} className="flex flex-col items-center text-center">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-[var(--color-text-inverse)] font-bold text-lg shrink-0"
                  style={{ background: s.color }}
                >
                  {s.num}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-[var(--color-text-primary)]">{s.title}</h3>
                <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{s.desc}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </>
  )
}
