/**
 * TPaper API 客户端封装
 * baseURL 从 NEXT_PUBLIC_API_URL 读取，默认 /api
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '/api';

export type PaperStatus =
  | 'uploading'
  | 'queued'
  | 'parsing'
  | 'modeling'
  | 'pending_review'
  | 'published'
  | 'partial_failed'
  | 'failed';

export type PaperMode = 'faithful' | 'lecture';
export type ApiPaperMode = 'faithful_transcription' | 'lecture_to_quiz';

export interface Paper {
  id: number;
  title: string;
  status: PaperStatus;
  mode: ApiPaperMode;
  slug: string;
  source_file_id?: number | null;
  source_file_name: string;
  question_count: number;
  created_at: string;
  updated_at: string;
  current_draft_id?: number | null;
  current_publication_id?: number | null;
  progress?: number;
  error_message?: string;
}

export interface Question {
  id: string;
  type: 'single_choice' | 'multi_choice' | 'true_false' | 'fill_blank' | 'subjective';
  number?: number | null;
  stem: string;
  options?: { key: string; text: string }[];
  correct_keys?: string[];
  true_false_answer?: boolean | null;
  acceptable_answers?: string[][];
  reference_answer?: string;
  explanation?: string;
  knowledge_points?: string[];
  answer_origin?: 'model_knowledge' | 'web_researched' | 'mixed' | 'needs_review';
  answer_sources?: { title: string; url: string; snippet?: string }[];
  needs_review?: boolean;
}

export interface Draft {
  id: number;
  paper_id: number;
  version: number;
  document: {
    title?: string;
    sections?: { id: string; title: string; question_ids: string[] }[];
    questions?: Question[];
    [key: string]: unknown;
  };
  presentation_html: string;
  theme_css: string;
  validation_result: { errors?: string[]; is_valid?: boolean };
  is_valid: boolean;
  created_at: string;
  updated_at: string;
}

export interface Publication {
  id: number;
  paper_id: number;
  version: number;
  compiled_html: string;
  compiled_css: string;
  content_hash: string;
  published_at: string;
  published_by: string;
  is_withdrawn: boolean;
}

export interface ModelProfile {
  id: number;
  name: string;
  protocol: 'openai_compatible' | 'anthropic_compatible';
  base_url: string;
  text_model: string;
  multimodal_model: string;
  supports_vision: boolean;
  timeout_seconds: number;
  max_concurrency: number;
  max_retries: number;
  allow_private_network: boolean;
  is_active: boolean;
  api_key_masked: string;
}

export interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

class ApiClientError extends Error implements ApiError {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.details = details;
  }
}

interface FetchOptions extends RequestInit {
  auth?: boolean;
  timeoutMs?: number;
}

async function request<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { auth: _auth = true, headers: customHeaders, timeoutMs = 30000, ...rest } = options;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (rest.method && rest.method !== 'GET' && rest.method !== 'HEAD') {
    headers['X-Requested-With'] = 'XMLHttpRequest';
  }

  const maxRetries = 2;
  let lastError: ApiClientError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${BASE_URL}${path}`, {
        ...rest,
        credentials: 'include',
        headers,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        let details: unknown;
        try {
          details = await res.json();
        } catch {
          // 响应非 JSON
        }
        const detailMsg =
          details && typeof details === 'object' && 'detail' in details && typeof (details as { detail: unknown }).detail === 'string'
            ? (details as { detail: string }).detail
            : `请求失败: ${res.status} ${res.statusText}`;
        const err = new ApiClientError(
          detailMsg,
          res.status,
          details
        );
        // 仅对 5xx 错误重试
        if (res.status >= 500 && attempt < maxRetries) {
          lastError = err;
          await new Promise(r => setTimeout(r, 500 * (attempt + 1)));
          continue;
        }
        throw err;
      }

      // 处理无内容响应
      if (res.status === 204) {
        return undefined as T;
      }

      return res.json() as Promise<T>;
    } catch (err) {
      if (err instanceof ApiClientError) {
        throw err;
      }
      const isTimeout = err instanceof Error && err.name === 'AbortError';
      const errMsg = isTimeout ? '网络请求超时' : `网络错误: ${err instanceof Error ? err.message : '未知'}`;
      // 网络错误重试
      if (attempt < maxRetries) {
        lastError = new ApiClientError(errMsg, 0);
        await new Promise(r => setTimeout(r, 500 * (attempt + 1)));
        continue;
      }
      throw lastError || new ApiClientError('网络错误', 0);
    }
  }

  throw lastError || new ApiClientError('请求失败', 0);
}

export const api = {
  get: <T>(path: string, options?: FetchOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    request<T>(path, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    request<T>(path, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    request<T>(path, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string, options?: FetchOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
  upload: async <T>(path: string, formData: FormData, options: FetchOptions = {}) => {
    const { auth: _auth = true, headers: customHeaders, ...rest } = options;
    const headers: Record<string, string> = {
      'X-Requested-With': 'XMLHttpRequest',
      ...(customHeaders as Record<string, string>),
    };

    // 上传大文件时 Cloudflare 可能引入显著延迟（~10s+），使用较长超时
    const controller = new AbortController();
    const uploadTimeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 120000);

    try {
      const res = await fetch(`${BASE_URL}${path}`, {
        ...rest,
        method: 'POST',
        body: formData,
        credentials: 'include',
        headers,
        signal: controller.signal,
      });

      if (!res.ok) {
        let details: unknown;
        try {
          details = await res.json();
        } catch {}
        throw new ApiClientError(`请求失败: ${res.status} ${res.statusText}`, res.status, details);
      }

      return res.json() as Promise<T>;
    } finally {
      clearTimeout(uploadTimeout);
    }
  },
};

export { ApiClientError };
