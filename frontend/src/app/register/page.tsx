'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    organization_name: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }

    setLoading(true)
    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
        organization_name: formData.organization_name || undefined,
      })
      router.push('/login?registered=true')
    } catch (err: unknown) {
      if (err instanceof Error) {
        const apiErr = err as { status?: number; data?: Record<string, string[]> }
        if (apiErr.data) {
          const messages = Object.values(apiErr.data).flat().join('. ')
          setError(messages || 'Error al registrarse')
        } else {
          setError(err.message || 'Error al registrarse')
        }
      } else {
        setError('Error al registrarse')
      }
    } finally {
      setLoading(false)
    }
  }

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Crear Cuenta</h1>
          <p className="text-slate-500 mt-2">Regístrate para comenzar</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Nombre
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => updateField('first_name', e.target.value)}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Apellido
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => updateField('last_name', e.target.value)}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Usuario
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => updateField('username', e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => updateField('email', e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Empresa / Organización
            </label>
            <input
              type="text"
              value={formData.organization_name}
              onChange={(e) => updateField('organization_name', e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Opcional"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contraseña
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => updateField('password', e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              minLength={8}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Confirmar contraseña
            </label>
            <input
              type="password"
              value={formData.confirmPassword}
              onChange={(e) => updateField('confirmPassword', e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              minLength={8}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {loading ? 'Registrando...' : 'Crear cuenta'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          ¿Ya tienes cuenta?{' '}
          <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  )
}
