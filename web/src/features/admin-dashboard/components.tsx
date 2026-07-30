import Link from 'next/link';
import StatusBadge from '@/components/StatusBadge';
import type { Paper } from '@/lib/api';
import { countStagePapers, formatDate, type Metric, type StatusOption, type WorkflowStage } from './data';

interface AdminDashboardHeaderProps {
  totalCount: number;
  attentionCount: number;
}

export function AdminDashboardHeader({
  totalCount,
  attentionCount,
}: AdminDashboardHeaderProps) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary)]">
          今日处理台
        </p>
        <h1 className="mt-2 text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
          资料转换工作台
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          管理上传、模型处理、人工审核和发布状态，共 {totalCount} 份资料
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {attentionCount > 0 && (
          <span className="inline-flex items-center rounded-[var(--radius-full)] bg-[var(--color-warning-bg)] px-3 py-1 text-xs font-medium text-[var(--color-warning-text)]">
            {attentionCount} 项需要处理
          </span>
        )}
        <Link
          href="/admin/upload"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
        >
          <PlusIcon />
          新建资料
        </Link>
      </div>
    </header>
  );
}

export function MetricsGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
      {metrics.map((metric) => (
        <article
          key={metric.label}
          className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg-elevated)] p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-[var(--color-text-tertiary)]">
                {metric.label}
              </p>
              <p className="mt-2 text-2xl font-bold text-[var(--color-text-primary)]">
                {metric.value}
              </p>
            </div>
            <span
              className="mt-1 h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: getMetricToneColor(metric.tone) }}
            />
          </div>
          <p className="mt-3 text-xs text-[var(--color-text-secondary)]">
            {metric.detail}
          </p>
        </article>
      ))}
    </section>
  );
}

interface WorkflowOverviewProps {
  papers: Paper[];
  stages: WorkflowStage[];
}

export function WorkflowOverview({ papers, stages }: WorkflowOverviewProps) {
  return (
    <section className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg-elevated)] p-4 md:p-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            转换流程
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            按资料从上传到发布的真实路径组织任务
          </p>
        </div>
        <Link
          href="/admin/upload"
          className="text-sm font-semibold text-[var(--color-primary)] hover:underline"
        >
          上传新资料
        </Link>
      </div>

      <div className="mt-5 grid grid-cols-1 md:grid-cols-5 gap-3">
        {stages.map((stage, index) => {
          const count = countStagePapers(papers, stage);
          return (
            <div
              key={stage.label}
              className="relative rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-page)] p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-primary-50)] text-xs font-bold text-[var(--color-primary)]">
                  {index + 1}
                </span>
                <span className="text-sm font-bold text-[var(--color-text-primary)]">
                  {count}
                </span>
              </div>
              <h3 className="mt-3 text-sm font-semibold text-[var(--color-text-primary)]">
                {stage.label}
              </h3>
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                {stage.description}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

interface PaperFiltersProps {
  search: string;
  statusFilter: StatusOption['value'];
  options: StatusOption[];
  resultCount: number;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: StatusOption['value']) => void;
}

export function PaperFilters({
  search,
  statusFilter,
  options,
  resultCount,
  onSearchChange,
  onStatusChange,
}: PaperFiltersProps) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            资料库
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            当前筛选出 {resultCount} 份资料
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 lg:flex-row">
        <label className="relative flex-1">
          <span className="sr-only">搜索资料</span>
          <SearchIcon />
          <input
            type="search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="搜索资料标题或文件名..."
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-[var(--color-bg)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-2 focus:ring-[var(--color-primary-50)] transition-colors"
          />
        </label>

        <div
          className="flex gap-2 overflow-x-auto pb-1"
          role="tablist"
          aria-label="资料状态筛选"
        >
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onStatusChange(option.value)}
              className={`px-3 py-2 text-sm font-medium rounded-[var(--radius-sm)] whitespace-nowrap transition-colors ${
                statusFilter === option.value
                  ? 'text-[var(--color-primary)] bg-[var(--color-primary-50)]'
                  : 'text-[var(--color-text-secondary)] bg-[var(--color-bg)] hover:bg-[var(--color-bg-hover)]'
              }`}
              aria-selected={statusFilter === option.value}
              role="tab"
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export function PaperGrid({ papers }: { papers: Paper[] }) {
  if (papers.length === 0) {
    return (
      <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] py-14 text-center">
        <p className="text-sm font-medium text-[var(--color-text-secondary)]">
          未找到匹配的资料
        </p>
        <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">
          换个关键词，或清空筛选条件再试一次
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {papers.map((paper) => (
        <PaperCard key={paper.id} paper={paper} />
      ))}
    </div>
  );
}

function PaperCard({ paper }: { paper: Paper }) {
  return (
    <Link
      href={`/admin/papers/${paper.id}`}
      className="group flex min-h-[220px] flex-col rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg-elevated)] p-5 shadow-sm transition-all hover:border-[var(--color-border-hover)] hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-primary-50)] text-[var(--color-primary)]">
            <DocumentIcon />
          </span>
          <span className="truncate text-xs text-[var(--color-text-tertiary)]">
            {paper.source_file_name || '未上传源文件'}
          </span>
        </div>
        <StatusBadge status={paper.status} size="sm" />
      </div>

      <h3 className="mt-4 text-sm font-semibold text-[var(--color-text-primary)] line-clamp-2 transition-colors group-hover:text-[var(--color-primary)]">
        {paper.title}
      </h3>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-[var(--color-text-tertiary)]">题目</dt>
          <dd className="mt-1 font-semibold text-[var(--color-text-primary)]">
            {paper.question_count} 题
          </dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-tertiary)]">创建</dt>
          <dd className="mt-1 font-semibold text-[var(--color-text-primary)]">
            {formatDate(paper.created_at)}
          </dd>
        </div>
      </dl>

      {paper.progress !== undefined && paper.progress > 0 && (
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-[var(--color-text-tertiary)]">处理进度</span>
            <span className="font-medium text-[var(--color-primary)]">
              {paper.progress}%
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[var(--color-bg-tertiary)]">
            <div
              className="h-full rounded-full bg-[var(--color-primary)] transition-all"
              style={{ width: `${paper.progress}%` }}
            />
          </div>
        </div>
      )}

      {paper.error_message && (
        <p className="mt-4 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] px-3 py-2 text-xs text-[var(--color-error-text)] line-clamp-2">
          {paper.error_message}
        </p>
      )}

      <div className="mt-auto pt-4 text-xs font-semibold text-[var(--color-primary)]">
        查看详情
      </div>
    </Link>
  );
}

function getMetricToneColor(tone: Metric['tone']) {
  const toneMap: Record<Metric['tone'], string> = {
    primary: 'var(--color-primary)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    error: 'var(--color-error)',
  };

  return toneMap[tone];
}

function PlusIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function SearchIcon() {
  return (
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
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}
