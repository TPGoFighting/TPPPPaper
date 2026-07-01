// 枚举
export type PaperMode = 'faithful_transcription' | 'lecture_to_quiz'
export type PaperStatus = 'uploading' | 'queued' | 'parsing' | 'modeling' | 'pending_review' | 'published' | 'partial_failed' | 'failed'
export type QuestionType = 'single_choice' | 'multi_choice' | 'true_false' | 'fill_blank' | 'subjective'
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

// PaperDocument 结构（SPEC 第12节）
export interface MediaRef {
  asset_id?: number
  storage_key?: string
  alt_text: string
  source_page?: number
}
export interface QuestionOption {
  key: string
  text: string
}
export interface Question {
  id: string
  number?: number
  type: QuestionType
  stem: string
  media: MediaRef[]
  score: number
  options: QuestionOption[]
  correct_keys: string[]
  true_false_answer?: boolean | null
  acceptable_answers: string[][]
  match_rule: string
  reference_answer: string
  scoring_points: string[]
  explanation: string
  knowledge_points: string[]
  source_page?: number
  confidence: number
  needs_review: boolean
  is_ai_generated: boolean
}
export interface Section {
  id: string
  title: string
  source_page?: number
  question_ids: string[]
}
export interface PaperDocument {
  title: string
  language: string
  metadata: Record<string, any>
  sections: Section[]
  questions: Question[]
}

// API 响应类型
export interface Paper {
  id: number
  title: string
  slug: string
  mode: PaperMode
  status: PaperStatus
  current_draft_id?: number
  current_publication_id?: number
  created_at: string
  updated_at: string
}
export interface ModelProfile {
  id: number
  name: string
  protocol: string
  base_url: string
  text_model: string
  multimodal_model: string
  supports_vision: boolean
  timeout_seconds: number
  max_concurrency: number
  max_retries: number
  allow_private_network: boolean
  is_active: boolean
  api_key_masked: string
}
export interface ModelProfileCreate {
  name: string
  protocol?: string
  base_url: string
  api_key?: string
  text_model?: string
  multimodal_model?: string
  supports_vision?: boolean
  timeout_seconds?: number
  max_concurrency?: number
  max_retries?: number
  allow_private_network?: boolean
}
export interface ModelProfileUpdate extends Partial<ModelProfileCreate> {
  is_active?: boolean
}
export interface Job {
  id: number
  paper_id: number
  job_type: string
  status: JobStatus
  stage: string
  current_page: number
  total_pages: number
  failed_pages: number[]
  retry_count: number
  error_code?: string
  error_message?: string
  call_summary: Record<string, any>
  created_at: string
  updated_at: string
}
export interface Draft {
  id: number
  paper_id: number
  version: number
  document: PaperDocument
  presentation_html: string
  theme_css: string
  validation_result: { errors: string[]; is_valid: boolean }
  is_valid: boolean
  created_at: string
  updated_at: string
}
export interface Publication {
  id: number
  paper_id: number
  version: number
  compiled_html: string
  compiled_css: string
  content_hash: string
  source_draft_version?: number
  published_at: string
  published_by: string
  is_withdrawn: boolean
}
export interface SourceFile {
  id: number
  original_filename: string
  mime_type: string
  size_bytes: number
  page_count?: number
  expires_at: string
  deleted_at?: string
}
export interface UploadResult {
  paper_id: number
  slug: string
  source_file_id: number
}
export interface PrecheckResult {
  can_publish: boolean
  issues: string[]
  removed: string[]
  clean_html_preview: string
}
export interface TestConnectionResult {
  success: boolean
  model: string
  latency_ms: number
  usage: Record<string, number>
  error: string
}
export interface PublicPaper {
  slug: string
  title: string
  version: number
  content_hash: string
  published_at: string
  compiled_html: string
  compiled_css: string
  document: PaperDocument
}
