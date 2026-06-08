'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { Lead } from '@/lib/types'

export default function LeadDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { addToast } = useToast()
  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ status: '', priority: '', notes: '' })

  useEffect(() => {
    if (!params.id) return
    setLoading(true)
    api.get<Lead>(`/leads/${params.id}/`)
      .then((data) => {
        setLead(data)
        setForm({ status: data.status, priority: data.priority, notes: '' })
      })
      .catch(() => {
        addToast('Error al cargar el lead.', 'error')
        router.push('/leads')
      })
      .finally(() => setLoading(false))
  }, [params.id, addToast, router])

  const handleSave = async () => {
    try {
      const payload: Record<string, unknown> = { status: form.status, priority: form.priority }
      const updated = await api.patch<Lead>(`/leads/${params.id}/`, payload)
      setLead(updated)
      setEditing(false)
      addToast('Lead actualizado correctamente.', 'success')
    } catch {
      addToast('Error al guardar los cambios.', 'error')
    }
  }

  const priorityBadge = (priority: string) => {
    const styles: Record<string, string> = {
      urgente: 'bg-red-100 text-red-800',
      alta: 'bg-orange-100 text-orange-800',
      media: 'bg-blue-100 text-blue-800',
      baja: 'bg-slate-100 text-slate-600',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${styles[priority] || ''}`}>
        {priority}
      </span>
    )
  }

  const statusBadge = (status: string) => {
    const labels: Record<string, string> = {
      new: 'Nuevo',
      contacted: 'Contactado',
      qualified: 'Calificado',
      proposal: 'En Propuesta',
      negotiation: 'En Negociación',
      won: 'Ganado',
      lost: 'Perdido',
    }
    return (
      <span className="px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
        {labels[status] || status}
      </span>
    )
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </DashboardLayout>
    )
  }

  if (!lead) return null

  const scoreColor = lead.score >= 70 ? 'text-green-600' : lead.score >= 40 ? 'text-yellow-600' : 'text-slate-400'

  return (
    <DashboardLayout>
      <div className="mb-6">
        <Link href="/leads" className="text-sm text-blue-600 hover:text-blue-800 mb-2 inline-block">
          ← Volver a leads
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{lead.company_name}</h1>
            <p className="text-slate-500 mt-1">
              {lead.detected_sector && `${lead.detected_sector} · `}
              {priorityBadge(lead.priority)} {statusBadge(lead.status)}
            </p>
          </div>
          <div className="flex gap-3">
            {editing ? (
              <>
                <button
                  onClick={() => { setEditing(false); setForm({ status: lead.status, priority: lead.priority, notes: '' }) }}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                >
                  Guardar
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Editar
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Información del Lead</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-400">Empresa</p>
                <p className="text-sm font-medium text-slate-700">{lead.company_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Estado de Empresa</p>
                <p className="text-sm font-medium text-slate-700">{lead.company_status || 'N/A'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Estado</p>
                {editing ? (
                  <select
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    <option value="new">Nuevo</option>
                    <option value="contacted">Contactado</option>
                    <option value="qualified">Calificado</option>
                    <option value="proposal">En Propuesta</option>
                    <option value="negotiation">En Negociación</option>
                    <option value="won">Ganado</option>
                    <option value="lost">Perdido</option>
                  </select>
                ) : (
                  <p className="text-sm font-medium text-slate-700">{statusBadge(lead.status)}</p>
                )}
              </div>
              <div>
                <p className="text-xs text-slate-400">Prioridad</p>
                {editing ? (
                  <select
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    <option value="baja">Baja</option>
                    <option value="media">Media</option>
                    <option value="alta">Alta</option>
                    <option value="urgente">Urgente</option>
                  </select>
                ) : (
                  <p className="text-sm font-medium text-slate-700">{priorityBadge(lead.priority)}</p>
                )}
              </div>
              <div>
                <p className="text-xs text-slate-400">Es Cliente Potencial</p>
                <p className="text-sm font-medium text-slate-700">{lead.is_potential_client ? 'Sí' : 'No'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Asignado A</p>
                <p className="text-sm font-medium text-slate-700">{lead.assigned_to || 'Sin asignar'}</p>
              </div>
            </div>
          </div>

          {lead.analysis_summary && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Resumen del Análisis</h2>
              <p className="text-sm text-slate-700 leading-relaxed">{lead.analysis_summary}</p>
            </div>
          )}

          {lead.reason && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Motivo de Clasificación</h2>
              <p className="text-sm text-slate-700 leading-relaxed">{lead.reason}</p>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center">
            <p className="text-sm text-slate-500 mb-2">Score</p>
            <p className={`text-4xl font-bold ${scoreColor}`}>{lead.score}</p>
            <p className="text-xs text-slate-400 mt-2">
              {lead.is_potential_client ? 'Cliente potencial' : 'No potencial'}
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="text-sm font-semibold text-slate-500 uppercase mb-3">Detalles</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-400">Sector Detectado</p>
                <p className="text-sm font-medium text-slate-700">{lead.detected_sector || 'No detectado'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Productos Recomendados</p>
                <p className="text-sm font-medium text-slate-700">{lead.recommended_products || 'Ninguno'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Creado</p>
                <p className="text-sm font-medium text-slate-700">{new Date(lead.created_at).toLocaleDateString('es-MX')}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Actualizado</p>
                <p className="text-sm font-medium text-slate-700">{new Date(lead.updated_at).toLocaleDateString('es-MX')}</p>
              </div>
            </div>
          </div>

          <Link
            href={`/companies/${lead.company}`}
            className="block text-center px-4 py-3 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100"
          >
            Ver empresa relacionada →
          </Link>
        </div>
      </div>
    </DashboardLayout>
  )
}
