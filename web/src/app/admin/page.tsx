'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import StatusBadge from '@/components/StatusBadge';
import type { Paper } from '@/lib/api';

const mockPapers: Paper[] = [
  {
    id: 'p-001',
    title: '2024 年高考数学模拟卷（一）',
    status: 'published',
    mode: 'faithful',
    source_file: '2024-math-mock-1.pdf',
    question_count: 22,
    created_at: '2024-03-15T09:30:00Z',
    updated_at: '2024-03-15T14:20:00Z',
    slug: '2024-math-mock-1',
  },
  {
    id: 'p-002',
    title: '高三物理讲义 - 电磁感应',
    status: 'pending_review',
    mode: 'lecture',
    source_file: 'physics-lecture-em.pdf',
    question_count: 15,
    created_at: '2024-03-14T16:00:00Z',
    updated_at: '2024-03-14T16:45:00Z',
  },
  {
    id: 'p-003',
    title: '英语完形填空专项训练',
    status: 'modeling',
    mode: 'faithful',
    source_file: 'english-cloze.docx',
    question_count: 0,
    created_at: '2024-03-14T11:20:00Z',
    updated_at: '2024-03-14T11:25:00Z',
    progress: 65,
  },
  {
    id: 'p-004',
    title: '化学实验操作题集',
    status: 'parsing',
    mode: 'faithful',
    source_file: 'chem-lab.pdf',
    question_count: 0,
    created_at: '2024-03-14T10:00:00Z',
    updated_at: '2024-03-14T10:05:00Z',
    progress: 30,
  },
  {
    id: 'p-005',
    title: '历史材料分析题汇编',
    status: 'failed',
    mode: 'lecture',
    source_file: 'history-analysis.pdf',
    question_count: 0,
    created_at: '2024-03-13T15:30:00Z',
    updated_at: '2024-03-13T15:35:00Z',
    error: '文件解析失败：PDF 内容为空',
  },
  {
    id: 'p-006',
    title: '生物遗传学复习题',
    status: 'published',
    mode: 'faithful',
    source_file: 'bio-genetics.pdf',
    question_count: 18,
    created_at: '2024-03-12T09:00:00Z',
    updated_at: '2024-03-12T12:00:00Z',
    slug: 'bio-genetics',
  },
  {
    id: 'p-007',
    title: '语文古诗文默写训练',
    status: 'partial_failed',
    mode: 'faithful',
    source_file: 'chinese-poetry.docx',
    question_count: 12,
    created_at: '2024-03-11T14:00:00Z',
    updated_at: '2024-03-11T14:30:00Z',
    error: '部分题目无法识别题型',
  },
  {
    id: 'p-008',
    title: '地理区域分析讲义',
    status: 'queued',
    mode: 'lecture',
    source_file: 'geo-regional.pdf',
    question_count: 0,
    created_at: '2024-03-11T08:00:00Z',
    updated_at: '2024-03-11T08:00:00Z',
  },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export default function AdminHomePage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filtered = useMemo(() => {
    return mockPapers.filter((p) => {
      const matchSearch =
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        p.source_file.toLowerCase().includes(search.toLowerCase());
      const matchStatus =
        statusFilter === 'all' || p.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [search, statusFilter]);

  const statusOptions = [
    { value: 'all', label: '全部' },
    { value: 'published', label: '已发布' },
    { value: 'pending_review', label: '待审核' },
    { value: 'modeling', label: '处理中' },
    { value: 'failed', label: '失败' },
  ];

  return (
    <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 py-6 md:py-8">
      {/* 页头 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            资料列表
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            共 {mockPapers.length} 份资料
          </p>
        </div>
        <Link
          href="/admin/upload"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity self-start sm:self-auto"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建资料
        </Link>
      </div>

      {/* 搜索与筛选 */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索资料标题或文件名..."
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-[var(--color-bg)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-2 focus:ring-[var(--color-primary-50)] transition-colors"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {statusOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setStatusFilter(opt.value)}
              className={`px-3 py-2 text-sm font-medium rounded-[var(--radius-sm)] whitespace-nowrap transition-colors ${
                statusFilter === opt.value
                  ? 'text-[var(--color-primary)] bg-[var(--color-primary-50)]'
                  : 'text-[var(--color-text-secondary)] bg-[var(--color-bg)] hover:bg-[var(--color-bg-hover)]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 资料卡片网格 */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-[var(--color-text-tertiary)]">
          <p className="text-sm">未找到匹配的资料</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((paper) => (
            <Link
              key={paper.id}
              href={`/admin/papers/${paper.id}`}
              className="group bg-[var(--color-bg-elevated)] rounded-[var(--radius-md)] shadow-sm border border-[var(--color-border-light)] p-5 hover:shadow-md hover:border-[var(--color-border-hover)] transition-all"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-9 h-9 rounded-[var(--radius-sm)] flex items-center justify-center shrink-0"
                    style={{ background: 'var(--color-primary-50)' }}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--color-primary)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                  </span>
                  <span className="text-xs text-[var(--color-text-tertiary)] truncate">
                    {paper.source_file}
                  </span>
                </div>
                <StatusBadge status={paper.status} size="sm" />
              </div>

              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] line-clamp-2 mb-2 group-hover:text-[var(--color-primary)] transition-colors">
                {paper.title}
              </h3>

              <div className="flex items-center gap-4 text-xs text-[var(--color-text-tertiary)]">
                <span className="inline-flex items-center gap-1">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M9 11l3 3L22 4" />
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                  </svg>
                  {paper.question_count} 题
                </span>
                <span className="inline-flex items-center gap-1">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  {formatDate(paper.created_at)}
                </span>
              </div>

              {paper.progress !== undefined && paper.progress > 0 && (
                <div className="mt-3">
                  <div className="h-1 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-primary)] rounded-full transition-all"
                      style={{ width: `${paper.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {paper.error && (
                <p className="mt-3 text-xs text-[var(--color-error-text)] line-clamp-1">
                  {paper.error}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
