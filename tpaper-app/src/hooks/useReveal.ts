import { useEffect } from 'react'

/**
 * 滚动渐入动画 hook：监听元素进入视口时添加 revealed 类。
 * 尊重 prefers-reduced-motion 偏好。
 */
export function useReveal() {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches

    const elements = document.querySelectorAll('.reveal')

    if (prefersReducedMotion) {
      elements.forEach((el) => el.classList.add('revealed'))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.1 },
    )

    elements.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])
}
