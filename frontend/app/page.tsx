'use client'

import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { 
  Brain, 
  Activity, 
  Users, 
  Eye,
  FileText,
  ChevronRight,
  Shield,
  Sparkles,
  ArrowRight,
  Scan,
  Stethoscope,
  Microscope,
  Heart
} from 'lucide-react'

const features = [
  {
    title: 'MCI/AD Detection',
    description: 'Advanced AI analysis of brain scans to detect Mild Cognitive Impairment and Alzheimer\'s Disease',
    icon: Brain,
    color: 'from-blue-500 to-blue-600',
    href: '/detection',
    emoji: '🧠',
    medicalIcon: Scan
  },
  {
    title: 'Parkinson\'s Analysis',
    description: 'Comprehensive evaluation of neurological patterns for Parkinson\'s Dementia classification',
    icon: Activity,
    color: 'from-teal-500 to-teal-600',
    href: '/detection',
    emoji: '⚡',
    medicalIcon: Stethoscope
  },
  {
    title: 'Explainable AI',
    description: 'Transparent AI insights showing brain regions and biomarkers affecting diagnosis',
    icon: Eye,
    color: 'from-green-500 to-green-600',
    href: '/explainable-ai',
    emoji: '👁️',
    medicalIcon: Microscope
  },
  {
    title: 'Doctor Analytics',
    description: 'Comprehensive dashboard for healthcare professionals to monitor patient progress',
    icon: Users,
    color: 'from-blue-600 to-cyan-600',
    href: '/doctor-dashboard',
    emoji: '👨‍⚕️',
    medicalIcon: Heart
  },
  {
    title: 'Patient Portal',
    description: 'Personalized reports and AI voice assistant for patient engagement',
    icon: Users,
    color: 'from-indigo-500 to-purple-500',
    href: '/patient-dashboard',
    emoji: '💚',
    medicalIcon: Heart
  },
  {
    title: 'Report Generation',
    description: 'Comprehensive medical reports with AI insights and recommendations',
    icon: FileText,
    color: 'from-gray-600 to-gray-700',
    href: '/detection',
    emoji: '📄',
    medicalIcon: FileText
  }
]

const steps = [
  {
    number: '01',
    title: 'Upload Medical Data',
    description: 'Upload MRI scans, CT images, and patient data. Our AI supports DICOM and standard medical imaging formats.',
    icon: Scan,
    emoji: '📤',
    medicalFocus: 'Medical Imaging'
  },
  {
    number: '02',
    title: 'AI Analysis & Diagnosis',
    description: 'Advanced neural networks analyze brain patterns, providing detailed classification and confidence scores.',
    icon: Brain,
    emoji: '🔍',
    medicalFocus: 'AI Diagnosis'
  },
  {
    number: '03',
    title: 'Clinical Reports & Monitoring',
    description: 'Generate comprehensive medical reports and track patient progress with continuous monitoring.',
    icon: FileText,
    emoji: '📊',
    medicalFocus: 'Clinical Care'
  }
]

