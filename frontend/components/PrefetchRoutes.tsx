'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'

const ROUTES_TO_PREFETCH = [
  '/login',
  '/signup',
  '/patient-dashboard',
  '/doctor-dashboard',
  '/detection',
  '/companion',
  '/companion/life-story',
  '/explainable-ai',
]

/**
 * Warm route JS chunks only. Avoid fetch(route) loops — they hammer the dev
 * server and can contribute to flaky CSS/chunk delivery in development.
 */
export default function PrefetchRoutes() {
  const router = useRouter()
  const hasWarmed = useRef(false)

  useEffect(() => {
    if (hasWarmed.current) return
    hasWarmed.current = true

    const timer = setTimeout(() => {
      ROUTES_TO_PREFETCH.forEach((route) => {
        try {
          router.prefetch(route)
        } catch {
          /* ignore */
        }
      })
    }, 800)

    return () => clearTimeout(timer)
  }, [router])

  return null
}
