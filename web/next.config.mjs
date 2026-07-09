/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl && !apiUrl.startsWith('/api')) {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_INTERNAL_URL ?? 'http://127.0.0.1:8000'}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
};

export default nextConfig;
