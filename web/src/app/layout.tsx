import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'TPaper',
    template: '%s · TPaper',
  },
  description: 'AI 试卷转换工具 - 管理后台与公开页面',
  icons: {
    icon: '/brand/tp-logo.jpg',
    apple: '/brand/tp-logo.jpg',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#050505',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
