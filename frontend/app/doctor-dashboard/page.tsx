'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { 
  Users, Search, Activity, Brain, FileText, Download, Eye, 
  Stethoscope, X, Loader2, ClipboardList, Send, Save
} from 'lucide-react'
import { PUBLIC_API_ROOT as API_URL } from '@/lib/publicApi'

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
  patient_name?: string
  doctor: any
  appointment: any
  uploaded_file: string
  status: string
  predicted_class: string
  predicted_class_display?: string
  confidence_score: number
  processing_time: number
  model_type?: string
  notes: string
  created_at: string
  review_status?: string
}

interface FHIRReport {
  id: number
  report_id: string
  patient: any
  doctor: any
  detection_result: any
  detection?: any
  detection_id?: string
  status: string
  issued_date: string
  conclusion: string
  conclusion_code: any
  created_at: string
  fhir_json?: any
}

export default function DoctorDashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterDiagnosis, setFilterDiagnosis] = useState('All')
  const [activeTab, setActiveTab] = useState<'overview' | 'records'>('overview')
  
  // State for real data
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [detectionResults, setDetectionResults] = useState<DetectionResult[]>([])
  const [fhirReports, setFhirReports] = useState<FHIRReport[]>([])
  const [allPatients, setAllPatients] = useState<any[]>([])
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

  // Draft review modal states
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [selectedDetectionForReview, setSelectedDetectionForReview] = useState<DetectionResult | null>(null)
  const [reviewForm, setReviewForm] = useState({
    ai_accepted: true,
    doctor_override_class: '',
    doctor_conclusion: '',
    doctor_notes: '',
    patient_summary: '',
    is_sent_to_patient: false
  })

  // Records tab filters
  const [recordsSearch, setRecordsSearch] = useState('')
  const [recordsStatusFilter, setRecordsStatusFilter] = useState('all')
  const [recordsDiagnosisFilter, setRecordsDiagnosisFilter] = useState('all')
  const [isSavingReview, setIsSavingReview] = useState(false)
  const [reviewMessage, setReviewMessage] = useState<{text: string, type: 'success'|'error'} | null>(null)

  // Auth check - redirect if not logged in or not a doctor
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
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

  // Fetch all registered patients
  const fetchAllPatients = async () => {
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/auth/patients/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setAllPatients(Array.isArray(data) ? data : [])
      }
    } catch (error) {
      console.error('Error fetching all patients:', error)
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
    } finally {
      setActionLoading(null)
    }
  }

  // Open review modal and fetch existing review if any
  const openReviewModal = async (detection: DetectionResult) => {
    setSelectedDetectionForReview(detection)
    setShowReviewModal(true)
    setReviewMessage(null)
    setReviewForm({
      ai_accepted: true,
      doctor_override_class: '',
      doctor_conclusion: `AI analysis suggests ${detection.predicted_class}. `,
      doctor_notes: '',
      patient_summary: `Your MRI scan has been analyzed. Initial findings indicate ${detection.predicted_class}. We will discuss these results and next steps during our upcoming consultation.`,
      is_sent_to_patient: false
    })

    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/${detection.id}/review/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setReviewForm({
          ai_accepted: data.ai_accepted,
          doctor_override_class: data.doctor_override_class || '',
          doctor_conclusion: data.doctor_conclusion,
          doctor_notes: data.doctor_notes,
          patient_summary: data.patient_summary,
          is_sent_to_patient: data.is_sent_to_patient
        })
      }
    } catch {
      // ignore
    }
  }

  // Save review from dashboard
  const handleSaveReview = async (sendToPatient: boolean) => {
    if (!selectedDetectionForReview) return

    if (!reviewForm.doctor_conclusion.trim()) {
      setReviewMessage({ text: 'Please write your clinical conclusion before saving.', type: 'error' })
      return
    }
    if (!reviewForm.ai_accepted && !reviewForm.doctor_override_class) {
      setReviewMessage({ text: 'Please select an override diagnosis.', type: 'error' })
      return
    }
    if (sendToPatient && !reviewForm.patient_summary.trim()) {
      setReviewMessage({ text: 'Please write a patient-facing summary before sending.', type: 'error' })
      return
    }

    setIsSavingReview(true)
    setReviewMessage(null)
    try {
      const token = localStorage.getItem('authToken')
      const bodyPayload = {
        ...reviewForm,
        is_sent_to_patient: sendToPatient || reviewForm.is_sent_to_patient
      }
      const response = await fetch(`${API_URL}/detection/detections/${selectedDetectionForReview.id}/review/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bodyPayload)
      })

      if (response.ok) {
        setReviewForm(prev => ({ ...prev, ...bodyPayload }))
        await fetchDetections()
        await fetchFHIRReports()

        if (sendToPatient) {
          setShowReviewModal(false)
          setReviewMessage(null)
        } else {
          setReviewMessage({ text: 'Draft saved successfully.', type: 'success' })
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.error || errorData.detail || 'Failed to save review')
      }
    } catch (err: any) {
      setReviewMessage({ text: err.message, type: 'error' })
    } finally {
      setIsSavingReview(false)
    }
  }

  // Generate FHIR report for a detection result
  const handleGenerateFHIRReport = async (detection: DetectionResult) => {
    const reviewStatus = detection.review_status
    if (!reviewStatus || reviewStatus === 'needs_review') {
      openReviewModal(detection)
      setReviewMessage({ text: 'Please write your clinical review first. The FHIR report will be generated when you send to patient.', type: 'error' })
      return
    }
    setActionLoading(detection.id)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/${detection.id}/generate_fhir_report/`, {
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
        await fetchFHIRReports()
        await fetchDetections()
        fetchAppointments()
      } else {
        const data = await response.json()
        if (data.error?.includes('review')) {
          openReviewModal(detection)
          setReviewMessage({ text: data.error, type: 'error' })
        } else {
          alert(data.error || 'Failed to generate report')
        }
      }
    } catch (error) {
      console.error('Error generating report:', error)
    } finally {
      setActionLoading(null)
    }
  }

  // View / export FHIR as formatted PDF
  const handleViewFHIRReport = async (reportId: number) => {
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/fhir-reports/${reportId}/fhir-json/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        const { generateFhirPdf } = await import('@/lib/generateFhirPdf')
        generateFhirPdf(data)
      } else {
        const data = await response.json()
        alert(data.error || 'Failed to fetch report')
      }
    } catch (error) {
      console.error('Error fetching FHIR report:', error)
      alert('Error fetching FHIR report')
    }
  }

  const handleExportFHIRReport = async (reportJson: any) => {
    if (!reportJson) return
    const { generateFhirPdf } = await import('@/lib/generateFhirPdf')
    generateFhirPdf(reportJson)
  }

  // Delete FHIR report
  const handleDeleteFHIRReport = async (reportId: number) => {
    if (!confirm('Are you sure you want to delete this FHIR report? This action cannot be undone.')) return
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/fhir-reports/${reportId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (response.ok || response.status === 204) {
        setFhirReports(prev => prev.filter(r => r.id !== reportId))
      } else {
        const errorData = await response.json().catch(() => ({}))
        alert(errorData.error || 'Failed to delete report.')
      }
    } catch (err) {
      console.error('Delete report error:', err)
      alert('Failed to delete report.')
    }
  }

  // Delete detection result
  const handleDeleteDetection = async (detectionId: number) => {
    if (!confirm('Are you sure you want to delete this detection result? This action cannot be undone.')) return
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_URL}/detection/detections/${detectionId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (response.ok || response.status === 204) {
        setDetectionResults(prev => prev.filter(d => d.id !== detectionId))
      } else {
        const errorData = await response.json().catch(() => ({}))
        alert(errorData.error || 'Failed to delete detection.')
      }
    } catch (err) {
      console.error('Delete detection error:', err)
      alert('Failed to delete detection.')
    }
  }

  useEffect(() => {
    if (user && user.role === 'doctor') {
      fetchAppointments()
      fetchDetections()
      fetchFHIRReports()
      fetchAllPatients()
    }
  }, [user])

  // Filter detections that the doctor has accepted (review_status === 'sent')
  const acceptedDetections = detectionResults.filter(d => d.review_status === 'sent')
  
  const getUniquePatientsCount = (classes: string[]) => {
    return new Set(acceptedDetections.filter(d => classes.includes(d.predicted_class)).map(d => d.patient)).size
  }

  const uniquePatients = new Set(acceptedDetections.map(d => d.patient)).size
  const uniqueCN = getUniquePatientsCount(['cn'])
  const uniqueDementia = getUniquePatientsCount(['dementia'])
  
  const uniqueAlzheimer = getUniquePatientsCount(['alzheimers'])
  const uniqueFTD = getUniquePatientsCount(['ftd'])
  const uniquePD = getUniquePatientsCount(['pd'])

  const allStats = [
    { label: 'Total Patients', value: uniquePatients, icon: Users, accent: 'bg-slate-100 text-slate-600' },
    { label: 'Control (CN)', value: uniqueCN, icon: Activity, accent: 'bg-blue-50 text-blue-600' },
    { label: 'Dementia', value: uniqueDementia, icon: Brain, accent: 'bg-violet-50 text-violet-600' },
    { label: "Alzheimer's", value: uniqueAlzheimer, icon: Brain, accent: 'bg-rose-50 text-rose-600' },
    { label: 'FTD', value: uniqueFTD, icon: Activity, accent: 'bg-amber-50 text-amber-600' },
    { label: 'Parkinson\'s', value: uniquePD, icon: Activity, accent: 'bg-emerald-50 text-emerald-600' },
  ]

  let subclassifierData = [
    { name: 'Alzheimer\'s', value: uniqueAlzheimer, color: '#e11d48' },
    { name: 'FTD', value: uniqueFTD, color: '#d97706' },
    { name: 'Parkinson\'s', value: uniquePD, color: '#059669' },
    { name: 'Control', value: uniqueCN, color: '#2563eb' },
  ].filter(c => c.value > 0)
  
  if (subclassifierData.length === 0) {
    subclassifierData = [{ name: 'No Data', value: 1, color: '#e5e7eb' }]
  }

  let binaryData = [
    { name: 'Dementia', value: uniqueDementia, color: '#7c3aed' },
    { name: 'Control', value: uniqueCN, color: '#2563eb' },
  ].filter(c => c.value > 0)

  if (binaryData.length === 0) {
    binaryData = [{ name: 'No Data', value: 1, color: '#e5e7eb' }]
  }

  // Unique patients list computation
  const patientsWithScans = new Map(
    acceptedDetections.reduce((map, detection) => {
      const pId = detection.patient;
      if (!pId) return map;
      if (!map.has(pId) || new Date(detection.created_at) > new Date(map.get(pId).created_at)) {
        map.set(pId, {
          ...detection,
          patientLabel: detection.patient_name || `${detection.patient?.user?.first_name || ''} ${detection.patient?.user?.last_name || ''}`.trim() || 'Unknown Patient',
        });
      }
      return map;
    }, new Map())
  );

  // Merge the full patient list with those that have scans
  const uniquePatientsData = allPatients.map(patient => {
    if (patientsWithScans.has(patient.id)) {
      return patientsWithScans.get(patient.id);
    }
    // Base fallback for users without scans
    return {
      id: `no-scan-${patient.id}`,
      patient: patient.id, // Just the ID
      patientLabel: patient.name || 'Unknown Patient',
      patient_email: patient.email,
      predicted_class: 'none',
      created_at: null
    };
  });

  const filteredPatientsData = uniquePatientsData.filter((p) => {
    const matchesSearch = p.patientLabel.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (p.patient_email && p.patient_email.toLowerCase().includes(searchQuery.toLowerCase())) ||
                          String(p.patient).toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterDiagnosis === 'All') return matchesSearch;
    
    // Map backend class to filter value
    let mappedClass = '';
    switch(p.predicted_class) {
      case 'alzheimers': mappedClass = 'Alzheimer\'s'; break;
      case 'dementia': mappedClass = 'Dementia'; break;
      case 'cn': mappedClass = 'CN'; break;
      case 'pd': mappedClass = 'PD'; break;
      case 'ftd': mappedClass = 'FTD'; break;
      case 'none': mappedClass = 'No Scan'; break;
    }
    
    const matchesFilter = mappedClass === filterDiagnosis;
    return matchesSearch && matchesFilter;
  });

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

  const pendingReviewCount = detectionResults.filter(d => d.review_status === 'draft' || d.review_status === 'needs_review' || !d.review_status).length

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Dr. {user?.first_name || user?.email?.split('@')[0]}&apos;s Dashboard
              </h1>
              <p className="text-base text-gray-500 mt-1">
                Clinical overview &amp; patient records
              </p>
            </div>
            {pendingReviewCount > 0 && (
              <button
                onClick={() => setActiveTab('records')}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
              >
                <ClipboardList size={16} />
                {pendingReviewCount} Pending Review{pendingReviewCount !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-5 py-3 text-base font-medium border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`px-5 py-3 text-base font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'records'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Patient Records
            {pendingReviewCount > 0 && (
              <span className="bg-blue-600 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
                {pendingReviewCount}
              </span>
            )}
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>

        {/* Hero Stats Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 mb-6"
        >
          <div className="grid grid-cols-3 lg:grid-cols-6 divide-x divide-gray-100">
            {allStats.map((stat, idx) => {
              const Icon = stat.icon
              return (
                <div key={idx} className="px-4 first:pl-0 last:pr-0 text-center">
                  <div className={`w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center ${stat.accent}`}>
                    <Icon size={18} />
                  </div>
                  <div className="text-3xl font-extrabold text-gray-900 tabular-nums">{stat.value}</div>
                  <div className="text-xs text-gray-500 mt-1 font-medium">{stat.label}</div>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Charts + Quick Actions row */}
        <div className="grid lg:grid-cols-3 gap-6 mb-6">
          {/* Binary Chart */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 h-full">
              <h3 className="text-sm font-bold text-gray-800 mb-1">Binary Classification</h3>
              <p className="text-xs text-gray-400 mb-3">Dementia vs Control</p>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={binaryData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={4} dataKey="value" stroke="none">
                      {binaryData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: '13px' }} formatter={(v: number, n: string) => [`${v}`, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-5 mt-2">
                {binaryData.map((e, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: e.color }} />
                    <span className="text-xs text-gray-600 font-medium">{e.name} ({e.value})</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Subtype Chart */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 h-full">
              <h3 className="text-sm font-bold text-gray-800 mb-1">Subtype Breakdown</h3>
              <p className="text-xs text-gray-400 mb-3">Multi-class distribution</p>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={subclassifierData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={4} dataKey="value" stroke="none">
                      {subclassifierData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: '13px' }} formatter={(v: number, n: string) => [`${v}`, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
                {subclassifierData.map((e, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: e.color }} />
                    <span className="text-xs text-gray-600 font-medium">{e.name} ({e.value})</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Quick Actions */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 h-full flex flex-col">
              <h3 className="text-sm font-bold text-gray-800 mb-1">Quick Actions</h3>
              <p className="text-xs text-gray-400 mb-4">Shortcuts to key workflows</p>
              <div className="flex-1 flex flex-col gap-3">
                <button onClick={() => setActiveTab('records')} className="flex items-center gap-3 p-3 rounded-xl bg-blue-50 hover:bg-blue-100 transition-colors text-left group">
                  <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
                    <Stethoscope size={16} className="text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Review Detections</p>
                    <p className="text-xs text-gray-500">{pendingReviewCount} pending</p>
                  </div>
                </button>
                <button onClick={() => router.push('/detection')} className="flex items-center gap-3 p-3 rounded-xl bg-teal-50 hover:bg-teal-100 transition-colors text-left">
                  <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center shrink-0">
                    <Brain size={16} className="text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">New MRI Analysis</p>
                    <p className="text-xs text-gray-500">Upload & detect</p>
                  </div>
                </button>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Patient Registry */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100">
              <div>
                <h3 className="text-base font-bold text-gray-800">Patient Registry</h3>
                <p className="text-sm text-gray-400">{filteredPatientsData.length} patient{filteredPatientsData.length !== 1 ? 's' : ''}</p>
              </div>
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                  <Input placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 h-10 w-56 text-sm border-gray-200 rounded-lg" />
                </div>
                <select value={filterDiagnosis} onChange={(e) => setFilterDiagnosis(e.target.value)} className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm">
                  <option value="All">All</option>
                  <option value="CN">CN</option>
                  <option value="Dementia">Dementia</option>
                  <option value="Alzheimer's">AD</option>
                  <option value="FTD">FTD</option>
                  <option value="PD">PD</option>
                  <option value="No Scan">No Scans</option>
                </select>
              </div>
            </div>
            {filteredPatientsData.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <Users className="h-10 w-10 mx-auto mb-3 text-gray-200" />
                <p className="text-sm">No patients found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      <th className="text-left py-3 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Patient</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Diagnosis</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Last Scan</th>
                      <th className="text-right py-3 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredPatientsData.map((patient) => {
                      const diagClass = patient.predicted_class
                      const diagLabel = diagClass === 'none' ? '' : (patient.predicted_class_display || diagClass)
                      const diagStyle =
                        diagClass === 'alzheimers' ? 'text-rose-700 bg-rose-50' :
                        diagClass === 'dementia' ? 'text-violet-700 bg-violet-50' :
                        diagClass === 'ftd' ? 'text-amber-700 bg-amber-50' :
                        diagClass === 'pd' ? 'text-emerald-700 bg-emerald-50' :
                        diagClass === 'cn' ? 'text-blue-700 bg-blue-50' :
                        ''
                      return (
                        <tr key={patient.id} className="hover:bg-gray-50/50 transition-colors">
                          <td className="py-3.5 px-6">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-100 to-teal-100 flex items-center justify-center shrink-0">
                                <span className="text-sm font-bold text-blue-700">{(patient.patientLabel || 'P')[0].toUpperCase()}</span>
                              </div>
                              <div>
                                <div className="font-semibold text-gray-900 text-sm">{patient.patientLabel}</div>
                                {patient.patient_email && <div className="text-xs text-gray-400">{patient.patient_email}</div>}
                              </div>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            {diagClass !== 'none' ? (
                              <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold ${diagStyle}`}>{diagLabel}</span>
                            ) : (
                              <span className="text-gray-300 text-xs">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-sm text-gray-500">
                            {patient.created_at ? new Date(patient.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="py-3.5 px-6 text-right">
                            {patient.created_at && (
                              <button onClick={() => setActiveTab('records')} className="text-sm text-blue-600 hover:text-blue-700 font-medium hover:underline">
                                View Records
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </motion.div>
        </>
        )}


        {/* Patient Records Tab */}
        {activeTab === 'records' && (() => {
          const completedDetections = detectionResults.filter(d => d.status === 'completed')
          const filtered = completedDetections.filter(d => {
            const name = (d.patient_name || `Patient #${d.patient}`).toLowerCase()
            const matchesSearch = !recordsSearch || 
              name.includes(recordsSearch.toLowerCase()) ||
              d.detection_id?.toLowerCase().includes(recordsSearch.toLowerCase())
            const matchesStatus = recordsStatusFilter === 'all' ||
              (recordsStatusFilter === 'needs_review' && (!d.review_status || d.review_status === 'needs_review')) ||
              d.review_status === recordsStatusFilter
            const matchesDiagnosis = recordsDiagnosisFilter === 'all' || d.predicted_class === recordsDiagnosisFilter
            return matchesSearch && matchesStatus && matchesDiagnosis
          })

          return (
          <div>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Filters */}
              <div className="px-6 py-4 border-b border-gray-100">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-gray-800">Clinical Records</h3>
                    <p className="text-sm text-gray-400">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                      <Input placeholder="Search..." value={recordsSearch} onChange={(e) => setRecordsSearch(e.target.value)} className="pl-9 h-10 w-56 text-sm rounded-lg" />
                    </div>
                    <select value={recordsStatusFilter} onChange={(e) => setRecordsStatusFilter(e.target.value)} className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm">
                      <option value="all">All Statuses</option>
                      <option value="needs_review">Needs Review</option>
                      <option value="draft">Draft</option>
                      <option value="sent">Sent</option>
                    </select>
                    <select value={recordsDiagnosisFilter} onChange={(e) => setRecordsDiagnosisFilter(e.target.value)} className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm">
                      <option value="all">All Diagnoses</option>
                      <option value="cn">CN</option>
                      <option value="dementia">Dementia</option>
                      <option value="alzheimers">Alzheimer&apos;s</option>
                      <option value="ftd">FTD</option>
                      <option value="pd">PD</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Content */}
              {(loadingDetections || loadingReports) ? (
                <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-gray-300" /></div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-16 text-gray-400">
                  <FileText className="h-10 w-10 mx-auto mb-3 text-gray-200" />
                  <p className="text-sm">{completedDetections.length === 0 ? 'No detection results yet.' : 'No records match your filters.'}</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {filtered.map((detection) => {
                    const reviewStatus = detection.review_status || 'needs_review'
                    const statusLabel = reviewStatus === 'sent' ? 'Sent' : reviewStatus === 'draft' ? 'Draft' : 'Pending'
                    const statusStyle = reviewStatus === 'sent' ? 'bg-emerald-50 text-emerald-700' : reviewStatus === 'draft' ? 'bg-amber-50 text-amber-700' : 'bg-gray-100 text-gray-600'
                    const diagBadge =
                      detection.predicted_class === 'alzheimers' ? 'text-rose-700 bg-rose-50' :
                      detection.predicted_class === 'dementia' ? 'text-violet-700 bg-violet-50' :
                      detection.predicted_class === 'cn' ? 'text-blue-700 bg-blue-50' :
                      detection.predicted_class === 'ftd' ? 'text-amber-700 bg-amber-50' :
                      detection.predicted_class === 'pd' ? 'text-emerald-700 bg-emerald-50' :
                      'text-gray-600 bg-gray-50'
                    const matchingReport = fhirReports.find(r =>
                      (r.detection_id && r.detection_id === detection.detection_id) ||
                      (r.detection_result && r.detection_result === detection.id) ||
                      (r.detection?.id && r.detection.id === detection.id)
                    )
                    const confidence = detection.confidence_score ? (detection.confidence_score * 100) : 0

                    return (
                      <div key={detection.id} className="px-6 py-4 hover:bg-gray-50/50 transition-colors group">
                        <div className="flex items-center gap-4">
                          {/* Avatar */}
                          <div className="w-11 h-11 rounded-full bg-gradient-to-br from-blue-100 to-teal-100 flex items-center justify-center shrink-0">
                            <span className="text-sm font-bold text-blue-700">{(detection.patient_name || 'P')[0].toUpperCase()}</span>
                          </div>

                          {/* Patient + ID */}
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-gray-900">{detection.patient_name || `Patient #${detection.patient}`}</div>
                            <div className="text-xs text-gray-400 font-mono mt-0.5">{detection.detection_id}</div>
                          </div>

                          {/* Diagnosis */}
                          <span className={`hidden sm:inline-block px-2.5 py-1 rounded text-xs font-bold ${diagBadge}`}>
                            {detection.predicted_class_display || detection.predicted_class}
                          </span>

                          {/* Confidence */}
                          <div className="hidden md:flex items-center gap-2 w-28">
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${confidence}%` }} />
                            </div>
                            <span className="text-xs font-bold text-gray-600 tabular-nums w-12 text-right">{confidence.toFixed(1)}%</span>
                          </div>

                          {/* Date */}
                          <span className="hidden lg:block text-sm text-gray-400 w-24 text-right">{new Date(detection.created_at).toLocaleDateString()}</span>

                          {/* Status */}
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${statusStyle}`}>{statusLabel}</span>

                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => openReviewModal(detection)}
                              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                                reviewStatus === 'sent' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-blue-600 text-white hover:bg-blue-700'
                              }`}
                            >
                              {reviewStatus === 'sent' ? <><Eye size={13} />View</> : reviewStatus === 'draft' ? <><FileText size={13} />Edit</> : <><Stethoscope size={13} />Review</>}
                            </button>

                            {matchingReport ? (
                              <button onClick={() => handleViewFHIRReport(matchingReport.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors" title="View Report (PDF)">
                                <Download size={15} />
                              </button>
                            ) : (
                              <button onClick={() => handleGenerateFHIRReport(detection)} disabled={actionLoading === detection.id} className="p-1.5 rounded-lg text-gray-300 hover:text-teal-600 hover:bg-teal-50 transition-colors disabled:opacity-50" title="Generate Report">
                                {actionLoading === detection.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText size={15} />}
                              </button>
                            )}

                            <button onClick={() => handleDeleteDetection(detection.id)} className="p-1.5 rounded-lg text-gray-200 hover:text-red-600 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100" title="Delete">
                              <X size={15} />
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
          )
        })()}
      </div>
      {/* FHIR modal removed — PDF opens in new window via handleViewFHIRReport */}

      {/* Review & Draft Modal */}
      {showReviewModal && selectedDetectionForReview && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl"
          >
            {/* Modal header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10 rounded-t-xl">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Clinical Report</h2>
                <p className="text-xs text-gray-500">
                  {selectedDetectionForReview.patient_name || 'Patient'} &middot; {selectedDetectionForReview.detection_id}
                </p>
              </div>
              <button 
                onClick={() => { setShowReviewModal(false); setReviewMessage(null) }}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                disabled={isSavingReview}
              >
                <X size={18} className="text-gray-400" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {reviewMessage && (
                <div className={`p-3 rounded-lg text-sm ${reviewMessage.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-red-50 text-red-700 border border-red-100'}`}>
                  {reviewMessage.text}
                </div>
              )}
              
              {/* AI Result + Accept/Override */}
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">AI Prediction</p>
                    <p className="text-base font-bold text-gray-900 mt-0.5">
                      {selectedDetectionForReview.predicted_class_display || selectedDetectionForReview.predicted_class}
                      <span className="text-sm font-normal text-gray-500 ml-2">
                        {selectedDetectionForReview.confidence_score ? `${(selectedDetectionForReview.confidence_score * 100).toFixed(1)}%` : ''}
                      </span>
                    </p>
                  </div>
                  <div className="flex border border-gray-200 rounded-lg overflow-hidden">
                    <button
                      onClick={() => setReviewForm(prev => ({ ...prev, ai_accepted: true, doctor_override_class: '' }))}
                      className={`px-4 py-2 text-xs font-semibold transition-colors ${reviewForm.ai_accepted ? 'bg-emerald-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
                    >
                      Accept AI
                    </button>
                    <button
                      onClick={() => setReviewForm(prev => ({ ...prev, ai_accepted: false }))}
                      className={`px-4 py-2 text-xs font-semibold border-l transition-colors ${!reviewForm.ai_accepted ? 'bg-red-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
                    >
                      Override
                    </button>
                  </div>
                </div>

                {!reviewForm.ai_accepted && (
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <label className="text-xs font-semibold text-gray-700 block mb-1.5">Your Diagnosis</label>
                    <select
                      value={reviewForm.doctor_override_class}
                      onChange={e => setReviewForm(prev => ({ ...prev, doctor_override_class: e.target.value }))}
                      className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-200"
                    >
                      <option value="">-- Select diagnosis --</option>
                      <option value="alzheimers">Alzheimer&apos;s Disease (AD)</option>
                      <option value="dementia">Dementia Detected</option>
                      <option value="cn">Control / Normal (CN)</option>
                      <option value="pd">Parkinson&apos;s Disease (PD)</option>
                      <option value="ftd">Frontotemporal Dementia (FTD)</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Clinical Conclusion */}
              <div>
                <label className="text-sm font-semibold text-gray-700 block mb-1.5">
                  Clinical Conclusion <span className="text-red-500">*</span>
                </label>
                <p className="text-xs text-gray-400 mb-2">Your professional assessment. This is included in the FHIR report.</p>
                <Textarea 
                  value={reviewForm.doctor_conclusion}
                  onChange={e => setReviewForm(prev => ({ ...prev, doctor_conclusion: e.target.value }))}
                  className="min-h-[100px] text-sm"
                  placeholder="Enter your clinical conclusion..."
                />
              </div>

              {/* Internal Notes */}
              <div>
                <label className="text-sm font-semibold text-gray-700 block mb-1.5">
                  Internal Notes <span className="text-xs font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded ml-1">Private</span>
                </label>
                <Textarea 
                  value={reviewForm.doctor_notes}
                  onChange={e => setReviewForm(prev => ({ ...prev, doctor_notes: e.target.value }))}
                  className="min-h-[70px] text-sm"
                  placeholder="Notes for your records only..."
                />
              </div>

              {/* Patient Summary */}
              <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-4">
                <label className="text-sm font-semibold text-blue-800 block mb-1">
                  Patient-Facing Summary <span className="text-red-500">*</span>
                </label>
                <p className="text-xs text-blue-600 mb-2">This message is what the patient sees. Use simple, clear language.</p>
                <Textarea 
                  value={reviewForm.patient_summary}
                  onChange={e => setReviewForm(prev => ({ ...prev, patient_summary: e.target.value }))}
                  className="min-h-[100px] text-sm border-blue-200 focus-visible:ring-blue-300 bg-white"
                  placeholder="Dear patient, your MRI results indicate..."
                />
              </div>

              {/* Info note about FHIR */}
              <p className="text-xs text-gray-400 text-center">
                Sending to patient will automatically generate/update the FHIR diagnostic report with your comments.
              </p>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between rounded-b-xl">
              <button
                onClick={() => { setShowReviewModal(false); setReviewMessage(null) }}
                className="text-sm text-gray-500 hover:text-gray-700 font-medium px-3 py-2"
                disabled={isSavingReview}
              >
                Cancel
              </button>
              <div className="flex gap-3">
                <Button 
                  variant="outline"
                  onClick={() => handleSaveReview(false)}
                  disabled={isSavingReview}
                >
                  <Save size={16} className="mr-2" />
                  Save Draft
                </Button>
                <Button 
                  onClick={() => handleSaveReview(true)}
                  disabled={isSavingReview}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isSavingReview ? <Loader2 size={16} className="animate-spin mr-2" /> : <Send size={16} className="mr-2" />}
                  {reviewForm.is_sent_to_patient ? 'Update & Send' : 'Send to Patient'}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}

    </div>
  )
}
