export default function Footer() {
  return (
    <footer className="py-8 bg-[var(--color-bg)] border-t border-[var(--color-border-light)]">
      <div className="mx-auto max-w-[var(--max-width)] px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[var(--color-text-tertiary)]">
        <p>TPaper &middot; AI 试卷转换工具</p>
        <p>&copy; 2025 TPaper. All rights reserved.</p>
      </div>
    </footer>
  )
}
