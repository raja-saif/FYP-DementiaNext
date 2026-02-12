'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { PieChart, Pie, Cell, BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { 
  Users, Search, Filter, TrendingUp, TrendingDown, AlertTriangle, 
  CheckCircle, Clock, Activity, Brain, FileText, Bell, Calendar,
  ArrowRight, Download, Eye, Stethoscope, X, Check, Loader2, Upload,
  ClipboardList
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Types
interface Appointment {
  id: number
  appointment_id: string
  patient: {
    id: number
    user: {
      id: number
      email: string
      first_name: string
      last_name: string
    }
    date_of_birth: string
    gender: string
  }
  doctor: any
  scheduled_date: string
  scheduled_time: string
  status: string
  reason: string
  notes: string
  created_at: string
}

interface DetectionResult {
  id: number
  detection_id: string
  patient: any
  doctor: any
  appointment: any
  uploaded_file: string
  status: string
  predicted_class: string
  confidence_score: number
  processing_time: number
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

export default function DoctorDashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'appointments' | 'detections' | 'reports'>('overview')
  
  // State for real data
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [detectionResults, setDetectionResults] = useState<DetectionResult[]>([])
  const [fhirReports, setFhirReports] = useState<FHIRReport[]>([])
  const [loadingAppointments, setLoadingAppointments] = useState(false)
  const [loadingDetections, setLoadingDetections] = useState(false)
  const [loadingReports, setLoadingReports] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  // Modal state for viewing FHIR JSON
  const [showReportModal, setShowReportModal] = useState(false)
  const [selectedReportJson, setSelectedReportJson] = useState<any | null>(null)
  
