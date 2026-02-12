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
  User, 
  Phone,
  FileText,
  Building,
  Loader2,
  Activity,
  Microscope,
  Heart,
  Shield,
  Zap,
  Sparkles,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

declare global {
  interface Window {
    google?: any
  }
}

export default function SignupPage() {
  const [userType, setUserType] = useState<'patient' | 'doctor'>('patient')
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone_number: '',
    // Patient fields
    date_of_birth: '',
    gender: '',
    // Doctor fields
    license_number: '',
    specialization: '',
    qualifications: '',
    experience_years: '',
    hospital_affiliation: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isGoogleReady, setIsGoogleReady] = useState(false)
  const router = useRouter()
  const { register } = useAuth()

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
      document.body.removeChild(script)
    }
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setIsLoading(false)
      return
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      setIsLoading(false)
      return
    }

    const userData: any = {
      email: formData.email,
      password: formData.password,
      first_name: formData.first_name,
      last_name: formData.last_name,
      role: userType,
      phone_number: formData.phone_number,
    }

    if (userType === 'patient') {
      userData.date_of_birth = formData.date_of_birth
      userData.gender = formData.gender
    } else {
      userData.license_number = formData.license_number
      userData.specialization = formData.specialization
      userData.qualifications = formData.qualifications
      userData.experience_years = parseInt(formData.experience_years) || 0
      userData.hospital_affiliation = formData.hospital_affiliation
    }

    const result = await register(userData)
    
    if (result.success) {
      if (userType === 'patient') {
        router.push('/patient-dashboard')
      } else {
        router.push('/doctor-dashboard')
      }
    } else {
      setError(result.error || 'Registration failed')
    }
    
    setIsLoading(false)
  }

  const handleGoogleSignup = () => {
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
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: any) => {
          try {
            const result = await loginWithGoogle(response.credential, userType)
            
            if (result.success) {
              if (userType === 'patient') {
                router.push('/patient-dashboard')
              } else {
                router.push('/doctor-dashboard')
              }
            } else {
              setError(result.error || 'Google signup failed')
            }
          } catch (err) {
            console.error('Google signup error:', err)
            setError('Failed to authenticate with Google')
          } finally {
            setIsLoading(false)
          }
        },
      })

      window.google.accounts.id.prompt()
    } catch (err) {
      console.error('Google Sign-In initialization error:', err)
      setError('Failed to initialize Google Sign-In')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50">
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="w-full max-w-md mx-auto">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <Card className="bg-white/90 backdrop-blur-xl border-blue-200 shadow-2xl">
              <CardHeader className="text-center pb-8">
                <div className="flex justify-center mb-6">
                  <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-2xl">
                    <Brain className="w-10 h-10 text-white" />
                  </div>
                </div>
                
                <CardTitle className="text-2xl font-bold text-gray-900">Create your account</CardTitle>
                
                <CardDescription className="text-gray-600">Secure medical platform access</CardDescription>
              </CardHeader>
              
              <CardContent>
                {/* Error Message */}
                {error && (
                  <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center space-x-2">
                    <AlertCircle className="w-5 h-5" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* User Type Selection */}
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setUserType('patient')}
                      className={`p-4 rounded-xl border ${
                        userType === 'patient' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                      }`}
                    >
                      Patient
                    </button>
                    <button
                      type="button"
                      onClick={() => setUserType('doctor')}
                      className={`p-4 rounded-xl border ${
                        userType === 'doctor' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                      }`}
                    >
                      Doctor
                    </button>
                  </div>

                  {/* Name Inputs */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="grid grid-cols-2 gap-4"
                  >
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        First Name
                      </label>
                      <div className="relative">
                        <User className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <Input
                          type="text"
                          name="first_name"
                          value={formData.first_name}
                          onChange={handleInputChange}
                          placeholder="First name"
                          className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                          required
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Last Name
                      </label>
                      <Input
                        type="text"
                        name="last_name"
                        value={formData.last_name}
                        onChange={handleInputChange}
                        placeholder="Last name"
                        className="py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Email Input */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.7 }}
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Medical Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <Input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        placeholder="your.email@medical.org"
                        className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Password Input */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.8 }}
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Secure Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <Input
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleInputChange}
                        placeholder="Create secure password"
                        className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Confirm Password Input */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.9 }}
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Confirm Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <Input
                        type="password"
                        name="confirmPassword"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="Confirm your password"
                        className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Conditional Fields */}
                  {userType === 'patient' ? (
                    <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Date of Birth *
                          </label>
                          <Input
                            type="date"
                            name="date_of_birth"
                            value={formData.date_of_birth}
                            onChange={handleInputChange}
                            className="py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Gender *
                          </label>
                          <select
                            name="gender"
                            value={formData.gender}
                            onChange={(e) => setFormData({...formData, gender: e.target.value})}
                            className="w-full py-3 px-4 text-base border border-gray-300 rounded-md focus:border-blue-500 focus:ring-blue-500 bg-white"
                            required
                          >
                            <option value="">Select Gender</option>
                            <option value="M">Male</option>
                            <option value="F">Female</option>
                            <option value="O">Other</option>
                          </select>
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Phone Number
                        </label>
                        <div className="relative">
                          <Phone className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <Input
                            type="tel"
                            name="phone_number"
                            value={formData.phone_number}
                            onChange={handleInputChange}
                            placeholder="+1 (555) 123-4567"
                            className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                          />
                        </div>
                      </div>
                    </motion.div>
                  ) : (
                    <>
                      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Medical License Number *
                        </label>
                        <div className="relative">
                          <FileText className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <Input
                            type="text"
                            name="license_number"
                            value={formData.license_number}
                            onChange={handleInputChange}
                            placeholder="MD123456789"
                            className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                            required
                          />
                        </div>
                      </motion.div>

                      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Specialization *
                        </label>
                        <select
                          name="specialization"
                          value={formData.specialization}
                          onChange={(e) => setFormData({...formData, specialization: e.target.value})}
                          className="w-full py-3 px-4 text-base border border-gray-300 rounded-md focus:border-blue-500 focus:ring-blue-500 bg-white"
                          required
                        >
                          <option value="">Select Specialization</option>
                          <option value="neurology">Neurology</option>
                          <option value="radiology">Radiology</option>
                          <option value="psychiatry">Psychiatry</option>
                          <option value="geriatrics">Geriatrics</option>
                          <option value="general">General Practitioner</option>
                        </select>
                      </motion.div>

                      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Qualifications *
                        </label>
                        <Input
                          type="text"
                          name="qualifications"
                          value={formData.qualifications}
                          onChange={handleInputChange}
                          placeholder="MBBS, MD (Neurology)"
                          className="py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                          required
                        />
                      </motion.div>

                      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Experience (Years) *
                        </label>
                        <Input
                          type="number"
                          name="experience_years"
                          value={formData.experience_years}
                          onChange={handleInputChange}
                          placeholder="10"
                          min="0"
                          className="py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                          required
                        />
                      </motion.div>

                      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Hospital/Clinic *
                        </label>
                        <div className="relative">
                          <Building className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <Input
                            type="text"
                            name="hospital_affiliation"
                            value={formData.hospital_affiliation}
                            onChange={handleInputChange}
                            placeholder="General Hospital"
                            className="pl-12 py-6 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 bg-white"
                            required
                          />
                        </div>
                      </motion.div>
                    </>
                  )}

                  {/* Register Button */}
                  <div>
                    <Button
                      type="submit"
                      disabled={isLoading}
                      className="w-full py-7 text-lg font-semibold bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Creating Medical Account...
                        </>
                      ) : (
                        <>
                          <Shield className="mr-2 h-5 w-5" />
                          Register Medical Account
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

                  {/* Google Signup Button */}
                  <div>
                    <Button
                      type="button"
                      onClick={handleGoogleSignup}
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
                          Sign up with Google
                        </>
                      ) : (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Loading Google...
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Login Link */}
                  <div className="text-center text-sm text-gray-600">
                    <span className="text-gray-500">Already have an account? </span>
                    <Link href="/login" className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
                      Access Medical Portal
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