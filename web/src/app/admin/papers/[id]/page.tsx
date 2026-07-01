'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import StatusBadge from '@/components/StatusBadge';
import type { Question } from '@/lib/api';

type TabKey = 'source' | 'editor' | 'meta';

const mockQuestions: Question[] = [
  {
    id: 'q1',
    type: 'single_choice',
    stem: '已知函数 f(x) = 2x² - 3x + 1，则 f(2) 的值为？',
    options: ['3', '5', '7', '9'],
    answer: 'A',
    explanation: 'f(2) = 2(2)² - 3(2) + 1 = 8 - 6 + 1 = 3',
  },
  {
    id: 'q2',
    type: 'short_answer',
    stem: '简述牛顿第二定律的内容及其数学表达式。',
    answer: '物体的加速度跟所受合外力成正比，跟物体的质量成反比。F = ma',
    explanation: '牛顿第二定律是经典力学的核心，描述力、质量与加速度的关系。',
  },
  {
    id: 'q3',
    type: 'true_false',
    stem: '光合作用只在植物的叶片中进行。',
    options: ['正确', '错误'],
    answer: 'B',
    explanation: '光合作用在含有叶绿体的细胞中进行，不限于叶片。',
  },
  {
    id: 'q4',
    type: 'multiple_choice',
    stem: '下列哪些属于可再生能源？（多选）',
    options: ['太阳能', '石油', '风能', '核能'],
    answer: 'AC',
    explanation: '太阳能和风能属于可再生能源，石油和核能属于不可再生能源。',
  },
];

const QUESTION_TYPE_LABELS: Record<Question['type'], string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '简答题',
};

