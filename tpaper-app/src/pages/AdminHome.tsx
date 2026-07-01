import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { paperService, publicationService } from '../api/services'
import { useApi } from '../hooks/useApi'
import type { Paper, PaperStatus, SourceFile } from '../api/types'

interface PaperWithSource extends Paper {
  source_file?: SourceFile | null
}

const STATUS_LABELS: Record<PaperStatus, string> = {
  uploading: '上传中',
  queued: '排队中',
  parsing: '解析中',
  modeling: '模型处理中',
  pending_review: '待审核',
  published: '已发布',
  partial_failed: '部分失败',
  failed: '失败',
}

const STATUS_STYLES: Record<PaperStatus, string> = {
  uploading: 'bg-[var(--color-info-bg)] text-[var(--color-info-text)]',
  queued: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]',
  parsing: 'bg-[var(--color-warning-bg)] text-[var(--color-warning-text)]',
  modeling: 'bg-[var(--color-warning-bg)] text-[var(--color-warning-text)]',
  pending_review: 'bg-[var(--color-warning-bg)] text-[var(--color-warning-text)]',
  published: 'bg-[var(--color-success-bg)] text-[var(--color-success-text)]',
  partial_failed: 'bg-[var(--color-warning-bg)] text-[var(--color-warning-text)]',
  failed: 'bg-[var(--color-error-bg)] text-[var(--color-error-text)]',
}
const MODE_LABELS: Record<Paper['mode'], string> = {
  faithful_transcription: '忠实转写',
  lecture_to_quiz: '讲义出题',
}

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'uploading', label: '上传中' },
  { value: 'queued', label: '排队中' },
  { value: 'parsing', label: '解析中' },
  { value: 'modeling', label: '模型处理中' },
  { value: 'pending_review', label: '待审核' },
  { value: 'published', label: '已发布' },
  { value: 'failed', label: '失败' },
  { value: 'partial_failed', label: '部分失败' },
]

const BTN_PRIMARY = 'px-3 py-1.5 rounded-[var(--radius-full)] text-xs font-medium bg-[var(--color-primary)] text-white hover:opacity-90 disabled:opacity-60 transition'
const BTN_GHOST = 'px-3 py-1.5 rounded-[var(--radius-full)] text-xs font-medium bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-60 transition'
const BTN_DANGER = 'px-3 py-1.5 rounded-[var(--radius-full)] text-xs font-medium text-[var(--color-error-text)] hover:bg-[var(--color-error-bg)] disabled:opacity-60 transition'

