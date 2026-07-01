'use client';

import { useState, useMemo } from 'react';

interface PublicQuestion {
  id: string;
  type: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer';
  stem: string;
  options?: string[];
  answer: string;
  explanation: string;
}

const mockQuestions: PublicQuestion[] = [
  {
    id: 'q1',
    type: 'single_choice',
    stem: '已知函数 f(x) = 2x² - 3x + 1，则 f(2) 的值为？',
    options: ['3', '5', '7', '9'],
    answer: 'A',
    explanation: '将 x = 2 代入函数：f(2) = 2(2)² - 3(2) + 1 = 8 - 6 + 1 = 3，故选 A。',
  },
  {
    id: 'q2',
    type: 'single_choice',
    stem: '下列哪个物理量的单位是牛顿？',
    options: ['质量', '速度', '力', '能量'],
    answer: 'C',
    explanation: '牛顿（N）是力的国际单位，1N = 1 kg·m/s²。',
  },
  {
    id: 'q3',
    type: 'true_false',
    stem: '光合作用只在植物的叶片中进行。',
    options: ['正确', '错误'],
    answer: 'B',
    explanation: '光合作用在含有叶绿体的细胞中进行，包括幼茎等绿色部位，不限于叶片。',
  },
  {
    id: 'q4',
    type: 'single_choice',
    stem: '中国古代四大发明中，最早出现的是？',
    options: ['造纸术', '印刷术', '火药', '指南针'],
    answer: 'A',
    explanation: '造纸术由东汉蔡伦改进，是四大发明中最早出现的。',
  },
];

