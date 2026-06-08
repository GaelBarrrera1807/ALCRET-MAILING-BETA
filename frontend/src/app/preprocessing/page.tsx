'use client'

import { useEffect, useState, useCallback } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api, getTokens, API_BASE } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { PreprocessingJob, PaginatedResponse } from '@/lib/types'

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
}

const statusLabels: Record<string, string> = {
  pending: 'Pendiente',
  processing: 'Procesando',
  completed: 'Completado',
  error: 'Error',
}

export default function PreprocessingPage() {
  const [jobs, setJobs] = useState<PreprocessingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const { addToast } = useToast()

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (statusFilter) params.status = statusFilter
      const data = await api.get<PaginatedResponse<PreprocessingJob>>('/preprocess-jobs/', params)
      setJobs(data.results)
      setTotal(data.count)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  const handleDownload = async (job: PreprocessingJob) => {
    if (!job.cleaned_file) {
      addToast('No hay archivo limpio disponible.', 'error')
      return
    }
    try {
      const { access } = await getTokens()
      if (!access) {
        addToast('Sesión expirada. Inicia sesión nuevamente.', 'error')
        return
      }
      const response = await fetch(
        `${API_BASE}/preprocess-jobs/${job.id}/download/`,
        { headers: { Authorization: `Bearer ${access}` } }
      )
      if (!response.ok) throw new Error('Error en descarga')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `preprocessed_${job.original_filename}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      addToast('Descarga iniciada.', 'success')
    } catch {
      addToast('Error al descargar el archivo.', 'error')
    }
  }

  const formatTime = (seconds: number | null) => {
    if (!seconds) return '-'
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
    return `${seconds.toFixed(1)}s`
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Preprocesamiento</h1>
          <p className="text-slate-500 mt-1">{total} trabajos realizados</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="pending">Pendiente</option>
          <option value="processing">Procesando</option>
          <option value="completed">Completado</option>
          <option value="error">Error</option>
        </select>
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
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Archivo</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Fecha</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Total</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Relevantes</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Filtrados</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Score Prom.</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Tiempo</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-slate-400">
                    No hay trabajos de preprocesamiento. Sube un archivo desde Empresas para comenzar.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm font-medium text-slate-900 truncate max-w-[200px]">
                      {job.original_filename}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {new Date(job.created_at).toLocaleDateString('es-MX', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-mono">{job.total_records}</td>
                    <td className="px-6 py-4 text-center text-sm font-mono text-green-600 font-semibold">
                      {job.relevant_records}
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-mono text-orange-500">
                      {job.filtered_records}
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-mono">
                      {job.stats_json?.avg_score ?? '-'}
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-mono text-slate-500">
                      {formatTime(job.processing_time)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[job.status] || 'bg-gray-100'}`}>
                        {statusLabels[job.status] || job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {job.status === 'completed' && job.cleaned_file && (
                        <button
                          onClick={() => handleDownload(job)}
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Descargar
                        </button>
                      )}
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
