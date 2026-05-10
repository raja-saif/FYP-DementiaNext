'use client'

import React, { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Navigation from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Upload, Brain, AlertCircle, CheckCircle2, FileText, Loader2, Download, Eye, Clock, Search, Send, Save, MessageSquare, Trash2, X, ArrowLeft } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import { normalizeDetectionResponse } from '@/lib/normalizeDetectionResponse'

type ModelType = 'binary' | 'subtype'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'

// Class labels for display
const CLASS_LABELS: Record<string, string> = {
  'alzheimers': "Alzheimer's Disease (AD)",
  'dementia': 'Dementia Detected',
  'cn': 'Control/Normal (CN)',
  'pd': "Parkinson's Disease (PD)",
  'ftd': 'Frontotemporal Dementia (FTD)',
}

/** API uses 0–1; production sometimes returns null if inference failed partway. */
function toConfidencePercent(score: unknown): number | null {
  if (score == null || score === '') return null
  const n = typeof score === 'number' ? score : Number.parseFloat(String(score))
  if (!Number.isFinite(n)) return null
  const pct = n > 1 ? Math.min(n, 100) : n * 100
  return Math.min(100, Math.max(0, pct))
}

function DetectionPageContent() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlDetectionId = searchParams.get('detection_id')

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedModel, setSelectedModel] = useState<ModelType>('binary')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasResults, setHasResults] = useState(false)
  const [detectionResult, setDetectionResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [folderFileCount, setFolderFileCount] = useState<number>(0)
  const [isZipping, setIsZipping] = useState(false)
  const [pipelineStep, setPipelineStep] = useState<number>(-1)
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<string>('')
  const [patientSearch, setPatientSearch] = useState('')
  const [showPatientDropdown, setShowPatientDropdown] = useState(false)
  const patientDropdownRef = useRef<HTMLDivElement>(null)
  const [previousScans, setPreviousScans] = useState<any[]>([])
  const [loadingScans, setLoadingScans] = useState(false)
  const [scanSearch, setScanSearch] = useState('')

  // Doctor Review states
  const [review, setReview] = useState({
    ai_accepted: true,
    doctor_conclusion: '',
    doctor_notes: '',
    patient_summary: '',
    is_sent_to_patient: false
  })
  const [isSavingReview, setIsSavingReview] = useState(false)
  const [reviewMessage, setReviewMessage] = useState<{text: string, type: 'success'|'error'} | null>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (patientDropdownRef.current && !patientDropdownRef.current.contains(event.target as Node)) {
        setShowPatientDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch patients for doctor
  useEffect(() => {
    if (user?.role === 'doctor') {
      const fetchPatients = async () => {
        try {
          const token = localStorage.getItem('authToken')
          const response = await fetch(`${API_BASE_URL}/api/auth/patients/`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (response.ok) {
            const data = await response.json()
            setPatients(data)
          }
        } catch (error) {
          console.error('Error fetching patients:', error)
        }
      }
      fetchPatients()
    }
  }, [user])

  const fetchPreviousScans = useCallback(async () => {
    if (user?.role === 'doctor') {
      setLoadingScans(true)
      try {
        const token = localStorage.getItem('authToken')
        const response = await fetch(`${API_BASE_URL}/api/detection/detections/my_uploads/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
          const data = await response.json()
          setPreviousScans(Array.isArray(data) ? data : data.results || [])
        }
      } catch (error) {
        console.error('Error fetching previous scans:', error)
      } finally {
        setLoadingScans(false)
      }
    }
  }, [user])

  // Fetch doctor's previous scans
  useEffect(() => {
    fetchPreviousScans()
  }, [fetchPreviousScans])

  const PIPELINE_STEPS = [
    { label: 'Uploading file', duration: 4 },
    { label: 'Phase 1 · DICOM → NIfTI', duration: 30 },
    { label: 'Phase 2 · Skull stripping', duration: 60 },
    { label: 'Phase 2 · Bias correction', duration: 40 },
    { label: 'Phase 2 · MNI registration', duration: 50 },
    { label: 'Phase 2 · Intensity norm', duration: 20 },
    { label: 'Phase 2 · Resampling 128³', duration: 20 },
    { label: 'AI inference (ResNet-34)', duration: 15 },
  ]

  // Auth check - redirect if not logged in or not a doctor
  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login')
      } else if (user.role !== 'doctor') {
        router.push('/patient-dashboard')
      }
    }
  }, [user, authLoading, router])


  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const fileName = file.name.toLowerCase()
      const validExtensions = ['.nii', '.nii.gz', '.dcm', '.zip']

      const isValidExt = validExtensions.some(ext => fileName.endsWith(ext))
      if (!isValidExt) {
        setError('Please upload a NIfTI file (.nii, .nii.gz), DICOM (.dcm), or a ZIP of MRI files')
        return
      }

      // Special validation for ZIP files to ensure they contain relevant MRI data
      if (fileName.endsWith('.zip')) {
        setIsZipping(true)
        setError(null)
        try {
          const { default: JSZip } = await import('jszip')
          const zip = new JSZip()
          const zipContent = await zip.loadAsync(file)

          const hasValidFiles = Object.values(zipContent.files).some(f => {
            if (f.dir) return false
            const n = f.name.toLowerCase()
            return n.endsWith('.nii') || n.endsWith('.nii.gz') || n.endsWith('.dcm') || (!n.split('/').pop()?.includes('.') && n !== '')
          })

          if (!hasValidFiles) {
            setError('Invalid ZIP content. The file must contain at least one NIfTI (.nii, .nii.gz) or DICOM (.dcm) file.')
            setSelectedFile(null)
            setIsZipping(false)
            return
          }
        } catch (err) {
          setError('Failed to validate ZIP file contents.')
          setSelectedFile(null)
          setIsZipping(false)
          return
        }
        setIsZipping(false)
      }

      setSelectedFile(file)
      setFolderFileCount(0)
      setError(null)
    }
  }

  const handleFolderSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const dcmFiles = Array.from(files).filter(f =>
      f.name.toLowerCase().endsWith('.dcm') || !f.name.includes('.')
    )

    if (dcmFiles.length === 0) {
      setError('No DICOM (.dcm) files found in the selected folder')
      return
    }

    setIsZipping(true)
    setError(null)

    try {
      const { default: JSZip } = await import('jszip')
      const zip = new JSZip()

      for (const f of dcmFiles) {
        const buf = await f.arrayBuffer()
        const relativePath = (f as any).webkitRelativePath || f.name
        zip.file(relativePath, buf)
      }

      const blob = await zip.generateAsync({ type: 'blob' })
      const zipFile = new File([blob], 'dicom_folder.zip', { type: 'application/zip' })

      setSelectedFile(zipFile)
      setFolderFileCount(dcmFiles.length)
    } catch (err) {
      setError('Failed to package DICOM folder. Please try uploading a ZIP file instead.')
      console.error('Zip error:', err)
    } finally {
      setIsZipping(false)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an image file first!')
      return
    }

    if (user?.role === 'doctor' && !selectedPatientId) {
      setError('Please select a patient to assign this detection to.')
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setPipelineStep(0)

    // Advance the timeline indicator as processing progresses
    let stepIdx = 0
    const isNifti = selectedFile?.name.toLowerCase().match(/\.(nii|nii\.gz|dcm|zip)$/)
    const stepsToRun = isNifti ? PIPELINE_STEPS : [PIPELINE_STEPS[0], PIPELINE_STEPS[7]]
    const advanceStep = () => {
      stepIdx++
      if (stepIdx < stepsToRun.length - 1) {
        setPipelineStep(stepIdx)
        setTimeout(advanceStep, stepsToRun[stepIdx].duration * 1000)
      }
    }
    setTimeout(advanceStep, stepsToRun[0].duration * 1000)

    try {
      const token = localStorage.getItem('authToken')
      if (!token) {
        setError('Authentication required. Please log in.')
        setIsAnalyzing(false)
        return
      }

      const formData = new FormData()
      formData.append('uploaded_file', selectedFile)
      formData.append('model_type', selectedModel)
      if (user?.role === 'doctor') formData.append('patient_id', selectedPatientId)

      const response = await fetch(
        `${API_BASE_URL}/api/detection/detections/upload_and_detect/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        }
      )

      if (!response.ok) {
        const contentType = response.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(errorData.error || errorData.detail || 'Detection failed')
        }
        throw new Error(`Server error (${response.status}). Please check that the backend is running.`)
      }

      const result = normalizeDetectionResponse(await response.json())

      const modelTypeKey: ModelType =
        result.model_type === 'subtype'
          ? 'subtype'
          : result.model_type === 'binary'
            ? 'binary'
            : selectedModel
      const modelDisplayName =
        modelTypeKey === 'subtype'
          ? 'Subtype Classifier (4-class ResNet-34)'
          : 'Binary Dementia Detector (ResNet-34)'

      setDetectionResult({
        modelType: modelDisplayName,
        modelTypeKey,
        predicted_class: result.predicted_class,
        classification:
          (result.predicted_class_display as string) ||
          CLASS_LABELS[String(result.predicted_class)] ||
          result.predicted_class,
        confidencePct: toConfidencePercent(result.confidence_score),
        processingTime: result.processing_time != null ? Number(result.processing_time).toFixed(2) : null,
        probabilities: result.prediction_probability,
        analysis: result.analysis_details,
        timestamp: result.created_at ? new Date(String(result.created_at)).toLocaleString() : '—',
        detectionId: result.id,
        modelVersion: result.model_version,
      })

      setHasResults(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during detection')
      console.error('Detection error:', err)
    } finally {
      setIsAnalyzing(false)
      setPipelineStep(-1)
    }
  }

  const fetchSingleDetection = useCallback(async (id: string) => {
    setIsAnalyzing(true)
    setError(null)
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_BASE_URL}/api/detection/detections/${id}/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const result = normalizeDetectionResponse(await response.json())
        const modelTypeKey: ModelType =
          result.model_type === 'subtype'
            ? 'subtype'
            : 'binary'
        const modelDisplayName =
          modelTypeKey === 'subtype'
            ? 'Subtype Classifier (4-class ResNet-34)'
            : 'Binary Dementia Detector (ResNet-34)'

        setDetectionResult({
          modelType: modelDisplayName,
          modelTypeKey,
          classification:
            (result.predicted_class_display as string) ||
            CLASS_LABELS[String(result.predicted_class)] ||
            result.predicted_class,
          confidencePct: toConfidencePercent(result.confidence_score),
          processingTime: result.processing_time != null ? Number(result.processing_time).toFixed(2) : null,
          probabilities: result.prediction_probability,
          analysis: result.analysis_details,
          timestamp: result.created_at ? new Date(String(result.created_at)).toLocaleString() : '—',
          detectionId: result.id,
          modelVersion: result.model_version,
          predicted_class: result.predicted_class,
        })
        setHasResults(true)
        if (result.patient != null) setSelectedPatientId(String(result.patient))
      } else {
        throw new Error('Failed to fetch detection record')
      }
    } catch (err) {
      console.error('Error fetching single detection:', err)
      setError('Could not load detection result.')
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  // Check for deep-linked detection_id
  useEffect(() => {
    if (urlDetectionId && user && !authLoading) {
      fetchSingleDetection(urlDetectionId)
    }
  }, [urlDetectionId, user, authLoading, fetchSingleDetection])

  const handleDownloadReport = () => {
    if (!detectionResult) return

    // Format probabilities with proper labels
    const formatProbabilities = () => {
      if (!detectionResult.probabilities) return 'N/A'
      return Object.entries(detectionResult.probabilities)
        .map(([cls, prob]: [string, any]) => {
          const pct = toConfidencePercent(prob)
          return `${CLASS_LABELS[cls] || cls}: ${pct != null ? `${pct.toFixed(2)}%` : 'N/A'}`
        })
        .join('\n')
    }

    // Generate clinical recommendations based on predicted class
    const getRecommendations = () => {
      const cls = detectionResult.predicted_class
      if (cls === 'alzheimers') {
        return `• Immediate consultation with a neurologist is recommended
• Consider additional diagnostic tests (PET scan, CSF analysis)
• Monitor cognitive function regularly
• Discuss treatment options with healthcare provider`
      } else if (cls === 'pd') {
        return `• Referral to movement disorder specialist recommended
• Consider dopamine transporter imaging (DaTscan)
• Evaluate motor and non-motor symptoms
• Discuss medication and therapy options`
      } else if (cls === 'ftd') {
        return `• Neuropsychological evaluation recommended
• Consider genetic counseling if family history present
• Speech and language therapy evaluation
• Behavioral management strategies may be needed`
      } else {
        return `• Results suggest normal cognitive function
• Continue regular health check-ups
• Maintain cognitive activities for brain health`
      }
    }

    const reportContent = `
DEMENTIA DETECTION REPORT
=========================

Report Generated: ${detectionResult.timestamp}
Detection ID: ${detectionResult.detectionId}

MODEL INFORMATION
-----------------
Model: ${detectionResult.modelType}
Model Version: ${detectionResult.modelVersion}
Processing Time: ${detectionResult.processingTime}s

CLASSIFICATION RESULTS
----------------------
Predicted Class: ${detectionResult.classification}
Confidence Score: ${detectionResult.confidencePct != null ? `${detectionResult.confidencePct.toFixed(1)}%` : 'N/A'}

CLASS PROBABILITIES
-------------------
${formatProbabilities()}

PATIENT INFORMATION
-------------------
Patient Name: ${patients.find(p => p.id.toString() === selectedPatientId)?.name || 'Unknown'}
Patient Email: ${patients.find(p => p.id.toString() === selectedPatientId)?.email || 'Unknown'}

CLINICAL RECOMMENDATIONS
------------------------
${getRecommendations()}

Generated by DementiaNext AI Detection System
    `.trim()

    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(reportContent))
    element.setAttribute('download', `dementia_report_${detectionResult.detectionId}.txt`)
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const resetForm = () => {
    setSelectedFile(null)
    setSelectedModel('binary')
    setHasResults(false)
    setDetectionResult(null)
    setReview({
      ai_accepted: true,
      doctor_conclusion: '',
      doctor_notes: '',
      patient_summary: '',
      is_sent_to_patient: false
    })
    setReviewMessage(null)
    setError(null)
    setSelectedPatientId('')
    setPatientSearch('')
    fetchPreviousScans()
  }

  const handleRerunDetection = async (scanId: number) => {
    setIsAnalyzing(true)
    setError(null)

    try {
      const token = localStorage.getItem('authToken')
      if (!token) {
        setError('Authentication required. Please log in.')
        setIsAnalyzing(false)
        return
      }

      const response = await fetch(
        `${API_BASE_URL}/api/detection/detections/${scanId}/rerun/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model_type: selectedModel,
          }),
        }
      )

      if (!response.ok) {
        const contentType = response.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(errorData.error || errorData.detail || 'Rerun failed')
        }
        throw new Error(`Server error (${response.status}).`)
      }

      const result = normalizeDetectionResponse(await response.json())

      const modelTypeKey: ModelType =
        result.model_type === 'subtype'
          ? 'subtype'
          : result.model_type === 'binary'
            ? 'binary'
            : selectedModel
      const modelDisplayName =
        modelTypeKey === 'subtype'
          ? 'Subtype Classifier (4-class ResNet-34)'
          : 'Binary Dementia Detector (ResNet-34)'

      setDetectionResult({
        modelType: modelDisplayName,
        modelTypeKey,
        predicted_class: result.predicted_class,
        classification:
          (result.predicted_class_display as string) ||
          CLASS_LABELS[String(result.predicted_class)] ||
          result.predicted_class,
        confidencePct: toConfidencePercent(result.confidence_score),
        processingTime: result.processing_time != null ? Number(result.processing_time).toFixed(2) : null,
        probabilities: result.prediction_probability,
        analysis: result.analysis_details,
        timestamp: result.created_at ? new Date(String(result.created_at)).toLocaleString() : '—',
        detectionId: result.id,
        modelVersion: result.model_version,
      })

      setHasResults(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      console.error('Rerun error:', err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const filteredScans = previousScans.filter(scan => {
    if (!scanSearch) return true
    const q = scanSearch.toLowerCase()
    return (
      scan.patient_name?.toLowerCase().includes(q) ||
      (scan.predicted_class_display || CLASS_LABELS[scan.predicted_class] || scan.predicted_class || '').toLowerCase().includes(q)
    )
  })

  const handleDeleteScan = async (scanId: number, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering the re-run click
    if (!confirm('Are you sure you want to delete this scan? This action cannot be undone.')) return
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_BASE_URL}/api/detection/detections/${scanId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (response.ok || response.status === 204) {
        setPreviousScans(prev => prev.filter(s => s.id !== scanId))
      } else {
        const errorData = await response.json().catch(() => ({}))
        alert(errorData.error || 'Failed to delete scan.')
      }
    } catch (err) {
      console.error('Delete scan error:', err)
      alert('Failed to delete scan.')
    }
  }

  // Pre-fill doctor review template when result becomes available
  useEffect(() => {
    if (hasResults && detectionResult) {
      const pred = detectionResult.classification
      setReview({
        ai_accepted: true,
        doctor_conclusion: `AI analysis suggests ${pred}. `,
        doctor_notes: '',
        patient_summary: `Your MRI scan has been analyzed. Initial findings indicate ${pred}. We will discuss these results and next steps during our upcoming consultation.`,
        is_sent_to_patient: false
      })
      setReviewMessage(null)
    }
  }, [hasResults, detectionResult])

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-teal-50">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    )
  }

  // Don't render if not authenticated
  if (!user) {
    return null
  }

  const handleSaveReview = async (sendToPatient: boolean) => {
    if (!detectionResult?.detectionId) return
    setIsSavingReview(true)
    setReviewMessage(null)
    try {
      const token = localStorage.getItem('authToken')
      const bodyPayload = {
        ...review,
        is_sent_to_patient: sendToPatient || review.is_sent_to_patient
      }
      const response = await fetch(`${API_BASE_URL}/api/detection/detections/${detectionResult.detectionId}/review/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bodyPayload)
      })

      if (response.ok) {
        setReview(prev => ({ ...prev, ...bodyPayload }))
        setReviewMessage({
          text: bodyPayload.is_sent_to_patient ? 'Report successfully sent to patient.' : 'Draft saved successfully.',
          type: 'success'
        })
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-teal-50">
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => router.push(user?.role === 'doctor' ? '/doctor-dashboard' : '/patient-dashboard')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 mb-4 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Dashboard
        </button>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-r from-blue-500 to-teal-500 flex items-center justify-center">
              <Brain className="text-white" size={40} />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
            <span className="bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
              Dementia Detection
            </span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Upload an MRI image for AI-powered dementia detection
          </p>
        </motion.div>

        {/* Error Alert */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3"
          >
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Error</h3>
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          </motion.div>
        )}

        {!hasResults ? (
          <div className="flex gap-6">
            {/* Previous Scans Sidebar */}
            {user?.role === 'doctor' && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="w-80 flex-shrink-0 hidden xl:block"
              >
                <Card className="border-2 border-purple-200 sticky top-24">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Clock size={18} />
                      Previous Scans
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Select a scan to re-run with a different model
                    </CardDescription>
                    <div className="relative mt-2">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                      <Input
                        placeholder="Search scans..."
                        value={scanSearch}
                        onChange={(e) => setScanSearch(e.target.value)}
                        className="pl-8 h-8 text-xs"
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="max-h-[60vh] overflow-y-auto space-y-2 pt-0">
                    {loadingScans ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="animate-spin text-purple-500" size={24} />
                      </div>
                    ) : filteredScans.length === 0 ? (
                      <p className="text-xs text-gray-500 text-center py-6">
                        {previousScans.length === 0 ? 'No previous scans yet.' : 'No matching scans.'}
                      </p>
                    ) : (
                      filteredScans.map(scan => (
                        <div
                          key={scan.id}
                          className="p-3 rounded-lg border border-gray-200 hover:border-purple-400 hover:bg-purple-50 cursor-pointer transition-all group relative"
                          onClick={() => handleRerunDetection(scan.id)}
                        >
                          <button
                            onClick={(e) => handleDeleteScan(scan.id, e)}
                            className="absolute top-1.5 right-1.5 p-1 rounded-full text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100 z-10"
                            title="Delete scan"
                          >
                            <X size={14} />
                          </button>
                          <div className="text-xs font-medium text-gray-900 mb-0.5 truncate pr-5">
                            {scan.patient_name || 'Unknown Patient'}
                          </div>
                          <div className="text-[11px] text-gray-500 truncate">
                            {scan.predicted_class_display || CLASS_LABELS[scan.predicted_class] || scan.predicted_class || 'Pending'}
                            {scan.confidence_score ? ` — ${(scan.confidence_score * 100).toFixed(0)}%` : ''}
                          </div>
                          <div className="flex items-center justify-between mt-1.5">
                            <span className="text-[10px] text-gray-400">
                              {new Date(scan.created_at).toLocaleString()}
                            </span>
                            <span className="text-[10px] font-medium text-purple-600 opacity-0 group-hover:opacity-100 transition-opacity">
                              Re-run →
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}

            <div className="flex-1 grid lg:grid-cols-3 gap-8">
            {/* Upload Section */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="lg:col-span-2"
            >
              <Card className="border-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Upload size={24} />
                    Upload MRI Image
                  </CardTitle>
                  <CardDescription>
                    Upload brain MRI slice or DICOM folder for analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid md:grid-cols-2 gap-4">
                    {/* Single file upload */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                      <label className="cursor-pointer block">
                        <Upload className="mx-auto mb-3 text-gray-400" size={36} />
                        <p className="text-base font-medium text-gray-700 mb-1">
                          Upload Single File
                        </p>
                        <p className="text-xs text-gray-500">
                          NIfTI (.nii, .nii.gz), DICOM (.dcm), ZIP
                        </p>
                        <Input
                          type="file"
                          onChange={handleFileSelect}
                          accept=".nii,.nii.gz,.dcm,.zip"
                          className="hidden"
                        />
                      </label>
                    </div>

                    {/* DICOM folder upload */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-teal-400 transition-colors">
                      <label className="cursor-pointer block">
                        <FileText className="mx-auto mb-3 text-gray-400" size={36} />
                        <p className="text-base font-medium text-gray-700 mb-1">
                          Upload DICOM Folder
                        </p>
                        <p className="text-xs text-gray-500">
                          Select a folder with .dcm slices
                        </p>
                        <input
                          type="file"
                          onChange={handleFolderSelect}
                          className="hidden"
                          {...({ webkitdirectory: 'true', directory: 'true', multiple: true } as any)}
                        />
                      </label>
                    </div>
                  </div>

                  {isZipping && (
                    <div className="p-4 bg-yellow-50 rounded-lg flex items-center gap-3">
                      <Loader2 className="animate-spin text-yellow-600" size={20} />
                      <p className="text-sm text-yellow-700">Packaging DICOM files...</p>
                    </div>
                  )}

                  {selectedFile && !isZipping && (
                    <div className="p-4 bg-blue-50 rounded-lg flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-sm text-gray-600">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                          {folderFileCount > 0 && ` · ${folderFileCount} DICOM slices`}
                        </p>
                      </div>
                      <CheckCircle2 className="text-green-600" size={24} />
                    </div>
                  )}

                  {/* Patient Selection for Doctors */}
                  {user?.role === 'doctor' && (
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-100" ref={patientDropdownRef}>
                      <label className="block text-sm font-semibold text-gray-800 mb-2">
                        Assign to Patient <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <Input
                          type="text"
                          placeholder="Search patient by name or email..."
                          value={patientSearch}
                          onChange={(e) => {
                            setPatientSearch(e.target.value)
                            setShowPatientDropdown(true)
                            setSelectedPatientId('') // Clear selection if user types
                          }}
                          onFocus={() => setShowPatientDropdown(true)}
                          className={`w-full bg-white ${selectedPatientId ? 'ring-2 ring-blue-500 border-blue-500' : ''}`}
                        />
                        {showPatientDropdown && (
                          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                            {patients
                              .filter(p => p.name.toLowerCase().includes(patientSearch.toLowerCase()) || p.email.toLowerCase().includes(patientSearch.toLowerCase()))
                              .map(p => (
                                <div
                                  key={p.id}
                                  className="px-4 py-2 hover:bg-blue-50 cursor-pointer text-sm"
                                  onClick={() => {
                                    setSelectedPatientId(p.id.toString())
                                    setPatientSearch(`${p.name} (${p.email})`)
                                    setShowPatientDropdown(false)
                                  }}
                                >
                                  <div className="font-medium text-gray-900">{p.name}</div>
                                  <div className="text-gray-500 text-xs">{p.email}</div>
                                </div>
                              ))}
                            {patients.filter(p => p.name.toLowerCase().includes(patientSearch.toLowerCase()) || p.email.toLowerCase().includes(patientSearch.toLowerCase())).length === 0 && (
                              <div className="px-4 py-3 text-sm text-gray-500 text-center">No patients found</div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Model Selection */}
                  <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-5 border border-purple-200">
                    <label className="block text-sm font-semibold text-gray-800 mb-3">
                      Select Detection Model
                    </label>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div
                        onClick={() => setSelectedModel('binary')}
                        className={`cursor-pointer rounded-lg p-4 border-2 transition-all ${selectedModel === 'binary'
                          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                          : 'border-gray-200 bg-white hover:border-blue-300'
                          }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${selectedModel === 'binary' ? 'border-blue-500' : 'border-gray-300'
                            }`}>
                            {selectedModel === 'binary' && (
                              <div className="w-2 h-2 rounded-full bg-blue-500" />
                            )}
                          </div>
                          <span className="font-semibold text-gray-900">Binary Detector</span>
                        </div>
                        <p className="text-xs text-gray-600 ml-6">
                          AD vs Control (2 classes)
                        </p>
                        <div className="mt-2 ml-6 text-xs text-gray-500">
                          AUC: 0.9707 • Acc: 91.84%
                        </div>
                      </div>

                      <div
                        onClick={() => setSelectedModel('subtype')}
                        className={`cursor-pointer rounded-lg p-4 border-2 transition-all ${selectedModel === 'subtype'
                          ? 'border-teal-500 bg-teal-50 ring-2 ring-teal-200'
                          : 'border-gray-200 bg-white hover:border-teal-300'
                          }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${selectedModel === 'subtype' ? 'border-teal-500' : 'border-gray-300'
                            }`}>
                            {selectedModel === 'subtype' && (
                              <div className="w-2 h-2 rounded-full bg-teal-500" />
                            )}
                          </div>
                          <span className="font-semibold text-gray-900">Subtype Classifier</span>
                          <Badge className="text-xs bg-teal-100 text-teal-700 border-teal-300">New</Badge>
                        </div>
                        <p className="text-xs text-gray-600 ml-6">
                          AD, PD, FTD, CN (4 classes)
                        </p>
                        <div className="mt-2 ml-6 text-xs text-gray-500">
                          AUC: 0.9763 • Acc: 88.62%
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Pipeline progress timeline */}
                  {isAnalyzing && (
                    <div className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-5 space-y-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Loader2 className="animate-spin text-blue-600" size={18} />
                        <p className="font-semibold text-blue-800 text-sm">
                          Processing MRI — please wait
                        </p>
                      </div>

                      <div className="space-y-2">
                        {PIPELINE_STEPS.map((step, idx) => {
                          const isDone = idx < pipelineStep
                          const isActive = idx === pipelineStep
                          const isPending = idx > pipelineStep
                          return (
                            <div key={idx} className="flex items-center gap-3">
                              {/* Circle indicator */}
                              <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold transition-all duration-500
                                ${isDone ? 'bg-green-500 text-white'
                                  : isActive ? 'bg-blue-600 text-white ring-4 ring-blue-200'
                                    : 'bg-gray-200 text-gray-400'}`}>
                                {isDone ? '✓' : idx + 1}
                              </div>

                              {/* Label + bar */}
                              <div className="flex-1">
                                <p className={`text-xs font-medium mb-1 transition-colors duration-300
                                  ${isDone ? 'text-green-700' : isActive ? 'text-blue-700' : 'text-gray-400'}`}>
                                  {step.label}
                                </p>
                                <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                                  <div className={`h-full rounded-full transition-all duration-1000
                                    ${isDone ? 'w-full bg-green-400'
                                      : isActive ? 'bg-blue-500 animate-pulse'
                                        : 'w-0 bg-gray-300'}`}
                                    style={isActive ? { width: '60%' } : undefined}
                                  />
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>

                      <p className="text-xs text-gray-500 text-center pt-1">
                        This may take 2–6 minutes for full DICOM pipeline processing
                      </p>
                    </div>
                  )}

                  <Button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !selectedFile || isZipping}
                    className="w-full py-6 text-lg bg-blue-600 hover:bg-blue-700"
                    size="lg"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="mr-2 animate-spin" size={20} />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Brain className="mr-2" size={20} />
                        Analyze MRI Image
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>

            {/* Info Section */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="space-y-6"
            >
              <Card className={`border-2 ${selectedModel === 'subtype' ? 'border-teal-200 bg-teal-50' : 'border-blue-200 bg-blue-50'}`}>
                <CardHeader>
                  <CardTitle className="text-lg">
                    {selectedModel === 'subtype' ? 'Subtype Classifier' : 'Binary Detector'}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <p className="font-semibold text-gray-900">ResNet-34</p>
                    {selectedModel === 'subtype' ? (
                      <>
                        <p className="text-gray-700">AUC: 0.9763 (macro)</p>
                        <p className="text-gray-700">Accuracy: 88.62%</p>
                        <p className="text-gray-700">Classes: AD, PD, FTD, CN</p>
                      </>
                    ) : (
                      <>
                        <p className="text-gray-700">AUC: 0.9707</p>
                        <p className="text-gray-700">Accuracy: 91.84%</p>
                        <p className="text-gray-700">Sensitivity: 88.46%</p>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-2 border-green-200 bg-green-50">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText size={20} />
                    Output
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-gray-700">
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      {selectedModel === 'subtype'
                        ? 'Classification (AD, PD, FTD, CN)'
                        : 'Classification (AD vs CN)'}
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      Confidence scores
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      Downloadable report
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          </div>
          </div>
        ) : (
          /* Results Section */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto space-y-6"
          >
            {!String(detectionResult.predicted_class || '').trim() &&
              detectionResult.confidencePct == null && (
              <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                <AlertCircle className="h-5 w-5 shrink-0 text-amber-600" />
                <div>
                  <p className="font-medium">No diagnosis data in API response</p>
                  <p className="mt-1 text-amber-900/90">
                    Open DevTools → Network, inspect the <code className="text-xs bg-amber-100/80 px-1 rounded">upload_and_detect</code> or{' '}
                    <code className="text-xs bg-amber-100/80 px-1 rounded">detections/&lt;id&gt;/</code> response body. You should see{' '}
                    <code className="text-xs bg-amber-100/80 px-1 rounded">predicted_class</code> and{' '}
                    <code className="text-xs bg-amber-100/80 px-1 rounded">confidence_score</code>. If they are null on the server, check deployed Django logs and that inference completes after preprocessing.
                  </p>
                </div>
              </div>
            )}
            {/* Result Header */}
            <Card className="border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-teal-600 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 size={24} className="text-white" />
                    <h2 className="text-lg font-semibold text-white">Analysis Complete</h2>
                  </div>
                  <Badge className="bg-white/20 text-white border-0 text-xs font-mono">
                    {detectionResult.detectionId}
                  </Badge>
                </div>
              </div>
              <CardContent className="p-6">
                <div className="flex flex-col md:flex-row md:items-center gap-6">
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Diagnosis</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {detectionResult.classification || '—'}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Confidence</p>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-teal-500 rounded-full"
                          style={{ width: `${detectionResult.confidencePct ?? 0}%` }}
                        />
                      </div>
                      <span className="text-xl font-bold text-blue-600 tabular-nums">
                        {detectionResult.confidencePct != null ? `${detectionResult.confidencePct.toFixed(1)}%` : '—'}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-6 text-sm text-gray-600">
                    <div>
                      <p className="text-xs text-gray-400">Time</p>
                      <p className="font-medium">{detectionResult.processingTime != null ? `${detectionResult.processingTime}s` : '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Model</p>
                      <p className="font-medium capitalize">{detectionResult.modelType || 'Binary'}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Probabilities */}
            {detectionResult.probabilities && (
              <Card className="border border-gray-200 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Classification Probabilities</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {Object.entries(detectionResult.probabilities)
                    .sort(([,a]: [string, any], [,b]: [string, any]) => b - a)
                    .map(([cls, prob]: [string, any]) => {
                      const isHighest = cls === detectionResult.predicted_class
                      const p = toConfidencePercent(prob) ?? 0
                      return (
                        <div key={cls} className="flex items-center gap-4">
                          <p className={`w-48 text-sm truncate ${isHighest ? 'font-semibold text-gray-900' : 'text-gray-600'}`}>
                            {CLASS_LABELS[cls] || cls}
                          </p>
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${isHighest ? 'bg-blue-600' : 'bg-gray-300'}`}
                              style={{ width: `${p}%` }}
                            />
                          </div>
                          <span className={`text-sm tabular-nums w-16 text-right ${isHighest ? 'font-semibold text-gray-900' : 'text-gray-500'}`}>
                            {Number.isFinite(p) ? `${p.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                      )
                    })}
                </CardContent>
              </Card>
            )}

            {/* Doctor Review */}
            {user?.role === 'doctor' && (
              <Card className="border border-gray-200 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <MessageSquare size={18} className="text-blue-600" />
                    Clinical Review
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {reviewMessage && (
                    <div className={`p-3 rounded-lg text-sm font-medium ${reviewMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                      {reviewMessage.text}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                    <span className="text-sm text-gray-700">
                      AI Diagnosis: <strong>{detectionResult.classification || '—'}</strong>
                    </span>
                    <div className="flex border rounded-lg overflow-hidden">
                      <button
                        onClick={() => setReview(prev => ({ ...prev, ai_accepted: true }))}
                        className={`px-3 py-1.5 text-xs font-medium transition-colors ${review.ai_accepted ? 'bg-green-100 text-green-700' : 'bg-white text-gray-500'}`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => setReview(prev => ({ ...prev, ai_accepted: false }))}
                        className={`px-3 py-1.5 text-xs font-medium border-l transition-colors ${!review.ai_accepted ? 'bg-red-100 text-red-700' : 'bg-white text-gray-500'}`}
                      >
                        Override
                      </button>
                    </div>
                  </div>

                  {!review.ai_accepted && (
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-gray-700">Override Diagnosis</label>
                      <select
                        value={(review as any).doctor_override_class || ''}
                        onChange={e => setReview(prev => ({ ...prev, doctor_override_class: e.target.value } as any))}
                        className="w-full h-9 rounded-md border border-gray-300 bg-white px-3 text-sm"
                      >
                        <option value="">Select diagnosis...</option>
                        <option value="alzheimers">Alzheimer&apos;s Disease (AD)</option>
                        <option value="dementia">Dementia Detected</option>
                        <option value="cn">Control/Normal (CN)</option>
                        <option value="pd">Parkinson&apos;s Disease (PD)</option>
                        <option value="ftd">Frontotemporal Dementia (FTD)</option>
                      </select>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-gray-700">Clinical Conclusion</label>
                    <Textarea 
                      placeholder="Your interpretation..."
                      value={review.doctor_conclusion}
                      onChange={e => setReview({ ...review, doctor_conclusion: e.target.value })}
                      className="min-h-[70px] text-sm"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      Internal Notes <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">Private</span>
                    </label>
                    <Textarea 
                      placeholder="Private notes..."
                      value={review.doctor_notes}
                      onChange={e => setReview({ ...review, doctor_notes: e.target.value })}
                      className="min-h-[60px] text-sm"
                    />
                  </div>

                  <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-blue-800">
                      <Send size={14} /> Patient Summary
                    </label>
                    <Textarea 
                      value={review.patient_summary}
                      onChange={e => setReview({ ...review, patient_summary: e.target.value })}
                      className="min-h-[80px] border-blue-200 bg-white text-sm"
                    />
                  </div>
                  
                  <div className="flex gap-3">
                    <Button 
                      onClick={() => handleSaveReview(false)} 
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      disabled={isSavingReview}
                    >
                      <Save className="w-4 h-4 mr-1" />
                      Save Draft
                    </Button>
                    <Button 
                      onClick={() => handleSaveReview(true)} 
                      size="sm"
                      className={`flex-1 ${review.is_sent_to_patient ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                      disabled={isSavingReview}
                    >
                      {isSavingReview ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Send className="w-4 h-4 mr-1" />}
                      {review.is_sent_to_patient ? 'Update Report' : 'Send to Patient'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Actions */}
            <div className="grid grid-cols-3 gap-3">
              <Button
                onClick={() => router.push(`/explainable-ai?detection_id=${detectionResult.detectionId}`)}
                className="bg-purple-600 hover:bg-purple-700 py-5"
              >
                <Eye className="mr-2" size={18} />
                Grad-CAM
              </Button>
              <Button
                onClick={handleDownloadReport}
                className="bg-blue-600 hover:bg-blue-700 py-5"
              >
                <Download className="mr-2" size={18} />
                Download Report
              </Button>
              <Button
                onClick={resetForm}
                variant="outline"
                className="py-5"
              >
                Analyze Another
              </Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default function DetectionPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <Loader2 className="h-10 w-10 animate-spin text-[#4ADE80]" aria-label="Loading" />
        </div>
      }
    >
      <DetectionPageContent />
    </Suspense>
  )
}
