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

export interface Paper {
  id: string;
  title: string;
  status: PaperStatus;
  mode: PaperMode;
  source_file: string;
  question_count: number;
  created_at: string;
  updated_at: string;
  slug?: string;
  progress?: number;
  error?: string;
}

export interface Question {
  id: string;
  type: 'single_choice' | 'multiple_choice' | 'true_false' | 'short_answer';
  stem: string;
  options?: string[];
  answer?: string;
  explanation?: string;
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

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem('tpaper_token');
}

interface FetchOptions extends RequestInit {
  auth?: boolean;
}

async function request<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { auth = true, headers: customHeaders, ...rest } = options;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (auth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers,
  });

  if (!res.ok) {
    let details: unknown;
    try {
      details = await res.json();
    } catch {
      // 响应非 JSON
    }
    throw new ApiClientError(
      `请求失败: ${res.status} ${res.statusText}`,
      res.status,
      details
    );
  }

  // 处理无内容响应
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
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
};

export { ApiClientError };
