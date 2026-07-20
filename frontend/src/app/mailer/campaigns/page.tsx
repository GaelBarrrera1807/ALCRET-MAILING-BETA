'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import CampaignStatusBadge from '@/components/mailer/CampaignStatusBadge'
import { getCampaigns, createCampaign, getTemplates } from '@/lib/mailer-api'
import { useToast } from '@/contexts/ToastContext'
import type { EmailCampaign, EmailTemplate, PaginatedResponse } from '@/lib/types'

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<EmailCampaign[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [form, setForm] = useState({ name: '', template: '', source_filter: 'all' })
  const [saving, setSaving] = useState(false)
  const { addToast } = useToast()

  const PAGE_SIZE = 25

  const fetchCampaigns = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (statusFilter) params.status = statusFilter
      const data = await getCampaigns(params)
      setCampaigns(data.results)
      setTotal(data.count)
    } catch {
      addToast('Error al cargar campañas', 'error')
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter, addToast])

  useEffect(() => {
    fetchCampaigns()
  }, [fetchCampaigns])

  const openCreate = async () => {
    try {
      const data = await getTemplates()
      setTemplates(data.results)
    } catch {
      setTemplates([])
    }
    setForm({ name: '', template: '', source_filter: 'all' })
    setShowCreate(true)
  }

  const handleCreate = async () => {
    if (!form.name.trim()) {
      addToast('El nombre es obligatorio', 'error')
      return
    }
    setSaving(true)
    try {
      await createCampaign({
        name: form.name.trim(),
        template: form.template || undefined,
        source_filter: form.source_filter,
      })
      addToast('Campaña creada', 'success')
      setShowCreate(false)
      fetchCampaigns()
    } catch {
      addToast('Error al crear campaña', 'error')
    } finally {
      setSaving(false)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Campañas</h1>
          <p className="text-slate-500 mt-1">{total} campañas</p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Nueva Campaña
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="draft">Borrador</option>
          <option value="scheduled">Programada</option>
          <option value="sending">Enviando</option>
          <option value="sent">Enviada</option>
          <option value="paused">Pausada</option>
          <option value="cancelled">Cancelada</option>
        </select>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-4">Nueva Campaña</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Nombre de la campaña"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Plantilla</label>
                <select
                  value={form.template}
                  onChange={(e) => setForm({ ...form, template: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="">Sin plantilla</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Filtrar destinatarios</label>
                <select
                  value={form.source_filter}
                  onChange={(e) => setForm({ ...form, source_filter: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="all">Todos</option>
                  <option value="internal">Internos</option>
                  <option value="external">Externos</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreate}
                disabled={saving || !form.name.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Creando...' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Destinatarios</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Enviados</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Fecha</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No hay campañas. Crea tu primera campaña.
                  </td>
                </tr>
              ) : (
                campaigns.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <Link href={`/mailer/campaigns/${c.id}`} className="font-medium text-slate-900 hover:text-blue-600">
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <CampaignStatusBadge status={c.status} />
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-slate-600">{c.total_recipients}</td>
                    <td className="px-6 py-4 text-center text-sm text-slate-600">{c.sent_count}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link
                        href={`/mailer/campaigns/${c.id}`}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200">
              <p className="text-sm text-slate-500">
                Mostrando {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, total)} de {total}
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
                  disabled={page >= totalPages}
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
