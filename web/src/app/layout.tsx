import type { Metadata, Viewport } from 'next';
import { Geist, Noto_Sans_SC } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  subsets: ['latin'],
  variable: '--font-geist',
  display: 'swap',
});

const notoSansSC = Noto_Sans_SC({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-sans-sc',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'TPaper',
    template: '%s · TPaper',
  },
  description: 'AI 试卷转换工具 - 管理后台与公开页面',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#1a73e8',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${notoSansSC.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
