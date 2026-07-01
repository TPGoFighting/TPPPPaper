import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadService, modelService } from '../api/services'
import { useApi } from '../hooks/useApi'
import type { PaperMode, QuestionType } from '../api/types'

const ALLOWED_EXT = ['pdf', 'docx', 'png', 'jpg', 'jpeg']
const MAX_SIZE = 50 * 1024 * 1024

const MODES: { value: PaperMode; title: string; desc: string }[] = [
  { value: 'faithful_transcription', title: '忠实转写', desc: '将试卷原样转写为可交互网页' },
  { value: 'lecture_to_quiz', title: '讲义出题', desc: '从讲义内容生成练习题' },
]

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: 'single_choice', label: '单选' },
  { value: 'multi_choice', label: '多选' },
  { value: 'true_false', label: '判断' },
  { value: 'fill_blank', label: '填空' },
  { value: 'subjective', label: '主观' },
]

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
export default function UploadWizard() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<PaperMode>('faithful_transcription')
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>(['single_choice', 'multi_choice'])
  const [questionCount, setQuestionCount] = useState(10)
  const [difficulty, setDifficulty] = useState('medium')
  const [language, setLanguage] = useState('zh')
  const [extraRequirements, setExtraRequirements] = useState('')
  const [uploading, setUploading] = useState(false)

  const { data: profiles } = useApi(() => modelService.list(), [])
  const activeProfile = profiles?.find((p) => p.is_active)

  const validateFile = (f: File): string => {
    const ext = f.name.split('.').pop()?.toLowerCase() || ''
    if (!ALLOWED_EXT.includes(ext)) return `不支持的文件类型：.${ext}（支持 PDF/DOCX/PNG/JPG）`
    if (f.size > MAX_SIZE) return `文件过大（${formatSize(f.size)}），最大支持 50MB`
    return ''
  }

  const handleFile = (f: File) => {
    const err = validateFile(f)
    if (err) {
      setError(err)
      setFile(null)
      return
    }
    setError('')
    setFile(f)
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }, [])

  const toggleQuestionType = (t: QuestionType) => {
    setQuestionTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  const handleUpload = async () => {
    if (!file) return
    if (mode === 'lecture_to_quiz' && questionTypes.length === 0) {
      setError('请至少选择一种题型')
      return
    }
    setUploading(true)
    setError('')
    try {
      await uploadService.init(file.name, file.type || 'application/octet-stream', file.size, mode)
      const result = await uploadService.upload(file, mode)
      navigate(`/progress/${result.paper_id}`)
    } catch (e: any) {
      setError(e.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }
  return (
    <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 py-6 sm:py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">上传新资料</h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">支持 PDF / DOCX / PNG / JPG，单文件最大 50MB</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 sm:p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">1. 选择文件</h2>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer border-2 border-dashed rounded-[var(--radius-md)] p-8 text-center transition ${
                dragging
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)]'
                  : 'border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-subtle)]'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.png,.jpg,.jpeg"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
              />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <div className="text-left">
                    <div className="text-sm font-medium text-[var(--color-text-primary)]">{file.name}</div>
                    <div className="text-xs text-[var(--color-text-secondary)]">{formatSize(file.size)}</div>
                  </div>
                </div>
              ) : (
                <div>
                  <svg className="mx-auto" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <p className="text-sm text-[var(--color-text-primary)] font-medium mt-2">拖拽文件到此处，或点击选择</p>
                  <p className="text-xs text-[var(--color-text-tertiary)] mt-1">PDF / DOCX / PNG / JPG，≤ 50MB</p>
                </div>
              )}
            </div>
            {file && (
              <button
                onClick={() => { setFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                className="mt-3 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-error-text)] transition"
              >
                移除文件
              </button>
            )}
          </section>
          <section className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 sm:p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">2. 选择处理模式</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {MODES.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value)}
                  className={`text-left p-4 rounded-[var(--radius-md)] border-2 transition ${
                    mode === m.value
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)]'
                      : 'border-[var(--color-border)] hover:border-[var(--color-primary)]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {m.value === 'faithful_transcription' ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M9 11l3 3L22 4" />
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                      </svg>
                    )}
                    <span className="font-medium text-[var(--color-text-primary)]">{m.title}</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1.5">{m.desc}</p>
                </button>
              ))}
            </div>
          </section>
          {mode === 'lecture_to_quiz' && (
            <section className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 sm:p-6 anim-fade-in">
              <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">3. 出题配置</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">题型（多选）</label>
                  <div className="flex flex-wrap gap-2">
                    {QUESTION_TYPES.map((t) => (
                      <button
                        key={t.value}
                        onClick={() => toggleQuestionType(t.value)}
                        className={`px-3.5 py-1.5 rounded-[var(--radius-full)] text-xs font-medium transition ${
                          questionTypes.includes(t.value)
                            ? 'bg-[var(--color-primary)] text-white'
                            : 'bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">题目数量</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={questionCount}
                      onChange={(e) => setQuestionCount(Math.max(1, Number(e.target.value) || 1))}
                      className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-lighter)] transition"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">难度</label>
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value)}
                      className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-lighter)] transition"
                    >
                      <option value="easy">简单</option>
                      <option value="medium">中等</option>
                      <option value="hard">困难</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">语言</label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-lighter)] transition"
                    >
                      <option value="zh">中文</option>
                      <option value="en">英文</option>
                    </select>
                  </div>
                </div>                <div>
                  <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">补充要求</label>
                  <textarea
                    value={extraRequirements}
                    onChange={(e) => setExtraRequirements(e.target.value)}
                    rows={3}
                    placeholder="如有特殊要求请填写…"
                    className="w-full px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-lighter)] transition resize-y"
                  />
                </div>
              </div>
            </section>
          )}
        </div>
        <div className="lg:col-span-1">
          <div className="bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)] shadow-sm p-5 sm:p-6 sticky top-20 space-y-4">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)]">提交概览</h2>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-[var(--color-text-tertiary)] text-xs">文件</div>
                <div className="text-[var(--color-text-primary)] font-medium break-all">{file ? file.name : '未选择'}</div>
                {file && <div className="text-xs text-[var(--color-text-secondary)]">{formatSize(file.size)}</div>}
              </div>
              <div>
                <div className="text-[var(--color-text-tertiary)] text-xs">模式</div>
                <div className="text-[var(--color-text-primary)] font-medium">{MODES.find((m) => m.value === mode)?.title}</div>
              </div>
              <div className="pt-3 border-t border-[var(--color-border-light)]">
                <div className="text-[var(--color-text-tertiary)] text-xs mb-1">使用模型（当前活跃 Profile）</div>
                {activeProfile ? (
                  <div className="space-y-1">
                    <div className="text-[var(--color-text-primary)] text-xs">文本：{activeProfile.text_model || '—'}</div>
                    <div className="text-[var(--color-text-primary)] text-xs">多模态：{activeProfile.multimodal_model || '—'}</div>
                    <div className="text-xs text-[var(--color-text-tertiary)]">{activeProfile.name}</div>
                  </div>
                ) : (
                  <div className="text-[var(--color-text-tertiary)] text-xs">{profiles ? '未配置活跃模型' : '加载中…'}</div>
                )}
              </div>
            </div>

            {error && (
              <div className="px-3 py-2 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error-text)] text-xs">{error}</div>
            )}

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full py-2.5 rounded-[var(--radius-full)] bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed transition"
            >
              {uploading ? '上传中…' : '开始上传'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}