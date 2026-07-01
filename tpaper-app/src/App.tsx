import type { ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Home from './pages/Home'
import Login from './pages/Login'
import AdminHome from './pages/AdminHome'
import UploadWizard from './pages/UploadWizard'
import TaskProgress from './pages/TaskProgress'
import ReviewEditor from './pages/ReviewEditor'
import Publish from './pages/Publish'
import ModelConfig from './pages/ModelConfig'
import PublicReview from './pages/PublicReview'
import Navbar from './components/Navbar'
import Footer from './components/Footer'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100dvh] flex flex-col bg-[var(--color-bg-page)]">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}

function Protected({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AdminLayout>{children}</AdminLayout>
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/p/:slug" element={<PublicReview />} />

      {/* 管理路由（需要登录） */}
      <Route path="/admin" element={<Protected><AdminHome /></Protected>} />
      <Route path="/upload" element={<Protected><UploadWizard /></Protected>} />
      <Route path="/progress/:paperId" element={<Protected><TaskProgress /></Protected>} />
      <Route path="/editor/:paperId" element={<Protected><ReviewEditor /></Protected>} />
      <Route path="/publish/:paperId" element={<Protected><Publish /></Protected>} />
      <Route path="/models" element={<Protected><ModelConfig /></Protected>} />

      {/* 兜底 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
