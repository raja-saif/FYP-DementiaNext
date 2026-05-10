/**
 * Django origin only (no trailing slash, no /api suffix).
 * Set NEXT_PUBLIC_API_BASE_URL on Vercel to your deployed API, e.g. https://your-space.hf.space
 */
function resolvePublicApiBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (explicit) {
    return explicit.replace(/\/$/, '').replace(/\/api\/?$/, '')
  }
  const legacy = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, '')
  if (legacy) {
    return legacy.replace(/\/api\/?$/, '')
  }
  return 'http://127.0.0.1:8000'
}

export const PUBLIC_API_BASE_URL = resolvePublicApiBaseUrl()

/** Mount point for DRF routes (same as Django core.urls). */
export const PUBLIC_API_ROOT = `${PUBLIC_API_BASE_URL}/api`