export default function PaperDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [activeTab, setActiveTab] = useState<TabKey>('editor');
  const [leftWidth, setLeftWidth] = useState(35);
  const [rightWidth, setRightWidth] = useState(30);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef<'left' | 'right' | null>(null);

  const onMouseDown = (which: 'left' | 'right') => {
    draggingRef.current = which;
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      if (draggingRef.current === 'left') {
        setLeftWidth(Math.max(20, Math.min(50, pct)));
      } else {
        const centerStart = leftWidth;
        setRightWidth(Math.max(20, Math.min(50, 100 - pct - centerStart)));
      }
    };
    const onMouseUp = () => {
      draggingRef.current = null;
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [leftWidth]);

  const startEdit = (q: Question) => {
    setEditingId(q.id);
    setEditText(q.stem);
  };

  const saveEdit = () => {
    setEditingId(null);
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'source', label: '原始文件' },
    { key: 'editor', label: '题目编辑' },
    { key: 'meta', label: '元信息' },
  ];

  return (
    <div className="h-[calc(100dvh-var(--nav-height))] md:h-[100dvh] flex flex-col">
      {/* 顶部信息栏 */}
      <div className="flex items-center justify-between gap-3 px-4 sm:px-6 py-3 bg-[var(--color-bg)] border-b border-[var(--color-border-light)] shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/admin"
            className="inline-flex items-center justify-center w-9 h-9 rounded-[var(--radius-sm)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] transition-colors shrink-0"
            aria-label="返回"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
          </Link>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
              2024 年高考数学模拟卷（一）
            </h1>
            <p className="text-xs text-[var(--color-text-tertiary)] truncate">
              ID: {id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status="pending_review" size="sm" />
          <button
            type="button"
            className="hidden sm:inline-flex items-center px-4 py-2 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
          >
            发布
          </button>
        </div>
      </div>

      {/* 移动端标签切换 */}
      <div className="md:hidden flex border-b border-[var(--color-border-light)] bg-[var(--color-bg)] shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.key
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-secondary)]'
            }`}
          >
            {tab.label}
            {activeTab === tab.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
            )}
          </button>
        ))}
      </div>

      {/* 三栏布局（桌面端） / 单栏（移动端） */}
      <div
        ref={containerRef}
        className="flex-1 flex overflow-hidden"
      >
        {/* 左栏：原始文件预览 */}
        <div
          className={`${activeTab === 'source' ? 'flex' : 'hidden'} md:flex flex-col border-r border-[var(--color-border-light)] bg-[var(--color-bg)] overflow-y-auto`}
          style={{ width: `${leftWidth}%` }}
        >
          <div className="px-4 py-3 border-b border-[var(--color-border-light)] sticky top-0 bg-[var(--color-bg)] z-10">
            <h2 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wide">
              原始文件
            </h2>
          </div>
          <div className="p-4 space-y-3">
            {[1, 2, 3].map((page) => (
              <div
                key={page}
                className="aspect-[3/4] bg-[var(--color-bg-subtle)] rounded-[var(--radius-sm)] border border-[var(--color-border-light)] flex items-center justify-center"
              >
                <span className="text-xs text-[var(--color-text-tertiary)]">
                  第 {page} 页预览
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 左分隔条 */}
        <div
          className="hidden md:block w-1 cursor-col-resize bg-[var(--color-border-light)] hover:bg-[var(--color-primary)] transition-colors shrink-0"
          onMouseDown={() => onMouseDown('left')}
        />

        {/* 中栏：题目编辑器 */}
        <div
          className={`${activeTab === 'editor' ? 'flex' : 'hidden'} md:flex flex-1 flex-col overflow-y-auto bg-[var(--color-bg-page)]`}
          style={{ width: `${100 - leftWidth - rightWidth}%` }}
        >
          <div className="px-4 sm:px-6 py-3 border-b border-[var(--color-border-light)] sticky top-0 bg-[var(--color-bg)] z-10">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wide">
                题目编辑 ({mockQuestions.length})
              </h2>
              <button
                type="button"
                className="text-xs text-[var(--color-primary)] hover:underline"
              >
                + 添加题目
              </button>
            </div>
          </div>
          <div className="p-4 sm:p-6 space-y-4">
            {mockQuestions.map((q, idx) => (
              <div
                key={q.id}
                className="bg-[var(--color-bg)] rounded-[var(--radius-md)] border border-[var(--color-border-light)] p-4 sm:p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[var(--color-text-primary)]">
                      {idx + 1}.
                    </span>
                    <span className="px-2 py-0.5 text-xs font-medium text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-full)]">
                      {QUESTION_TYPE_LABELS[q.type]}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => startEdit(q)}
                    className="p-1.5 text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-50)] rounded-[var(--radius-sm)] transition-colors"
                    aria-label="编辑"
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </button>
                </div>

                {editingId === q.id ? (
                  <div>
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full p-3 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border-focus)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-50)] resize-y"
                      rows={3}
                    />
                    <div className="flex gap-2 mt-2">
                      <button
                        type="button"
                        onClick={saveEdit}
                        className="px-3 py-1.5 text-xs font-medium text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-sm)]"
                      >
                        保存
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)] rounded-[var(--radius-sm)]"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-[var(--color-text-primary)] leading-relaxed mb-3">
                      {q.stem}
                    </p>
                    {q.options && (
                      <div className="space-y-1.5 mb-3">
                        {q.options.map((opt, i) => {
                          const letter = String.fromCharCode(65 + i);
                          const isAnswer = q.answer?.includes(letter);
                          return (
                            <div
                              key={i}
                              className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-[var(--radius-sm)] ${
                                isAnswer
                                  ? 'text-[var(--color-success-600)] bg-[var(--color-success-bg)]'
                                  : 'text-[var(--color-text-secondary)]'
                              }`}
                            >
                              <span className="font-medium">{letter}.</span>
                              {opt}
                              {isAnswer && (
                                <svg
                                  width="14"
                                  height="14"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2.5"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                >
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                    {q.explanation && (
                      <div className="mt-2 p-3 bg-[var(--color-bg-subtle)] rounded-[var(--radius-sm)]">
                        <p className="text-xs text-[var(--color-text-tertiary)] mb-1">
                          解析
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                          {q.explanation}
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 右分隔条 */}
        <div
          className="hidden md:block w-1 cursor-col-resize bg-[var(--color-border-light)] hover:bg-[var(--color-primary)] transition-colors shrink-0"
          onMouseDown={() => onMouseDown('right')}
        />

        {/* 右栏：元信息与预览 */}
        <div
          className={`${activeTab === 'meta' ? 'flex' : 'hidden'} md:flex flex-col border-l border-[var(--color-border-light)] bg-[var(--color-bg)] overflow-y-auto`}
          style={{ width: `${rightWidth}%` }}
        >
          <div className="px-4 py-3 border-b border-[var(--color-border-light)] sticky top-0 bg-[var(--color-bg)] z-10">
            <h2 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wide">
              元信息
            </h2>
          </div>
          <div className="p-4 space-y-5">
            <div>
              <label className="text-xs font-medium text-[var(--color-text-tertiary)] block mb-1.5">
                标题
              </label>
              <input
                type="text"
                defaultValue="2024 年高考数学模拟卷（一）"
                className="w-full px-3 py-2 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)]"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--color-text-tertiary)] block mb-1.5">
                公开链接
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value="/p/2024-math-mock-1"
                  className="flex-1 px-3 py-2 text-sm bg-[var(--color-bg-subtle)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-secondary)]"
                />
                <button
                  type="button"
                  className="px-3 py-2 text-xs font-medium text-[var(--color-primary)] bg-[var(--color-primary-50)] rounded-[var(--radius-sm)] hover:bg-[var(--color-primary-100)] transition-colors"
                >
                  复制
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-[var(--color-text-tertiary)] block mb-1">
                  题目数
                </label>
                <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {mockQuestions.length}
                </p>
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--color-text-tertiary)] block mb-1">
                  创建时间
                </label>
                <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                  2024-03-15
                </p>
              </div>
            </div>
            <div className="pt-4 border-t border-[var(--color-border-light)]">
              <button
                type="button"
                className="w-full inline-flex items-center justify-center px-4 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity mb-2"
              >
                发布试卷
              </button>
              <button
                type="button"
                className="w-full inline-flex items-center justify-center px-4 py-2.5 text-sm font-semibold text-[var(--color-error-text)] bg-[var(--color-error-bg)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
              >
                删除资料
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
