'use client'

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { api, getTokens } from '@/lib/api'
import type { User } from '@/lib/types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: { username: string; email: string; password: string; first_name: string; last_name: string; organization_name?: string }) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const data = await api.get<User>('/auth/users/me/')
      setUser(data)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    getTokens().then(({ access }) => {
      if (access) {
        refreshUser().finally(() => setLoading(false))
      } else {
        setLoading(false)
      }
    })
  }, [refreshUser])

  const login = async (username: string, password: string) => {
    await api.login(username, password)
    await refreshUser()
  }

  const register = async (data: { username: string; email: string; password: string; first_name: string; last_name: string; organization_name?: string }) => {
    await api.register(data)
  }

  const logout = () => {
    api.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
