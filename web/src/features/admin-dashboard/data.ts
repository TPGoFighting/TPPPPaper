import type { Paper, PaperStatus } from '@/lib/api';

export interface StatusOption {
  value: PaperStatus | 'all' | 'active' | 'needs_attention';
  label: string;
}

export interface Metric {
  label: string;
  value: string;
  detail: string;
  tone: 'primary' | 'success' | 'warning' | 'error';
}

export interface WorkflowStage {
  label: string;
  description: string;
  statuses: PaperStatus[];
}

export const statusOptions: StatusOption[] = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '处理中' },
  { value: 'needs_attention', label: '需处理' },
  { value: 'published', label: '已发布' },
  { value: 'failed', label: '失败' },
];

export const workflowStages: WorkflowStage[] = [
  {
    label: '导入',
    description: '上传与排队',
    statuses: ['uploading', 'queued'],
  },
  {
    label: '解析',
    description: '识别版面与题目',
    statuses: ['parsing'],
  },
  {
    label: '建模',
    description: '生成交互式复习结构',
    statuses: ['modeling'],
  },
  {
    label: '审核',
    description: '人工确认与修订',
    statuses: ['pending_review', 'partial_failed'],
  },
  {
    label: '发布',
    description: '公开访问与答题',
    statuses: ['published'],
  },
];

export const activeStatuses: PaperStatus[] = ['uploading', 'queued', 'parsing', 'modeling'];
export const attentionStatuses: PaperStatus[] = ['pending_review', 'partial_failed', 'failed'];

export function formatDate(iso: string): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export function getMetrics(papers: Paper[]): Metric[] {
  const published = papers.filter((paper) => paper.status === 'published').length;
  const active = papers.filter((paper) => activeStatuses.includes(paper.status)).length;
  const review = papers.filter((paper) => paper.status === 'pending_review').length;
  const failed = papers.filter((paper) =>
    ['partial_failed', 'failed'].includes(paper.status)
  ).length;

  return [
    {
      label: '资料总数',
      value: String(papers.length),
      detail: `${published} 份已发布`,
      tone: 'primary',
    },
    {
      label: '正在转换',
      value: String(active),
      detail: '排队、解析与建模中',
      tone: 'warning',
    },
    {
      label: '待审核',
      value: String(review),
      detail: '需要人工确认',
      tone: 'primary',
    },
    {
      label: '异常任务',
      value: String(failed),
      detail: '需要重新处理或修订',
      tone: failed > 0 ? 'error' : 'success',
    },
  ];
}

export function countStagePapers(papers: Paper[], stage: WorkflowStage): number {
  return papers.filter((paper) => stage.statuses.includes(paper.status)).length;
}

export function matchesStatusFilter(paper: Paper, filter: StatusOption['value']): boolean {
  if (filter === 'all') return true;
  if (filter === 'active') return activeStatuses.includes(paper.status);
  if (filter === 'needs_attention') return attentionStatuses.includes(paper.status);
  return paper.status === filter;
}
