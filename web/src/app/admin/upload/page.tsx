'use client';

import { useState, useCallback, useRef } from 'react';
import Link from 'next/link';

type UploadMode = 'faithful' | 'lecture';

interface SelectedFile {
  name: string;
  size: number;
  type: string;
}

export default function UploadPage() {
  const [mode, setMode] = useState<UploadMode>('faithful');
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile({ name: dropped.name, size: dropped.size, type: dropped.type });
    }
  }, []);

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile({ name: selected.name, size: selected.size, type: selected.type });
    }
  };

  const handleUpload = () => {
    if (!file) return;
    setUploading(true);
    setTimeout(() => {
      setUploading(false);
      window.location.href = '/admin';
    }, 1500);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const modes: {
    value: UploadMode;
    title: string;
    desc: string;
    icon: React.ReactNode;
  }[] = [
    {
      value: 'faithful',
      title: '忠实转写',
      desc: '保留原试卷结构，逐题转换为可交互网页，适合已有试卷的数字化',
      icon: (
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="8" y1="13" x2="16" y2="13" />
          <line x1="8" y1="17" x2="16" y2="17" />
        </svg>
      ),
    },
    {
      value: 'lecture',
      title: '讲义出题',
      desc: 'AI 阅读讲义内容，自动生成练习题与考点梳理，适合复习资料转化',
      icon: (
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6 md:py-8">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)] mb-6">
        <Link href="/admin" className="hover:text-[var(--color-primary)] transition-colors">
          首页
        </Link>
        <span>/</span>
        <span className="text-[var(--color-text-primary)]">上传资料</span>
      </div>

      <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)] mb-8">
        上传新资料
      </h1>

      {/* 步骤 1: 选择模式 */}
      <section className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="w-7 h-7 rounded-full bg-[var(--color-primary)] text-[var(--color-text-inverse)] text-sm font-bold flex items-center justify-center">
            1
          </span>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            选择转换模式
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {modes.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setMode(m.value)}
              className={`text-left p-5 rounded-[var(--radius-md)] border-2 transition-all ${
                mode === m.value
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)]'
                  : 'border-[var(--color-border-light)] bg-[var(--color-bg)] hover:border-[var(--color-border-hover)]'
              }`}
            >
              <div
                className={`w-10 h-10 rounded-[var(--radius-sm)] flex items-center justify-center mb-3 ${
                  mode === m.value
                    ? 'text-[var(--color-primary)] bg-[var(--color-bg)]'
                    : 'text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)]'
                }`}
              >
                {m.icon}
              </div>
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">
                {m.title}
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                {m.desc}
              </p>
            </button>
          ))}
        </div>
      </section>

      {/* 步骤 2: 上传文件 */}
      <section className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="w-7 h-7 rounded-full bg-[var(--color-primary)] text-[var(--color-text-inverse)] text-sm font-bold flex items-center justify-center">
            2
          </span>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            上传文件
          </h2>
        </div>

        {!file ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-[var(--radius-md)] border-2 border-dashed p-10 text-center transition-all ${
              dragging
                ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)]'
                : 'border-[var(--color-border)] hover:border-[var(--color-border-hover)] bg-[var(--color-bg)]'
            }`}
          >
            <div className="w-14 h-14 mx-auto rounded-full bg-[var(--color-primary-50)] flex items-center justify-center mb-4">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="text-sm font-medium text-[var(--color-text-primary)] mb-1">
              拖拽文件到此处，或点击选择
            </p>
            <p className="text-xs text-[var(--color-text-tertiary)]">
              支持 PDF、Word、图片格式，单个文件不超过 20MB
            </p>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
              onChange={handleSelect}
            />
          </div>
        ) : (
          <div className="bg-[var(--color-bg)] rounded-[var(--radius-md)] border border-[var(--color-border-light)] p-5">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-[var(--radius-sm)] bg-[var(--color-success-bg)] flex items-center justify-center shrink-0">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--color-success)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                  {file.name}
                </p>
                <p className="text-xs text-[var(--color-text-tertiary)]">
                  {formatSize(file.size)}
                </p>
              </div>
              {!uploading && (
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="p-2 text-[var(--color-text-tertiary)] hover:text-[var(--color-error-text)] hover:bg-[var(--color-error-bg)] rounded-[var(--radius-sm)] transition-colors"
                  aria-label="移除文件"
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
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
            {uploading && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-[var(--color-text-secondary)] mb-1.5">
                  <span>上传中...</span>
                  <span>processing</span>
                </div>
                <div className="h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-primary)] rounded-full"
                    style={{ animation: 'progress-indeterminate 1.5s ease-in-out infinite' }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 步骤 3: 确认提交 */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <span
            className={`w-7 h-7 rounded-full text-sm font-bold flex items-center justify-center transition-colors ${
              file
                ? 'bg-[var(--color-primary)] text-[var(--color-text-inverse)]'
                : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)]'
            }`}
          >
            3
          </span>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            确认并提交
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="inline-flex items-center justify-center gap-2 px-6 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <>
                <svg
                  className="animate-spin"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                提交中...
              </>
            ) : (
              '开始转换'
            )}
          </button>
          <Link
            href="/admin"
            className="inline-flex items-center justify-center px-6 py-2.5 text-sm font-semibold text-[var(--color-text-secondary)] bg-[var(--color-bg)] border border-[var(--color-border)] rounded-[var(--radius-full)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            取消
          </Link>
        </div>
      </section>
    </div>
  );
}