  // Notes modal state
  const [showNotesModal, setShowNotesModal] = useState(false)
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null)
  const [appointmentNotes, setAppointmentNotes] = useState('')

  // Auth check - redirect if not logged in or not a doctor
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/signup')
    } else if (!authLoading && user && user.role === 'patient') {
      // Patients should go to patient dashboard
      router.push('/patient-dashboard')
    }
  }, [user, authLoading, router])

  // Fetch appointments
  const fetchAppointments = async () => {
    setLoadingAppointments(true)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/appointments/`, {
        headers: { 'Authorization': `Bearer ${token}` }
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

  // Fetch detection results
  const fetchDetections = async () => {
    setLoadingDetections(true)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setDetectionResults(Array.isArray(data) ? data : data.results || [])
      }
    } catch (error) {
      console.error('Error fetching detections:', error)
    } finally {
      setLoadingDetections(false)
    }
  }

  // Fetch FHIR reports
  const fetchFHIRReports = async () => {
    setLoadingReports(true)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/fhir-reports/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setFhirReports(Array.isArray(data) ? data : data.results || [])
      }
    } catch (error) {
      console.error('Error fetching reports:', error)
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

  // Handle appointment approval
  const handleApproveAppointment = async (appointmentId: number) => {
    setActionLoading(appointmentId)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/appointments/${appointmentId}/approve/`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        fetchAppointments()
      }
    } catch (error) {
      console.error('Error approving appointment:', error)
    } finally {
      setActionLoading(null)
    }
  }

  // Handle appointment rejection
  const handleRejectAppointment = async (appointmentId: number) => {
    setActionLoading(appointmentId)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/appointments/${appointmentId}/reject/`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        fetchAppointments()
      }
    } catch (error) {
      console.error('Error rejecting appointment:', error)
    } finally {
      setActionLoading(null)
    }
  }

  // Run AI detection on uploaded MRI
  const handleRunDetection = async (detectionId: number) => {
    setActionLoading(detectionId)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/${detectionId}/run_detection/`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        fetchDetections()
        alert('AI Detection completed successfully!')
      } else {
        const data = await response.json()
        alert(data.error || 'Failed to run detection')
      }
    } catch (error) {
      console.error('Error running detection:', error)
      alert('Error running detection')
    } finally {
      setActionLoading(null)
    }
  }

  // Generate FHIR report for a detection result
  const handleGenerateFHIRReport = async (detectionId: number) => {
    setActionLoading(detectionId)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/${detectionId}/generate_fhir_report/`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          hospital_name: 'DementiaNext AI Diagnostic Center'
        })
      })
      if (response.ok) {
        fetchFHIRReports()
        fetchDetections()
        fetchAppointments()
        alert('FHIR Diagnostic Report generated successfully!')
      } else {
        const data = await response.json()
        alert(data.error || 'Failed to generate report')
      }
    } catch (error) {
      console.error('Error generating report:', error)
      alert('Error generating report')
    } finally {
      setActionLoading(null)
    }
  }

  // View FHIR JSON for a report
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

  // Export FHIR JSON
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

  useEffect(() => {
    if (user && user.role === 'doctor') {
      fetchAppointments()
      fetchDetections()
      fetchFHIRReports()
    }
  }, [user])

  // Overview statistics
  const stats = [
    { label: 'Total Patients', value: '142', change: '+8', trend: 'up', icon: Users, color: 'from-blue-500 to-blue-600' },
    { label: 'Urgent Cases', value: '12', change: '+3', trend: 'up', icon: AlertTriangle, color: 'from-red-500 to-red-600' },
    { label: 'Stable Cases', value: '98', change: '-2', trend: 'down', icon: CheckCircle, color: 'from-green-500 to-green-600' },
    { label: 'Pending Reports', value: '8', change: '+2', trend: 'up', icon: FileText, color: 'from-teal-500 to-teal-600' },
  ]

  // Classification distribution
  const classificationData = [
    { name: 'AD', value: 52, color: '#0066cc' },
    { name: 'MCI', value: 33, color: '#00a896' },
    { name: 'PDD', value: 25, color: '#10b981' },
    { name: 'Prodromal', value: 19, color: '#64748b' },
    { name: 'Control', value: 13, color: '#6366f1' },
  ]

  // Severity distribution
  const severityData = [
    { severity: 'Mild', count: 54 },
    { severity: 'Moderate', count: 62 },
    { severity: 'Severe', count: 26 },
  ]

  // Recent activity trends
  const activityData = [
    { month: 'Jun', newDiagnoses: 18, followUps: 45, reports: 32 },
    { month: 'Jul', newDiagnoses: 22, followUps: 48, reports: 35 },
    { month: 'Aug', newDiagnoses: 19, followUps: 52, reports: 38 },
    { month: 'Sep', newDiagnoses: 25, followUps: 50, reports: 42 },
    { month: 'Oct', newDiagnoses: 21, followUps: 55, reports: 45 },
  ]

  // Patient list
  const patients = [
    {
      id: 'PT-2025-001',
      name: 'Margaret Thompson',
      age: 72,
      diagnosis: 'AD',
      model: 'Alzheimer\'s Model',
      severity: 'Moderate',
      lastVisit: '2 days ago',
      score: 72,
      trend: 'stable',
      alerts: 0,
      priority: 'normal'
    },
    {
      id: 'PT-2025-045',
      name: 'Robert Martinez',
      age: 68,
      diagnosis: 'PDD',
      model: 'Parkinson\'s Model',
      severity: 'Mild',
      lastVisit: '1 week ago',
      score: 78,
      trend: 'stable',
      alerts: 0,
      priority: 'normal'
    },
    {
      id: 'PT-2025-089',
      name: 'Elizabeth Chen',
      age: 65,
      diagnosis: 'MCI',
      model: 'Alzheimer\'s Model',
      severity: 'Early',
      lastVisit: '3 days ago',
      score: 85,
      trend: 'improving',
      alerts: 1,
      priority: 'monitor'
    },
    {
      id: 'PT-2025-112',
      name: 'James Wilson',
      age: 74,
      diagnosis: 'Prodromal',
      model: 'Parkinson\'s Model',
      severity: 'Early',
      lastVisit: '5 days ago',
      score: 82,
      trend: 'stable',
      alerts: 0,
      priority: 'normal'
    },
    {
      id: 'PT-2025-078',
      name: 'Patricia Davis',
      age: 70,
      diagnosis: 'AD',
      model: 'Alzheimer\'s Model',
      severity: 'Severe',
      lastVisit: '1 day ago',
      score: 48,
      trend: 'declining',
      alerts: 3,
      priority: 'urgent'
    },
  ]

  // Alerts & Notifications
  const alerts = [
    {
      type: 'urgent',
      message: 'PT-2025-078: Rapid cognitive decline detected - immediate review needed',
      time: '10 min ago',
      patient: 'Patricia Davis'
    },
    {
      type: 'warning',
      message: 'PT-2025-089: Follow-up appointment overdue',
      time: '2 hours ago',
      patient: 'Elizabeth Chen'
    },
    {
      type: 'info',
      message: '8 pending reports require review and signature',
      time: '1 day ago',
      patient: 'Multiple patients'
    },
  ]

  const getTrendIcon = (trend: string) => {
    switch(trend) {
      case 'declining': return <TrendingDown className="text-red-500" size={16} />
      case 'improving': return <TrendingUp className="text-green-500" size={16} />
      default: return <Activity className="text-blue-500" size={16} />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch(priority) {
      case 'urgent': return 'border-red-300 bg-red-50'
      case 'monitor': return 'border-orange-300 bg-orange-50'
      default: return 'border-gray-200 bg-white'
    }
  }

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
  if (!user || user.role !== 'doctor') {
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
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold mb-2 text-gray-900">
                <span className="bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
                  Dr. {user?.first_name || user?.email?.split('@')[0]}'s Dashboard
                </span>
              </h1>
              <p className="text-xl text-gray-600">
                Comprehensive patient monitoring and analytics
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" size="lg">
                <Bell size={20} className="mr-2" />
                Alerts
                {alerts.length > 0 && (
                  <Badge className="ml-2 bg-red-500">{alerts.length}</Badge>
                )}
              </Button>
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
                <Download size={20} className="mr-2" />
                Export Data
              </Button>
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
            variant={activeTab === 'appointments' ? 'default' : 'outline'}
            onClick={() => setActiveTab('appointments')}
            className={activeTab === 'appointments' ? 'bg-green-600' : ''}
          >
            <Calendar className="mr-2" size={18} />
            Appointments
            {appointments.filter(a => a.status === 'pending').length > 0 && (
              <Badge className="ml-2 bg-red-500">{appointments.filter(a => a.status === 'pending').length}</Badge>
            )}
          </Button>
          <Button
            variant={activeTab === 'detections' ? 'default' : 'outline'}
            onClick={() => setActiveTab('detections')}
            className={activeTab === 'detections' ? 'bg-purple-600' : ''}
          >
            <Brain className="mr-2" size={18} />
            Detection Results
          </Button>
          <Button
            variant={activeTab === 'reports' ? 'default' : 'outline'}
            onClick={() => setActiveTab('reports')}
            className={activeTab === 'reports' ? 'bg-teal-600' : ''}
          >
            <FileText className="mr-2" size={18} />
            FHIR Reports
          </Button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12"
        >
          {stats.map((stat, idx) => {
            const Icon = stat.icon
            return (
              <Card key={idx} className="border-2 hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg bg-gradient-to-r ${stat.color} flex items-center justify-center`}>
                      <Icon className="text-white" size={24} />
                    </div>
                    <div className={`flex items-center gap-1 text-sm font-medium ${
                      stat.trend === 'up' ? 'text-blue-600' : 'text-gray-600'
                    }`}>
                      {stat.change}
                      {stat.trend === 'up' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    </div>
                  </div>
                  <div className="text-3xl font-bold mb-1 text-gray-900">{stat.value}</div>
                  <div className="text-sm text-gray-600">{stat.label}</div>
                </CardContent>
              </Card>
            )
          })}
        </motion.div>

        {/* Alerts Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-12"
        >
          <Card className="border-2 border-orange-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell size={24} />
                Priority Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {alerts.map((alert, idx) => {
                  const bgColors = {
                    urgent: 'bg-red-50 border-red-300',
                    warning: 'bg-yellow-50 border-yellow-300',
                    info: 'bg-blue-50 border-blue-300'
                  }
                  const iconColors = {
                    urgent: 'text-red-600',
                    warning: 'text-yellow-600',
                    info: 'text-blue-600'
                  }
                  return (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg border-2 ${bgColors[alert.type as keyof typeof bgColors]}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <AlertTriangle className={`flex-shrink-0 mt-0.5 ${iconColors[alert.type as keyof typeof iconColors]}`} size={20} />
                          <div className="flex-1">
                            <p className="font-medium mb-1">{alert.message}</p>
                            <div className="flex items-center gap-4 text-sm text-gray-600">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {alert.time}
                              </span>
                            </div>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm">
                          Review
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Analytics Charts */}
        <div className="grid lg:grid-cols-2 gap-8 mb-12">
          {/* Classification Distribution */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Card className="border-2">
              <CardHeader>
                <CardTitle>Classification Distribution</CardTitle>
                <CardDescription>Patient breakdown by AI model diagnosis</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={classificationData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {classificationData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Severity Distribution */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Card className="border-2">
              <CardHeader>
                <CardTitle>Severity Distribution</CardTitle>
                <CardDescription>Patient count by severity level</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={severityData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="severity" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="count" fill="#0066cc" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Activity Trends */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mb-12"
        >
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp size={24} />
                Clinical Activity Trends (Last 5 Months)
              </CardTitle>
              <CardDescription>
                Tracking diagnoses, follow-ups, and report generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={activityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="newDiagnoses" stroke="#0066cc" strokeWidth={3} name="New Diagnoses" />
                    <Line type="monotone" dataKey="followUps" stroke="#00a896" strokeWidth={3} name="Follow-ups" />
                    <Line type="monotone" dataKey="reports" stroke="#10b981" strokeWidth={3} name="Reports Generated" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Patient List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          <Card className="border-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Users size={24} />
                  Patient List
                </CardTitle>
                <div className="flex gap-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                    <Input
                      placeholder="Search patients..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 w-64"
                    />
                  </div>
                  <Button variant="outline">
                    <Filter size={18} className="mr-2" />
                    Filter
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {patients.map((patient) => (
                  <div
                    key={patient.id}
                    className={`p-6 rounded-lg border-2 ${getPriorityColor(patient.priority)} hover:shadow-md transition-all`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-lg">{patient.name}</h3>
                          <Badge variant="secondary">{patient.id}</Badge>
                          <Badge className="bg-blue-100 text-blue-800">{patient.diagnosis}</Badge>
                          {patient.alerts > 0 && (
                            <Badge variant="destructive" className="flex items-center gap-1">
                              <Bell size={12} />
                              {patient.alerts}
                            </Badge>
                          )}
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Age:</span>
                            <div className="font-medium">{patient.age}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Model:</span>
                            <div className="font-medium text-xs">{patient.model}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Severity:</span>
                            <div className="font-medium">{patient.severity}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Score:</span>
                            <div className="font-medium">{patient.score}/100</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Trend:</span>
                            <div className="flex items-center gap-1 font-medium">
                              {getTrendIcon(patient.trend)}
                              {patient.trend}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline">
                              <Eye size={16} className="mr-1" />
                              View
                            </Button>
                            <Button size="sm" className="bg-blue-600">
                              <FileText size={16} className="mr-1" />
                              Report
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex justify-center">
                <Button variant="outline">
                  Load More Patients
                  <ArrowRight className="ml-2" size={18} />
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        </>
        )}

        {/* Appointments Tab */}
        {activeTab === 'appointments' && (
          <div className="space-y-6">
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="text-green-600" size={24} />
                  Patient Appointments
                </CardTitle>
                <CardDescription>
                  Manage appointment requests from patients
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
                    <p className="text-sm mt-2">Appointment requests from patients will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {appointments.map((apt) => (
                      <div 
                        key={apt.id} 
                        className={`p-6 rounded-xl border-2 transition-all ${
                          apt.status === 'pending' ? 'border-yellow-300 bg-yellow-50' :
                          apt.status === 'approved' ? 'border-green-300 bg-green-50' :
                          apt.status === 'rejected' ? 'border-red-300 bg-red-50' :
                          apt.status === 'completed' ? 'border-blue-300 bg-blue-50' :
                          'border-gray-300 bg-gray-50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="font-semibold text-xl text-gray-900">
                                {apt.patient?.user?.first_name} {apt.patient?.user?.last_name}
                              </h3>
                              <Badge variant="secondary">{apt.appointment_id}</Badge>
                              <Badge 
                                className={
                                  apt.status === 'pending' ? 'bg-yellow-200 text-yellow-800' :
                                  apt.status === 'approved' ? 'bg-green-200 text-green-800' :
                                  apt.status === 'rejected' ? 'bg-red-200 text-red-800' :
                                  apt.status === 'completed' ? 'bg-blue-200 text-blue-800' :
                                  'bg-gray-200 text-gray-800'
                                }
                              >
                                {apt.status}
                              </Badge>
                            </div>
                            
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                              <div>
                                <span className="text-gray-500">Email:</span>
                                <div className="font-medium">{apt.patient?.user?.email}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Date:</span>
                                <div className="font-medium">{new Date(apt.scheduled_date).toLocaleDateString()}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Time:</span>
                                <div className="font-medium">{apt.scheduled_time}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Gender:</span>
                                <div className="font-medium capitalize">{apt.patient?.gender || 'N/A'}</div>
                              </div>
                            </div>

                            {apt.reason && (
                              <div className="p-3 bg-white/60 rounded-lg mb-3">
                                <span className="text-sm text-gray-500 font-medium">Reason:</span>
                                <p className="text-gray-700">{apt.reason}</p>
                              </div>
                            )}

                            {apt.notes && (
                              <div className="p-3 bg-blue-100 rounded-lg">
                                <span className="text-sm text-blue-600 font-medium">Notes:</span>
                                <p className="text-gray-700">{apt.notes}</p>
                              </div>
                            )}
                          </div>

                          <div className="flex flex-col gap-2 ml-4">
                            {apt.status === 'pending' && (
                              <>
                                <Button
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700"
                                  onClick={() => handleApproveAppointment(apt.id)}
                                  disabled={actionLoading === apt.id}
                                >
                                  {actionLoading === apt.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <>
                                      <Check size={16} className="mr-1" />
                                      Approve
                                    </>
                                  )}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleRejectAppointment(apt.id)}
                                  disabled={actionLoading === apt.id}
                                >
                                  <X size={16} className="mr-1" />
                                  Reject
                                </Button>
                              </>
                            )}
                            {apt.status === 'approved' && (
                              <Button
                                size="sm"
                                className="bg-blue-600 hover:bg-blue-700"
                                onClick={() => {
                                  // Navigate to upload/run detection for this patient
                                  // This could open a modal or redirect
                                  alert('Ready to run detection for this patient')
                                }}
                              >
                                <Brain size={16} className="mr-1" />
                                Run Detection
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

        {/* Detection Results Tab */}
        {activeTab === 'detections' && (
          <div className="space-y-6">
            {/* Pending MRI Scans */}
            <Card className="border-2 border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="text-orange-600" size={24} />
                  Pending MRI Scans
                </CardTitle>
                <CardDescription>
                  MRI scans uploaded by patients awaiting AI detection analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                {detectionResults.filter(d => d.status === 'pending').length === 0 ? (
                  <div className="text-center py-4 text-gray-500">
                    <p>No pending MRI scans</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {detectionResults.filter(d => d.status === 'pending').map((detection) => (
                      <div key={detection.id} className="p-4 rounded-lg border-2 bg-white border-orange-200">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-lg text-gray-900">
                              {detection.patient?.user?.first_name} {detection.patient?.user?.last_name}
                            </h3>
                            <p className="text-sm text-gray-600">
                              Patient ID: {detection.patient?.id} | Detection ID: {detection.detection_id}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                              Uploaded: {new Date(detection.created_at).toLocaleString()}
                            </p>
                            {detection.notes && (
                              <p className="text-sm text-gray-600 mt-1">Notes: {detection.notes}</p>
                            )}
                          </div>
                          <Button
                            className="bg-orange-600 hover:bg-orange-700"
                            onClick={() => handleRunDetection(detection.id)}
                            disabled={actionLoading === detection.id}
                          >
                            {actionLoading === detection.id ? (
                              <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : (
                              <Brain className="mr-2" size={16} />
                            )}
                            Run AI Detection
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Completed Detections */}
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="text-purple-600" size={24} />
                  Completed Detection Results
                </CardTitle>
                <CardDescription>
                  View AI detection results and generate FHIR diagnostic reports
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingDetections ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
                  </div>
                ) : detectionResults.filter(d => d.status === 'completed').length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Brain className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg">No completed detection results yet</p>
                    <p className="text-sm mt-2">Run AI detection on pending MRI scans to see results</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {detectionResults.filter(d => d.status === 'completed').map((detection) => (
                      <div key={detection.id} className="p-6 rounded-xl border-2 hover:shadow-lg transition-all">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="font-semibold text-xl text-gray-900">
                                {detection.patient?.user?.first_name} {detection.patient?.user?.last_name}
                              </h3>
                              <Badge variant="secondary">{detection.detection_id}</Badge>
                              <Badge 
                                className={
                                  detection.predicted_class === 'alzheimers' ? 'bg-red-100 text-red-800' :
                                  detection.predicted_class === 'cn' ? 'bg-green-100 text-green-800' :
                                  'bg-blue-100 text-blue-800'
                                }
                              >
                                {detection.predicted_class === 'alzheimers' ? "Alzheimer's" : 
                                 detection.predicted_class === 'cn' ? 'Normal/Control' : 
                                 detection.predicted_class}
                              </Badge>
                            </div>
                            
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mt-3">
                              <div>
                                <span className="text-gray-500">Confidence:</span>
                                <div className="font-medium text-green-600">
                                  {detection.confidence_score ? `${(detection.confidence_score * 100).toFixed(1)}%` : 'N/A'}
                                </div>
                              </div>
                              <div>
                                <span className="text-gray-500">Processing Time:</span>
                                <div className="font-medium">{detection.processing_time?.toFixed(2)}s</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Patient ID:</span>
                                <div className="font-medium">{detection.patient?.id}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Date:</span>
                                <div className="font-medium">{new Date(detection.created_at).toLocaleDateString()}</div>
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-col gap-2 ml-4">
                            <Button
                              size="sm"
                              className="bg-teal-600 hover:bg-teal-700"
                              onClick={() => handleGenerateFHIRReport(detection.id)}
                              disabled={actionLoading === detection.id}
                            >
                              {actionLoading === detection.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <>
                                  <FileText size={16} className="mr-1" />
                                  Generate FHIR Report
                                </>
                              )}
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

        {/* FHIR Reports Tab */}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="text-teal-600" size={24} />
                  FHIR Diagnostic Reports
                </CardTitle>
                <CardDescription>
                  HL7 FHIR R4 compliant diagnostic reports generated from detection results
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingReports ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
                  </div>
                ) : fhirReports.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg">No FHIR reports yet</p>
                    <p className="text-sm mt-2">Generate reports from detection results in the Detection Results tab</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {fhirReports.map((report) => (
                      <div key={report.id} className="p-6 rounded-xl border-2 hover:shadow-lg transition-all">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="font-semibold text-xl text-gray-900">
                                Report #{report.report_id}
                              </h3>
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
                                <Badge variant="outline">{formatFHRCoding(report.conclusion_code)}</Badge>
                              )}
                            </div>
                            
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                              <div>
                                <span className="text-gray-500">Patient:</span>
                                <div className="font-medium">
                                  {report.patient?.user?.first_name} {report.patient?.user?.last_name}
                                </div>
                              </div>
                              <div>
                                <span className="text-gray-500">Issued:</span>
                                <div className="font-medium">{new Date(report.issued || report.issued_date || report.created_at).toLocaleDateString()}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Detection ID:</span>
                                <div className="font-medium">{report.detection_id || report.detection?.detection_id || report.detection_result?.result_id || 'N/A'}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Created:</span>
                                <div className="font-medium">{new Date(report.created_at).toLocaleDateString()}</div>
                              </div>
                            </div>

                            {report.conclusion && (
                              <div className="p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-500 font-medium">Conclusion:</span>
                                <p className="text-gray-700">{report.conclusion}</p>
                              </div>
                            )}
                          </div>

                          <div className="flex flex-col gap-2 ml-4">
                            <Button size="sm" variant="outline" onClick={() => handleViewFHIRReport(report.id)}>
                              <Eye size={16} className="mr-1" />
                              View
                            </Button>
                            <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={() => handleExportFHIRReport(report.fhir_json || report)}>
                              <Download size={16} className="mr-1" />
                              Export
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
      </div>
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
    </div>
  )
}
