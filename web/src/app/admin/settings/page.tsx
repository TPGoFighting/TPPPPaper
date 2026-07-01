'use client';

import { useState } from 'react';

interface Provider {
  id: string;
  name: string;
  model: string;
  icon: React.ReactNode;
}

const providers: Provider[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    model: 'GPT-4o / GPT-4',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
      </svg>
    ),
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    model: 'Claude 3.5',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
        <path d="M8 12c0-2.21 1.79-4 4-4" />
        <path d="M12 16c2.21 0 4-1.79 4-4" />
      </svg>
    ),
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    model: 'DeepSeek-V3',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    ),
  },
  {
    id: 'custom',
    name: '自定义',
    model: '填写自定义信息',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
  },
];

const modelChips = ['gpt-4o', 'gpt-4o-mini', 'claude-3.5-sonnet', 'deepseek-chat'];

type ToastState = 'idle' | 'success' | 'error' | 'testing';

export default function SettingsPage() {
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const [modelInput, setModelInput] = useState('gpt-4o');
  const [advancedOpen, setAdvancedOpen] = useState(true);
  const [temperature, setTemperature] = useState(0.7);
  const [toast, setToast] = useState<ToastState>('idle');

  const testConnection = () => {
    setToast('testing');
    setTimeout(() => {
      setToast('success');
      setTimeout(() => setToast('idle'), 4000);
    }, 1200);
  };

  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 py-6 md:py-8">
      {/* 页头 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="w-10 h-10 rounded-[var(--radius-md)] bg-[var(--color-primary-50)] flex items-center justify-center text-[var(--color-primary)]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </span>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            模型配置
          </h1>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)]">
          配置大模型 API 连接，用于试卷智能解析与转换
        </p>
      </div>

      {/* 服务商选择 */}
      <section className="bg-[var(--color-bg)] rounded-[var(--radius-md)] shadow-sm border border-[var(--color-border-light)] p-5 sm:p-6 mb-5">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">
          选择 API 服务商
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {providers.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelectedProvider(p.id)}
              className={`relative flex items-center gap-3 p-4 rounded-[var(--radius-md)] border-2 text-left transition-all ${
                selectedProvider === p.id
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-50)]'
                  : 'border-[var(--color-border-light)] hover:border-[var(--color-border-hover)]'
              }`}
            >
              {selectedProvider === p.id && (
                <span className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[var(--color-primary)] flex items-center justify-center">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </span>
              )}
              <span
                className={`shrink-0 ${selectedProvider === p.id ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-secondary)]'}`}
              >
                {p.icon}
              </span>
              <div className="flex flex-col gap-0.5 min-w-0">
                <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {p.name}
                </span>
                <span className="text-xs text-[var(--color-text-tertiary)] truncate">
                  {p.model}
                </span>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* 连接配置 */}
      <section className="bg-[var(--color-bg)] rounded-[var(--radius-md)] shadow-sm border border-[var(--color-border-light)] p-5 sm:p-6 mb-5">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">
          连接配置
        </h2>

        {/* API Key */}
        <div className="mb-5">
          <label htmlFor="api-key" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
            API Key
          </label>
          <div className="relative">
            <input
              id="api-key"
              type={showKey ? 'text' : 'password'}
              placeholder="sk-xxxxxxxxxxxxxxxx"
              defaultValue="sk-demo-key-sample-xxxxx"
              autoComplete="off"
              className="w-full px-3 py-2.5 pr-11 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-2 focus:ring-[var(--color-primary-50)] transition-colors font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors"
              aria-label="显示或隐藏密钥"
            >
              {showKey ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-[var(--color-text-tertiary)]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>密钥仅存储在本地设备，不会上传至任何服务器</span>
          </div>
        </div>

        {/* Base URL */}
        <div className="mb-5">
          <label htmlFor="base-url" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
            Base URL
          </label>
          <input
            id="base-url"
            type="url"
            placeholder="https://api.openai.com/v1"
            defaultValue="https://api.openai.com/v1"
            className="w-full px-3 py-2.5 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-2 focus:ring-[var(--color-primary-50)] transition-colors"
          />
        </div>

        {/* Model */}
        <div>
          <label htmlFor="model-name" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
            模型
          </label>
          <input
            id="model-name"
            type="text"
            placeholder="gpt-4o"
            value={modelInput}
            onChange={(e) => setModelInput(e.target.value)}
            className="w-full px-3 py-2.5 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-2 focus:ring-[var(--color-primary-50)] transition-colors font-mono"
          />
          <div className="flex flex-wrap gap-2 mt-2.5">
            {modelChips.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setSelectedModel(m);
                  setModelInput(m);
                }}
                className={`px-3 py-1 text-xs font-medium rounded-[var(--radius-full)] transition-colors ${
                  selectedModel === m
                    ? 'text-[var(--color-primary)] bg-[var(--color-primary-50)] border border-[var(--color-primary-200)]'
                    : 'text-[var(--color-text-secondary)] bg-[var(--color-bg-subtle)] hover:bg-[var(--color-bg-hover)]'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 高级选项 */}
      <section className="bg-[var(--color-bg)] rounded-[var(--radius-md)] shadow-sm border border-[var(--color-border-light)] overflow-hidden mb-5">
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          className="w-full flex items-center justify-between p-5 sm:p-6 hover:bg-[var(--color-bg-hover)] transition-colors"
        >
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            高级选项
          </h2>
          <svg
            className="transition-transform duration-200"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              color: 'var(--color-text-tertiary)',
              transform: advancedOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {advancedOpen && (
          <div className="px-5 sm:px-6 pb-5 sm:pb-6 space-y-5 border-t border-[var(--color-border-light)] pt-5">
            <div>
              <div className="flex justify-between mb-2">
                <label htmlFor="timeout" className="text-sm font-medium text-[var(--color-text-primary)]">
                  请求超时
                </label>
                <span className="text-sm text-[var(--color-text-tertiary)]">60 秒</span>
              </div>
              <input
                id="timeout"
                type="number"
                defaultValue={60}
                min={10}
                max={300}
                step={10}
                className="w-full px-3 py-2.5 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)] transition-colors"
              />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <label htmlFor="max-tokens" className="text-sm font-medium text-[var(--color-text-primary)]">
                  最大 Token
                </label>
                <span className="text-sm text-[var(--color-text-tertiary)]">4096</span>
              </div>
              <input
                id="max-tokens"
                type="number"
                defaultValue={4096}
                min={256}
                max={128000}
                step={256}
                className="w-full px-3 py-2.5 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)] transition-colors"
              />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <label htmlFor="temperature" className="text-sm font-medium text-[var(--color-text-primary)]">
                  Temperature
                </label>
                <span className="text-sm font-semibold text-[var(--color-primary)]">
                  {temperature.toFixed(1)}
                </span>
              </div>
              <input
                id="temperature"
                type="range"
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-[var(--color-primary)]"
              />
              <div className="flex justify-between mt-1.5 text-xs text-[var(--color-text-tertiary)]">
                <span>0 (精确)</span>
                <span>2 (创意)</span>
              </div>
            </div>
            <div>
              <label htmlFor="system-prompt" className="text-sm font-medium text-[var(--color-text-primary)] block mb-2">
                System Prompt
              </label>
              <textarea
                id="system-prompt"
                placeholder="你是一个试卷解析助手..."
                rows={3}
                className="w-full px-3 py-2.5 text-sm bg-[var(--color-bg-page)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-border-focus)] transition-colors resize-y"
              />
            </div>
          </div>
        )}
      </section>

      {/* Toast */}
      {toast !== 'idle' && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 anim-fade-in"
          style={{ animation: 'tp-toast-in 0.3s ease-md3' }}
        >
          <div
            className={`flex items-center gap-3 px-4 py-3 rounded-[var(--radius-md)] shadow-lg ${
              toast === 'success'
                ? 'bg-[var(--color-success-bg)] text-[var(--color-success-600)]'
                : toast === 'error'
                ? 'bg-[var(--color-error-bg)] text-[var(--color-error-text)]'
                : 'bg-[var(--color-info-bg)] text-[var(--color-info-text)]'
            }`}
          >
            {toast === 'testing' ? (
              <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            )}
            <div>
              <span className="text-sm font-medium">
                {toast === 'testing' ? '正在测试连接...' : toast === 'success' ? '连接成功' : '连接失败'}
              </span>
              {toast === 'success' && (
                <p className="text-xs opacity-80">
                  模型 {modelInput || 'gpt-4o'} 响应正常，延迟 320ms
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={testConnection}
          disabled={toast === 'testing'}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-[var(--color-primary)] bg-[var(--color-bg)] border border-[var(--color-border)] rounded-[var(--radius-full)] hover:bg-[var(--color-bg-hover)] transition-colors disabled:opacity-50"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          测试连接
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] bg-[var(--color-primary)] rounded-[var(--radius-full)] hover:opacity-90 transition-opacity"
        >
          保存设置
        </button>
      </div>
    </div>
  );
}
