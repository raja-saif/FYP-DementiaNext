import type { Metadata } from 'next'
/** Global styles must load before any other imports that pull CSS-dependent UI. */
import './globals.css'
import { Inter, JetBrains_Mono } from 'next/font/google'
import Providers from './providers'
import PrefetchRoutes from '@/components/PrefetchRoutes'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'DementiaNext - Advanced Dementia Detection & Monitoring',
  description: 'AI-powered dementia detection, classification, and monitoring system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrains.variable}`}>
      <body className={`${inter.className} antialiased bg-background text-foreground`}>
        <Providers>
          <PrefetchRoutes />
          {children}
        </Providers>
      </body>
    </html>
  )
}
