'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

type UserRole = 'patient' | 'doctor' | 'admin' | null

interface PatientProfile {
  patient_id: string
  date_of_birth: string
  gender: string
  blood_group?: string
  address?: string
  emergency_contact?: string
}

interface DoctorProfile {
  doctor_id: string
  license_number: string
  specialization: string
  qualifications: string
  experience_years: number
  hospital_affiliation: string
  consultation_fee: string
  is_verified: boolean
}

interface User {
  id: string
  email: string
  name: string
  first_name: string
  last_name: string
  role: UserRole
  phone_number?: string
  profile?: PatientProfile | DoctorProfile
}

interface AuthContextType {
  user: User | null
  userRole: UserRole
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (userData: RegisterData) => Promise<{ success: boolean; error?: string }>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

interface RegisterData {
  email: string
  password: string
  first_name: string
  last_name: string
  role: 'patient' | 'doctor'
  phone_number?: string
  // Patient fields
  date_of_birth?: string
  gender?: 'M' | 'F' | 'O'
  blood_group?: string
  address?: string
  emergency_contact?: string
  // Doctor fields
  license_number?: string
  specialization?: string
  qualifications?: string
  experience_years?: number
  hospital_affiliation?: string
  consultation_fee?: number
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  userRole: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => ({ success: false }),
  register: async () => ({ success: false }),
  logout: async () => {},
  refreshUser: async () => {},
})

export const useAuth = () => useContext(AuthContext)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
  const apiUrl = (path: string) => `${apiBase}${path}`

  const userRole = user?.role || null
  const isAuthenticated = !!user

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    if (token) {
      verifyToken(token)
    } else {
      setIsLoading(false)
    }
  }, [])

  const verifyToken = async (token: string) => {
    try {
      const response = await fetch(apiUrl('/api/profile'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setUser(data.user)
        localStorage.setItem('authToken', token)
      } else {
        localStorage.removeItem('authToken')
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      localStorage.removeItem('authToken')
    } finally {
      setIsLoading(false)
    }
  }

  const refreshUser = async () => {
    const token = localStorage.getItem('authToken')
    if (token) {
      await verifyToken(token)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch(apiUrl('/api/login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (response.ok) {
        setUser(data.user)
        localStorage.setItem('authToken', data.token)
        return { success: true }
      } else {
        return { success: false, error: data.error }
      }
    } catch (error) {
      return { success: false, error: 'Network error' }
    }
  }

  const register = async (userData: RegisterData) => {
    try {
      const response = await fetch(apiUrl('/api/register'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      })

      const data = await response.json()

      if (response.ok) {
        setUser(data.user)
        localStorage.setItem('authToken', data.token)
        return { success: true }
      } else {
        const errorMessage = typeof data === 'object' && data !== null 
          ? (data.error || JSON.stringify(data)) 
          : 'Registration failed'
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      return { success: false, error: 'Network error' }
    }
  }

  const logout = async () => {
    try {
      setUser(null)
      localStorage.removeItem('authToken')
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <AuthContext.Provider value={{ 
      user, 
      userRole, 
      isAuthenticated, 
      isLoading, 
      login, 
      register,
      logout,
      refreshUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}



