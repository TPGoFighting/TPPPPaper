import type { PaperStatus } from '@/lib/api';

interface StatusConfig {
  label: string;
  color: string;
  bg: string;
  dot: string;
  pulse?: boolean;
}

const STATUS_MAP: Record<PaperStatus, StatusConfig> = {
  uploading: {
    label: '上传中',
    color: 'var(--color-info-text)',
    bg: 'var(--color-info-bg)',
    dot: 'var(--color-info)',
    pulse: true,
  },
  queued: {
    label: '排队中',
    color: 'var(--color-text-secondary)',
    bg: 'var(--color-bg-tertiary)',
    dot: 'var(--color-text-tertiary)',
  },
  parsing: {
    label: '解析中',
    color: 'var(--color-info-text)',
    bg: 'var(--color-info-bg)',
    dot: 'var(--color-info)',
    pulse: true,
  },
  modeling: {
    label: '建模中',
    color: 'var(--color-info-text)',
    bg: 'var(--color-info-bg)',
    dot: 'var(--color-info)',
    pulse: true,
  },
  pending_review: {
    label: '待审核',
    color: 'var(--color-warning-text)',
    bg: 'var(--color-warning-bg)',
    dot: 'var(--color-warning)',
  },
  published: {
    label: '已发布',
    color: 'var(--color-success-600)',
    bg: 'var(--color-success-bg)',
    dot: 'var(--color-success)',
  },
  partial_failed: {
    label: '部分失败',
    color: 'var(--color-warning-text)',
    bg: 'var(--color-warning-bg)',
    dot: 'var(--color-warning)',
  },
  failed: {
    label: '失败',
    color: 'var(--color-error-text)',
    bg: 'var(--color-error-bg)',
    dot: 'var(--color-error)',
  },
};

interface StatusBadgeProps {
  status: PaperStatus;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? STATUS_MAP.queued;
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 ${padding} font-medium rounded-[var(--radius-full)] whitespace-nowrap`}
      style={{ color: config.color, backgroundColor: config.bg }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{
          backgroundColor: config.dot,
          animation: config.pulse
            ? 'pulse-dot 1.4s cubic-bezier(0.2, 0, 0, 1) infinite'
            : undefined,
        }}
      />
      {config.label}
    </span>
  );
}
