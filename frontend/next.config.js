/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  // Avoid experimental.optimizePackageImports — it has caused production webpack
  // "Cannot read properties of undefined (reading 'call')" / broken chunks on Vercel.
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  onDemandEntries: {
    maxInactiveAge: 1000 * 60 * 60,
    pagesBufferLength: 20,
  },
}

module.exports = nextConfig
