'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AdminDashboardHeader,
  MetricsGrid,
  PaperFilters,
  PaperGrid,
  WorkflowOverview,
} from '@/features/admin-dashboard/components';
import {
  attentionStatuses,
  getMetrics,
  matchesStatusFilter,
  statusOptions,
  workflowStages,
  type StatusOption,
} from '@/features/admin-dashboard/data';
import { api, type Paper } from '@/lib/api';

export default function AdminHomePage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusOption['value']>('all');
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPapers = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) {
        setLoading(true);
      }
      setError('');
      const data = await api.get<Paper[]>('/papers');
      setPapers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '资料列表加载失败');
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, []);

  const hasProcessingPapers = useMemo(() => {
    return papers.some((p) => ['uploading', 'queued', 'parsing', 'modeling'].includes(p.status));
  }, [papers]);

  useEffect(() => {
    void loadPapers(true);
  }, [loadPapers]);

  useEffect(() => {
    if (!hasProcessingPapers) return;
    const timer = window.setInterval(() => {
      void loadPapers(false);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [hasProcessingPapers, loadPapers]);

  const filteredPapers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return papers.filter((paper) => {
      const matchesSearch =
        query.length === 0 ||
        paper.title.toLowerCase().includes(query) ||
        paper.source_file_name.toLowerCase().includes(query);

      return matchesSearch && matchesStatusFilter(paper, statusFilter);
    });
  }, [papers, search, statusFilter]);

  const metrics = useMemo(() => getMetrics(papers), [papers]);
  const attentionCount = useMemo(
    () => papers.filter((paper) => attentionStatuses.includes(paper.status)).length,
    [papers]
  );

  return (
    <div className="mx-auto flex max-w-[var(--max-width)] flex-col gap-6 px-4 py-6 sm:px-6 md:py-8">
      <AdminDashboardHeader
        totalCount={papers.length}
        attentionCount={attentionCount}
      />

      <MetricsGrid metrics={metrics} />

      <WorkflowOverview papers={papers} stages={workflowStages} />

      {error && (
        <div className="rounded-[var(--radius-md)] border border-[var(--color-error-500)] bg-[var(--color-error-bg)] px-4 py-3 text-sm text-[var(--color-error-text)]">
          {error}
        </div>
      )}

      <PaperFilters
        search={search}
        statusFilter={statusFilter}
        options={statusOptions}
        resultCount={filteredPapers.length}
        onSearchChange={setSearch}
        onStatusChange={setStatusFilter}
      />

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-[220px] animate-pulse rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg)]"
            />
          ))}
        </div>
      ) : (
        <PaperGrid papers={filteredPapers} />
      )}
    </div>
  );
}
