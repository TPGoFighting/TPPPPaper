import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { paperService, draftService, publicationService } from '../api/services'
import type { Paper, Draft, Publication, PrecheckResult } from '../api/types'

export default function Publish() {
  const { paperId } = useParams<{ paperId: string }>()
  const [paper, setPaper] = useState<Paper | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [publications, setPublications] = useState<Publication[]>([])
  const [precheck, setPrecheck] = useState<PrecheckResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [withdrawing, setWithdrawing] = useState<number | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [device, setDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [showPubLink, setShowPubLink] = useState<string | null>(null)

  const DEVICE_W: Record<string, string> = { desktop: '100%', tablet: '768px', mobile: '375px' }

  const fetchData = async () => {
    const id = parseInt(paperId || '0', 10)
    if (!id) { setError('无效的资料 ID'); setLoading(false); return }
    try {
      const [p, pubs] = await Promise.all([
        paperService.get(id),
        publicationService.listByPaper(id),
      ])
      setPaper(p)
      setPublications(pubs)
      if (p.current_draft_id) {
        const d = await draftService.get(p.current_draft_id)
        setDraft(d)
      }
    } catch (e: any) { setError(e.message || '加载失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [paperId])

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3000)
  }

  const runPrecheck = async () => {
    if (!draft) return
    try {
      const r = await publicationService.precheck(draft.id)
      setPrecheck(r)
    } catch (e: any) { showToast('error', e.message || '预检失败') }
  }

  const handlePublish = async () => {
    if (!draft || !precheck?.can_publish) return
    setPublishing(true)
    try {
      const pub = await publicationService.publish(draft.id)
      showToast('success', '发布成功')
      setShowPubLink(`/p/${paper!.slug}`)
      setPublications([pub, ...publications])
      setPaper({ ...paper!, status: 'published', current_publication_id: pub.id })
    } catch (e: any) { showToast('error', e.message || '发布失败') }
    finally { setPublishing(false) }
  }

  const handleWithdraw = async (pubId: number) => {
    setWithdrawing(pubId)
    try {
      await publicationService.withdraw(pubId)
      showToast('success', '已撤回')
      setPublications(pubs => pubs.map(p => p.id === pubId ? { ...p, is_withdrawn: true } : p))
      fetchData()
    } catch (e: any) { showToast('error', e.message || '撤回失败') }
    finally { setWithdrawing(null) }
  }

  const previewDoc = draft
    ? `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${draft.theme_css}</style></head><body><div class="tp-publication">${draft.presentation_html}</div></body></html>`
    : ''

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (error) return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p className="text-[var(--color-error)] mb-4">{error}</p>
      <Link to="/admin" className="text-[var(--color-primary)] underline">返回管理首页</Link>
    </div>
  )
  if (!paper) return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p className="text-[var(--color-text-secondary)] mb-4">未找到资料</p>
      <Link to="/admin" className="text-[var(--color-primary)] underline">返回管理首页</Link>
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* 顶部 */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
          返回
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">{paper.title}</h1>
          <p className="text-sm text-[var(--color-text-tertiary)]">
            slug: {paper.slug} &middot; 状态: {paper.status}
            {draft && ` · 草稿 v${draft.version}`}
          </p>
        </div>
        {draft && (
          <Link to={`/editor/${paper.id}`} className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-full border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors">
            返回编辑
          </Link>
        )}
      </div>

      {showPubLink && (
        <div className="rounded-xl bg-green-50 border border-green-200 p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-green-800">发布成功</p>
            <p className="text-xs text-green-600">
              公开链接：<a href={showPubLink} target="_blank" rel="noopener noreferrer" className="underline">{window.location.origin}{showPubLink}</a>
            </p>
          </div>
          <button onClick={() => setShowPubLink(null)} className="text-green-600 hover:text-green-800 text-sm">关闭</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：预检 */}
        <div className="space-y-4">
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-[var(--color-text-primary)]">发布前检查</h2>
              <button onClick={runPrecheck} className="px-3 py-1.5 text-sm font-medium rounded-full bg-[var(--color-primary)] text-white hover:opacity-90 transition-colors">
                运行检查
              </button>
            </div>
            {!precheck ? (
              <p className="text-sm text-[var(--color-text-tertiary)]">点击"运行检查"进行发布前验证</p>
            ) : (
              <div className="space-y-3">
                <div className={`flex items-center gap-2 p-3 rounded-lg ${precheck.can_publish ? 'bg-green-50' : 'bg-red-50'}`}>
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${precheck.can_publish ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}`}>
                    {precheck.can_publish ? '✓' : '✗'}
                  </span>
                  <span className={`text-sm font-medium ${precheck.can_publish ? 'text-green-700' : 'text-red-700'}`}>
                    {precheck.can_publish ? '可以发布' : '存在阻塞问题'}
                  </span>
                </div>
                {precheck.issues.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[var(--color-text-tertiary)]">检查结果：</p>
                    {precheck.issues.map((issue, i) => (
                      <div key={i} className={`text-xs px-3 py-1.5 rounded-lg ${
                        issue.includes('错误') || issue.includes('缺少') || issue.includes('必须')
                          ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                      }`}>{issue}</div>
                    ))}
                  </div>
                )}
                {precheck.removed.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[var(--color-text-tertiary)]">被移除的不安全内容：</p>
                    {precheck.removed.map((item, i) => (
                      <div key={i} className="text-xs px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 font-mono">{item}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 发布按钮 */}
          <button onClick={handlePublish}
            disabled={!precheck?.can_publish || publishing}
            className={`w-full py-3 rounded-xl font-semibold text-white transition-all ${
              precheck?.can_publish ? 'bg-green-600 hover:bg-green-700 active:scale-[0.98]' : 'bg-gray-400 cursor-not-allowed'
            }`}>
            {publishing ? '发布中...' : precheck?.can_publish ? '确认发布' : '请先通过检查'}
          </button>
        </div>

        {/* 右侧：预览 */}
        <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">预览</h3>
            <div className="flex gap-1">
              {Object.entries(DEVICE_W).map(([k]) => (
                <button key={k} onClick={() => setDevice(k as typeof device)}
                  className={`px-2 py-1 text-xs rounded-lg transition-colors ${device === k ? 'bg-[var(--color-primary)] text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'}`}>
                  {k === 'desktop' ? '桌面' : k === 'tablet' ? '平板' : '手机'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-center p-2 bg-[var(--color-bg-page)]">
            <iframe srcDoc={previewDoc} style={{ width: DEVICE_W[device], height: '500px' }}
              className="border border-[var(--color-border)] rounded-lg bg-white shadow-sm" title="预览" />
          </div>
        </div>
      </div>

      {/* 发布历史 */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-4">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-3">发布历史</h2>
        {publications.length === 0 ? (
          <p className="text-sm text-[var(--color-text-tertiary)]">暂无发布版本</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[var(--color-text-tertiary)] border-b border-[var(--color-border)]">
                  <th className="pb-2 font-medium">版本</th>
                  <th className="pb-2 font-medium">发布时间</th>
                  <th className="pb-2 font-medium">内容哈希</th>
                  <th className="pb-2 font-medium">发布者</th>
                  <th className="pb-2 font-medium">状态</th>
                  <th className="pb-2 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {publications.map(pub => (
                  <tr key={pub.id} className={`border-b border-[var(--color-border)] ${paper.current_publication_id === pub.id ? 'bg-blue-50/50' : ''}`}>
                    <td className="py-2.5">
                      <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-[var(--color-bg-hover)]">v{pub.version}</span>
                      {paper.current_publication_id === pub.id && <span className="ml-1.5 text-xs text-[var(--color-primary)]">当前</span>}
                    </td>
                    <td className="py-2.5 text-[var(--color-text-secondary)]">{new Date(pub.published_at).toLocaleString('zh-CN')}</td>
                    <td className="py-2.5 text-[var(--color-text-tertiary)] font-mono text-xs">{pub.content_hash.slice(0, 12)}</td>
                    <td className="py-2.5 text-[var(--color-text-secondary)]">{pub.published_by}</td>
                    <td className="py-2.5">
                      {pub.is_withdrawn
                        ? <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">已撤回</span>
                        : <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">活跃</span>
                      }
                    </td>
                    <td className="py-2.5 text-right">
                      {!pub.is_withdrawn && (
                        <button onClick={() => handleWithdraw(pub.id)}
                          disabled={withdrawing === pub.id}
                          className="text-xs text-red-600 hover:text-red-800 disabled:opacity-50">
                          {withdrawing === pub.id ? '撤回中...' : '撤回'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}