/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  // swcMinify removed — enabled by default since Next 13+ (avoid duplicate opt)
  experimental: {
    // framer-motion omitted: optimizePackageImports can break its module graph (webpack "__webpack_modules__[moduleId] is not a function")
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  onDemandEntries: {
    maxInactiveAge: 1000 * 60 * 60,
    pagesBufferLength: 20,
  },
}

module.exports = nextConfig
