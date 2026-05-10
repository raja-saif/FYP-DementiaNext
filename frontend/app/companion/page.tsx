'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import Navigation from '@/components/Navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { Button } from '@/components/ui/button'
import { 
  Mic, Send, Volume2, VolumeX, MessageCircle, Stethoscope, Loader2, 
  Plus, MessageSquare, Menu, Trash2, Square, X, BookOpen, ArrowLeft
} from 'lucide-react'

import { PUBLIC_API_BASE_URL as API_BASE } from '@/lib/publicApi'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content_text: string
  audio_url?: string | null
  timestamp: string
}

interface Session {
  id: number
  mode: string
  started_at: string
  summary: string
  last_message: { role: string; content_text: string } | null
}

export default function CompanionPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [mode, setMode] = useState<'patient' | 'caregiver'>('patient')
  const [patientId, setPatientId] = useState<string>('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [showLifeStory, setShowLifeStory] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Redirect doctors away from companion
  useEffect(() => {
    if (!authLoading && user?.role === 'doctor') {
      router.push('/doctor-dashboard')
    }
  }, [user, authLoading, router])

  useEffect(() => {
    const timer = setTimeout(scrollToBottom, 100)
    return () => clearTimeout(timer)
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (user?.role === 'patient') setMode('patient')
  }, [user])

  const getToken = () => localStorage.getItem('authToken')

  const fetchSessions = useCallback(async () => {
    try {
      let url = `${API_BASE}/api/companion/sessions/`
      if (mode === 'caregiver' && patientId) url += `?patient_id=${patientId}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      if (res.ok) {
        const data = await res.json()
        const sessionsData = Array.isArray(data) ? data : data.results || []
        setSessions(sessionsData)
        return sessionsData
      }
    } catch { console.error('Failed to fetch sessions') }
    return []
  }, [mode, patientId])

  useEffect(() => {
    const init = async () => {
      const sessionsData = await fetchSessions()
      if (sessionsData.length > 0 && !sessionId) loadSession(sessionsData[0].id)
    }
    init()
  }, [])

  useEffect(() => { fetchSessions() }, [fetchSessions])

  const loadSession = async (id: number) => {
    setSessionId(id)
    if (window.innerWidth < 768) setIsSidebarOpen(false)
    try {
      const res = await fetch(`${API_BASE}/api/companion/sessions/${id}/messages/`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) setMessages(await res.json())
    } catch { console.error('Failed to load session') }
  }

  const startNewChat = () => {
    setSessionId(null)
    setMessages([])
    if (window.innerWidth < 768) setIsSidebarOpen(false)
  }

  const deleteSession = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this conversation?')) return
    try {
      const res = await fetch(`${API_BASE}/api/companion/sessions/${id}/`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== id))
        if (sessionId === id) { setSessionId(null); setMessages([]) }
      }
    } catch { console.error('Failed to delete') }
  }

  const pollForAudio = async (taskId: string, maxAttempts = 30): Promise<string | null> => {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const res = await fetch(`${API_BASE}/api/companion/chat/tts-status/${taskId}/`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (res.ok) {
          const data = await res.json()
          if (data.status === 'completed' && data.audio_url) return data.audio_url
          if (data.status === 'failed') return null
        }
      } catch {}
      await new Promise(resolve => setTimeout(resolve, 200))
    }
    return null
  }

  const stopStreaming = () => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
    setIsLoading(false)
  }

  const sendMessage = async (text: string, audioBlob?: Blob) => {
    if (!text && !audioBlob) return
    setIsLoading(true)
    setIsStreaming(true)
    abortControllerRef.current = new AbortController()

    const userMsg: Message = {
      id: Date.now(), role: 'user',
      content_text: text || '🎤 Voice message...',
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setInputText('')
    
    const userMsgId = userMsg.id
    const assistantMsgId = Date.now() + 1
    setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content_text: '', timestamp: new Date().toISOString() }])

    try {
      const formData = new FormData()
      if (text) formData.append('message', text)
      if (audioBlob) formData.append('audio', audioBlob, 'recording.webm')
      formData.append('mode', mode)
      if (sessionId) formData.append('session_id', String(sessionId))
      if (mode === 'caregiver' && patientId) formData.append('patient_id', patientId)

      const res = await fetch(`${API_BASE}/api/companion/chat/send-stream/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
        signal: abortControllerRef.current.signal,
      })

      if (!res.ok) throw new Error((await res.json()).error || 'Request failed')

      const reader = res.body?.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullContent = '', ttsTaskId: string | null = null, newSessionId: number | null = null, buffer = ''

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const parts = buffer.split('\n\n')
            buffer = parts.pop() || ''

            for (const part of parts) {
              for (const line of part.split('\n')) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6).trim())
                    if (data.type === 'transcription') {
                      setMessages(prev => prev.map(msg => msg.id === userMsgId ? { ...msg, content_text: `🎤 "${data.content}"` } : msg))
                    } else if (data.type === 'chunk') {
                      fullContent += data.content
                      setMessages(prev => prev.map(msg => msg.id === assistantMsgId ? { ...msg, content_text: fullContent } : msg))
                    } else if (data.type === 'done' || data.type === 'faq_hit') {
                      fullContent = data.content || fullContent
                      newSessionId = data.session_id
                      ttsTaskId = data.tts_task_id
                      setMessages(prev => prev.map(msg => msg.id === assistantMsgId ? { ...msg, content_text: fullContent } : msg))
                    } else if (data.type === 'error') throw new Error(data.message)
                  } catch {}
                }
              }
            }
          }
        } finally { reader.releaseLock() }
      }

      if (newSessionId) { setSessionId(newSessionId); fetchSessions() }
      if (ttsTaskId && mode === 'patient') {
        pollForAudio(ttsTaskId).then(audioUrl => {
          if (audioUrl) {
            setMessages(prev => prev.map(msg => msg.id === assistantMsgId ? { ...msg, audio_url: audioUrl } : msg))
            playAudio(`${API_BASE}${audioUrl}`)
          }
        })
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setMessages(prev => prev.map(msg => msg.id === assistantMsgId ? { ...msg, content_text: `Sorry, something went wrong.` } : msg))
      }
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const playAudio = (url: string) => {
    stopAudio()
    const audio = new Audio(url)
    audioRef.current = audio
    audio.onplay = () => setIsPlayingAudio(true)
    audio.onended = () => setIsPlayingAudio(false)
    audio.onpause = () => setIsPlayingAudio(false)
    audio.onerror = () => setIsPlayingAudio(false)
    audio.play().catch(() => setIsPlayingAudio(false))
  }

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    setIsPlayingAudio(false)
  }

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
        stream.getTracks().forEach(t => t.stop())
        // Only send if recording was longer than 1 second (not cancelled and not empty)
        if (recordingTime >= 1) {
          sendMessage('', blob)
        }
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
    timerRef.current = null
  }

  const cancelRecording = () => {
    // Stop the media recorder without triggering the onstop handler to send
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      const recorder = mediaRecorderRef.current
      recorder.ondataavailable = null
      recorder.onstop = () => {
        // Just clean up, don't send
        recorder.stream?.getTracks().forEach(t => t.stop())
      }
      recorder.stop()
    }
    setIsRecording(false)
    setRecordingTime(0)
    timerRef.current && clearInterval(timerRef.current)
    timerRef.current = null
    audioChunksRef.current = []
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && inputText.trim() && !isLoading) {
      e.preventDefault()
      sendMessage(inputText)
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`
  const isPatientMode = mode === 'patient'

  return (
    <ProtectedRoute>
      <div className="h-screen flex flex-col bg-gradient-to-br from-slate-100 via-blue-50 to-teal-50">
        <Navigation />
        
        <div className="flex-1 flex overflow-hidden p-3 gap-3">
          {/* Sidebar - Wider with better styling */}
          <div className={`${isSidebarOpen ? 'w-96' : 'w-0'} bg-white flex-shrink-0 flex flex-col transition-all duration-300 overflow-hidden rounded-2xl border border-gray-200 shadow-lg`}>
            {/* Sidebar Header */}
            <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-blue-500 to-teal-500">
              <button
                onClick={() => router.push('/patient-dashboard')}
                className="flex items-center gap-1 text-white/80 hover:text-white text-xs mb-2 transition-colors"
              >
                <ArrowLeft size={12} />
                Back to Dashboard
              </button>
              <button 
                onClick={startNewChat}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/20 hover:bg-white/30 text-white text-sm font-medium transition-all backdrop-blur-sm border border-white/30"
              >
                <Plus className="w-5 h-5" /> New Conversation
              </button>
            </div>
            
            {/* Conversations List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">Recent Chats</p>
              {sessions.map(s => {
                const displayName = s.summary || (s.last_message?.content_text?.slice(0, 35) + (s.last_message?.content_text && s.last_message.content_text.length > 35 ? '...' : '')) || 'New conversation'
                return (
                  <div
                    key={s.id}
                    onClick={() => loadSession(s.id)}
                    className={`group flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer text-sm transition-all ${
                      sessionId === s.id 
                        ? 'bg-gradient-to-r from-blue-50 to-teal-50 text-blue-700 border-2 border-blue-200 shadow-sm' 
                        : 'text-gray-600 hover:bg-gray-50 border border-transparent hover:border-gray-200'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      s.mode === 'caregiver' 
                        ? 'bg-gradient-to-br from-purple-100 to-pink-100 text-purple-600' 
                        : 'bg-gradient-to-br from-blue-100 to-teal-100 text-blue-600'
                    }`}>
                      {s.mode === 'caregiver' ? <Stethoscope className="w-5 h-5" /> : <MessageSquare className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="block truncate font-medium text-gray-800">{displayName}</span>
                      <span className="block text-xs text-gray-400 mt-0.5">
                        {s.mode === 'caregiver' ? 'Caregiver Mode' : 'Patient Chat'}
                      </span>
                    </div>
                    <button
                      onClick={(e) => deleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-2 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )
              })}
            </div>

            {/* Life Story Button - Thematic Design */}
            <div className="p-4 border-t border-gray-100">
              <button
                onClick={() => setShowLifeStory(true)}
                className="w-full flex items-center gap-3 px-4 py-4 rounded-xl bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500 text-white hover:from-violet-600 hover:via-purple-600 hover:to-fuchsia-600 font-medium transition-all shadow-lg hover:shadow-xl hover:scale-[1.02] group"
              >
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div className="text-left">
                  <span className="block font-semibold">Add Life Story</span>
                  <span className="block text-xs text-white/80">Record memories & preferences</span>
                </div>
              </button>
            </div>
          </div>

          {/* Main Chat Area - With border and better styling */}
          <div className="flex-1 flex flex-col bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden">
            {/* Top bar */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gradient-to-r from-white to-gray-50">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                  className="p-2 rounded-xl text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-all"
                >
                  <Menu className="w-5 h-5" />
                </button>
                <div>
                  <span className="text-gray-800 font-semibold text-lg">
                    {isPatientMode ? 'Companion Chat' : 'Caregiver Assistant'}
                  </span>
                  <span className="block text-xs text-gray-400">
                    {isPatientMode ? 'Your friendly AI companion' : 'Support & guidance for caregivers'}
                  </span>
                </div>
              </div>
              
              {user?.role === 'patient' && (
                <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1.5">
                  <button
                    onClick={() => { setMode('patient'); startNewChat() }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                      mode === 'patient' 
                        ? 'bg-white text-blue-600 shadow-md' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <MessageCircle className="w-4 h-4" />
                    Patient Chat
                  </button>
                  <button
                    onClick={() => { setMode('caregiver'); startNewChat() }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                      mode === 'caregiver' 
                        ? 'bg-white text-purple-600 shadow-md' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <Stethoscope className="w-4 h-4" />
                    Caregiver Mode
                  </button>
                </div>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto bg-gradient-to-b from-gray-50/50 to-white">
              <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
                {messages.length === 0 && (
                  <div className="text-center pt-16">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500 via-teal-500 to-green-500 flex items-center justify-center shadow-xl">
                      <MessageCircle className="w-10 h-10 text-white" />
                    </div>
                    <h2 className="text-3xl font-bold text-gray-800 mb-3">
                      {isPatientMode ? `Hello${user?.first_name ? `, ${user.first_name}` : ''}!` : 'How can I help today?'}
                    </h2>
                    <p className="text-gray-500 max-w-md mx-auto text-lg">
                      {isPatientMode 
                        ? "I'm here to chat with you anytime. Just speak or type your message."
                        : 'Ask me about dementia care strategies and patient support.'}
                    </p>
                  </div>
                )}

                {messages.map(msg => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-2' : ''}`}>
                      <div className={`rounded-2xl px-5 py-4 shadow-md ${
                        msg.role === 'user' 
                          ? 'bg-gradient-to-r from-blue-500 via-blue-600 to-teal-500 text-white' 
                          : 'bg-white text-gray-800 border border-gray-100'
                      }`}>
                        <p className="whitespace-pre-wrap leading-relaxed">{msg.content_text}</p>
                        {msg.audio_url && (
                          <button
                            onClick={() => isPlayingAudio ? stopAudio() : playAudio(`${API_BASE}${msg.audio_url}`)}
                            className={`mt-3 flex items-center gap-2 text-sm font-medium ${msg.role === 'user' ? 'text-white/90 hover:text-white' : 'text-blue-500 hover:text-blue-600'}`}
                          >
                            {isPlayingAudio ? <><VolumeX className="w-4 h-4" /> Stop</> : <><Volume2 className="w-4 h-4" /> Listen</>}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && messages[messages.length - 1]?.content_text === '' && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3 flex items-center gap-2 shadow-sm">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Stop Listening floating button */}
            {isPlayingAudio && (
              <div className="flex justify-center py-2">
                <button
                  onClick={stopAudio}
                  className="flex items-center gap-2 px-5 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-full text-sm font-medium shadow-lg transition-all"
                >
                  <VolumeX className="w-4 h-4" />
                  Stop Listening
                </button>
              </div>
            )}

            {/* Input Area - Fixed at bottom */}
            <div className="border-t border-gray-100 bg-white p-4">
              <div className="max-w-3xl mx-auto">
                <div className="relative flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                  {/* Recording indicator with cancel button */}
                  {isRecording && (
                    <div className="absolute -top-14 left-1/2 -translate-x-1/2 bg-gradient-to-r from-red-500 to-pink-500 text-white px-5 py-2.5 rounded-full flex items-center gap-3 text-sm shadow-xl">
                      <span className="w-3 h-3 bg-white rounded-full animate-pulse" />
                      <span className="font-medium">Recording {formatTime(recordingTime)}</span>
                      <button 
                        onClick={cancelRecording}
                        className="ml-2 p-1 hover:bg-white/20 rounded-full transition-colors"
                        title="Cancel recording"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  )}

                  {/* Mic button */}
                  {isStreaming ? (
                    <button
                      onClick={stopStreaming}
                      className="p-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-all shadow-md"
                    >
                      <Square className="w-5 h-5" />
                    </button>
                  ) : (
                    <button
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={isLoading && !isRecording}
                      className={`p-3 rounded-xl transition-all ${
                        isRecording 
                          ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white shadow-lg scale-110' 
                          : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'
                      } disabled:opacity-50`}
                      title={isRecording ? 'Stop recording and send' : 'Start recording'}
                    >
                      {isRecording ? <Send className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    </button>
                  )}

                  {/* Text input */}
                  <input
                    type="text"
                    value={inputText}
                    onChange={e => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isPatientMode ? "Type your message..." : "Ask about caregiving..."}
                    disabled={isLoading || isRecording}
                    className="flex-1 bg-transparent text-gray-800 placeholder-gray-400 py-2 text-lg focus:outline-none disabled:opacity-50"
                  />

                  {/* Send button */}
                  <button
                    onClick={() => sendMessage(inputText)}
                    disabled={!inputText.trim() || isLoading || isRecording}
                    className="p-3 rounded-xl bg-gradient-to-r from-blue-500 to-teal-500 text-white hover:from-blue-600 hover:to-teal-600 transition-all shadow-md hover:shadow-lg hover:scale-105 disabled:opacity-30 disabled:hover:scale-100"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                
                <p className="text-center text-xs text-gray-400 mt-3">
                  DementiaNext may make mistakes. Please verify important information.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Life Story Modal */}
        {showLifeStory && <LifeStoryModal onClose={() => setShowLifeStory(false)} patientId={mode === 'caregiver' ? patientId : undefined} />}
      </div>
    </ProtectedRoute>
  )
}

