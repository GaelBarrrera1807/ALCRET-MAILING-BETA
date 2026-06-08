'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api, getTokens, API_BASE } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { Company, PaginatedResponse } from '@/lib/types'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [uploading, setUploading] = useState(false)
  const [threshold, setThreshold] = useState(0)
  const [useAiFallback, setUseAiFallback] = useState(false)
  const [previewData, setPreviewData] = useState<{
    total: number
    relevant: number
    filtered: number
    avg_score: number
    by_priority: Record<string, number>
  } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [lastUploadStats, setLastUploadStats] = useState<{
    total: number
    relevant: number
    filtered: number
  } | null>(null)
  const { addToast } = useToast()

  const fetchCompanies = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page: String(page) }
      if (statusFilter) params.status = statusFilter
      const data = await api.get<PaginatedResponse<Company>>('/companies/', params)
      setCompanies(data.results)
      setTotal(data.count)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => {
    fetchCompanies()
  }, [fetchCompanies])

  const handlePreprocess = async (file: File) => {
    setPreviewLoading(true)
    setPreviewData(null)
    setCurrentJobId(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('threshold', String(threshold))
    formData.append('use_ai_fallback', String(useAiFallback))
    try {
      const resp = await api.upload<{ task_id: string; job_id: string; status: string }>('/preprocess/', formData)
      setCurrentJobId(resp.job_id)
      addToast('Preprocesando archivo...', 'success')
      const checkResult = await pollTask(resp.job_id) as {
        status: string
        total_records: number
        relevant_records: number
        filtered_records: number
        stats_json: {
          avg_score: number
          by_priority: Record<string, number>
        }
      }
      if (checkResult.status === 'completed') {
        setPreviewData({
          total: checkResult.total_records,
          relevant: checkResult.relevant_records,
          filtered: checkResult.filtered_records,
          avg_score: checkResult.stats_json?.avg_score ?? 0,
          by_priority: checkResult.stats_json?.by_priority ?? {},
        })
        addToast(`Preprocesamiento completado: ${checkResult.relevant_records} relevantes de ${checkResult.total_records}`, 'success')
      } else {
        setCurrentJobId(null)
        addToast('Error en preprocesamiento.', 'error')
      }
    } catch (err) {
      console.error(err)
      setCurrentJobId(null)
      addToast('Error al preprocesar el archivo.', 'error')
    } finally {
      setPreviewLoading(false)
    }
  }

  const pollTask = async (taskId: string, maxRetries = 120): Promise<unknown> => {
    for (let i = 0; i < maxRetries; i++) {
      await new Promise((r) => setTimeout(r, 1500))
      try {
        const resp = await api.get<{ status: string }>(`/preprocess-jobs/${taskId}/`)
        if (resp.status === 'completed' || resp.status === 'error') {
          return resp
        }
      } catch {
        // continue polling
      }
    }
    throw new Error('Timeout polling task')
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setLastUploadStats(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('threshold', String(threshold))
    formData.append('use_ai_fallback', String(useAiFallback))

    try {
      await api.upload<{ task_id: string; status: string; threshold: number }>('/companies/upload/', formData)
      await new Promise((r) => setTimeout(r, 3000))
      addToast(
        `Archivo subido (threshold ${threshold}${useAiFallback ? ', IA activada' : ''}). Las empresas relevantes se están procesando.`,
        'success',
      )
      fetchCompanies()
    } catch (err) {
      console.error(err)
      addToast('Error al subir el archivo.', 'error')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDownloadClean = async () => {
    if (!currentJobId) return
    try {
      const { access } = await getTokens()
      if (!access) {
        addToast('Sesión expirada. Inicia sesión nuevamente.', 'error')
        return
      }
      const response = await fetch(
        `${API_BASE}/preprocess-jobs/${currentJobId}/download/`,
        { headers: { Authorization: `Bearer ${access}` } }
      )
      if (!response.ok) throw new Error('Error en descarga')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `preprocessed_${previewFile?.name || 'archivo'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      addToast('Descarga iniciada.', 'success')
    } catch {
      addToast('Error al descargar el archivo.', 'error')
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setPreviewFile(file)
      setPreviewData(null)
      handlePreprocess(file)
    }
  }

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      analyzing: 'bg-blue-100 text-blue-800',
      analyzed: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
    }
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      analyzing: 'Analizando',
      analyzed: 'Analizado',
      error: 'Error',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100'}`}>
        {labels[status] || status}
      </span>
    )
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Empresas</h1>
          <p className="text-slate-500 mt-1">{total} empresas registradas</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todos los estados</option>
            <option value="pending">Pendiente</option>
            <option value="analyzing">Analizando</option>
            <option value="analyzed">Analizado</option>
            <option value="error">Error</option>
          </select>

          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-600 font-medium">Threshold:</label>
            <input
              type="range"
              min={0}
              max={100}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-sm font-mono text-slate-700 w-8">{threshold}</span>
          </div>

          <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={useAiFallback}
              onChange={(e) => setUseAiFallback(e.target.checked)}
              className="rounded border-slate-300"
            />
            Usar IA para dudosos
          </label>

          <div className="ml-auto flex gap-2">
            <label className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200 cursor-pointer border border-slate-300">
              {previewLoading ? 'Preprocesando...' : 'Previsualizar'}
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileSelect}
                className="hidden"
                disabled={previewLoading}
              />
            </label>
            <label className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 cursor-pointer">
              {uploading ? 'Subiendo...' : 'Subir CSV/Excel'}
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {previewLoading && (
          <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
            {useAiFallback ? 'Preprocesando con IA (puede tardar ~2 min)...' : 'Preprocesando archivo...'}
          </div>
        )}

        {previewData && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-blue-800">Vista previa de preprocesamiento</h3>
              <div className="flex items-center gap-2">
                {currentJobId && (
                  <button
                    onClick={handleDownloadClean}
                    className="text-xs px-3 py-1 bg-white border border-blue-300 text-blue-700 rounded hover:bg-blue-50 font-medium"
                  >
                    Descargar archivo limpio
                  </button>
                )}
                {previewFile && (
                  <span className="text-xs text-blue-600 truncate max-w-xs">{previewFile.name}</span>
                )}
              </div>
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-blue-700">{previewData.total}</p>
                <p className="text-xs text-blue-600">Registros totales</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{previewData.relevant}</p>
                <p className="text-xs text-blue-600">Relevantes (score ≥ {threshold})</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-500">{previewData.filtered}</p>
                <p className="text-xs text-blue-600">Filtrados</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-700">{previewData.avg_score}</p>
                <p className="text-xs text-blue-600">Score promedio</p>
              </div>
            </div>
            {Object.keys(previewData.by_priority).length > 0 && (
              <div className="mt-2 flex gap-2 flex-wrap">
                {Object.entries(previewData.by_priority).map(([p, c]) => (
                  <span key={p} className="text-xs bg-white px-2 py-1 rounded border border-blue-200 text-blue-700">
                    {p}: {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {lastUploadStats && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-green-700">{lastUploadStats.total}</p>
                <p className="text-xs text-green-600">Registros totales</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-700">{lastUploadStats.relevant}</p>
                <p className="text-xs text-green-600">Empresas creadas (enviadas a Cerebras)</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-500">{lastUploadStats.filtered}</p>
                <p className="text-xs text-green-600">Filtradas (sin enviar a Cerebras)</p>
              </div>
            </div>
          </div>
        )}
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
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Sector</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Score</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Ciudad</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {companies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No hay empresas. Sube un archivo CSV o Excel para comenzar.
                  </td>
                </tr>
              ) : (
                companies.map((company) => (
                  <tr key={company.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <Link href={`/companies/${company.id}`} className="font-medium text-slate-900 hover:text-blue-600">
                        {company.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {company.sector_name || company.detected_sector || '-'}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`font-bold text-lg ${
                        company.score >= 70 ? 'text-green-600' : company.score >= 40 ? 'text-yellow-600' : 'text-slate-400'
                      }`}>
                        {company.score}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">{statusBadge(company.status)}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{company.city || '-'}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Link
                          href={`/companies/${company.id}`}
                          className="text-sm text-slate-500 hover:text-blue-600 font-medium"
                        >
                          Ver
                        </Link>
                        {company.status === 'pending' && (
                          <button
                            onClick={async () => {
                              try {
                                await api.post(`/companies/${company.id}/analyze/`)
                                addToast('Análisis iniciado correctamente.', 'success')
                                fetchCompanies()
                              } catch {
                                addToast('Error al iniciar el análisis.', 'error')
                              }
                            }}
                            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Analizar
                          </button>
                        )}
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
