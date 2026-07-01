import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { jobService, paperService } from '../api/services'
import { useApi } from '../hooks/useApi'
import type { Job, PaperStatus, JobStatus } from '../api/types'

const STAGES = [
  { key: 'preprocessing', label: '预处理' },
  { key: 'extracting', label: '来源提取' },
  { key: 'generating_document', label: '生成文档' },
  { key: 'generating_presentation', label: '生成网页' },
  { key: 'sanitizing', label: '净化' },
  { key: 'done', label: '完成' },
]

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

const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '已失败',
  cancelled: '已取消',
}

function pickLatestJob(jobs: Job[] | null): Job | null {
  if (!jobs || jobs.length === 0) return null
  return [...jobs].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0]
}
export default function TaskProgress() {
  const { paperId } = useParams<{ paperId: string }>()
  const navigate = useNavigate()
  const id = Number(paperId)

  const { data: jobs, error: jobsError, refetch } = useApi(
    () => jobService.listByPaper(id),
    [id],
    { pollInterval: 2000 }
  )
  const { data: paper } = useApi(
    () => paperService.get(id),
    [id],
    { pollInterval: 2000 }
  )

  const [retrying, setRetrying] = useState(false)
  const latestJob = pickLatestJob(jobs)

  const handleRetry = async () => {
    if (!latestJob) return
    setRetrying(true)
    try {
      await jobService.retry(latestJob.id)
      await refetch()
    } catch {
      setRetrying(false)
    } finally {
      setRetrying(false)
    }
  }

  const currentStageIndex = latestJob ? STAGES.findIndex((s) => s.key === latestJob.stage) : -1
  const isFailed = latestJob?.status === 'failed'
  const isSucceeded = latestJob?.status === 'succeeded'
  return (
    <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 py-6 sm:py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">
          {paper?.title || '任务进度'}
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          资料状态：{paper ? STATUS_LABELS[paper.status] : '加载中…'}
        </p>
      </div>

      {jobsError && (
        <div className="mb-4 px-4 py-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error-text)] text-sm">{jobsError}</div>
      )}

      {!latestJob ? (
        <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-12 text-center text-[var(--color-text-secondary)] text-sm">
          等待任务启动…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 sm:p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-5">处理阶段</h2>            <ol className="space-y-1">
              {STAGES.map((s, i) => {
                const done = i < currentStageIndex
                const active = i === currentStageIndex && !isFailed
                const failed = i === currentStageIndex && isFailed
                return (
                  <li key={s.key} className="flex items-center gap-3 py-2">
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                      done ? 'bg-[var(--color-success-bg)] text-[var(--color-success-text)]' :
                      active ? 'bg-[var(--color-primary)] text-white' :
                      failed ? 'bg-[var(--color-error-bg)] text-[var(--color-error-text)]' :
                      'bg-[var(--color-bg-subtle)] text-[var(--color-text-tertiary)]'
                    }`}>
                      {done ? '✓' : active ? <span className="animate-pulse">●</span> : failed ? '!' : i + 1}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${active ? 'text-[var(--color-primary)]' : failed ? 'text-[var(--color-error-text)]' : 'text-[var(--color-text-primary)]'}`}>{s.label}</div>
                      {active && s.key === 'extracting' && latestJob.total_pages > 0 && (
                        <div className="text-xs text-[var(--color-text-secondary)]">第 {latestJob.current_page} / {latestJob.total_pages} 页</div>
                      )}
                    </div>
                  </li>
                )
              })}
            </ol>

            {latestJob.stage === 'extracting' && latestJob.total_pages > 0 && (
              <div className="mt-4">
                <div className="h-1.5 rounded-full bg-[var(--color-bg-subtle)] overflow-hidden">
                  <div className="h-full bg-[var(--color-primary)] transition-all" style={{ width: `${Math.min(100, (latestJob.current_page / latestJob.total_pages) * 100)}%` }} />
                </div>
              </div>
            )}

            {isFailed && latestJob.error_message && (
              <div className="mt-5 px-4 py-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error-text)] text-sm">
                <div className="font-medium mb-1">处理失败</div>
                <div className="text-xs break-words">{latestJob.error_message}</div>
                {latestJob.error_code && <div className="text-xs mt-1 opacity-75">错误码：{latestJob.error_code}</div>}
              </div>
            )}
          </div>
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5">
              <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">任务详情</h2>
              <dl className="space-y-2.5 text-sm">
                <div className="flex justify-between"><dt className="text-[var(--color-text-secondary)]">任务状态</dt><dd className="font-medium text-[var(--color-text-primary)]">{JOB_STATUS_LABELS[latestJob.status]}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-secondary)]">当前页</dt><dd className="text-[var(--color-text-primary)]">{latestJob.current_page} / {latestJob.total_pages || '-'}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-secondary)]">已完成</dt><dd className="text-[var(--color-text-primary)]">{Math.max(0, latestJob.current_page - 1)}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-secondary)]">失败页</dt><dd className="text-[var(--color-text-primary)]">{latestJob.failed_pages.length}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-secondary)]">重试次数</dt><dd className="text-[var(--color-text-primary)]">{latestJob.retry_count}</dd></div>
              </dl>
            </div>

            <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 space-y-3">
              {isFailed && (
                <button onClick={handleRetry} disabled={retrying} className="w-full py-2.5 rounded-[var(--radius-full)] bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-60 transition">
                  {retrying ? '重试中…' : '重试任务'}
                </button>
              )}
              {isSucceeded && paper?.status === 'pending_review' && (
                <button onClick={() => navigate(`/editor/${id}`)} className="w-full py-2.5 rounded-[var(--radius-full)] bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 transition">进入审核</button>
              )}
              {isSucceeded && paper?.status === 'published' && (
                <button onClick={() => navigate(`/publish/${id}`)} className="w-full py-2.5 rounded-[var(--radius-full)] bg-[var(--color-success)] text-white text-sm font-medium hover:opacity-90 transition">查看公开页</button>
              )}
              <button onClick={() => navigate('/admin')} className="w-full py-2.5 rounded-[var(--radius-full)] bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] text-sm font-medium hover:bg-[var(--color-bg-hover)] transition">返回管理</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}