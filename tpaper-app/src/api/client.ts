const BASE_URL = '/api'

class ApiClient {
  private async request<T>(method: string, path: string, body?: any, skipAuthRedirect = false): Promise<T> {
    const headers: Record<string, string> = {
      'X-Requested-With': 'XMLHttpRequest',
    }
    let options: RequestInit = { method, headers, credentials: 'include' }
    if (body !== undefined) {
      if (body instanceof FormData) {
        options.body = body
      } else {
        headers['Content-Type'] = 'application/json'
        options.body = JSON.stringify(body)
      }
    }
    const res = await fetch(`${BASE_URL}${path}`, options)
    if (res.status === 401 && !skipAuthRedirect) {
      window.location.href = '/login'
      throw new Error('未登录')
    }
    if (res.status === 204) return undefined as T
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`)
    }
    return data
  }
  get<T>(path: string, skipAuth?: boolean) { return this.request<T>('GET', path, undefined, skipAuth) }
  post<T>(path: string, body?: any) { return this.request<T>('POST', path, body) }
  patch<T>(path: string, body?: any) { return this.request<T>('PATCH', path, body) }
  delete<T>(path: string) { return this.request<T>('DELETE', path) }
}

export const apiClient = new ApiClient()
