'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';

interface PublicPaper {
  slug: string;
  title: string;
  version: number;
  content_hash: string;
  published_at: string;
  compiled_html: string;
  compiled_css: string;
}

export default function PublicPaperPage() {
  const params = useParams<{ slug: string }>();
  const [paper, setPaper] = useState<PublicPaper | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isSubscribed = true;

    async function loadPublicPaper() {
      try {
        const data = await api.get<PublicPaper>(`/public/papers/${params.slug}`, { auth: false });
        if (isSubscribed) {
          setPaper(data);
        }
      } catch (err) {
        if (isSubscribed) {
          setError(err instanceof Error ? err.message : '页面加载失败');
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    void loadPublicPaper();

    return () => {
      isSubscribed = false;
    };
  }, [params.slug]);

  // 当 paper 挂载完成后，激活并运行注入 HTML 中的交互 Runtime <script>
  useEffect(() => {
    if (!paper || !containerRef.current) return;
    const container = containerRef.current;
    const oldScripts = Array.from(container.querySelectorAll('script'));

    oldScripts.forEach((oldScript) => {
      const newScript = document.createElement('script');
      Array.from(oldScript.attributes).forEach((attr) => {
        newScript.setAttribute(attr.name, attr.value);
      });
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode?.replaceChild(newScript, oldScript);
    });
  }, [paper]);

  if (loading) {
    return (
      <main className="grid min-h-[100dvh] place-items-center bg-[var(--color-bg-page)] px-4 text-sm text-[var(--color-text-secondary)]">
        加载复习页...
      </main>
    );
  }

  if (!paper) {
    return (
      <main className="grid min-h-[100dvh] place-items-center bg-[var(--color-bg-page)] px-4">
        <div className="max-w-sm text-center">
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">页面不可用</h1>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] bg-white">
      <style dangerouslySetInnerHTML={{ __html: paper.compiled_css }} />
      <div ref={containerRef} dangerouslySetInnerHTML={{ __html: paper.compiled_html }} />
    </main>
  );
}
