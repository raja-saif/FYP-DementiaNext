'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Navigation from '@/components/Navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { Mic, Trash2, User, BookOpen, Volume2, ArrowLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

interface Entry {
  id: number
  title: string
  content: string
  audio_file: string
  created_at: string
}

export default function LifeStoryPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [entries, setEntries] = useState<Entry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [patientIdInput, setPatientIdInput] = useState('')
  
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const getToken = () => localStorage.getItem('authToken')

  const fetchEntries = async () => {
    setIsLoading(true)
    try {
      let url = `${API_BASE}/api/companion/life-story/`
      if (user?.role !== 'patient' && patientIdInput) url += `?patient_id=${patientIdInput}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      if (res.ok) {
        const data = await res.json()
        setEntries(Array.isArray(data) ? data : data.results || [])
      }
    } catch {}
    setIsLoading(false)
  }

  useEffect(() => {
    if (user?.role === 'patient' || patientIdInput) fetchEntries()
    else setIsLoading(false)
  }, [user, patientIdInput])

  const startRecording = async () => {
    try {
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
    } catch { alert('Microphone access required.') }
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
    if (patientIdInput) formData.append('patient_id', patientIdInput)

    try {
      const res = await fetch(`${API_BASE}/api/companion/life-story/upload-voice/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      })
      if (res.ok) { clearRecording(); fetchEntries() }
    } catch {}
    setIsSaving(false)
  }

  const deleteEntry = async (id: number) => {
    if (!confirm('Delete?')) return
    try {
      await fetch(`${API_BASE}/api/companion/life-story/${id}/`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` }
      })
      setEntries(prev => prev.filter(e => e.id !== id))
    } catch {}
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-teal-50">
        <Navigation />
        <div className="max-w-2xl mx-auto px-4 py-8">
          <button
            onClick={() => router.push('/patient-dashboard')}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 mb-4 transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-teal-500 flex items-center justify-center">
              <BookOpen className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Life Story</h1>
            <p className="text-gray-500">
              Record voice messages that help the chatbot respond accurately
            </p>
          </div>

          {/* Patient ID for doctors */}
          {user?.role !== 'patient' && (
            <div className="mb-6 flex items-center justify-center gap-3">
              <User className="w-4 h-4 text-gray-400" />
              <input
                type="number"
                value={patientIdInput}
                onChange={e => setPatientIdInput(e.target.value)}
                placeholder="Patient ID"
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-800 text-sm w-32 focus:outline-none focus:border-blue-400"
              />
            </div>
          )}

          {/* Recording Section */}
          <div className="bg-white rounded-2xl p-6 mb-6 border border-gray-200 shadow-sm">
            {!audioBlob ? (
              <div className="text-center">
                {isRecording ? (
                  <div className="space-y-4">
                    <div className="w-24 h-24 mx-auto rounded-full bg-red-50 flex items-center justify-center">
                      <div className="w-20 h-20 rounded-full bg-red-500 flex items-center justify-center animate-pulse">
                        <Mic className="w-10 h-10 text-white" />
                      </div>
                    </div>
                    <p className="text-3xl font-mono text-red-500">{formatTime(recordingTime)}</p>
                    <p className="text-gray-500 text-sm">Speak clearly about patient information...</p>
                    <button
                      onClick={stopRecording}
                      className="px-8 py-3 bg-red-500 hover:bg-red-600 text-white rounded-full transition-colors font-medium"
                    >
                      Stop Recording
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <p className="text-gray-600 mb-4">
                      Examples: &quot;Sarah is my daughter, she visits every Sunday at 2pm&quot;
                      <br />
                      &quot;Ahmed prefers his tea without sugar&quot;
                    </p>
                    <button
                      onClick={startRecording}
                      className="px-8 py-4 bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white rounded-full transition-colors flex items-center gap-3 mx-auto text-lg font-medium"
                    >
                      <Mic className="w-6 h-6" /> Start Recording
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
                  placeholder="Brief title (e.g., 'About daughter Sarah')"
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-800 placeholder-gray-400 focus:outline-none focus:border-blue-400 text-lg"
                />
                <div className="flex gap-3">
                  <button
                    onClick={clearRecording}
                    className="flex-1 px-4 py-3 border border-gray-300 text-gray-600 hover:bg-gray-50 rounded-xl transition-colors"
                  >
                    Re-record
                  </button>
                  <button
                    onClick={saveEntry}
                    disabled={isSaving || !title.trim()}
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white rounded-xl transition-colors disabled:opacity-50 font-medium"
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Entries List */}
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              {entries.length} Saved {entries.length === 1 ? 'Entry' : 'Entries'}
            </h2>
            
            {isLoading ? (
              <div className="text-center py-8 text-gray-400">Loading...</div>
            ) : entries.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No entries yet. Record your first voice message above.
              </div>
            ) : (
              entries.map(entry => (
                <div key={entry.id} className="bg-white rounded-xl p-4 flex items-center gap-4 border border-gray-200 shadow-sm">
                  <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Volume2 className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-900 font-medium truncate">{entry.title}</p>
                    {entry.content && (
                      <p className="text-gray-500 text-sm truncate">{entry.content}</p>
                    )}
                  </div>
                  {entry.audio_file && (
                    <audio src={`${API_BASE}${entry.audio_file}`} controls className="w-32 h-8" />
                  )}
                  <button
                    onClick={() => deleteEntry(entry.id)}
                    className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}
