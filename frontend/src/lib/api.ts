const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api'
export { API_BASE }

interface RequestOptions {
  method?: string
  body?: unknown
  params?: Record<string, string>
  isFormData?: boolean
}

class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, data: unknown) {
    super(`API Error: ${status}`)
    this.status = status
    this.data = data
  }
}

let inMemoryAccess: string | null = null

function getStorage() {
  if (typeof window === 'undefined') return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

export async function getTokens() {
  if (typeof window === 'undefined') return { access: null, refresh: null }
  const storage = getStorage()
  return {
    access: inMemoryAccess || storage?.getItem('access_token') || null,
    refresh: storage?.getItem('refresh_token') || null,
  }
}

function storeTokens(access: string, refresh?: string) {
  inMemoryAccess = access
  const storage = getStorage()
  if (storage) {
    storage.setItem('access_token', access)
    if (refresh) storage.setItem('refresh_token', refresh)
  }
}

function clearTokens() {
  inMemoryAccess = null
  const storage = getStorage()
  if (storage) {
    storage.removeItem('access_token')
    storage.removeItem('refresh_token')
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { access } = await getTokens()
  const headers: Record<string, string> = {}

  if (!options.isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  if (access) {
    headers['Authorization'] = `Bearer ${access}`
  }

  const url = new URL(`${API_BASE}${endpoint}`)
  if (options.params) {
    Object.entries(options.params).forEach(([k, v]) => url.searchParams.set(k, v))
  }

  const config: RequestInit = {
    method: options.method || 'GET',
    headers,
  }

  if (options.body) {
    config.body = options.isFormData ? (options.body as FormData) : JSON.stringify(options.body)
  }

  const response = await fetch(url.toString(), config)

  if (response.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      return request<T>(endpoint, options)
    }
    clearTokens()
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new ApiError(401, { detail: 'Sesión expirada' })
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ApiError(response.status, data)
  }

  if (response.status === 204) return {} as T
  return response.json()
}

async function refreshToken(): Promise<boolean> {
  const { refresh } = await getTokens()
  if (!refresh) return false

  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) {
      clearTokens()
      return false
    }
    const data = await res.json()
    storeTokens(data.access)
    return true
  } catch {
    clearTokens()
    return false
  }
}

export const api = {
  get: <T>(endpoint: string, params?: Record<string, string>) =>
    request<T>(endpoint, { params }),

  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'POST', body }),

  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PUT', body }),

  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PATCH', body }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),

  upload: <T>(endpoint: string, formData: FormData) =>
    request<T>(endpoint, { method: 'POST', body: formData, isFormData: true }),

  login: async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null))
    const data = await res.json()
    storeTokens(data.access, data.refresh)
    return data
  },

  register: (data: { username: string; email: string; password: string; first_name: string; last_name: string; organization_name?: string }) =>
    request<unknown>('/auth/register/', { method: 'POST', body: data }),

  logout: () => {
    clearTokens()
  },

  isAuthenticated: async () => {
    const { access } = await getTokens()
    if (!access) return false
    try {
      await request('/auth/users/me/')
      return true
    } catch {
      return false
    }
  },
}

export { ApiError }
