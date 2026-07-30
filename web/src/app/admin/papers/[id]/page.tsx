'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import StatusBadge from '@/components/StatusBadge';
import { api, type Draft, type Paper, type Publication, type Question } from '@/lib/api';

const QUESTION_TYPE_LABELS: Record<Question['type'], string> = {
  single_choice: '单选题',
  multi_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  subjective: '主观题',
};

export default function PaperDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const paperId = Number(params.id);

  const [paper, setPaper] = useState<Paper | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadDetail = useCallback(async () => {
    try {
      setError('');
      const nextPaper = await api.get<Paper>(`/papers/${paperId}`);
      setPaper(nextPaper);
      if (nextPaper.current_draft_id) {
        setDraft(await api.get<Draft>(`/drafts/${nextPaper.current_draft_id}`));
      } else {
        setDraft(null);
      }
      setPublications(await api.get<Publication[]>(`/publications/paper/${paperId}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : '资料加载失败');
    } finally {
      setLoading(false);
    }
  }, [paperId]);

  const isProcessing = useMemo(() => {
    if (!paper) return false;
    return ['uploading', 'queued', 'parsing', 'modeling'].includes(paper.status);
  }, [paper]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (!isProcessing) return;
    const timer = window.setInterval(loadDetail, 3000);
    return () => window.clearInterval(timer);
  }, [isProcessing, loadDetail]);

  const questions = useMemo(
    () => (draft?.document.questions ?? []) as Question[],
    [draft]
  );

  async function validateDraft() {
    if (!draft) return;
    const result = await api.post<{ is_valid: boolean; errors: string[] }>(
      `/drafts/${draft.id}/validate`
    );
    setMessage(result.is_valid ? '草稿校验通过。' : `校验未通过：${result.errors.join('；')}`);
    await loadDetail();
  }

  async function publishDraft() {
    setMessage('');
    setError('');
    if (!draft?.is_valid) {
      setError('草稿未通过校验，无法发布。请先修复审核项后重新校验。');
      return;
    }
    try {
      await api.post<Publication>('/publications', { draft_id: draft.id });
      setMessage('发布成功，公开页面已更新。');
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : '发布失败');
    }
  }

  async function reprocessPaper() {
    setMessage('');
    await api.post(`/papers/${paperId}/reprocess`);
    setMessage('已重新加入处理队列。');
    await loadDetail();
  }

  async function deletePaper() {
    await api.delete(`/papers/${paperId}`);
    router.push('/admin');
  }

  if (loading) {
    return <div className="p-6 text-sm text-[var(--color-text-secondary)]">加载中...</div>;
  }

  if (!paper) {
    return (
      <div className="p-6">
        <Link href="/admin" className="text-sm text-[var(--color-primary)]">返回后台</Link>
        <p className="mt-4 text-sm text-[var(--color-error-text)]">{error || '资料不存在'}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-[var(--max-width)] flex-col gap-5 px-4 py-6 sm:px-6 md:py-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <Link href="/admin" className="text-sm font-medium text-[var(--color-primary)] hover:underline">
            返回工作台
          </Link>
          <h1 className="mt-3 text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            {paper.title}
          </h1>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
            {paper.source_file_name || '未绑定源文件'} · {questions.length} 题 · ID {paper.id}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={paper.status} size="sm" />
          {paper.slug && (
            <Link href={`/p/${paper.slug}`} className="tp-button-secondary">
              打开公开页
            </Link>
          )}
          <button
            type="button"
            onClick={publishDraft}
            disabled={!draft?.is_valid}
            title={!draft?.is_valid ? '请先通过草稿校验' : undefined}
            className="tp-button-primary"
          >
            发布
          </button>
        </div>
      </header>

      {(message || error) && (
        <div
          className={`rounded-[var(--radius-sm)] px-4 py-3 text-sm ${
            error
              ? 'bg-[var(--color-error-bg)] text-[var(--color-error-text)]'
              : 'bg-[var(--color-success-bg)] text-[var(--color-success-text)]'
          }`}
        >
          {error || message}
        </div>
      )}

      {isProcessing && (
        <div className="rounded-[var(--radius-md)] border border-blue-200/80 bg-blue-50/70 p-4 dark:border-blue-900/50 dark:bg-blue-950/30">
          <div className="flex items-center justify-between text-xs font-semibold text-[var(--color-primary)]">
            <span className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-600" />
              </span>
              AI 试卷结构化解析中... ({paper.status})
            </span>
            <span>{paper.progress ?? 15}%</span>
          </div>
          <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-blue-100 dark:bg-blue-900/50">
            <div
              className="h-full bg-[var(--color-primary)] transition-all duration-500 ease-out"
              style={{ width: `${Math.max(5, Math.min(100, paper.progress ?? 15))}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">
            后台 Celery 流水线正在进行视觉/文本 OCR 提取、模型结构化建模与网页净化生成，完成时自动进入待审核状态。
          </p>
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg)]">
          <div className="flex items-center justify-between border-b border-[var(--color-border-light)] px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-[var(--color-text-primary)]">结构化题目</h2>
              <p className="text-xs text-[var(--color-text-tertiary)]">来自当前草稿</p>
            </div>
            <button type="button" onClick={validateDraft} disabled={!draft} className="tp-button-secondary">
              校验草稿
            </button>
          </div>

          {questions.length === 0 ? (
            <div className="p-8 text-sm text-[var(--color-text-secondary)]">
              暂无草稿题目。资料处理完成后会出现在这里。
            </div>
          ) : (
            <div className="divide-y divide-[var(--color-border-light)]">
              {questions.map((question, index) => (
                <article key={question.id} className="p-5">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-[var(--color-text-primary)]">
                      {question.number ?? index + 1}.
                    </span>
                    <span className="rounded-[var(--radius-full)] bg-[var(--color-primary-50)] px-2 py-0.5 text-xs font-medium text-[var(--color-primary)]">
                      {QUESTION_TYPE_LABELS[question.type] ?? question.type}
                    </span>
                    {question.needs_review && (
                      <span className="rounded-[var(--radius-full)] bg-[var(--color-warning-bg)] px-2 py-0.5 text-xs font-medium text-[var(--color-warning-text)]">
                        需复核
                      </span>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed text-[var(--color-text-primary)]">
                    {question.stem}
                  </p>
                  {question.options && question.options.length > 0 && (
                    <div className="mt-3 grid gap-2">
                      {question.options.map((option) => (
                        <div
                          key={option.key}
                          className={`rounded-[var(--radius-sm)] border px-3 py-2 text-sm ${
                            question.correct_keys?.includes(option.key)
                              ? 'border-[var(--color-success)] bg-[var(--color-success-bg)] text-[var(--color-success-600)]'
                              : 'border-[var(--color-border-light)] text-[var(--color-text-secondary)]'
                          }`}
                        >
                          <span className="mr-2 font-semibold">{option.key}.</span>
                          {option.text}
                        </div>
                      ))}
                    </div>
                  )}
                  {(question.explanation || question.reference_answer) && (
                    <div className="mt-3 rounded-[var(--radius-sm)] bg-[var(--color-bg-subtle)] px-3 py-2 text-xs leading-relaxed text-[var(--color-text-secondary)]">
                      {question.reference_answer && (
                        <p><span className="font-semibold">参考答案：</span>{question.reference_answer}</p>
                      )}
                      {question.explanation && (
                        <p className={question.reference_answer ? 'mt-2' : ''}><span className="font-semibold">解析：</span>{question.explanation}</p>
                      )}
                      {question.answer_origin && (
                        <p className="mt-2 text-[var(--color-text-tertiary)]">
                          依据：{question.answer_origin === 'web_researched' || question.answer_origin === 'mixed' ? '网页检索 + AI 推导' : question.answer_origin === 'model_knowledge' ? 'AI 知识推导' : '待人工复核'}
                        </p>
                      )}
                      {question.answer_sources && question.answer_sources.length > 0 && (
                        <ul className="mt-2 list-disc pl-4 text-[var(--color-text-tertiary)]">
                          {question.answer_sources.map((source) => (
                            <li key={source.url}><a className="underline" href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a></li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>

        <aside className="flex flex-col gap-4">
          <section className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg)] p-5">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)]">发布状态</h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-text-secondary)]">草稿</dt>
                <dd className="font-medium text-[var(--color-text-primary)]">
                  {draft ? `v${draft.version} · ${draft.is_valid ? '有效' : '待校验'}` : '无'}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-text-secondary)]">发布版本</dt>
                <dd className="font-medium text-[var(--color-text-primary)]">
                  {publications.length ? `v${publications[0].version}` : '未发布'}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-text-secondary)]">Slug</dt>
                <dd className="font-mono text-xs text-[var(--color-text-primary)]">{paper.slug}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg)] p-5">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)]">操作</h2>
            <div className="mt-4 grid gap-2">
              <button type="button" onClick={reprocessPaper} className="tp-button-secondary">
                重新处理
              </button>
              <button
                type="button"
                onClick={deletePaper}
                className="rounded-[var(--radius-full)] bg-[var(--color-error-bg)] px-5 py-2.5 text-sm font-semibold text-[var(--color-error-text)] transition-opacity hover:opacity-90"
              >
                删除资料
              </button>
            </div>
          </section>
        </aside>
      </section>
    </div>
  );
}
