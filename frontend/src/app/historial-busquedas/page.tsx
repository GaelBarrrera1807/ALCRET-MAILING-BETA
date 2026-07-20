'use client'

import { useEffect, useState, useCallback } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import type { ScrapingJobSummary, SearchCompany, PaginatedResponse } from '@/lib/types'

interface ExpandedRow {
  jobId: string
  loading: boolean
  companies: SearchCompany[]
}

export default function HistorialBusquedasPage() {
  const [jobs, setJobs] = useState<ScrapingJobSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<ExpandedRow | null>(null)

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<PaginatedResponse<ScrapingJobSummary>>('/scraping-jobs/', {
        job_type: 'MAPS_DISCOVERY',
      })
      setJobs(data.results)
    } catch (err) {
      console.error('Error fetching history:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  const toggleExpand = async (jobId: string) => {
    if (expanded?.jobId === jobId) {
      setExpanded(null)
      return
    }
    setExpanded({ jobId, loading: true, companies: [] })
    try {
      const data = await api.get<{ results: SearchCompany[] }>('/companies/', {
        scraping_job: jobId,
      })
      setExpanded({ jobId, loading: false, companies: data.results })
    } catch {
      setExpanded({ jobId, loading: false, companies: [] })
    }
  }

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Historial de Búsquedas</h1>
        <p className="text-slate-500 mt-1">
          Todas las prospecciones realizadas con Google Maps
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-12 text-center">
          <p className="text-slate-400 text-lg">No hay búsquedas guardadas aún</p>
          <p className="text-slate-400 text-sm mt-1">
            Realiza una prospección en Lead Finder para ver el historial
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => {
            const isExpanded = expanded?.jobId === job.id
            return (
              <div
                key={job.id}
                className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-shadow hover:shadow-md"
              >
                <button
                  onClick={() => toggleExpand(job.id)}
                  className="w-full text-left p-5 flex items-center justify-between gap-4"
                >
                  <div className="flex-1 min-w-0 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900 truncate">
                        {job.search_query || '—'}
                      </p>
                    </div>
                    <div className="text-sm text-slate-600">
                      {job.location || '—'}
                    </div>
                    <div className="text-sm text-slate-500">
                      {new Date(job.created_at).toLocaleDateString('es-MX', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                    <div className="flex items-center justify-between md:justify-end gap-3">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        {job.companies_count} empresas
                      </span>
                      <svg
                        className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t border-slate-100">
                    {expanded!.loading ? (
                      <div className="flex justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                      </div>
                    ) : expanded!.companies.length === 0 ? (
                      <p className="text-center py-8 text-sm text-slate-400">
                        Sin empresas asociadas a esta búsqueda
                      </p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Empresa</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Score</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Google Rating</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Reseñas</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Categoría</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Coordenadas</th>
                              <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Contactos</th>
                            </tr>
                          </thead>
                          <tbody>
                            {expanded!.companies.map((c) => (
                              <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-5 py-3">
                                  <p className="font-medium text-slate-900 truncate max-w-[200px]">{c.name}</p>
                                </td>
                                <td className="px-5 py-3">
                                  <span className={`font-bold ${c.score >= 60 ? 'text-green-600' : c.score >= 30 ? 'text-amber-600' : 'text-slate-400'}`}>
                                    {c.score}
                                  </span>
                                </td>
                                <td className="px-5 py-3">
                                  {c.google_rating != null ? (
                                    <div className="flex items-center gap-1">
                                      <svg className="w-4 h-4 fill-amber-400" viewBox="0 0 20 20">
                                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                      </svg>
                                      <span className="font-medium text-slate-700">{c.google_rating.toFixed(1)}</span>
                                    </div>
                                  ) : (
                                    <span className="text-slate-300">—</span>
                                  )}
                                </td>
                                <td className="px-5 py-3 text-slate-600">
                                  {c.google_reviews_count != null ? c.google_reviews_count.toLocaleString() : '—'}
                                </td>
                                <td className="px-5 py-3">
                                  {c.maps_categories && c.maps_categories.length > 0 ? (
                                    <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium truncate max-w-[160px]">
                                      {c.maps_categories[0]}
                                    </span>
                                  ) : (
                                    <span className="text-slate-300">—</span>
                                  )}
                                </td>
                                <td className="px-5 py-3 text-xs text-slate-500 font-mono">
                                  {c.latitude != null && c.longitude != null
                                    ? `${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}`
                                    : '—'}
                                </td>
                                <td className="px-5 py-3">
                                  {c.contacts_count > 0 ? (
                                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium">
                                      {c.contacts_count}
                                    </span>
                                  ) : (
                                    <span className="text-slate-300">—</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </DashboardLayout>
  )
}
