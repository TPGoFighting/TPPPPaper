'use client';

import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="grid min-h-[100dvh] place-items-center bg-[var(--color-bg-page)] px-4">
          <div className="max-w-sm text-center">
            <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
              页面出错了
            </h1>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
              {this.state.error?.message || '未知错误'}
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-4 py-2 text-sm font-medium text-white bg-[var(--color-primary)] rounded-[var(--radius-sm)] hover:opacity-90 transition-opacity"
              >
                重试
              </button>
              <a
                href="/admin"
                className="px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] border border-[var(--color-border-light)] rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-hover)] transition-colors"
              >
                返回工作台
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
