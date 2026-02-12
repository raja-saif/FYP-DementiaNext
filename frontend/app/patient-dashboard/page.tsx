'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { 
  Heart, Calendar, FileText, Download, Users, Brain, Activity, 
  Clock, Mic, Volume2, Send, Bot, User, MessageSquare, Bell,
  CheckCircle, AlertCircle, Eye, TrendingUp, UserPlus, Stethoscope,
  CalendarPlus, X, Loader2, FileUp, Upload
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Types
interface Doctor {
  id: number
  user: {
    id: number
    email: string
    first_name: string
    last_name: string
  }
  specialization: string
  qualifications: string
  experience_years: number
  consultation_fee: string
}

interface Appointment {
  id: number
  appointment_id: string
  doctor: Doctor
  patient: any
  scheduled_date: string
  scheduled_time: string
  status: string
  reason: string
  notes: string
  created_at: string
}

interface FHIRReport {
  id: number
  report_id: string
  patient: any
  doctor: any
  detection_result: any
  status: string
  issued_date: string
  conclusion: string
  conclusion_code: any
  created_at: string
}

export default function PatientDashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
const [activeTab, setActiveTab] = useState<'overview' | 'reports' | 'visits' | 'doctors' | 'chatbot'>('overview')
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [chatMode, setChatMode] = useState<'voice' | 'text' | 'both'>('both')
  const [messages, setMessages] = useState<Array<{ id: number; type: 'user' | 'assistant'; text: string }>>([
    { id: 1, type: 'assistant', text: 'Hello! I\'m your AI health assistant. You can talk to me or type your questions. How can I help you today?' }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // New state for doctors and appointments
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [fhirReports, setFhirReports] = useState<FHIRReport[]>([])
  const [loadingDoctors, setLoadingDoctors] = useState(false)
  const [loadingAppointments, setLoadingAppointments] = useState(false)
  const [loadingReports, setLoadingReports] = useState(false)
  // Modal and selected JSON for patient reports
  const [showReportModal, setShowReportModal] = useState(false)
  const [selectedReportJson, setSelectedReportJson] = useState<any | null>(null)
  
  // Booking modal state
  const [showBookingModal, setShowBookingModal] = useState(false)
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null)
  const [bookingDate, setBookingDate] = useState('')
  const [bookingTime, setBookingTime] = useState('')
  const [bookingReason, setBookingReason] = useState('')
  const [bookingLoading, setBookingLoading] = useState(false)
  const [bookingError, setBookingError] = useState('')

  // MRI Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  // Auth check - redirect if not logged in or not a patient
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/signup')
    } else if (!authLoading && user && user.role === 'doctor') {
      // Doctors should go to doctor dashboard
      router.push('/doctor-dashboard')
    }
  }, [user, authLoading, router])

  // Fetch doctors
  const fetchDoctors = async () => {
    setLoadingDoctors(true)
    try {
      const token = localStorage.getItem('authToken')
      console.log('Fetching doctors with token:', token ? 'exists' : 'missing')
      const response = await fetch(`${API_URL}/auth/doctors/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      console.log('Doctors response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('Doctors data:', data)
        setDoctors(data)
      } else {
        const errorData = await response.text()
        console.error('Doctors fetch error:', errorData)
      }
    } catch (error) {
      console.error('Error fetching doctors:', error)
    } finally {
      setLoadingDoctors(false)
    }
  }

  // Fetch appointments
  const fetchAppointments = async () => {
    setLoadingAppointments(true)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/appointments/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setAppointments(Array.isArray(data) ? data : data.results || [])
      }
    } catch (error) {
      console.error('Error fetching appointments:', error)
    } finally {
      setLoadingAppointments(false)
    }
  }

  // Fetch FHIR reports
  const fetchFHIRReports = async () => {
    setLoadingReports(true)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/fhir-reports/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setFhirReports(Array.isArray(data) ? data : data.results || [])
      }
    } catch (error) {
      console.error('Error fetching FHIR reports:', error)
    } finally {
      setLoadingReports(false)
    }
  }

  // Helper to format FHIR coding fields for display
  const formatFHRCoding = (coding: any) => {
    if (!coding) return null
    try {
      if (Array.isArray(coding)) return coding.map(c => c.display || c.code || JSON.stringify(c)).join(', ')
      if (typeof coding === 'object') return coding.display || coding.code || JSON.stringify(coding)
      return String(coding)
    } catch (e) {
      return String(coding)
    }
  }

  const handleViewFHIRReport = async (reportId: number) => {
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/fhir-reports/${reportId}/fhir-json/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setSelectedReportJson(data)
        setShowReportModal(true)
      } else {
        const data = await response.json()
        alert(data.error || 'Failed to fetch FHIR JSON')
      }
    } catch (error) {
      console.error('Error fetching FHIR JSON:', error)
      alert('Error fetching FHIR JSON')
    }
  }

  const handleExportFHIRReport = (reportJson: any) => {
    if (!reportJson) return
    const content = JSON.stringify(reportJson, null, 2)
    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const element = document.createElement('a')
    element.href = url
    element.download = `fhir_report_${reportJson.id || reportJson.report_id || 'report'}.json`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    URL.revokeObjectURL(url)
  }

  // Book appointment
  const handleBookAppointment = async () => {
    if (!selectedDoctor || !bookingDate || !bookingTime) {
      setBookingError('Please fill in all required fields')
      return
    }

    // Client-side validation for past dates
    const selectedDateTime = new Date(`${bookingDate}T${bookingTime}`)
    const now = new Date()
    if (selectedDateTime < now) {
      setBookingError('Cannot book appointments in the past. Please select a future date and time.')
      return
    }

    setBookingLoading(true)
    setBookingError('')
    
    try {
      const token = localStorage.getItem('authToken')
      const requestBody = {
        doctor_id: selectedDoctor.id,
        scheduled_date: bookingDate,
        scheduled_time: bookingTime,
        reason: bookingReason || 'General Consultation'
      }
      console.log('Booking appointment with:', requestBody)
      console.log('Token:', token ? 'exists' : 'missing')
      
      const response = await fetch(`${API_URL}/detection/appointments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      })

      console.log('Response status:', response.status)
      
      if (response.ok) {
        setShowBookingModal(false)
        setSelectedDoctor(null)
        setBookingDate('')
        setBookingTime('')
        setBookingReason('')
        fetchAppointments()
        alert('Appointment booked successfully!')
      } else {
        const data = await response.json()
        console.log('Error response:', data)
        // Handle different error formats from DRF
        let errorMessage = 'Failed to book appointment'
        if (data.error) {
          errorMessage = data.error
        } else if (data.scheduled_date) {
          errorMessage = Array.isArray(data.scheduled_date) ? data.scheduled_date[0] : data.scheduled_date
        } else if (data.detail) {
          errorMessage = data.detail
        } else if (data.non_field_errors) {
          errorMessage = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors
        } else if (typeof data === 'object') {
          // Try to extract first error from object
          const firstKey = Object.keys(data)[0]
          if (firstKey) {
            errorMessage = Array.isArray(data[firstKey]) ? data[firstKey][0] : data[firstKey]
          }
        }
        setBookingError(errorMessage)
      }
    } catch (error) {
      console.error('Booking error:', error)
      setBookingError('Failed to book appointment. Please try again.')
    } finally {
      setBookingLoading(false)
    }
  }

  // Cancel appointment
  const handleCancelAppointment = async (appointmentId: number) => {
    if (!confirm('Are you sure you want to cancel this appointment?')) return

    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/appointments/${appointmentId}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ status: 'cancelled' })
      })

      if (response.ok) {
        fetchAppointments()
      }
    } catch (error) {
      console.error('Error cancelling appointment:', error)
    }
  }

  // Upload MRI scan for approved appointment
  const handleUploadMRI = async () => {
    if (!uploadFile || !selectedAppointment) {
      setUploadError('Please select a file to upload')
      return
    }

    setUploadLoading(true)
    setUploadError('')

    try {
      const token = localStorage.getItem('authToken')
      const formData = new FormData()
      formData.append('uploaded_file', uploadFile)
      formData.append('appointment_id', selectedAppointment.id.toString())
      formData.append('notes', `MRI scan for appointment ${selectedAppointment.appointment_id}`)

      const response = await fetch(`${API_URL}/detection/detections/upload_for_appointment/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (response.ok) {
        setShowUploadModal(false)
        setSelectedAppointment(null)
        setUploadFile(null)
        fetchAppointments()
        alert('MRI scan uploaded successfully! Your doctor will review it soon.')
      } else {
        const data = await response.json()
        setUploadError(data.error || data.detail || 'Failed to upload MRI scan')
      }
    } catch (error) {
      console.error('Upload error:', error)
      setUploadError('Failed to upload MRI scan. Please try again.')
    } finally {
      setUploadLoading(false)
    }
  }

  // Open upload modal for an approved appointment
  const openUploadModal = (appointment: Appointment) => {
    setSelectedAppointment(appointment)
    setUploadFile(null)
    setUploadError('')
    setShowUploadModal(true)
  }

  useEffect(() => {
    if (user && user.role === 'patient') {
      fetchDoctors()
      fetchAppointments()
      fetchFHIRReports()
    }
  }, [user])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Simulate voice recognition
  const handleStartListening = () => {
    setIsListening(true)
    setTimeout(() => {
      const sampleQuestions = [
        'What are my latest test results?',
        'When is my next appointment?',
        'How should I take my medications?',
        'What exercises can I do?'
      ]
      const randomQuestion = sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]
      setInputMessage(randomQuestion)
      setIsListening(false)
      handleSendMessage(randomQuestion)
    }, 2000)
  }

  // Simulate text-to-speech
  const handleSpeak = (text: string) => {
    setIsSpeaking(true)
    // In real implementation, use Web Speech API
    // const utterance = new SpeechSynthesisUtterance(text)
    // window.speechSynthesis.speak(utterance)
    setTimeout(() => {
      setIsSpeaking(false)
    }, 3000)
  }

  const handleSendMessage = (customText?: string) => {
    const text = customText || inputMessage
    if (!text.trim()) return

    const userMessage = {
      id: messages.length + 1,
      type: 'user' as const,
      text
    }
    setMessages([...messages, userMessage])
    setInputMessage('')

    // Simulate AI response
    setTimeout(() => {
      const response = getAIResponse(text)
      const aiMessage = {
        id: messages.length + 2,
        type: 'assistant' as const,
        text: response
      }
      setMessages(prev => [...prev, aiMessage])
      
      if (chatMode === 'voice' || chatMode === 'both') {
        handleSpeak(response)
      }
    }, 1500)
  }

  const getAIResponse = (question: string): string => {
    const lower = question.toLowerCase()
    if (lower.includes('test') || lower.includes('results')) {
      return 'Your latest cognitive assessment shows stable performance at 72/100. This is good news! Your memory exercises are helping. Keep up the great work!'
    }
    if (lower.includes('appointment')) {
      return 'Your next appointment with Dr. Sarah Johnson is on November 15, 2024 at 10:30 AM. It\'s a routine check-up. Would you like me to add a reminder?'
    }
    if (lower.includes('medication') || lower.includes('medicine')) {
      return 'Take your morning medication (Donepezil 10mg) with breakfast, and evening medication (Memantine 5mg) with dinner. Always take them at the same time each day.'
    }
    if (lower.includes('exercise')) {
      return 'I recommend 20-30 minutes of walking daily, gentle stretching, and memory exercises like puzzles. These help keep your mind and body active!'
    }
    return 'I\'m here to help! You can ask me about your test results, appointments, medications, exercises, or any health concerns you have.'
  }

  const memoryData = [
    { month: 'May', score: 70 },
    { month: 'June', score: 71 },
    { month: 'July', score: 71 },
    { month: 'August', score: 72 },
    { month: 'September', score: 72 },
    { month: 'October', score: 72 },
  ]

  const reports = [
    { id: 1, title: 'Cognitive Assessment Report', date: 'Oct 15, 2024', type: 'Assessment', status: 'Available' },
    { id: 2, title: 'MRI Brain Scan Analysis', date: 'Sep 28, 2024', type: 'Imaging', status: 'Available' },
    { id: 3, title: 'Medication Review', date: 'Sep 15, 2024', type: 'Clinical', status: 'Available' },
    { id: 4, title: 'Quarterly Progress Report', date: 'Aug 30, 2024', type: 'Progress', status: 'Available' },
  ]

  const visits = [
    { id: 1, doctor: 'Dr. Sarah Johnson', specialty: 'Neurologist', date: 'Oct 10, 2024', type: 'Follow-up', notes: 'Stable condition, continue current treatment' },
    { id: 2, doctor: 'Dr. Michael Chen', specialty: 'Geriatric Specialist', date: 'Sep 22, 2024', type: 'Routine Check', notes: 'Overall health good, recommend more physical activity' },
    { id: 3, doctor: 'Dr. Sarah Johnson', specialty: 'Neurologist', date: 'Aug 15, 2024', type: 'Assessment', notes: 'Cognitive tests show improvement with therapy' },
  ]

  const upcomingAppointments = [
    { id: 1, doctor: 'Dr. Sarah Johnson', specialty: 'Neurologist', date: 'Nov 15, 2024', time: '10:30 AM', type: 'Routine Check-up' },
    { id: 2, doctor: 'Physical Therapist', specialty: 'PT Department', date: 'Nov 08, 2024', time: '2:00 PM', type: 'Physical Therapy' },
  ]

  const reminders = [
    { id: 1, title: 'Take Morning Medication', time: '8:00 AM', icon: '💊', priority: 'high' },
    { id: 2, title: 'Upcoming Appointment with Dr. Johnson', time: 'Nov 15', icon: '📅', priority: 'high' },
    { id: 3, title: 'Complete Memory Exercise', time: 'Daily', icon: '🧠', priority: 'medium' },
    { id: 4, title: '30-minute Walk', time: 'Daily', icon: '🚶', priority: 'medium' },
  ]

  // Show loading while auth is being checked
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-teal-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect will happen via useEffect, show nothing while redirecting
  if (!user || user.role !== 'patient') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-teal-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Redirecting...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-teal-50">
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <div className="bg-gradient-to-r from-blue-600 to-teal-600 rounded-3xl p-8 md:p-12 text-white shadow-xl">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
                <Heart className="text-white" size={32} />
              </div>
              <div>
                <h1 className="text-3xl md:text-4xl font-bold">Hello, {user?.first_name || user?.email?.split('@')[0] || 'there'}! 👋</h1>
                <p className="text-xl text-blue-100 mt-1">
                  Welcome to your health dashboard
                </p>
              </div>
            </div>
            
            <div className="grid md:grid-cols-4 gap-4 mt-8">
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <div className="text-2xl mb-1">📊</div>
                <div className="text-sm text-blue-100">Health Score</div>
                <div className="text-lg font-semibold">72/100</div>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <div className="text-2xl mb-1">📅</div>
                <div className="text-sm text-blue-100">Next Appointment</div>
                <div className="text-lg font-semibold">Nov 15</div>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <div className="text-2xl mb-1">💊</div>
                <div className="text-sm text-blue-100">Medications</div>
                <div className="text-lg font-semibold">All Taken</div>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-xl p-4">
                <div className="text-2xl mb-1">📄</div>
                <div className="text-sm text-blue-100">New Reports</div>
                <div className="text-lg font-semibold">2 Available</div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
          <Button
            variant={activeTab === 'overview' ? 'default' : 'outline'}
            onClick={() => setActiveTab('overview')}
            className={activeTab === 'overview' ? 'bg-blue-600' : ''}
          >
            <Activity className="mr-2" size={18} />
            Overview
          </Button>
          <Button
            variant={activeTab === 'doctors' ? 'default' : 'outline'}
            onClick={() => setActiveTab('doctors')}
            className={activeTab === 'doctors' ? 'bg-purple-600' : ''}
          >
            <Stethoscope className="mr-2" size={18} />
            Find Doctors
          </Button>
          <Button
            variant={activeTab === 'reports' ? 'default' : 'outline'}
            onClick={() => setActiveTab('reports')}
            className={activeTab === 'reports' ? 'bg-blue-600' : ''}
          >
            <FileText className="mr-2" size={18} />
            FHIR Reports
          </Button>
          <Button
            variant={activeTab === 'visits' ? 'default' : 'outline'}
            onClick={() => setActiveTab('visits')}
            className={activeTab === 'visits' ? 'bg-blue-600' : ''}
          >
            <Calendar className="mr-2" size={18} />
            My Appointments
          </Button>
          <Button
            variant={activeTab === 'chatbot' ? 'default' : 'outline'}
            onClick={() => setActiveTab('chatbot')}
            className={activeTab === 'chatbot' ? 'bg-teal-600' : ''}
          >
            <MessageSquare className="mr-2" size={18} />
            AI Assistant
          </Button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Reminders */}
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="text-orange-600" size={24} />
                  Important Reminders
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  {reminders.map((reminder) => (
                    <div
                      key={reminder.id}
                      className={`p-4 rounded-lg border-2 ${
                        reminder.priority === 'high' ? 'border-orange-200 bg-orange-50' : 'border-blue-200 bg-blue-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-3xl">{reminder.icon}</div>
                        <div className="flex-1">
                          <div className="font-semibold text-gray-900">{reminder.title}</div>
                          <div className="text-sm text-gray-600">{reminder.time}</div>
                        </div>
                        {reminder.priority === 'high' && (
                          <AlertCircle className="text-orange-600" size={20} />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
              {/* FHIR JSON modal */}
              {showReportModal && selectedReportJson && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white rounded-lg max-w-3xl w-full p-6 overflow-auto max-h-[80vh]">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold">FHIR Diagnostic Report JSON</h3>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleExportFHIRReport(selectedReportJson)}>
                          <Download size={16} className="mr-1" />
                          Export
                        </Button>
                        <Button size="sm" onClick={() => { setShowReportModal(false); setSelectedReportJson(null) }}>
                          Close
                        </Button>
                      </div>
                    </div>
                    <pre className="text-xs whitespace-pre-wrap bg-gray-50 p-4 rounded">{JSON.stringify(selectedReportJson, null, 2)}</pre>
                  </div>
                </div>
              )}
            </Card>

            {/* Progress Chart */}
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="text-green-600" size={24} />
                  Your Health Progress
                </CardTitle>
                <CardDescription>
                  Your cognitive score over the past 6 months - showing steady improvement!
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={memoryData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="score" 
                        stroke="#0066cc" 
                        strokeWidth={4}
                        dot={{ r: 6, fill: '#0066cc' }}
                        name="Health Score"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-6 p-4 bg-green-50 border-2 border-green-200 rounded-lg">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="text-green-600 flex-shrink-0 mt-1" size={24} />
                    <div>
                      <h4 className="font-semibold text-lg mb-2 text-green-900">Great Progress!</h4>
                      <p className="text-gray-700">
                        Your score has been stable at 72 for the last 3 months. Your daily exercises and medications are working well. Keep up the excellent work!
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Reports Tab - FHIR Reports */}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="text-blue-600" size={24} />
                  My FHIR Diagnostic Reports
                </CardTitle>
                <CardDescription>
                  View your HL7 FHIR R4 compliant diagnostic reports
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingReports ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  </div>
                ) : fhirReports.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg">No diagnostic reports yet</p>
                    <p className="text-sm mt-2">Reports will appear here after your doctor completes a detection analysis</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {fhirReports.map((report) => (
                      <div key={report.id} className="p-4 rounded-lg border-2 hover:border-blue-300 transition-all">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-lg text-gray-900 mb-1">
                              Report #{report.report_id}
                            </h3>
                            <div className="flex items-center gap-4 text-sm text-gray-600">
                                <span className="flex items-center gap-1">
                                <Calendar size={14} />
                                {new Date(report.issued || report.issued_date || report.created_at).toLocaleDateString()}
                              </span>
                              <Badge 
                                className={
                                  report.status === 'final' ? 'bg-green-100 text-green-800' :
                                  report.status === 'preliminary' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }
                              >
                                {report.status}
                              </Badge>
                              {report.conclusion_code && (
                                <Badge variant="secondary">{formatFHRCoding(report.conclusion_code)}</Badge>
                              )}
                            </div>
                            {report.conclusion && (
                              <p className="mt-2 text-sm text-gray-700 bg-gray-50 p-2 rounded">
                                {report.conclusion}
                              </p>
                            )}
                          </div>
                            <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={() => handleViewFHIRReport(report.id)}>
                              <Eye size={16} className="mr-1" />
                              View
                            </Button>
                            <Button size="sm" className="bg-blue-600" onClick={() => handleExportFHIRReport(report.fhir_json || report)}>
                              <Download size={16} className="mr-1" />
                              Download
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Visits Tab - My Appointments */}
        {activeTab === 'visits' && (
          <div className="space-y-6">
            {/* Upcoming/Pending Appointments */}
            <Card className="border-2 border-green-200 bg-green-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="text-green-600" size={24} />
                  My Appointments
                </CardTitle>
                <CardDescription>
                  View and manage your scheduled appointments
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingAppointments ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-green-600" />
                  </div>
                ) : appointments.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Calendar className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg">No appointments yet</p>
                    <p className="text-sm mt-2">Go to "Find Doctors" to book your first appointment</p>
                    <Button 
                      className="mt-4 bg-purple-600 hover:bg-purple-700"
                      onClick={() => setActiveTab('doctors')}
                    >
                      <Stethoscope className="mr-2" size={18} />
                      Find Doctors
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {appointments.map((apt) => (
                      <div 
                        key={apt.id} 
                        className={`p-4 rounded-lg border-2 bg-white ${
                          apt.status === 'approved' ? 'border-green-300' :
                          apt.status === 'pending' ? 'border-yellow-300' :
                          apt.status === 'rejected' ? 'border-red-300' :
                          apt.status === 'cancelled' ? 'border-gray-300' :
                          'border-blue-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-lg text-gray-900">
                              Dr. {apt.doctor?.user?.first_name} {apt.doctor?.user?.last_name}
                            </h3>
                            <p className="text-gray-600">{apt.doctor?.specialization}</p>
                            <div className="flex items-center gap-4 mt-2">
                              <span className="flex items-center gap-1 text-sm">
                                <Calendar size={14} />
                                {new Date(apt.scheduled_date).toLocaleDateString()}
                              </span>
                              <span className="flex items-center gap-1 text-sm">
                                <Clock size={14} />
                                {apt.scheduled_time}
                              </span>
                              <Badge 
                                className={
                                  apt.status === 'approved' ? 'bg-green-100 text-green-800' :
                                  apt.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                  apt.status === 'rejected' ? 'bg-red-100 text-red-800' :
                                  apt.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
                                  apt.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                                  'bg-gray-100 text-gray-800'
                                }
                              >
                                {apt.status}
                              </Badge>
                            </div>
                            {apt.reason && (
                              <p className="text-sm text-gray-600 mt-2">
                                <strong>Reason:</strong> {apt.reason}
                              </p>
                            )}
                            {apt.notes && (
                              <p className="text-sm text-gray-600 mt-1">
                                <strong>Notes:</strong> {apt.notes}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-col gap-2">
                            {apt.status === 'approved' && (
                              <Button 
                                className="bg-blue-600 hover:bg-blue-700"
                                size="sm"
                                onClick={() => openUploadModal(apt)}
                              >
                                <FileUp className="mr-1" size={14} />
                                Upload MRI
                              </Button>
                            )}
                            {(apt.status === 'pending' || apt.status === 'approved') && (
                              <Button 
                                variant="destructive" 
                                size="sm"
                                onClick={() => handleCancelAppointment(apt.id)}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Doctors Tab - Find and Book */}
        {activeTab === 'doctors' && (
          <div className="space-y-6">
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Stethoscope className="text-purple-600" size={24} />
                  Available Doctors
                </CardTitle>
                <CardDescription>
                  Browse doctors and book appointments for dementia screening
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingDoctors ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
                  </div>
                ) : doctors.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Stethoscope className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg">No doctors available</p>
                    <p className="text-sm mt-2">Please check back later</p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {doctors.map((doctor) => (
                      <div key={doctor.id} className="p-6 rounded-xl border-2 hover:border-purple-300 hover:shadow-lg transition-all">
                        <div className="flex items-start gap-4">
                          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-2xl font-bold">
                            {doctor.user.first_name?.[0]}{doctor.user.last_name?.[0]}
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-xl text-gray-900">
                              Dr. {doctor.user.first_name} {doctor.user.last_name}
                            </h3>
                            <p className="text-purple-600 font-medium">{doctor.specialization}</p>
                            <p className="text-sm text-gray-600 mt-1">{doctor.qualifications}</p>
                            <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                              <span>{doctor.experience_years} years experience</span>
                              <span className="font-semibold text-green-600">
                                ${doctor.consultation_fee}
                              </span>
                            </div>
                          </div>
                        </div>
                        <Button 
                          className="w-full mt-4 bg-purple-600 hover:bg-purple-700"
                          onClick={() => {
                            setSelectedDoctor(doctor)
                            setShowBookingModal(true)
                          }}
                        >
                          <CalendarPlus className="mr-2" size={18} />
                          Book Appointment
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* AI Chatbot Tab */}
        {activeTab === 'chatbot' && (
          <div className="grid lg:grid-cols-4 gap-6">
            {/* Chat Interface */}
            <Card className="lg:col-span-3 border-2 h-[700px] flex flex-col">
              <CardHeader className="border-b bg-gradient-to-r from-teal-50 to-blue-50">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Bot className="text-teal-600" size={28} />
                      AI Health Assistant
                    </CardTitle>
                    <CardDescription>
                      Ask questions using voice or text
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={chatMode === 'voice' ? 'default' : 'outline'}
                      onClick={() => setChatMode('voice')}
                      className={chatMode === 'voice' ? 'bg-teal-600' : ''}
                    >
                      <Mic size={16} />
                    </Button>
                    <Button
                      size="sm"
                      variant={chatMode === 'text' ? 'default' : 'outline'}
                      onClick={() => setChatMode('text')}
                      className={chatMode === 'text' ? 'bg-teal-600' : ''}
                    >
                      <MessageSquare size={16} />
                    </Button>
                    <Button
                      size="sm"
                      variant={chatMode === 'both' ? 'default' : 'outline'}
                      onClick={() => setChatMode('both')}
                      className={chatMode === 'both' ? 'bg-teal-600' : ''}
                    >
                      Both
                    </Button>
                  </div>
                </div>
              </CardHeader>

              {/* Messages */}
              <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === 'user'
                        ? 'bg-gradient-to-r from-blue-500 to-blue-600'
                        : 'bg-gradient-to-r from-teal-500 to-teal-600'
                    }`}>
                      {message.type === 'user' ? (
                        <User className="text-white" size={20} />
                      ) : (
                        <Bot className="text-white" size={20} />
                      )}
                    </div>
                    <div className={`flex-1 max-w-[80%] ${message.type === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                      <div className={`rounded-2xl px-4 py-3 ${
                        message.type === 'user'
                          ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        <p className="text-base leading-relaxed">{message.text}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
                <div ref={messagesEndRef} />
              </CardContent>

              {/* Input Area */}
              <div className="border-t p-4 bg-gray-50">
                {(chatMode === 'voice' || chatMode === 'both') && (
                  <div className="flex justify-center mb-4">
                    <Button
                      onClick={handleStartListening}
                      disabled={isListening}
                      className={`${isListening ? 'bg-red-600 animate-pulse' : 'bg-teal-600'} hover:bg-teal-700`}
                      size="lg"
                    >
                      <Mic className="mr-2" size={20} />
                      {isListening ? 'Listening...' : 'Tap to Speak'}
                    </Button>
                  </div>
                )}
                {(chatMode === 'text' || chatMode === 'both') && (
                  <div className="flex gap-2">
                    <Input
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Type your question here..."
                      className="flex-1"
                    />
                    <Button onClick={() => handleSendMessage()} size="lg" className="bg-teal-600 hover:bg-teal-700">
                      <Send size={20} />
                    </Button>
                  </div>
                )}
              </div>
            </Card>

            {/* Chatbot Info */}
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="text-lg">Quick Questions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  'What are my test results?',
                  'When is my next appointment?',
                  'How should I take medications?',
                  'What exercises should I do?',
                  'Tell me about my condition',
                ].map((q, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    className="w-full justify-start text-left h-auto py-3"
                    onClick={() => {
                      setInputMessage(q)
                      handleSendMessage(q)
                    }}
                  >
                    {q}
                  </Button>
                ))}
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Booking Modal */}
      {showBookingModal && selectedDoctor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Book Appointment</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowBookingModal(false)
                  setSelectedDoctor(null)
                  setBookingError('')
                }}
              >
                <X size={24} />
              </Button>
            </div>

            <div className="space-y-4">
              {/* Doctor Info */}
              <div className="flex items-center gap-4 p-4 bg-purple-50 rounded-xl">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-xl font-bold">
                  {selectedDoctor.user.first_name?.[0]}{selectedDoctor.user.last_name?.[0]}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">
                    Dr. {selectedDoctor.user.first_name} {selectedDoctor.user.last_name}
                  </h3>
                  <p className="text-purple-600">{selectedDoctor.specialization}</p>
                </div>
              </div>

              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Appointment Date *
                </label>
                <Input
                  type="date"
                  value={bookingDate}
                  onChange={(e) => setBookingDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full"
                />
              </div>

              {/* Time */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Time *
                </label>
                <Input
                  type="time"
                  value={bookingTime}
                  onChange={(e) => setBookingTime(e.target.value)}
                  className="w-full"
                />
              </div>

              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason for Visit
                </label>
                <Textarea
                  value={bookingReason}
                  onChange={(e) => setBookingReason(e.target.value)}
                  placeholder="Describe your symptoms or reason for the appointment..."
                  rows={3}
                  className="w-full"
                />
              </div>

              {bookingError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {bookingError}
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowBookingModal(false)
                    setSelectedDoctor(null)
                    setBookingError('')
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1 bg-purple-600 hover:bg-purple-700"
                  onClick={handleBookAppointment}
                  disabled={bookingLoading}
                >
                  {bookingLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Booking...
                    </>
                  ) : (
                    'Confirm Booking'
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Upload MRI Modal */}
      {showUploadModal && selectedAppointment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6"
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-gray-900">Upload MRI Scan</h2>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setSelectedAppointment(null)
                  setUploadFile(null)
                  setUploadError('')
                }}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Appointment Info */}
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="font-medium text-blue-900">
                  Appointment: {selectedAppointment.appointment_id}
                </p>
                <p className="text-sm text-blue-700 mt-1">
                  Dr. {selectedAppointment.doctor?.user?.first_name} {selectedAppointment.doctor?.user?.last_name}
                </p>
                <p className="text-sm text-blue-700">
                  {new Date(selectedAppointment.scheduled_date).toLocaleDateString()} at {selectedAppointment.scheduled_time}
                </p>
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  MRI Scan File *
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                  <input
                    type="file"
                    accept=".nii,.nii.gz,.dcm,.jpg,.jpeg,.png"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="hidden"
                    id="mri-upload"
                  />
                  <label htmlFor="mri-upload" className="cursor-pointer">
                    <Upload className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-2 text-sm text-gray-600">
                      {uploadFile ? uploadFile.name : 'Click to upload MRI scan'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Supported: NIfTI (.nii, .nii.gz), DICOM (.dcm), or image files
                    </p>
                  </label>
                </div>
              </div>

              {uploadError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {uploadError}
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowUploadModal(false)
                    setSelectedAppointment(null)
                    setUploadFile(null)
                    setUploadError('')
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                  onClick={handleUploadMRI}
                  disabled={uploadLoading || !uploadFile}
                >
                  {uploadLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <FileUp className="mr-2" size={16} />
                      Upload MRI
                    </>
                  )}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
