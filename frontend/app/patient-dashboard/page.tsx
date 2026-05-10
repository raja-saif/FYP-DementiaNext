'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  Heart, Trash2, Mic, MicOff, X, FileText,
  Loader2, BookOpen, MessageCircle, Volume2, ChevronRight, Brain, Eye, Activity,
  Download, ArrowLeft
} from 'lucide-react'

import { PUBLIC_API_BASE_URL as API_BASE } from '@/lib/publicApi'

interface LifeStoryEntry {
  id: number
  title: string
  content?: string
  audio_file?: string
  created_at: string
}

interface DoctorReport {
  id: number
  detection_id: string
  doctor_name: string
  ai_accepted: boolean
  doctor_override_class: string
  doctor_conclusion: string
  patient_summary: string
  predicted_class: string
  predicted_class_display: string
  confidence_score: number
  model_type: string
  processing_time: number
  has_fhir_report: boolean
  fhir_report_id: number | null
  sent_at: string
  created_at: string
}

export default function PatientDashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  // Life Story states
  const [showLifeStory, setShowLifeStory] = useState(false)
  const [lifeStoryEntries, setLifeStoryEntries] = useState<LifeStoryEntry[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [showSetupPrompt, setShowSetupPrompt] = useState(false)
  
  // Doctor Reports state
  const [doctorReports, setDoctorReports] = useState<DoctorReport[]>([])
  const [loadingReports, setLoadingReports] = useState(false)
  const [expandedReport, setExpandedReport] = useState<number | null>(null)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const getToken = () => localStorage.getItem('authToken')

  // Check auth and redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    } else if (!authLoading && user && user.role === 'doctor') {
      router.push('/doctor-dashboard')
    }
  }, [user, authLoading, router])

  // Check if this is first visit - show Life Story setup prompt
  useEffect(() => {
    if (user && user.role === 'patient') {
      const hasSeenSetup = localStorage.getItem(`lifeStorySetup_${user.id}`)
      if (!hasSeenSetup) {
        setShowSetupPrompt(true)
      }
      fetchLifeStoryEntries()
      fetchDoctorReports()
    }
  }, [user])

  const fetchDoctorReports = async () => {
    setLoadingReports(true)
    try {
      const res = await fetch(`${API_BASE}/api/detection/patient-reports/mine/`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setDoctorReports(Array.isArray(data) ? data : data.results || [])
      }
    } catch (e) {
      console.error('Failed to fetch doctor reports:', e)
    } finally {
      setLoadingReports(false)
    }
  }

  const downloadFHIRReport = async (reportId: number, patientName?: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/detection/patient-reports/${reportId}/fhir/`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const fhirJson = await res.json()
        const { generateFhirPdf } = await import('@/lib/generateFhirPdf')
        generateFhirPdf(fhirJson, patientName)
      }
    } catch (e) {
      console.error('Failed to download FHIR report:', e)
    }
  }

  const getClassLabel = (cls: string) => {
    const map: Record<string, string> = {
      'alzheimers': "Alzheimer's Disease",
      'dementia': 'Dementia Detected',
      'cn': 'Control / Normal',
      'ftd': 'Frontotemporal Dementia',
      'pd': "Parkinson's Disease",
    }
    return map[cls] || cls
  }

  const dismissSetupPrompt = () => {
    if (user) {
      localStorage.setItem(`lifeStorySetup_${user.id}`, 'true')
    }
    setShowSetupPrompt(false)
  }

  const fetchLifeStoryEntries = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/companion/life-story/`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setLifeStoryEntries(Array.isArray(data) ? data : data.results || [])
      }
    } catch {}
  }

  // Recording functions
  const startRecording = async () => {
    try {
      // Check if mediaDevices is supported
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Your browser does not support microphone access. Please use Chrome, Firefox, or Edge.')
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        setAudioUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach(t => t.stop())
      }
      mediaRecorder.start(250)
      setIsRecording(true)
      setRecordingTime(0)
      timerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000)
    } catch (err: any) {
      console.error('Microphone error:', err)
      if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        alert('❌ Microphone not found\n\nPlease:\n1. Connect a microphone\n2. Check system sound settings\n3. Restart your browser')
      } else if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        alert('❌ Microphone permission denied\n\nPlease:\n1. Click the 🔒 lock icon in the address bar\n2. Allow microphone access\n3. Reload the page')
      } else {
        alert('❌ Could not access microphone\n\nError: ' + (err.message || 'Unknown error'))
      }
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.state !== 'inactive' && mediaRecorderRef.current?.stop()
    setIsRecording(false)
    timerRef.current && clearInterval(timerRef.current)
  }

  const clearRecording = () => {
    setAudioBlob(null)
    audioUrl && URL.revokeObjectURL(audioUrl)
    setAudioUrl(null)
    setTitle('')
  }

  const saveEntry = async () => {
    if (!audioBlob || !title.trim()) return
    setIsSaving(true)
    
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    formData.append('title', title)
    formData.append('category', 'instructions')

    try {
      const res = await fetch(`${API_BASE}/api/companion/life-story/upload-voice/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      })
      if (res.ok) {
        clearRecording()
        fetchLifeStoryEntries()
      }
    } catch {}
    setIsSaving(false)
  }

  const deleteEntry = async (id: number) => {
    if (!confirm('Delete this entry?')) return
    try {
      await fetch(`${API_BASE}/api/companion/life-story/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      setLifeStoryEntries(prev => prev.filter(e => e.id !== id))
    } catch {}
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

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

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <div className="bg-gradient-to-r from-blue-600 to-teal-600 rounded-2xl p-6 text-white shadow-xl">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
                <Heart className="text-white" size={28} />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Hello, {user?.first_name || 'there'}! 👋</h1>
                <p className="text-blue-100">How are you feeling today?</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-blue-200"
              onClick={() => router.push('/companion')}
            >
              <CardContent className="p-6 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-teal-500 flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-800">Chat with Me</h3>
                  <p className="text-sm text-gray-500">Talk or ask questions</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400 ml-auto" />
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-teal-200"
              onClick={() => setShowLifeStory(true)}
            >
              <CardContent className="p-6 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-teal-500 to-green-500 flex items-center justify-center">
                  <BookOpen className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-800">Life Story</h3>
                  <p className="text-sm text-gray-500">{lifeStoryEntries.length} recordings</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400 ml-auto" />
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Doctor Reports Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="shadow-md border border-gray-100 rounded-xl overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-gray-100">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="w-5 h-5 text-blue-600" />
                Doctor&apos;s Reports
              </CardTitle>
              <span className="text-sm text-gray-400">{doctorReports.length} report{doctorReports.length !== 1 ? 's' : ''}</span>
            </CardHeader>
            <CardContent className="p-0">
              {loadingReports ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : doctorReports.length === 0 ? (
                <div className="text-center py-10 px-6">
                  <FileText className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                  <p className="text-gray-500 font-medium">No reports available yet</p>
                  <p className="text-sm text-gray-400 mt-1">Your doctor will share your MRI scan results here after review.</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {doctorReports.map(report => {
                    const isExpanded = expandedReport === report.id
                    const finalDiagnosis = !report.ai_accepted && report.doctor_override_class
                      ? getClassLabel(report.doctor_override_class)
                      : (report.predicted_class_display || getClassLabel(report.predicted_class))
                    return (
                      <div key={report.id} className="p-5">
                        {/* Report Header - always visible */}
                        <button
                          onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                          className="w-full text-left"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3 flex-1 min-w-0">
                              <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center shrink-0 mt-0.5">
                                <Activity className="w-5 h-5 text-blue-600" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <p className="font-semibold text-gray-900">Dr. {report.doctor_name}</p>
                                  <span className="text-xs text-gray-400">
                                    {new Date(report.sent_at || report.created_at).toLocaleDateString('en-US', {
                                      year: 'numeric', month: 'short', day: 'numeric'
                                    })}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-700 mt-1 font-medium">{finalDiagnosis}</p>
                                {!isExpanded && report.patient_summary && (
                                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">{report.patient_summary}</p>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              {report.has_fhir_report && (
                                <span className="text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-100 rounded-full px-2.5 py-0.5">FHIR</span>
                              )}
                              <ChevronRight className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                            </div>
                          </div>
                        </button>

                        {/* Expanded Details */}
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            className="mt-4 ml-13 space-y-4"
                          >
                            {/* Diagnosis Details Card */}
                            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                              <div className="grid grid-cols-1 gap-4">
                                <div>
                                  <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Diagnosis</p>
                                  <p className="text-sm font-bold text-gray-900 mt-1">{finalDiagnosis}</p>
                                </div>
                              </div>
                            </div>

                            {/* Doctor's Conclusion */}
                            {report.doctor_conclusion && (
                              <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wider font-medium mb-1.5">Clinical Conclusion</p>
                                <div className="bg-white p-4 rounded-lg border border-gray-200 text-sm text-gray-800 leading-relaxed">
                                  {report.doctor_conclusion}
                                </div>
                              </div>
                            )}

                            {/* Patient Summary */}
                            {report.patient_summary && (
                              <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wider font-medium mb-1.5">Summary for You</p>
                                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-sm text-gray-800 leading-relaxed">
                                  {report.patient_summary}
                                </div>
                              </div>
                            )}

                            {/* Detection ID + FHIR Download */}
                            <div className="flex items-center justify-between pt-2">
                              <span className="text-xs font-mono text-gray-400">{report.detection_id}</span>
                              {report.has_fhir_report && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); downloadFHIRReport(report.id, user?.first_name || 'Patient') }}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white rounded-md text-sm font-medium hover:bg-teal-700 transition-colors"
                                >
                                  <Download size={14} />
                                  Download Report (PDF)
                                </button>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Life Story Entries Preview */}
        {lifeStoryEntries.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-6"
          >
            <Card className="shadow-md">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <BookOpen className="w-5 h-5 text-teal-600" />
                  Life Story Recordings
                </CardTitle>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => setShowLifeStory(true)}
                >
                  View All
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {lifeStoryEntries.slice(0, 3).map(entry => (
                    <div key={entry.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <Volume2 className="w-5 h-5 text-teal-600" />
                      <span className="flex-1 font-medium text-gray-800">{entry.title}</span>
                      {entry.audio_file && (
                        <audio src={`${API_BASE}${entry.audio_file}`} controls className="w-32 h-8" />
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>

      {/* Life Story Setup Prompt Modal */}
      {showSetupPrompt && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl"
          >
            <div className="text-center mb-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-teal-500 to-green-500 flex items-center justify-center">
                <BookOpen className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">Help Your Loved One Remember</h2>
              <p className="text-gray-600">
                <strong>As a caregiver</strong>, record important details about your patient's life — their favorite memories, 
                family names, daily routines, and preferences. This helps our AI companion have more meaningful, 
                personalized conversations with them.
              </p>
            </div>
            <div className="space-y-3">
              <Button 
                onClick={() => { dismissSetupPrompt(); setShowLifeStory(true); }}
                className="w-full bg-gradient-to-r from-teal-500 to-green-500 hover:from-teal-600 hover:to-green-600"
              >
                Set Up Now
              </Button>
              <Button 
                onClick={dismissSetupPrompt}
                variant="outline"
                className="w-full"
              >
                Skip for Now
              </Button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Life Story Modal */}
      {showLifeStory && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-800">Life Story</h2>
                <p className="text-sm text-gray-500">Record voice messages for the chatbot</p>
              </div>
              <button onClick={() => setShowLifeStory(false)} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {/* Recording Section */}
              <div className="bg-gradient-to-br from-blue-50 to-teal-50 rounded-xl p-4 border border-blue-100">
                {!audioBlob ? (
                  <div className="text-center py-4">
                    {isRecording ? (
                      <div className="space-y-4">
                        <div className="w-20 h-20 mx-auto rounded-full bg-red-100 flex items-center justify-center">
                          <div className="w-16 h-16 rounded-full bg-red-500 flex items-center justify-center animate-pulse">
                            <Mic className="w-8 h-8 text-white" />
                          </div>
                        </div>
                        <p className="text-2xl font-mono text-red-500">{formatTime(recordingTime)}</p>
                        <button
                          onClick={stopRecording}
                          className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-full transition-colors"
                        >
                          Stop Recording
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <p className="text-gray-600 text-sm">
                          Record information that will help the chatbot assist you better
                        </p>
                        <button
                          onClick={startRecording}
                          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white rounded-full transition-colors flex items-center gap-2 mx-auto shadow-md"
                        >
                          <Mic className="w-5 h-5" /> Start Recording
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <audio controls src={audioUrl || ''} className="w-full" />
                    <input
                      type="text"
                      value={title}
                      onChange={e => setTitle(e.target.value)}
                      placeholder="Brief title (e.g., 'Daily routine')"
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-800 placeholder-gray-400 focus:outline-none focus:border-blue-400"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={clearRecording}
                        className="flex-1 px-4 py-2 border border-gray-300 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                      >
                        Re-record
                      </button>
                      <button
                        onClick={saveEntry}
                        disabled={isSaving || !title.trim()}
                        className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white rounded-lg transition-colors disabled:opacity-50"
                      >
                        {isSaving ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Existing Entries */}
              {lifeStoryEntries.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-500">Saved Recordings</h3>
                  {lifeStoryEntries.map(entry => (
                    <div key={entry.id} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-gray-800 text-sm font-medium truncate">{entry.title}</p>
                        {entry.content && (
                          <p className="text-gray-500 text-xs truncate">{entry.content}</p>
                        )}
                      </div>
                      {entry.audio_file && (
                        <audio src={`${API_BASE}${entry.audio_file}`} controls className="w-24 h-8 mx-2" />
                      )}
                      <button
                        onClick={() => deleteEntry(entry.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
