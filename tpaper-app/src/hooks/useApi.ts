import { useState, useEffect, useCallback, useRef } from 'react'

interface UseApiOptions {
  pollInterval?: number  // 轮询间隔（毫秒）
  enabled?: boolean      // 是否启用
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: any[] = [],
  options: UseApiOptions = {}
) {
  const { pollInterval, enabled = true } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const refetch = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (e: any) {
      setError(e.message || '请求失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!enabled) return
    refetch()
    if (pollInterval) {
      const timer = setInterval(refetch, pollInterval)
      return () => clearInterval(timer)
    }
  }, [...deps, enabled, pollInterval, refetch])

  return { data, error, loading, refetch }
}
