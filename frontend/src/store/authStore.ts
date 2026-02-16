import { create } from 'zustand'
import api from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loadProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

  login: async (username: string, password: string) => {
    const { data } = await api.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    set({ isAuthenticated: true })

    // Завантажити профіль
    const profile = await api.get('/auth/profile/')
    set({ user: profile.data })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  loadProfile: async () => {
    set({ isLoading: true })
    try {
      const { data } = await api.get('/auth/profile/')
      set({ user: data, isAuthenticated: true })
    } catch {
      set({ user: null, isAuthenticated: false })
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    } finally {
      set({ isLoading: false })
    }
  },
}))
