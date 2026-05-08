/** @type {import(next).NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: (process.env.NEXT_PUBLIC_API_URL || 'http://backend:8080') + '/:path*',
      },
    ]
  },
}

module.exports = nextConfig
