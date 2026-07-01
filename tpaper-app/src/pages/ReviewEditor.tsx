import { useState, useEffect, useMemo, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { paperService, draftService } from '../api/services'
import type { Paper, Draft, Question, QuestionType, PaperDocument } from '../api/types'

const TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: '单选题', multi_choice: '多选题', true_false: '判断题',
  fill_blank: '填空题', subjective: '主观题',
}
const DEVICE_WIDTHS: Record<string, string> = { desktop: '100%', tablet: '768px', mobile: '375px' }

function newQuestion(n: number): Question {
  return {
    id: `q_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`, number: n,
    type: 'single_choice', stem: '', media: [], score: 5,
    options: [{ key: 'A', text: '' }, { key: 'B', text: '' }, { key: 'C', text: '' }, { key: 'D', text: '' }],
    correct_keys: [], true_false_answer: null, acceptable_answers: [], match_rule: 'exact',
    reference_answer: '', scoring_points: [], explanation: '', knowledge_points: [],
    confidence: 1.0, needs_review: false, is_ai_generated: false,
  }
}

export default function ReviewEditor() {
  const { paperId } = useParams<{ paperId: string }>()
  const navigate = useNavigate()
  const [paper, setPaper] = useState<Paper | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'questions' | 'htmlcss' | 'preview'>('questions')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [device, setDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [htmlEd, setHtmlEd] = useState('')
  const [cssEd, setCssEd] = useState('')
  const [aiOpen, setAiOpen] = useState(false)
  const [aiQid, setAiQid] = useState<string | null>(null)
  const [aiInstr, setAiInstr] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; msg: string } | null>(null)
  const qRefs = useRef<Record<string, HTMLDivElement | null>>({})

  useEffect(() => {
    const id = parseInt(paperId || '0', 10)
    if (!id) { setError('无效的资料 ID'); setLoading(false); return }
    ;(async () => {
      try {
        const p = await paperService.get(id)
        setPaper(p)
        if (p.current_draft_id) {
          const d = await draftService.get(p.current_draft_id)
          setDraft(d); setHtmlEd(d.presentation_html); setCssEd(d.theme_css)
        }
      } catch (e: any) { setError(e.message || '加载失败') }
      finally { setLoading(false) }
    })()
  }, [paperId])

  const showToast = (type: 'success' | 'error' | 'info', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3000)
  }

  const previewDoc = useMemo(() =>
    `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${cssEd}</style></head><body>${htmlEd}</body></html>`,
    [htmlEd, cssEd]
  )

  const updateDoc = (updater: (doc: PaperDocument) => PaperDocument) => {
    if (!draft) return
    setDraft({ ...draft, document: updater(draft.document) })
    setDirty(true)
  }
  const updateQ = (qid: string, patch: Partial<Question>) =>
    updateDoc(doc => ({ ...doc, questions: doc.questions.map(q => q.id === qid ? { ...q, ...patch } : q) }))
  const deleteQ = (qid: string) => {
    updateDoc(doc => ({
      ...doc,
      questions: doc.questions.filter(q => q.id !== qid),
      sections: doc.sections.map(s => ({ ...s, question_ids: s.question_ids.filter(id => id !== qid) })),
    }))
    if (expandedId === qid) setExpandedId(null)
  }
  const dupQ = (qid: string) => {
    if (!draft) return
    const q = draft.document.questions.find(q => q.id === qid)
    if (!q) return
    const copy = { ...q, id: `q_${Date.now()}_${Math.random().toString(36).slice(2, 8)}` }
    const idx = draft.document.questions.findIndex(q => q.id === qid)
    updateDoc(doc => ({ ...doc, questions: [...doc.questions.slice(0, idx + 1), copy, ...doc.questions.slice(idx + 1)] }))
  }
  const moveQ = (qid: string, dir: -1 | 1) => {
    if (!draft) return
    const qs = [...draft.document.questions]
    const idx = qs.findIndex(q => q.id === qid)
    const ni = idx + dir
    if (ni < 0 || ni >= qs.length) return
    const tmp = qs[idx]; qs[idx] = qs[ni]; qs[ni] = tmp
    updateDoc(doc => ({ ...doc, questions: qs }))
  }
  const insertQ = (afterId?: string) => {
    const q = newQuestion((draft?.document.questions.length || 0) + 1)
    updateDoc(doc => {
      if (afterId) {
        const idx = doc.questions.findIndex(q => q.id === afterId)
        const qs = [...doc.questions]
        qs.splice(idx + 1, 0, q)
        return { ...doc, questions: qs }
      }
      return { ...doc, questions: [...doc.questions, q] }
    })
    setExpandedId(q.id)
  }
  const addSection = () =>
    updateDoc(doc => ({ ...doc, sections: [...doc.sections, { id: `s_${Date.now()}`, title: '新章节', question_ids: [] }] }))
  const assignSection = (qid: string, sid: string) =>
    updateDoc(doc => ({
      ...doc,
      sections: doc.sections.map(s => ({
        ...s,
        question_ids: sid === s.id ? [...s.question_ids.filter(id => id !== qid), qid] : s.question_ids.filter(id => id !== qid),
      })),
    }))
  const saveDraft = async () => {
    if (!draft) return
    setSaving(true)
    try {
      const updated = await draftService.update(draft.id, { document: draft.document, presentation_html: htmlEd, theme_css: cssEd })
      setDraft(updated); setDirty(false)
      showToast('success', '保存成功')
    } catch (e: any) { showToast('error', e.message || '保存失败') }
    finally { setSaving(false) }
  }
  const validateDraft = async () => {
    if (!draft) return
    setValidating(true)
    try {
      const r = await draftService.validate(draft.id)
      setDraft({ ...draft, is_valid: r.is_valid, validation_result: { errors: r.errors, is_valid: r.is_valid } })
      showToast(r.is_valid ? 'success' : 'error', r.is_valid ? '校验通过' : `校验失败: ${r.errors.length} 个错误`)
    } catch (e: any) { showToast('error', e.message || '校验失败') }
    finally { setValidating(false) }
  }
  const openAi = (qid: string) => { setAiQid(qid); setAiInstr(''); setAiOpen(true) }
  const runAi = async () => {
    if (!draft || !aiQid || !aiInstr.trim()) return
    setAiLoading(true)
    try {
      const r = await draftService.aiModify(draft.id, aiQid, aiInstr)
      updateQ(aiQid, r.modified_question)
      setAiOpen(false)
      showToast('success', 'AI 修改已应用，请保存以生效')
    } catch (e: any) { showToast('error', e.message || 'AI 修改失败') }
    finally { setAiLoading(false) }
  }
  const scrollToQ = (qid: string) => {
    setExpandedId(qid)
    qRefs.current[qid]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (error) return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p className="text-[var(--color-error)] mb-4">{error}</p>
      <Link to="/" className="text-[var(--color-primary)] underline">返回首页</Link>
    </div>
  )
  if (!paper || !draft) return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p className="text-[var(--color-text-secondary)] mb-4">未找到草稿</p>
      <Link to="/" className="text-[var(--color-primary)] underline">返回首页</Link>
    </div>
  )

  const questions = draft.document?.questions || []
  const sections = draft.document?.sections || []
  const valErrors = draft.validation_result?.errors || []
  const btnBase = "inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full transition-colors"
  const btnFilled = btnBase + " bg-[var(--color-primary)] text-[var(--color-text-inverse)] hover:opacity-90"
  const btnOutlined = btnBase + " border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]"
  const iconBtn = "p-1.5 rounded-lg text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] transition-colors"
  return (
    <div className="min-h-[calc(100dvh-var(--nav-height))] flex flex-col">
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 sm:px-6 py-3 flex items-center gap-2 sm:gap-3 flex-wrap">
        <Link to="/" className={btnOutlined}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
          返回
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold text-[var(--color-text-primary)] truncate">{paper.title}</h1>
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
            <span>草稿 v{draft.version}</span>
            {dirty && <span className="text-amber-600">未保存</span>}
            <span className={draft.is_valid ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}>
              {draft.is_valid ? '校验通过' : '有错误'}
            </span>
          </div>
        </div>
        <button onClick={validateDraft} disabled={validating} className={btnOutlined}>{validating ? '校验中...' : '校验'}</button>
        <button onClick={saveDraft} disabled={saving} className={btnFilled}>{saving ? '保存中...' : '保存草稿'}</button>
        <button onClick={() => navigate(`/publish/${paper.id}`)} disabled={!draft.is_valid}
          className={btnFilled + (!draft.is_valid ? ' opacity-40 cursor-not-allowed' : '')}
          title={!draft.is_valid ? '需通过校验后才能发布' : '进入发布'}>发布</button>
      </div>
      <div className="lg:hidden flex border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
        {([['questions', '题目编辑'], ['htmlcss', 'HTML/CSS'], ['preview', '预览']] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex-1 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === k ? 'border-[var(--color-primary)] text-[var(--color-primary)]' : 'border-transparent text-[var(--color-text-secondary)]'}`}>{label}</button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-[260px_1fr_1fr] gap-0">          <aside className="hidden lg:flex flex-col border-r border-[var(--color-border)] bg-[var(--color-bg-elevated)] overflow-y-auto">
            <div className="p-4 border-b border-[var(--color-border)]">
              <h3 className="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">资料信息</h3>
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between"><dt className="text-[var(--color-text-tertiary)]">模式</dt><dd className="text-[var(--color-text-secondary)]">{paper.mode === 'faithful_transcription' ? '忠实转录' : '讲义转题'}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-tertiary)]">状态</dt><dd className="text-[var(--color-text-secondary)]">{paper.status}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-tertiary)]">题目数</dt><dd className="text-[var(--color-text-secondary)]">{questions.length}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--color-text-tertiary)]">章节</dt><dd className="text-[var(--color-text-secondary)]">{sections.length}</dd></div>
              </dl>
            </div>
            <div className="p-4 border-b border-[var(--color-border)]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide">章节</h3>
                <button onClick={addSection} className="text-xs text-[var(--color-primary)] hover:underline">+ 添加</button>
              </div>
              <div className="space-y-1">
                {sections.map(s => (
                  <div key={s.id} className="text-sm text-[var(--color-text-secondary)] truncate flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)]" />
                    {s.title} <span className="text-[var(--color-text-tertiary)]">({s.question_ids.length})</span>
                  </div>
                ))}
                {sections.length === 0 && <p className="text-xs text-[var(--color-text-tertiary)]">暂无章节</p>}
              </div>
            </div>
            <div className="p-4 flex-1">
              <h3 className="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">题目列表</h3>
              <div className="space-y-1">
                {questions.map((q, i) => (
                  <button key={q.id} onClick={() => scrollToQ(q.id)}
                    className={`w-full text-left px-2 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-2 ${expandedId === q.id ? 'bg-[var(--color-primary-50)] text-[var(--color-primary)]' : 'hover:bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)]'}`}>
                    <span className="text-xs font-mono w-5">{i + 1}</span>
                    <span className="flex-1 truncate">{q.stem.slice(0, 20) || '空题目'}</span>
                    {(q.confidence < 0.8 || q.needs_review) && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="低置信度" />}
                  </button>
                ))}
              </div>
            </div>
          </aside>          {/* Middle column - structured editor */}
          <section className={`border-r border-[var(--color-border)] overflow-y-auto ${(tab === 'questions' || tab === 'htmlcss') ? 'block' : 'hidden'} lg:block`}>
            {tab === 'htmlcss' && (
              <div className="p-4 space-y-4 h-full flex flex-col">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">HTML / CSS 编辑器</h3>
                  <button onClick={saveDraft} disabled={saving} className={btnOutlined + ' text-xs'}>{saving ? '保存中...' : '保存'}</button>
                </div>
                <div className="flex-1 flex flex-col gap-3 min-h-0">
                  <div className="flex-1 flex flex-col min-h-0">
                    <label className="text-xs font-medium text-[var(--color-text-tertiary)] mb-1">HTML (presentation_html)</label>
                    <textarea value={htmlEd} onChange={e => { setHtmlEd(e.target.value); setDirty(true) }}
                      className="flex-1 w-full p-3 text-xs font-mono rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] min-h-[150px]" spellCheck={false} />
                  </div>
                  <div className="flex-1 flex flex-col min-h-0">
                    <label className="text-xs font-medium text-[var(--color-text-tertiary)] mb-1">CSS (theme_css)</label>
                    <textarea value={cssEd} onChange={e => { setCssEd(e.target.value); setDirty(true) }}
                      className="flex-1 w-full p-3 text-xs font-mono rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] min-h-[150px]" spellCheck={false} />
                  </div>
                </div>
              </div>
            )}
            {tab !== 'htmlcss' && (
              <div className="p-4 space-y-3">
                {valErrors.length > 0 && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                    <h4 className="text-sm font-semibold text-red-800 mb-1">校验错误 ({valErrors.length})</h4>
                    <ul className="text-xs text-red-700 space-y-0.5 list-disc list-inside">
                      {valErrors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">题目编辑 ({questions.length})</h3>
                  <button onClick={() => insertQ()} className={btnOutlined + ' text-xs'}>+ 插入新题</button>
                </div>                {questions.map((q, i) => {
                  const isExp = expandedId === q.id
                  const lowConf = q.confidence < 0.8 || q.needs_review
                  return (
                    <div key={q.id} ref={el => { qRefs.current[q.id] = el }}
                      className={`rounded-xl border bg-[var(--color-bg-elevated)] transition-shadow ${isExp ? 'border-[var(--color-primary)] shadow-md' : 'border-[var(--color-border)]'} ${lowConf ? 'ring-1 ring-amber-300' : ''}`}>
                      <div className="flex items-center gap-2 p-3">
                        <button onClick={() => setExpandedId(isExp ? null : q.id)} className="flex items-center gap-2 flex-1 min-w-0 text-left">
                          <span className="w-7 h-7 rounded-full bg-[var(--color-bg-hover)] text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-primary-50)] text-[var(--color-primary)] shrink-0">{TYPE_LABELS[q.type]}</span>
                          <span className="text-sm text-[var(--color-text-secondary)] truncate flex-1">{q.stem.slice(0, 40) || '空题目'}</span>
                          <span className="text-xs text-[var(--color-text-tertiary)] shrink-0">{q.score}分</span>
                          {lowConf && <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 shrink-0" title={`置信度: ${q.confidence}`}>待审</span>}
                        </button>
                        <div className="flex items-center gap-0.5 shrink-0">
                          <button onClick={() => moveQ(q.id, -1)} disabled={i === 0} className={iconBtn + ' disabled:opacity-30'} title="上移"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 15l-6-6-6 6" /></svg></button>
                          <button onClick={() => moveQ(q.id, 1)} disabled={i === questions.length - 1} className={iconBtn + ' disabled:opacity-30'} title="下移"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6" /></svg></button>
                          <button onClick={() => openAi(q.id)} className={iconBtn} title="AI 修改"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z" /></svg></button>
                          <button onClick={() => dupQ(q.id)} className={iconBtn} title="复制"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg></button>
                          <button onClick={() => deleteQ(q.id)} className={iconBtn + ' hover:text-red-600'} title="删除"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" /></svg></button>
                        </div>
                      </div>
                      {isExp && (
                        <div className="p-3 border-t border-[var(--color-border)] space-y-3">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            <div className="col-span-2 sm:col-span-1">
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">题型</label>
                              <select value={q.type} onChange={e => updateQ(q.id, { type: e.target.value as QuestionType })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]">
                                {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">分值</label>
                              <input type="number" value={q.score} onChange={e => updateQ(q.id, { score: parseFloat(e.target.value) || 0 })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]" min={0} />
                            </div>
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">来源页</label>
                              <input type="number" value={q.source_page || ''} onChange={e => updateQ(q.id, { source_page: parseInt(e.target.value) || undefined })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]" />
                            </div>
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">章节</label>
                              <select value={sections.find(s => s.question_ids.includes(q.id))?.id || ''}
                                onChange={e => assignSection(q.id, e.target.value)}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]">
                                <option value="">无</option>
                                {sections.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}
                              </select>
                            </div>
                          </div>
                          <div>
                            <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">题干</label>
                            <textarea value={q.stem} onChange={e => updateQ(q.id, { stem: e.target.value })}
                              className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none" rows={3} />
                          </div>
                          {(q.type === 'single_choice' || q.type === 'multi_choice') && (
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">
                                选项 ({q.type === 'single_choice' ? '单选' : '多选'})
                                <button onClick={() => updateQ(q.id, { options: [...q.options, { key: String.fromCharCode(65 + q.options.length), text: '' }] })}
                                  className="ml-2 text-[var(--color-primary)] hover:underline">+ 添加选项</button>
                              </label>
                              <div className="space-y-1.5">
                                {q.options.map((opt, oi) => (
                                  <div key={opt.key} className="flex items-center gap-2">
                                    <span className="w-6 text-xs font-bold text-[var(--color-text-tertiary)]">{opt.key}.</span>
                                    <input value={opt.text} onChange={e => {
                                      const opts = [...q.options]; opts[oi] = { ...opts[oi], text: e.target.value }
                                      updateQ(q.id, { options: opts })
                                    }} className="flex-1 px-2 py-1 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]" />
                                    <button onClick={() => updateQ(q.id, { options: q.options.filter((_, j) => j !== oi) })}
                                      className="text-red-400 hover:text-red-600 text-xs">删除</button>
                                  </div>
                                ))}
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                <span className="text-xs text-[var(--color-text-tertiary)]">正确答案：</span>
                                {q.options.map(opt => (
                                  <label key={opt.key} className="flex items-center gap-1 text-xs cursor-pointer">
                                    <input type={q.type === 'single_choice' ? 'radio' : 'checkbox'}
                                      checked={q.correct_keys.includes(opt.key)}
                                      onChange={() => {
                                        if (q.type === 'single_choice') {
                                          updateQ(q.id, { correct_keys: [opt.key] })
                                        } else {
                                          updateQ(q.id, {
                                            correct_keys: q.correct_keys.includes(opt.key)
                                              ? q.correct_keys.filter(k => k !== opt.key)
                                              : [...q.correct_keys, opt.key]
                                          })
                                        }
                                      }} />
                                    {opt.key}
                                  </label>
                                ))}
                              </div>
                            </div>
                          )}
                          {q.type === 'true_false' && (
                            <div className="flex items-center gap-4">
                              <span className="text-xs text-[var(--color-text-tertiary)]">正确答案：</span>
                              <label className="flex items-center gap-1 text-sm cursor-pointer">
                                <input type="radio" name={`tf-${q.id}`} checked={q.true_false_answer === true}
                                  onChange={() => updateQ(q.id, { true_false_answer: true })} />正确
                              </label>
                              <label className="flex items-center gap-1 text-sm cursor-pointer">
                                <input type="radio" name={`tf-${q.id}`} checked={q.true_false_answer === false}
                                  onChange={() => updateQ(q.id, { true_false_answer: false })} />错误
                              </label>
                            </div>
                          )}
                          {q.type === 'fill_blank' && (
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">可接受答案（每空一行，多个答案用逗号分隔）</label>
                              <textarea value={q.acceptable_answers.map(a => a.join(', ')).join('\n')}
                                onChange={e => updateQ(q.id, { acceptable_answers: e.target.value.split('\n').map(line => line.split(',').map(s => s.trim()).filter(Boolean)).filter(a => a.length > 0) })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none" rows={3} />
                              <select value={q.match_rule} onChange={e => updateQ(q.id, { match_rule: e.target.value })}
                                className="mt-1 px-2 py-1 text-xs rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]">
                                <option value="exact">精确匹配</option>
                                <option value="contains">包含即对</option>
                                <option value="regex">正则匹配</option>
                              </select>
                            </div>
                          )}
                          {q.type === 'subjective' && (
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">参考答案</label>
                              <textarea value={q.reference_answer} onChange={e => updateQ(q.id, { reference_answer: e.target.value })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none" rows={4} />
                              <label className="text-xs text-[var(--color-text-tertiary)] block mt-2 mb-1">评分要点（每行一个）</label>
                              <textarea value={q.scoring_points.join('\n')}
                                onChange={e => updateQ(q.id, { scoring_points: e.target.value.split('\n').filter(Boolean) })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none" rows={3} />
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">解析</label>
                              <textarea value={q.explanation} onChange={e => updateQ(q.id, { explanation: e.target.value })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] resize-none" rows={2} />
                            </div>
                            <div>
                              <label className="text-xs text-[var(--color-text-tertiary)] block mb-1">知识点（逗号分隔）</label>
                              <input value={q.knowledge_points.join(', ')}
                                onChange={e => updateQ(q.id, { knowledge_points: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                                className="w-full px-2 py-1.5 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]" />
                            </div>
                          </div>
                          <div className="flex items-center justify-between pt-1">
                            <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-tertiary)] cursor-pointer">
                              <input type="checkbox" checked={q.needs_review} onChange={e => updateQ(q.id, { needs_review: e.target.checked })} />
                              需人工审核
                            </label>
                            <span className="text-xs text-[var(--color-text-tertiary)]">置信度: {(q.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex gap-2">
                            <button onClick={() => insertQ(q.id)} className={btnOutlined + ' text-xs'}>下方插入</button>
                            <button onClick={() => openAi(q.id)} className={btnOutlined + ' text-xs'}>AI 修改</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
                {questions.length === 0 && (
                  <div className="text-center py-12 text-[var(--color-text-tertiary)]">
                    <p className="text-sm">暂无题目</p>
                    <button onClick={() => insertQ()} className="mt-2 text-[var(--color-primary)] text-sm hover:underline">添加第一道题</button>
                  </div>
                )}
              </div>
            )}
          </section>
          {/* 预览面板 */}
          <section className={`overflow-y-auto bg-white ${tab === 'preview' ? 'block' : 'hidden'} lg:block`}>
            <div className="flex items-center justify-between p-3 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">预览</h3>
              <div className="flex gap-1">
                {Object.entries(DEVICE_WIDTHS).map(([k]) => (
                  <button key={k} onClick={() => setDevice(k as typeof device)}
                    className={`px-2 py-1 text-xs rounded-lg transition-colors ${device === k ? 'bg-[var(--color-primary)] text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'}`}>
                    {k === 'desktop' ? '桌面' : k === 'tablet' ? '平板' : '手机'}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-center p-4 bg-[var(--color-bg-page)] min-h-full">
              <iframe srcDoc={previewDoc} style={{ width: DEVICE_WIDTHS[device], height: '100%', minHeight: '600px' }}
                className="border border-[var(--color-border)] rounded-lg bg-white shadow-sm" title="预览" />
            </div>
          </section>
        </div>
      </div>
      {/* AI 修改弹窗 */}
      {aiOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setAiOpen(false)}>
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">AI 修改题目</h3>
            <label className="text-sm text-[var(--color-text-secondary)] block mb-1">修改指令</label>
            <textarea value={aiInstr} onChange={e => setAiInstr(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] resize-none mb-4" rows={3}
              placeholder="例如：将这道题改为多选题，增加两个错误选项" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setAiOpen(false)} className={btnOutlined}>取消</button>
              <button onClick={runAi} disabled={aiLoading || !aiInstr.trim()} className={btnFilled + ' disabled:opacity-50'}>
                {aiLoading ? '处理中...' : '执行'}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium transition-all ${
          toast.type === 'success' ? 'bg-green-600 text-white' : toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-blue-600 text-white'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}