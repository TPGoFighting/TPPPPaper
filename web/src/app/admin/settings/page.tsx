'use client';

import { useEffect, useState } from 'react';
import { api, type ModelProfile } from '@/lib/api';

const DEFAULT_PROFILE = {
  name: 'LongCat',
  base_url: 'https://api.longcat.chat/anthropic',
  text_model: 'LongCat-2.0',
  multimodal_model: 'LongCat-2.0',
  timeout_seconds: 90,
  supports_vision: false,
  allow_private_network: false,
};

type SaveState = 'idle' | 'saving' | 'testing' | 'success' | 'error';

export default function SettingsPage() {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [name, setName] = useState(DEFAULT_PROFILE.name);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_PROFILE.base_url);
  const [apiKey, setApiKey] = useState('');
  const [textModel, setTextModel] = useState(DEFAULT_PROFILE.text_model);
  const [timeout, setTimeoutValue] = useState(DEFAULT_PROFILE.timeout_seconds);
  const [supportsVision, setSupportsVision] = useState(DEFAULT_PROFILE.supports_vision);
  const [state, setState] = useState<SaveState>('idle');
  const [message, setMessage] = useState('');

  useEffect(() => {
    async function loadProfiles() {
      try {
        const data = await api.get<ModelProfile[]>('/model-profiles');
        setProfiles(data);
        const active = data.find((profile) => profile.is_active) ?? data[0];
        if (active) {
          setActiveId(active.id);
          setName(active.name);
          setBaseUrl(active.base_url);
          setTextModel(active.text_model);
          setTimeoutValue(active.timeout_seconds);
          setSupportsVision(active.supports_vision);
        }
      } catch (err) {
        setMessage(err instanceof Error ? err.message : '模型配置加载失败');
        setState('error');
      }
    }

    void loadProfiles();
  }, []);

  async function saveProfile() {
    try {
      setState('saving');
      setMessage('');
      const payload = {
        name,
        protocol: 'openai_compatible',
        base_url: baseUrl,
        api_key: apiKey,
        text_model: textModel,
        multimodal_model: textModel,
        supports_vision: supportsVision,
        timeout_seconds: timeout,
        max_concurrency: 2,
        max_retries: 2,
        allow_private_network: false,
        is_active: true,
      };
      const saved = activeId
        ? await api.patch<ModelProfile>(`/model-profiles/${activeId}`, payload)
        : await api.post<ModelProfile>('/model-profiles', payload);
      setActiveId(saved.id);
      setProfiles((current) => {
        const rest = current.filter((profile) => profile.id !== saved.id);
        return [saved, ...rest];
      });
      setApiKey('');
      setState('success');
      setMessage('配置已保存，后续上传会使用该模型处理。');
    } catch (err) {
      setState('error');
      setMessage(err instanceof Error ? err.message : '保存失败');
    }
  }

  async function testConnection() {
    if (!apiKey && !activeId) {
      setState('error');
      setMessage('测试连接需要填写 API Key 或选择已保存的模型配置。');
      return;
    }

    try {
      setState('testing');
      setMessage('');
      const result = await api.post<{
        success: boolean;
        latency_ms: number;
        model: string;
        error?: string;
      }>('/model-profiles/test-connection', {
        profile_id: activeId ?? undefined,
        base_url: baseUrl,
        api_key: apiKey || undefined,
        model: textModel,
        allow_private_network: false,
      });
      if (!result.success) {
        throw new Error(result.error || '连接失败');
      }
      setState('success');
      setMessage(`连接成功，模型 ${result.model || textModel}，延迟 ${result.latency_ms}ms。`);
    } catch (err) {
      setState('error');
      setMessage(err instanceof Error ? err.message : '连接失败');
    }
  }

  const activeProfile = profiles.find((p) => p.id === activeId) ?? profiles[0];

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6 md:py-8">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary)]">
          Model Core
        </p>
        <h1 className="mt-2 text-2xl md:text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
          模型配置
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          用 LongCat 或其他兼容模型把资料解析成结构化试卷。
        </p>
      </div>

      <section className="rounded-[var(--radius-md)] border border-[var(--color-border-light)] bg-[var(--color-bg)] p-5 sm:p-6">
        <div className="grid gap-5">
          <Field label="配置名称">
            <input value={name} onChange={(event) => setName(event.target.value)} className="tp-input" />
          </Field>
          <Field label="Base URL">
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} className="tp-input font-mono" />
          </Field>
          <Field label="API Key">
            <input
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              type="password"
              placeholder={activeProfile?.api_key_masked || '留空保留已加密密钥 (ak_...)'}
              className="tp-input font-mono"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="模型">
              <input value={textModel} onChange={(event) => setTextModel(event.target.value)} className="tp-input font-mono" />
            </Field>
            <Field label="超时秒数">
              <input
                type="number"
                min={10}
                max={300}
                value={timeout}
                onChange={(event) => setTimeoutValue(Number(event.target.value))}
                className="tp-input"
              />
            </Field>
          </div>
          <label className="flex items-center justify-between rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-page)] px-4 py-3">
            <span>
              <span className="block text-sm font-medium text-[var(--color-text-primary)]">启用视觉能力</span>
              <span className="text-xs text-[var(--color-text-tertiary)]">图片资料会尝试走多模态识别</span>
            </span>
            <input
              type="checkbox"
              checked={supportsVision}
              onChange={(event) => setSupportsVision(event.target.checked)}
              className="h-4 w-4 accent-[var(--color-primary)]"
            />
          </label>
        </div>

        {message && (
          <div
            className={`mt-5 rounded-[var(--radius-sm)] px-4 py-3 text-sm ${
              state === 'error'
                ? 'bg-[var(--color-error-bg)] text-[var(--color-error-text)]'
                : 'bg-[var(--color-success-bg)] text-[var(--color-success-text)]'
            }`}
          >
            {message}
          </div>
        )}

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={testConnection}
            disabled={state === 'testing'}
            className="tp-button-secondary"
          >
            {state === 'testing' ? '测试中...' : '测试连接'}
          </button>
          <button
            type="button"
            onClick={saveProfile}
            disabled={state === 'saving'}
            className="tp-button-primary"
          >
            {state === 'saving' ? '保存中...' : '保存配置'}
          </button>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-[var(--color-text-primary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
