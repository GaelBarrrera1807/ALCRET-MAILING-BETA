'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (message: string, type?: ToastType) => void
  removeToast: (id: number) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

let nextId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = ++nextId
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => removeToast(id), 4000)
  }, [removeToast])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white max-w-sm animate-slide-up ${
              toast.type === 'success' ? 'bg-green-600' :
              toast.type === 'error' ? 'bg-red-600' :
              'bg-blue-600'
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <span>{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-white/80 hover:text-white ml-2"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
