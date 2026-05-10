'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Navigation from '@/components/Navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { MessageCircle, Clock, Calendar, ChevronRight, Stethoscope, User } from 'lucide-react'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

interface SessionSummary {
  id: number
  mode: string
  started_at: string
  ended_at: string | null
  message_count: number
  cognitive_stage_at_time: string
  last_message: {
    role: string
    content_text: string
    timestamp: string
  } | null
}

interface SessionMessage {
  id: number
  role: string
  content_text: string
  audio_url: string
  timestamp: string
  response_time_ms: number | null
}

export default function CompanionDashboard() {
  const { user } = useAuth()
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [selectedSession, setSelectedSession] = useState<number | null>(null)
  const [sessionMessages, setSessionMessages] = useState<SessionMessage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [patientIdInput, setPatientIdInput] = useState('')

  const getToken = () => localStorage.getItem('authToken')

  const fetchSessions = async () => {
    setIsLoading(true)
    try {
      let url = `${API_BASE}/api/companion/sessions/`
      if (user?.role !== 'patient' && patientIdInput) {
        url += `?patient_id=${patientIdInput}`
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (res.ok) {
        const data = await res.json()
        setSessions(Array.isArray(data) ? data : data.results || [])
      }
    } catch {
      console.error('Failed to fetch sessions')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchMessages = async (sessionId: number) => {
    setIsLoadingMessages(true)
    setSelectedSession(sessionId)
    try {
      const res = await fetch(`${API_BASE}/api/companion/sessions/${sessionId}/messages/`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (res.ok) {
        const data = await res.json()
        setSessionMessages(Array.isArray(data) ? data : data.results || [])
      }
    } catch {
      console.error('Failed to fetch messages')
    } finally {
      setIsLoadingMessages(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'patient' || patientIdInput) {
      fetchSessions()
    } else {
      setIsLoading(false)
    }
  }, [user, patientIdInput])

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  }

  const totalMessages = sessions.reduce((sum, s) => sum + s.message_count, 0)
  const avgMessages = sessions.length > 0 ? Math.round(totalMessages / sessions.length) : 0

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-b from-blue-50 via-white to-teal-50">
        <Navigation />
        <div className="max-w-6xl mx-auto px-4 py-8">

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
              Companion Dashboard
            </h1>
            <p className="text-gray-500 mt-1">Review conversation history and session details</p>
          </div>

          {/* Patient ID for doctors */}
          {user?.role !== 'patient' && (
            <div className="mb-6 flex items-center gap-3 bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <label className="text-sm font-medium text-gray-600">Patient User ID:</label>
              <input
                type="number"
                value={patientIdInput}
                onChange={e => setPatientIdInput(e.target.value)}
                placeholder="Enter patient ID"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
              />
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <MessageCircle className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">{sessions.length}</p>
                  <p className="text-xs text-gray-500">Total Sessions</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-teal-100 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-teal-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">{totalMessages}</p>
                  <p className="text-xs text-gray-500">Total Messages</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">{avgMessages}</p>
                  <p className="text-xs text-gray-500">Avg Messages/Session</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Sessions list */}
            <div className="lg:col-span-1">
              <h2 className="text-lg font-semibold text-gray-700 mb-3">Sessions</h2>
              {isLoading ? (
                <div className="text-center py-10 text-gray-400">Loading...</div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-10 text-gray-400">
                  <MessageCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No conversations yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {sessions.map(session => (
                    <button
                      key={session.id}
                      onClick={() => fetchMessages(session.id)}
                      className={`w-full text-left p-4 rounded-xl border transition-all ${
                        selectedSession === session.id
                          ? 'border-blue-500 bg-blue-50 shadow'
                          : 'border-gray-200 bg-white hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {session.mode === 'patient' ? (
                            <User className="w-4 h-4 text-blue-500" />
                          ) : (
                            <Stethoscope className="w-4 h-4 text-teal-500" />
                          )}
                          <span className="text-sm font-medium text-gray-700 capitalize">{session.mode} mode</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {formatDate(session.started_at)} at {formatTime(session.started_at)}
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                        <span>{session.message_count} messages</span>
                        {session.cognitive_stage_at_time && (
                          <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{session.cognitive_stage_at_time}</span>
                        )}
                      </div>
                      {session.last_message && (
                        <p className="mt-2 text-xs text-gray-500 truncate">
                          {session.last_message.content_text}
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Messages panel */}
            <div className="lg:col-span-2">
              <h2 className="text-lg font-semibold text-gray-700 mb-3">Conversation</h2>
              {selectedSession === null ? (
                <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
                  <MessageCircle className="w-16 h-16 mx-auto mb-3 opacity-30" />
                  <p>Select a session to view the conversation</p>
                </div>
              ) : isLoadingMessages ? (
                <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
                  Loading messages...
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3 max-h-[600px] overflow-y-auto">
                  {sessionMessages.map(msg => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                          msg.role === 'user'
                            ? 'bg-gradient-to-r from-blue-600 to-teal-600 text-white'
                            : msg.role === 'system'
                            ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content_text}</p>
                        <div className={`text-xs mt-1 ${
                          msg.role === 'user' ? 'text-blue-200' : 'text-gray-400'
                        }`}>
                          {formatTime(msg.timestamp)}
                          {msg.response_time_ms && ` · ${msg.response_time_ms}ms`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}
