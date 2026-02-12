'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  Brain, 
  Scan, 
  Stethoscope, 
  Lock, 
  Mail, 
  Sparkles, 
  Loader2,
  Activity,
  Microscope,
  Heart,
  Shield,
  Zap,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

declare global {
  interface Window {
    google?: any
  }
}

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isGoogleReady, setIsGoogleReady] = useState(false)
  const router = useRouter()
  const { login, user } = useAuth()

  // Load Google Identity Services
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => {
      setIsGoogleReady(true)
    }
    document.body.appendChild(script)

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script)
      }
    }
  }, [])

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      if (user.role === 'patient') {
        router.push('/patient-dashboard')
      } else if (user.role === 'doctor') {
        router.push('/doctor-dashboard')
      }
    }
  }, [user, router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    const result = await login(email, password)
    
    if (result.success) {
      // Redirect based on user role (will be handled by useEffect after user state updates)
    } else {
      setError(result.error || 'Invalid email or password')
    }
    
    setIsLoading(false)
  }

  const handleGoogleLogin = () => {
    if (!isGoogleReady || !window.google) {
      setError('Google Sign-In is not loaded yet. Please try again.')
      return
    }

    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
    if (!clientId) {
      setError('Google OAuth is not configured.')
      return
    }

    setError('')
    setIsLoading(true)

    try {
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: 'email profile',
        ux_mode: 'popup',
        callback: async (tokenResponse: any) => {
          if (tokenResponse.error) {
            setError(`Google login failed: ${tokenResponse.error}`)
            setIsLoading(false)
            return
          }

          try {
            const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
              headers: {
                Authorization: `Bearer ${tokenResponse.access_token}`,
              },
            })

            if (!userInfoResponse.ok) {
              throw new Error('Failed to get user info from Google')
            }

            const userInfo = await userInfoResponse.json()
            const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiBase}/api/auth/google`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                email: userInfo.email,
                name: userInfo.name,
                google_id: userInfo.sub,
                role: 'patient', // Default role for Google login
              }),
            })

            const data = await response.json()

            if (response.ok) {
              localStorage.setItem('authToken', data.token)
              if (data.user.role === 'patient') {
                router.push('/patient-dashboard')
              } else {
                router.push('/doctor-dashboard')
              }
            } else {
              setError(data.error || 'Google login failed')
              setIsLoading(false)
            }
          } catch (err) {
            setError('Failed to authenticate with Google. Please try again.')
            setIsLoading(false)
          }
        },
      })

      tokenClient.requestAccessToken()
    } catch (err) {
      setError('Failed to initialize Google Sign-In.')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50 relative overflow-hidden">
      {/* Professional Medical Background */}
      <div className="absolute inset-0">
        {/* MRI Scan Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-10 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl animate-pulse"></div>
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-teal-200 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-green-200 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        </div>

        {/* Floating Medical Elements */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(8)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-16 h-16 opacity-10"
              style={{
                left: `${15 + i * 12}%`,
                top: `${10 + i * 10}%`,
              }}
              animate={{
                y: [0, -30, 0],
                rotate: [0, 180, 360],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 15 + i * 2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 1.5,
              }}
            >
              <Brain className="w-full h-full text-blue-600" />
            </motion.div>
          ))}
        </div>

        {/* Scan Lines Animation */}
        <motion.div
          animate={{
            x: [0, 100, 0],
            opacity: [0.1, 0.3, 0.1],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-400/20 to-transparent"
        />
      </div>

      <div className="relative flex items-center justify-center min-h-screen p-4">
        <div className="w-full max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Side - Logo/Brand Visual Only (no text) */}
          <motion.div
            initial={{ opacity: 0, x: -100 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, type: "spring" }}
            className="hidden lg:block"
          >
            {/* Professional MRI Scanner */}
            <div className="relative mb-16">
              <motion.div
                animate={{
                  scale: [1, 1.02, 1],
                  rotateY: [0, 2, 0],
                }}
                transition={{
                  duration: 6,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="relative"
              >
                {/* MRI Scanner Frame */}
                <div className="w-96 h-96 mx-auto bg-gradient-to-br from-white to-blue-50 rounded-3xl border-4 border-blue-200 shadow-2xl relative overflow-hidden">
                  {/* Professional Scanner Ring */}
                  <div className="absolute inset-6 border-4 border-blue-300 rounded-full animate-spin" style={{ animationDuration: '12s' }}>
                    <div className="absolute inset-3 border-2 border-cyan-300 rounded-full animate-spin" style={{ animationDuration: '8s', animationDirection: 'reverse' }}>
                      <div className="absolute inset-3 border border-teal-300 rounded-full animate-spin" style={{ animationDuration: '6s' }}>
                      </div>
                    </div>
                  </div>
                  
                  {/* Brain Scan Visualization */}
                  <div className="absolute inset-12 flex items-center justify-center">
                    <motion.div
                      animate={{
                        scale: [0.9, 1.1, 0.9],
                        opacity: [0.7, 1, 0.7],
                      }}
                      transition={{
                        duration: 4,
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                      className="w-32 h-32 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-2xl"
                    >
                      <Brain className="w-16 h-16 text-white" />
                    </motion.div>
                  </div>

                  {/* Professional Scan Lines */}
                  <motion.div
                    animate={{
                      y: [0, 400, 0],
                    }}
                    transition={{
                      duration: 3,
                      repeat: Infinity,
                      ease: "linear"
                    }}
                    className="absolute w-full h-1 bg-gradient-to-r from-transparent via-blue-400 to-transparent opacity-60"
                  />
                </div>

                {/* Medical Status Indicators */}
                <div className="absolute -top-6 -right-6 w-16 h-16 bg-red-500 rounded-full flex items-center justify-center shadow-lg animate-pulse">
                  <Heart className="w-8 h-8 text-white" />
                </div>
                <div className="absolute -bottom-6 -left-6 w-16 h-16 bg-green-500 rounded-full flex items-center justify-center shadow-lg animate-pulse" style={{ animationDelay: '0.5s' }}>
                  <Activity className="w-8 h-8 text-white" />
                </div>
                <div className="absolute top-1/2 -left-10 w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-pulse" style={{ animationDelay: '1s' }}>
                  <Microscope className="w-6 h-6 text-white" />
                </div>
                <div className="absolute top-1/4 -right-8 w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center shadow-lg animate-pulse" style={{ animationDelay: '1.5s' }}>
                  <Zap className="w-6 h-6 text-white" />
                </div>
              </motion.div>
            </div>

            {/* Branding title */}
            <motion.div 
              className="text-center mt-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <h1 className="text-7xl font-bold bg-gradient-to-r from-blue-600 via-teal-600 to-green-600 bg-clip-text text-transparent mb-4">
                DementiaNext
              </h1>
            </motion.div>
          </motion.div>

          {/* Right Side - Professional Login Form */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-lg mx-auto">
            <Card className="bg-white/90 backdrop-blur-xl border-blue-200 shadow-2xl">
              <CardHeader className="text-center pb-8">
                <div className="flex justify-center mb-6">
                  <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-2xl">
                    <Brain className="w-10 h-10 text-white" />
                  </div>
                </div>
                <CardTitle className="text-2xl font-bold text-gray-900">Sign in</CardTitle>
                <CardDescription className="text-gray-600">Access your account</CardDescription>
              </CardHeader>
              
              <CardContent>
                {/* Error Message */}
                {error && (
                  <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center space-x-2">
                    <AlertCircle className="w-5 h-5" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleLogin} className="space-y-6">
                  {/* Email Input */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6 }}
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <Input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your@email.com"
                        className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Password Input */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.7 }}
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Secure Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <Input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter secure password"
                        className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Login Button */}
                  <div>
                    <Button
                      type="submit"
                      disabled={isLoading}
                      className="w-full py-7 text-lg font-semibold bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Accessing Medical Portal...
                        </>
                      ) : (
                        <>
                          <Shield className="mr-2 h-5 w-5" />
                          Access Medical Platform
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Divider */}
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-300"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="px-2 bg-white text-gray-500">or continue with</span>
                    </div>
                  </div>

                  {/* Google Login Button */}
                  <div>
                    <Button
                      type="button"
                      onClick={handleGoogleLogin}
                      disabled={isLoading || !isGoogleReady}
                      className="w-full py-7 text-lg font-semibold bg-white hover:bg-gray-50 text-gray-900 border-2 border-gray-300 hover:border-gray-400 shadow-lg hover:shadow-xl transition-all duration-300"
                    >
                      {isGoogleReady ? (
                        <>
                          <svg className="mr-3 h-6 w-6" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                          </svg>
                          Sign in with Google
                        </>
                      ) : (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Loading Google...
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Sign Up Link */}
                  <div className="text-center text-sm text-gray-600">
                    <span className="text-gray-500">New to DementiaNext? </span>
                    <Link href="/signup" className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
                      Register Medical Account
                    </Link>
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  )
}