function formatTime(iso: string): string {
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前`
  return d.toLocaleDateString('zh-CN')
}

function formatCountdown(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now()
  if (diff <= 0) return '即将删除'
  const hr = Math.floor(diff / 3600000)
  const min = Math.floor((diff % 3600000) / 60000)
  if (hr > 0) return `${hr}小时${min}分后删除`
  return `${min}分钟后删除`
}

export default function AdminHome() {
  const [statusFilter, setStatusFilter] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [actionError, setActionError] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchInput.trim()), 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const { data: papers, loading, error, refetch } = useApi<PaperWithSource[]>(
    () => paperService.list({ status: statusFilter || undefined, q: debouncedQ || undefined }) as Promise<PaperWithSource[]>,
    [statusFilter, debouncedQ]
  )

  const list = papers ?? []

  const handleReprocess = async (id: number) => {
    setActionError('')
    setBusyId(id)
    try {
      await paperService.reprocess(id)
      await refetch()
    } catch (e: any) {
      setActionError(e.message || '重新解析失败')
    } finally {
      setBusyId(null)
    }
  }

  const handleWithdraw = async (p: Paper) => {
    if (!p.current_publication_id) return
    if (!window.confirm('确定撤回该发布版本？')) return
    setActionError('')
    setBusyId(p.id)
    try {
      await publicationService.withdraw(p.current_publication_id)
      await refetch()
    } catch (e: any) {
      setActionError(e.message || '撤回失败')
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (p: Paper) => {
    if (!window.confirm(`确定删除「${p.title}」？此操作不可恢复。`)) return
    setActionError('')
    setBusyId(p.id)
    try {
      await paperService.delete(p.id)
      await refetch()
    } catch (e: any) {
      setActionError(e.message || '删除失败')
    } finally {
      setBusyId(null)
    }
  }
  return (
    <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 py-6 sm:py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">资料管理</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">查看、审核与管理所有上传的资料</p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-[var(--radius-full)] bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 transition self-start sm:self-auto"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          上传新资料
        </button>
      </div>

      <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-4 sm:p-5 mb-6 space-y-4">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="按标题搜索…"
            className="w-full pl-10 pr-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-lighter)] transition"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3.5 py-1.5 rounded-[var(--radius-full)] text-xs font-medium transition ${
                statusFilter === f.value
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {(actionError || error) && (
        <div className="mb-4 px-4 py-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error-text)] text-sm">
          {actionError || error}
        </div>
      )}

      {loading && list.length === 0 ? (
        <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-12 text-center text-[var(--color-text-secondary)] text-sm">
          加载中…
        </div>
      ) : list.length === 0 ? (
        <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-12 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[var(--color-bg-subtle)] mb-3">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm">暂无资料</p>
          <button onClick={() => navigate('/upload')} className="mt-4 text-sm text-[var(--color-primary)] font-medium hover:underline">
            去上传第一份资料
          </button>
        </div>
      ) : (        <>
          <div className="hidden md:block bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-light)] text-left text-[var(--color-text-secondary)]">
                  <th className="px-5 py-3 font-medium">标题</th>
                  <th className="px-5 py-3 font-medium">类型</th>
                  <th className="px-5 py-3 font-medium">状态</th>
                  <th className="px-5 py-3 font-medium">更新时间</th>
                  <th className="px-5 py-3 font-medium">公开链接</th>
                  <th className="px-5 py-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {list.map((p) => (
                  <tr key={p.id} className="border-b border-[var(--color-border-light)] last:border-0 hover:bg-[var(--color-bg-subtle)] transition">
                    <td className="px-5 py-4">
                      <div className="font-medium text-[var(--color-text-primary)]">{p.title}</div>
                      {p.source_file?.expires_at && !p.source_file.deleted_at && (
                        <div className="text-xs text-[var(--color-warning-text)] mt-0.5">
                          ⏳ 源文件 {formatCountdown(p.source_file.expires_at)}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4 text-[var(--color-text-secondary)]">{MODE_LABELS[p.mode]}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-block px-2.5 py-1 rounded-[var(--radius-full)] text-xs font-medium ${STATUS_STYLES[p.status]}`}>
                        {STATUS_LABELS[p.status]}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-[var(--color-text-secondary)] whitespace-nowrap">{formatTime(p.updated_at)}</td>
                    <td className="px-5 py-4">
                      {p.status === 'published' ? (
                        <a href={`/p/${p.slug}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[var(--color-primary)] hover:underline">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                            <polyline points="15 3 21 3 21 9" />
                            <line x1="10" y1="14" x2="21" y2="3" />
                          </svg>
                          查看
                        </a>
                      ) : (
                        <span className="text-[var(--color-text-tertiary)]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {p.status === 'pending_review' && (
                          <button onClick={() => navigate(`/editor/${p.id}`)} className={BTN_PRIMARY}>打开草稿</button>
                        )}
                        {p.status === 'published' && (
                          <>
                            <button onClick={() => navigate(`/publish/${p.id}`)} className={BTN_GHOST}>查看版本</button>
                            <button onClick={() => handleWithdraw(p)} disabled={busyId === p.id} className={BTN_GHOST}>撤回</button>
                          </>
                        )}
                        {(p.status === 'failed' || p.status === 'partial_failed') && (
                          <button onClick={() => handleReprocess(p.id)} disabled={busyId === p.id} className={BTN_PRIMARY}>重新解析</button>
                        )}
                        <button onClick={() => handleDelete(p)} disabled={busyId === p.id} className={BTN_DANGER}>删除</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="md:hidden space-y-3">
            {list.map((p) => (
              <div key={p.id} className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="min-w-0">
                    <div className="font-medium text-[var(--color-text-primary)] truncate">{p.title}</div>
                    <div className="text-xs text-[var(--color-text-tertiary)] mt-0.5">{MODE_LABELS[p.mode]} · {formatTime(p.updated_at)}</div>
                  </div>
                  <span className={`flex-shrink-0 inline-block px-2.5 py-1 rounded-[var(--radius-full)] text-xs font-medium ${STATUS_STYLES[p.status]}`}>
                    {STATUS_LABELS[p.status]}
                  </span>
                </div>
                {p.source_file?.expires_at && !p.source_file.deleted_at && (
                  <div className="text-xs text-[var(--color-warning-text)] mb-2">⏳ 源文件 {formatCountdown(p.source_file.expires_at)}</div>
                )}
                <div className="flex flex-wrap gap-2 pt-2 border-t border-[var(--color-border-light)]">
                  {p.status === 'pending_review' && (
                    <button onClick={() => navigate(`/editor/${p.id}`)} className={BTN_PRIMARY}>打开草稿</button>
                  )}
                  {p.status === 'published' && (
                    <>
                      <button onClick={() => navigate(`/publish/${p.id}`)} className={BTN_GHOST}>查看版本</button>
                      <button onClick={() => handleWithdraw(p)} disabled={busyId === p.id} className={BTN_GHOST}>撤回</button>
                    </>
                  )}
                  {(p.status === 'failed' || p.status === 'partial_failed') && (
                    <button onClick={() => handleReprocess(p.id)} disabled={busyId === p.id} className={BTN_PRIMARY}>重新解析</button>
                  )}
                  <button onClick={() => handleDelete(p)} disabled={busyId === p.id} className={BTN_DANGER}>删除</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}