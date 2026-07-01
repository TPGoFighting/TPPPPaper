import { useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { publicService } from '../api/services'

export default function PublicReview() {
  const { slug } = useParams<{ slug: string }>()
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!slug) return
    ;(async () => {
      try {
        const paper = await publicService.getPaper(slug)
        setTitle(paper.title)
      } catch (e: any) {
        setError(e.message || '加载失败')
      } finally {
        setLoading(false)
      }
    })()
  }, [slug])

  if (loading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-[#f5f5f7]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0071e3]" />
      </div>
    )
  }

  if (error || !slug) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-[#f5f5f7] p-6">
        <div className="text-center max-w-md">
          <p className="text-lg font-semibold text-[#1d1d1f] mb-2">无法加载试卷</p>
          <p className="text-sm text-[#6e6e73]">{error || '试卷不存在或已下线'}</p>
        </div>
      </div>
    )
  }

  // 通过 iframe 加载后端渲染的完整试卷页面
  const pageUrl = `/api/public/papers/${slug}/page`

  return (
    <div className="fixed inset-0 bg-[#f5f5f7]">
      <iframe
        src={pageUrl}
        title={title}
        className="w-full h-full border-0"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  )
}