'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { Lead, PaginatedResponse } from '@/lib/types'

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const { addToast } = useToast()

  const fetchLeads = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (statusFilter) params.status = statusFilter
      if (priorityFilter) params.priority = priorityFilter
      const data = await api.get<PaginatedResponse<Lead>>('/leads/', params)
      setLeads(data.results)
      setTotal(data.count)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter, priorityFilter])

  useEffect(() => {
    fetchLeads()
  }, [fetchLeads])

  const updateLeadStatus = async (id: string, status: string) => {
    try {
      await api.patch(`/leads/${id}/`, { status })
      addToast('Estado actualizado correctamente.', 'success')
      fetchLeads()
    } catch (err) {
      console.error(err)
      addToast('Error al actualizar el estado.', 'error')
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

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Leads</h1>
          <p className="text-slate-500 mt-1">{total} leads generados</p>
        </div>
        <div className="flex gap-3">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todos los estados</option>
            <option value="new">Nuevo</option>
            <option value="contacted">Contactado</option>
            <option value="qualified">Calificado</option>
            <option value="proposal">En Propuesta</option>
            <option value="negotiation">En Negociación</option>
            <option value="won">Ganado</option>
            <option value="lost">Perdido</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => { setPriorityFilter(e.target.value); setPage(1) }}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todas las prioridades</option>
            <option value="urgente">Urgente</option>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Empresa</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Score</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Prioridad</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Sector</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No hay leads. Analiza empresas para generar leads.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <Link href={`/leads/${lead.id}`} className="font-medium text-slate-900 hover:text-blue-600">
                        {lead.company_name}
                      </Link>
                      {lead.recommended_products && (
                        <p className="text-xs text-slate-400 mt-0.5">
                          {lead.recommended_products}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`font-bold text-lg ${
                        lead.score >= 70 ? 'text-green-600' : lead.score >= 40 ? 'text-yellow-600' : 'text-slate-400'
                      }`}>
                        {lead.score}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">{priorityBadge(lead.priority)}</td>
                    <td className="px-6 py-4 text-center">{statusBadge(lead.status)}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{lead.detected_sector || '-'}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Link
                          href={`/leads/${lead.id}`}
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Ver
                        </Link>
                        <select
                          value={lead.status}
                          onChange={(e) => updateLeadStatus(lead.id, e.target.value)}
                          className="text-xs border border-slate-300 rounded px-2 py-1"
                        >
                          <option value="new">Nuevo</option>
                          <option value="contacted">Contactado</option>
                          <option value="qualified">Calificado</option>
                          <option value="proposal">En Propuesta</option>
                          <option value="negotiation">En Negociación</option>
                          <option value="won">Ganado</option>
                          <option value="lost">Perdido</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          {total > 25 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200">
              <p className="text-sm text-slate-500">
                Mostrando {(page - 1) * 25 + 1}-{Math.min(page * 25, total)} de {total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm border border-slate-300 rounded disabled:opacity-50"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 25 >= total}
                  className="px-3 py-1 text-sm border border-slate-300 rounded disabled:opacity-50"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </DashboardLayout>
  )
}