// Life Story Modal Component - Voice Only
function LifeStoryModal({ onClose, patientId }: { onClose: () => void; patientId?: string }) {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [entries, setEntries] = useState<any[]>([])
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const getToken = () => localStorage.getItem('authToken')

  useEffect(() => {
    fetchEntries()
  }, [])

  const fetchEntries = async () => {
    try {
      let url = `${API_BASE}/api/companion/life-story/`
      if (patientId) url += `?patient_id=${patientId}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      if (res.ok) {
        const data = await res.json()
        setEntries(Array.isArray(data) ? data : data.results || [])
      }
    } catch {}
  }

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
    if (patientId) formData.append('patient_id', patientId)

    try {
      const res = await fetch(`${API_BASE}/api/companion/life-story/upload-voice/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      })
      if (res.ok) {
        clearRecording()
        fetchEntries()
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
      setEntries(prev => prev.filter(e => e.id !== id))
    } catch {}
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[80vh] flex flex-col overflow-hidden shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Life Story</h2>
            <p className="text-sm text-gray-500">Record voice messages for the chatbot to use</p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
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
                      Record information about the patient that the chatbot should know
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
                  placeholder="Brief title (e.g., 'Sarah visits Sundays')"
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
          {entries.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-500">Saved Entries</h3>
              {entries.map(entry => (
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
  )
}
