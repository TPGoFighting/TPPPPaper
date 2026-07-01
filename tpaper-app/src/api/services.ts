import { apiClient } from './client'
import type {
  Paper, ModelProfile, ModelProfileCreate, ModelProfileUpdate,
  Job, Draft, Publication, UploadResult, PrecheckResult,
  TestConnectionResult, PublicPaper, PaperDocument, Question,
} from './types'

// Auth
export const authService = {
  login: (username: string, password: string) =>
    apiClient.post<{ username: string; logged_in: boolean }>('/auth/login', { username, password }),
  logout: () => apiClient.post('/auth/logout'),
  me: () => apiClient.get<{ username: string; role: string }>('/auth/me', true),
}

// Papers
export const paperService = {
  list: (params?: { status?: string; q?: string }) => {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.q) query.set('q', params.q)
    const qs = query.toString()
    return apiClient.get<Paper[]>(`/papers${qs ? '?' + qs : ''}`)
  },
  get: (id: number) => apiClient.get<Paper>(`/papers/${id}`),
  create: (title: string, mode: string) => apiClient.post<Paper>('/papers', { title, mode }),
  delete: (id: number) => apiClient.delete(`/papers/${id}`),
  reprocess: (id: number) => apiClient.post(`/papers/${id}/reprocess`),
}

// Uploads
export const uploadService = {
  init: (filename: string, mimeType: string, sizeBytes: number, mode: string) => {
    const params = new URLSearchParams({ filename, mime_type: mimeType, size_bytes: String(sizeBytes), mode })
    return apiClient.post(`/uploads/init?${params.toString()}`)
  },
  upload: (file: File, mode: string) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<UploadResult>(`/uploads/file?mode=${mode}`, formData)
  },
}

// Jobs
export const jobService = {
  get: (id: number) => apiClient.get<Job>(`/jobs/${id}`),
  listByPaper: (paperId: number) => apiClient.get<Job[]>(`/jobs/paper/${paperId}`),
  cancel: (id: number) => apiClient.post(`/jobs/${id}/cancel`),
  retry: (id: number) => apiClient.post(`/jobs/${id}/retry`),
}

// Drafts
export const draftService = {
  get: (id: number) => apiClient.get<Draft>(`/drafts/${id}`),
  update: (id: number, data: { document?: PaperDocument; presentation_html?: string; theme_css?: string }) =>
    apiClient.patch<Draft>(`/drafts/${id}`, data),
  validate: (id: number) => apiClient.post<{ is_valid: boolean; errors: string[] }>(`/drafts/${id}/validate`),
  aiModify: (draftId: number, questionId: string, instruction: string) =>
    apiClient.post<{ modified_question: Question }>(`/drafts/${draftId}/ai-modify`, { question_id: questionId, instruction }),
}

// Publications
export const publicationService = {
  precheck: (draftId: number) => apiClient.post<PrecheckResult>(`/publications/precheck?draft_id=${draftId}`),
  publish: (draftId: number) => apiClient.post<Publication>('/publications', { draft_id: draftId }),
  get: (id: number) => apiClient.get<Publication>(`/publications/${id}`),
  listByPaper: (paperId: number) => apiClient.get<Publication[]>(`/publications/paper/${paperId}`),
  withdraw: (id: number) => apiClient.post(`/publications/${id}/withdraw`),
}

// Model Profiles
export const modelService = {
  list: () => apiClient.get<ModelProfile[]>('/model-profiles'),
  get: (id: number) => apiClient.get<ModelProfile>(`/model-profiles/${id}`),
  create: (data: ModelProfileCreate) => apiClient.post<ModelProfile>('/model-profiles', data),
  update: (id: number, data: ModelProfileUpdate) => apiClient.patch<ModelProfile>(`/model-profiles/${id}`, data),
  delete: (id: number) => apiClient.delete(`/model-profiles/${id}`),
  testConnection: (data: { base_url: string; api_key: string; model: string; allow_private_network?: boolean }) =>
    apiClient.post<TestConnectionResult>('/model-profiles/test-connection', data),
}

// Public
export const publicService = {
  getPaper: (slug: string) => apiClient.get<PublicPaper>(`/public/papers/${slug}`),
}
