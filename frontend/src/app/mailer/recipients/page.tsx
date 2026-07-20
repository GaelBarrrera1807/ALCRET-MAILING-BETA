'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import {
  getRecipients,
  createRecipient,
  bulkCreateRecipients,
  unsubscribeRecipient,
} from '@/lib/mailer-api'
import { useToast } from '@/contexts/ToastContext'
import type { EmailRecipient, PaginatedResponse } from '@/lib/types'

export default function RecipientsPage() {
  const [recipients, setRecipients] = useState<EmailRecipient[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [showBulk, setShowBulk] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newFirstName, setNewFirstName] = useState('')
  const [bulkText, setBulkText] = useState('')
  const [saving, setSaving] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToast()

  const PAGE_SIZE = 25

  const fetchRecipients = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (sourceFilter) params.source = sourceFilter
      if (activeFilter) params.is_active = activeFilter
      if (search.trim()) params.search = search.trim()
      const data = await getRecipients(params)
      setRecipients(data.results)
      setTotal(data.count)
    } catch {
      addToast('Error al cargar destinatarios', 'error')
    } finally {
      setLoading(false)
    }
  }, [page, sourceFilter, activeFilter, search, addToast])

  useEffect(() => {
    fetchRecipients()
  }, [fetchRecipients])

  const handleAdd = async () => {
    if (!newEmail.trim()) return
    setSaving(true)
    try {
      await createRecipient({
        email: newEmail.trim(),
        first_name: newFirstName.trim() || undefined,
        source: 'manual',
      })
      addToast('Destinatario añadido', 'success')
      setShowAdd(false)
      setNewEmail('')
      setNewFirstName('')
      fetchRecipients()
    } catch {
      addToast('Error al añadir destinatario', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleBulk = async () => {
    const emails = bulkText
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0 && l.includes('@'))
    if (emails.length === 0) {
      addToast('Ingresa al menos un email válido', 'error')
      return
    }
    setSaving(true)
    try {
      const result = await bulkCreateRecipients(emails, 'manual')
      addToast(`${result.created} creados, ${result.skipped} omitidos`, 'success')
      setShowBulk(false)
      setBulkText('')
      fetchRecipients()
    } catch {
      addToast('Error al importar destinatarios', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleCsvImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    const lines = text.split('\n').slice(1)
    const emails = lines
      .map((l) => l.split(',')[0]?.trim())
      .filter((l) => l && l.includes('@'))
    if (emails.length === 0) {
      addToast('No se encontraron emails válidos en el CSV', 'error')
      return
    }
    setSaving(true)
    try {
      const result = await bulkCreateRecipients(emails, 'csv_upload')
      addToast(`${result.created} creados, ${result.skipped} omitidos`, 'success')
      fetchRecipients()
    } catch {
      addToast('Error al importar CSV', 'error')
    } finally {
      setSaving(false)
      e.target.value = ''
    }
  }

  const handleUnsubscribe = async (id: string) => {
    if (!confirm('¿Dar de baja este destinatario?')) return
    try {
      await unsubscribeRecipient(id)
      addToast('Destinatario dado de baja', 'success')
      fetchRecipients()
    } catch {
      addToast('Error al dar de baja', 'error')
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Destinatarios</h1>
          <p className="text-slate-500 mt-1">{total} destinatarios</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowBulk(true); setShowAdd(false) }}
            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
          >
            Importar CSV
          </button>
          <button
            onClick={() => { setShowAdd(true); setShowBulk(false) }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Añadir Destinatario
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Buscar por email o nombre..."
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={sourceFilter}
            onChange={(e) => { setSourceFilter(e.target.value); setPage(1) }}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todas las fuentes</option>
            <option value="manual">Manual</option>
            <option value="csv_upload">CSV</option>
            <option value="lead_generation">Generación de Leads</option>
          </select>
          <select
            value={activeFilter}
            onChange={(e) => { setActiveFilter(e.target.value); setPage(1) }}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </div>
      </div>

      {/* Add modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold mb-4">Añadir Destinatario</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email *</label>
                <input
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="correo@ejemplo.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
                <input
                  value={newFirstName}
                  onChange={(e) => setNewFirstName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Nombre (opcional)"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleAdd}
                disabled={saving || !newEmail.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Añadiendo...' : 'Añadir'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk modal */}
      {showBulk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
            <h2 className="text-lg font-semibold mb-4">Importar Destinatarios</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Emails (uno por línea)
                </label>
                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  className="w-full h-32 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="correo1@ejemplo.com&#10;correo2@ejemplo.com&#10;correo3@ejemplo.com"
                />
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <span className="flex-1">O importa un archivo CSV (columna A: email)</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleCsvImport}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Subir CSV
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowBulk(false)}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleBulk}
                disabled={saving || !bulkText.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Importando...' : 'Importar'}
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
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Email</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Empresa</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Fuente</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Activo</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {recipients.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No hay destinatarios. Añade destinatarios manualmente o importa un CSV.
                  </td>
                </tr>
              ) : (
                recipients.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm text-slate-900">{r.email}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{r.first_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{r.company_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{r.source || '-'}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${r.is_active ? 'bg-green-500' : 'bg-red-400'}`} />
                    </td>
                    <td className="px-6 py-4 text-center">
                      {r.is_active && (
                        <button
                          onClick={() => handleUnsubscribe(r.id)}
                          className="text-sm text-red-500 hover:text-red-700 font-medium"
                        >
                          Dar de baja
                        </button>
                      )}
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