// Feature card component with auth check
function FeatureCard({ feature, isAuthenticated }: { feature: typeof features[0], isAuthenticated: boolean }) {
  const router = useRouter()
  
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    if (!isAuthenticated) {
      router.push('/signup')
    } else {
      router.push(feature.href)
    }
  }

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <Card className="h-full hover:shadow-2xl transition-all duration-300 group border-2 hover:border-blue-400 bg-gradient-to-br from-white to-blue-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/5 to-teal-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        <CardHeader>
          <div className="relative mb-4">
            <div className={`w-20 h-20 rounded-2xl bg-gradient-to-r ${feature.color} flex items-center justify-center shadow-xl group-hover:shadow-2xl transition-all duration-300`}>
              <feature.icon className="w-8 h-8 text-white" />
            </div>
            <div className="absolute -top-2 -right-2 text-4xl">{feature.emoji}</div>
            <div className="absolute -bottom-2 -left-2 w-8 h-8 bg-white rounded-full flex items-center justify-center shadow-lg">
              <feature.medicalIcon className="w-4 h-4 text-blue-600" />
            </div>
          </div>
          <CardTitle className="text-2xl group-hover:text-blue-600 transition-colors text-gray-800">
            {feature.title}
          </CardTitle>
          <CardDescription className="text-base leading-relaxed text-gray-600">
            {feature.description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center text-blue-600 font-semibold group-hover:translate-x-2 transition-transform">
            {isAuthenticated ? 'Access Now' : 'Sign up to access'}
            <ArrowRight className="ml-2 w-5 h-5" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function HomePage() {
  const { isAuthenticated } = useAuth()
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50">
      <Navigation />
      
      {/* Hero Section with Professional MRI Theme */}
      <section className="relative overflow-hidden pt-32 pb-40">
        {/* Professional Medical Background Elements */}
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
                top: `${5 + i * 12}%`,
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
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            {/* Professional MRI Scanner */}
            <div className="flex justify-center mb-12">
              <div className="relative">
                <div className="w-48 h-48 bg-gradient-to-br from-white to-blue-50 rounded-3xl border-4 border-blue-200 shadow-2xl relative overflow-hidden">
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
                      className="w-24 h-24 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-2xl"
                    >
                      <Brain className="w-12 h-12 text-white" />
                    </motion.div>
                  </div>

                  {/* Professional Scan Lines */}
                  <motion.div
                    animate={{
                      y: [0, 200, 0],
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
                <div className="absolute -top-4 -right-4 w-12 h-12 bg-red-500 rounded-full flex items-center justify-center shadow-lg animate-pulse">
                  <Heart className="w-6 h-6 text-white" />
                </div>
                <div className="absolute -bottom-4 -left-4 w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg animate-pulse" style={{ animationDelay: '0.5s' }}>
                  <Scan className="w-6 h-6 text-white" />
                </div>
                <div className="absolute top-1/2 -left-8 w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-pulse" style={{ animationDelay: '1s' }}>
                  <Microscope className="w-5 h-5 text-white" />
                </div>
              </div>
            </div>
            
            <h1 className="text-6xl md:text-8xl font-extrabold mb-8">
              <span className="bg-gradient-to-r from-blue-600 via-teal-600 to-green-600 bg-clip-text text-transparent">
                DementiaNext
              </span>
            </h1>
            
            <div className="mb-6">
              <p className="text-2xl md:text-3xl text-gray-700 mb-4 max-w-4xl mx-auto font-semibold">
                Advanced MRI-Based AI Platform for Neurological Analysis
              </p>
              <div className="h-1 bg-gradient-to-r from-blue-600 via-teal-600 to-green-600 max-w-md mx-auto rounded-full"></div>
            </div>
            
            <p className="text-xl text-gray-600 mb-12 max-w-3xl mx-auto">
              Revolutionary neural networks analyze brain scans to detect MCI, Alzheimer's Disease, and Parkinson's Dementia with clinical-grade accuracy
            </p>
            
            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <Link href="/signup">
                <Button className="text-xl px-12 py-8 bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700 shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-105">
                  <Scan className="mr-3 w-6 h-6" />
                  Start MRI Analysis
                  <ChevronRight className="ml-2 w-6 h-6" />
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="outline" className="text-xl px-12 py-8 border-4 border-blue-600 text-blue-600 hover:bg-blue-50 shadow-xl hover:shadow-2xl transition-all duration-300">
                  <Shield className="mr-3 w-6 h-6" />
                  Medical Portal Access
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Medical Stats Section */}
      <section className="py-20 bg-white/70 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Medical-Grade AI Performance</h2>
            <p className="text-xl text-gray-600">Trusted by healthcare professionals worldwide</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-teal-50 shadow-lg hover:shadow-xl transition-all duration-300 border border-blue-200">
              <div className="text-5xl mb-3">🎯</div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent mb-2">99.7%</div>
              <div className="text-gray-700 font-semibold">MRI Accuracy</div>
              <div className="text-sm text-gray-500 mt-2">FDA Validated</div>
            </div>
            <div className="text-center p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-teal-50 shadow-lg hover:shadow-xl transition-all duration-300 border border-blue-200">
              <div className="text-5xl mb-3">✨</div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent mb-2">97.5%</div>
              <div className="text-gray-700 font-semibold">Classification Precision</div>
              <div className="text-sm text-gray-500 mt-2">Clinical Grade</div>
            </div>
            <div className="text-center p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-teal-50 shadow-lg hover:shadow-xl transition-all duration-300 border border-blue-200">
              <div className="text-5xl mb-3">👥</div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent mb-2">10K+</div>
              <div className="text-gray-700 font-semibold">Patients Analyzed</div>
              <div className="text-sm text-gray-500 mt-2">Global Reach</div>
            </div>
            <div className="text-center p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-teal-50 shadow-lg hover:shadow-xl transition-all duration-300 border border-blue-200">
              <div className="text-5xl mb-3">🤖</div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent mb-2">24/7</div>
              <div className="text-gray-700 font-semibold">AI Support</div>
              <div className="text-sm text-gray-500 mt-2">Always Available</div>
            </div>
          </div>
        </div>
      </section>

      {/* Medical Features Section */}
      <section className="py-24 relative bg-gradient-to-br from-blue-50 to-teal-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20">
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-xl">
                <Stethoscope className="w-8 h-8 text-white" />
              </div>
            </div>
            <h2 className="text-5xl md:text-6xl font-bold mb-6 text-gray-900">
              <span className="bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
                Comprehensive Medical AI Platform
              </span>
            </h2>
            <p className="text-2xl text-gray-600 max-w-3xl mx-auto">
              Advanced neural networks for accurate neurological diagnosis and transparent medical insights
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <FeatureCard key={index} feature={feature} isAuthenticated={isAuthenticated} />
            ))}
          </div>
        </div>
      </section>

      {/* Medical Workflow Section */}
      <section className="py-24 bg-gradient-to-br from-blue-50 to-teal-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20">
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-full flex items-center justify-center shadow-xl">
                <Microscope className="w-8 h-8 text-white" />
              </div>
            </div>
            <h2 className="text-5xl md:text-6xl font-bold mb-6 text-gray-900">
              <span className="bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
                Medical AI Workflow
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              From medical imaging to clinical diagnosis - our AI-powered workflow
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-12">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                <div className="rounded-lg h-full border-2 shadow-2xl hover:shadow-3xl transition-all bg-white relative overflow-hidden group border-blue-200">
                  <div className="absolute top-0 right-0 text-9xl font-bold text-blue-100 opacity-50 -mr-8 -mt-4 group-hover:text-teal-100 transition-colors">
                    {step.number}
                  </div>
                  <div className="p-6">
                    <div className="relative mb-6">
                      <div className="w-24 h-24 rounded-2xl bg-gradient-to-r from-blue-500 to-teal-500 flex items-center justify-center shadow-2xl group-hover:scale-110 transition-transform duration-300">
                        <step.icon className="w-12 h-12 text-white" />
                      </div>
                      <div className="absolute -top-3 -right-3 text-5xl">{step.emoji}</div>
                      <div className="absolute -bottom-2 -left-2 bg-blue-600 text-white px-2 py-1 rounded-full text-xs font-semibold">
                        {step.medicalFocus}
                      </div>
                    </div>
                    <h3 className="font-semibold tracking-tight text-3xl mb-4 text-gray-800">
                      {step.title}
                    </h3>
                    <p className="text-gray-600 text-lg leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Medical CTA Section */}
      <section className="py-32 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-cyan-600 to-teal-600"></div>
        <div className="absolute inset-0 bg-black/10"></div>
        
        {/* MRI Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          {[...Array(12)].map((_, i) => (
            <div
              key={i}
              className="absolute w-24 h-24 opacity-20"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
            >
              <Brain className="w-full h-full text-white animate-pulse" style={{ animationDelay: `${i * 0.5}s` }} />
            </div>
          ))}
        </div>
        
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-16 shadow-2xl hover:shadow-3xl transition-all duration-300 border border-white/20">
            <div className="flex justify-center mb-8">
              <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center">
                <Brain className="w-10 h-10 text-white" />
              </div>
            </div>
            <h2 className="text-5xl md:text-6xl font-bold text-white mb-8">
              Ready to Transform Neurological Care?
            </h2>
            <p className="text-2xl text-blue-100 mb-12 max-w-3xl mx-auto leading-relaxed">
              Join healthcare professionals worldwide using DementiaNext for accurate neurological diagnosis
            </p>
            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <Link href="/signup">
                <Button className="text-xl px-12 py-8 bg-white text-blue-600 hover:bg-gray-100 shadow-2xl font-bold hover:shadow-3xl transition-all duration-300 transform hover:scale-105">
                  <Scan className="mr-3 w-6 h-6" />
                  Start MRI Analysis
                  <Sparkles className="ml-2 w-6 h-6" />
                </Button>
              </Link>
              <Link href="/login">
                <Button className="text-xl px-12 py-8 bg-white/10 text-white border-4 border-white hover:bg-white hover:text-blue-600 shadow-2xl font-bold backdrop-blur hover:shadow-3xl transition-all duration-300">
                  <Shield className="mr-3 w-6 h-6" />
                  Medical Portal Access
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Medical Footer */}
      <footer className="bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-4 mb-6 md:mb-0">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div>
                <span className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  DementiaNext
                </span>
                <p className="text-sm text-blue-300 mt-1">Advanced Neurological AI Platform</p>
              </div>
            </div>
            <div className="text-blue-300 text-center md:text-right">
              <p className="text-lg">© 2025 DementiaNext. All rights reserved.</p>
              <p className="text-sm mt-2 text-cyan-400">Advancing neurological care with AI 🧠</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}