export default function PublicPaperPage() {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const score = useMemo(() => {
    return mockQuestions.reduce((acc, q) => {
      return acc + (answers[q.id] === q.answer ? 1 : 0);
    }, 0);
  }, [answers]);

  const progress = useMemo(() => {
    const answered = Object.keys(answers).length;
    return Math.round((answered / mockQuestions.length) * 100);
  }, [answers]);

  const handleSelect = (questionId: string, option: string) => {
    if (submitted) return;
    setAnswers((prev) => ({ ...prev, [questionId]: option }));
  };

  const handleSubmit = () => {
    setSubmitted(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReset = () => {
    setAnswers({});
    setSubmitted(false);
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--color-bg-page)]">
      {/* 吸顶进度条（移动端） */}
      <div className="sticky top-0 z-30 md:hidden bg-[var(--color-bg)] border-b border-[var(--color-border-light)]">
        <div className="px-4 py-2.5">
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] mb-1.5">
            <span className="font-medium">{progress}%</span>
            <span>{Object.keys(answers).length} / {mockQuestions.length}</span>
          </div>
          <div className="h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-primary)] rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* 桌面端头部 */}
      <div className="hidden md:block bg-[var(--color-bg)] border-b border-[var(--color-border-light)]">
        <div className="mx-auto max-w-3xl px-6 py-8">
          <span className="inline-block px-3 py-1 text-xs font-semibold text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-full)] mb-3">
            在线复习
          </span>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-primary)] mb-2">
            2024 年高考数学模拟卷（一）
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)]">
            共 {mockQuestions.length} 题 · 满分 {mockQuestions.length} 分
          </p>
        </div>
      </div>

      {/* 移动端标题 */}
      <div className="md:hidden px-4 py-4">
        <h1 className="text-lg font-bold text-[var(--color-text-primary)] mb-1">
          2024 年高考数学模拟卷（一）
        </h1>
        <p className="text-xs text-[var(--color-text-secondary)]">
          共 {mockQuestions.length} 题
        </p>
      </div>

      {/* 成绩展示 */}
      {submitted && (
        <div className="mx-auto max-w-3xl px-4 sm:px-6 mt-4 md:mt-6">
          <div className="bg-[var(--color-bg)] rounded-[var(--radius-md)] border border-[var(--color-border-light)] p-5 sm:p-6 text-center">
            <div
              className="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3"
              style={{
                background:
                  score >= mockQuestions.length * 0.6
                    ? 'var(--color-success-bg)'
                    : 'var(--color-warning-bg)',
              }}
            >
              <span
                className="text-2xl font-bold"
                style={{
                  color:
                    score >= mockQuestions.length * 0.6
                      ? 'var(--color-success)'
                      : 'var(--color-warning)',
                }}
              >
                {score}
              </span>
            </div>
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-1">
              得分 {score} / {mockQuestions.length}
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              正确率 {Math.round((score / mockQuestions.length) * 100)}%
            </p>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center px-4 py-2 text-sm font-semibold text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-full)] hover:bg-[var(--color-primary-100)] transition-colors"
            >
              重新答题
            </button>
          </div>
        </div>
      )}

      {/* 题目列表（单列阅读） */}
      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-4 md:py-6 space-y-4">
        {mockQuestions.map((q, idx) => {
          const userAnswer = answers[q.id];
          const isCorrect = submitted && userAnswer === q.answer;
          const isWrong = submitted && userAnswer && userAnswer !== q.answer;

          return (
            <div
              key={q.id}
              className="bg-[var(--color-bg)] rounded-[var(--radius-md)] border border-[var(--color-border-light)] p-5 sm:p-6"
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm font-bold text-[var(--color-text-primary)]">
                  {idx + 1}.
                </span>
                <span className="px-2 py-0.5 text-xs font-medium text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)] rounded-[var(--radius-full)]">
                  {q.type === 'single_choice'
                    ? '单选'
                    : q.type === 'multiple_choice'
                    ? '多选'
                    : q.type === 'true_false'
                    ? '判断'
                    : '简答'}
                </span>
                {submitted && (
                  <span
                    className={`ml-auto inline-flex items-center gap-1 text-xs font-medium ${
                      isCorrect
                        ? 'text-[var(--color-success-600)]'
                        : isWrong
                        ? 'text-[var(--color-error-text)]'
                        : 'text-[var(--color-text-tertiary)]'
                    }`}
                  >
                    {isCorrect ? (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        正确
                      </>
                    ) : isWrong ? (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                        错误
                      </>
                    ) : (
                      '未作答'
                    )}
                  </span>
                )}
              </div>

              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed mb-4">
                {q.stem}
              </p>

              {q.options && (
                <div className="space-y-2">
                  {q.options.map((opt, i) => {
                    const letter = String.fromCharCode(65 + i);
                    const selected = userAnswer === letter;
                    const showCorrect = submitted && q.answer.includes(letter);
                    const showWrong = submitted && selected && !q.answer.includes(letter);

                    return (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleSelect(q.id, letter)}
                        disabled={submitted}
                        className={`w-full flex items-center gap-3 px-4 py-3 text-sm rounded-[var(--radius-sm)] border transition-all text-left ${
                          showCorrect
                            ? 'border-[var(--color-success)] bg-[var(--color-success-bg)] text-[var(--color-success-600)]'
                            : showWrong
                            ? 'border-[var(--color-error)] bg-[var(--color-error-bg)] text-[var(--color-error-text)]'
                            : selected
                            ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)]'
                            : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-hover)] hover:bg-[var(--color-bg-hover)]'
                        } ${submitted ? 'cursor-default' : 'cursor-pointer'}`}
                      >
                        <span className="w-6 h-6 rounded-full border flex items-center justify-center text-xs font-semibold shrink-0"
                          style={{
                            borderColor: showCorrect ? 'var(--color-success)' : showWrong ? 'var(--color-error)' : selected ? 'var(--color-primary)' : 'var(--color-border)',
                          }}
                        >
                          {letter}
                        </span>
                        {opt}
                      </button>
                    );
                  })}
                </div>
              )}

              {submitted && q.explanation && (
                <div className="mt-4 p-4 bg-[var(--color-info-bg)] rounded-[var(--radius-sm)] border-l-2 border-[var(--color-info)]">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-info)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <span className="text-xs font-semibold text-[var(--color-info-text)]">
                      解析
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                    {q.explanation}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 底部提交栏 */}
      {!submitted && (
        <div className="sticky bottom-0 z-30 bg-[var(--color-bg)] border-t border-[var(--color-border-light)] px-4 sm:px-6 py-3">
          <div className="mx-auto max-w-3xl flex items-center justify-between gap-4">
            <span className="text-xs text-[var(--color-text-secondary)]">
              已答 {Object.keys(answers).length} / {mockQuestions.length}
            </span>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={Object.keys(answers).length === 0}
              className="inline-flex items-center px-6 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              提交答卷
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
