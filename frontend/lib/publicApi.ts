/**
 * Django API origin (scheme + host + port), no trailing slash.
 *
 * Production (Vercel, etc.): set NEXT_PUBLIC_API_BASE_URL at build time, e.g.
 *   https://your-backend.hf.space
 *
 * Legacy: NEXT_PUBLIC_API_URL may be the full /api prefix URL — we strip /api
 * to recover the origin.
 */
function resolvePublicApiBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (explicit) {
    return explicit.replace(/\/$/, '')
  }

  const legacy = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (legacy) {
    return legacy.replace(/\/$/, '').replace(/\/api\/?$/, '')
  }

  return 'http://127.0.0.1:8000'
}

export const PUBLIC_API_BASE_URL = resolvePublicApiBaseUrl()

/** Same origin + `/api` (Django routes are mounted under /api/). */
export const PUBLIC_API_ROOT = `${PUBLIC_API_BASE_URL}/api`
