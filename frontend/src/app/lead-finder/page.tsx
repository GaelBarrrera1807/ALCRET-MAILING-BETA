'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import type { ApiError } from '@/lib/api'

// ── Types ──────────────────────────────────────────────

interface ScrapingJob {
  id: string
  organization: string | null
  company: string | null
  company_name: string
  url: string
  job_type: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  result: LeadFinderResult | null
  error_message: string
  created_at: string
  updated_at: string
}

interface LeadFinderCompany {
  id: string
  name: string
  score: number
  sector: string
  website: string
  contacts_count: number
  latitude?: number | null
  longitude?: number | null
  google_rating?: number | null
  google_reviews_count?: number | null
  maps_categories?: string[]
  main_photo_url?: string | null
}

interface LeadFinderResult {
  search_query: string
  location: string
  total_raw: number
  pipeline_total: number
  pipeline_relevant: number
  pipeline_filtered: number
  created: number
  errors: number
  company_ids: string[]
  snov_enriched_count: number
  snov_contacts_total: number
  credits_consumed: number
  companies: LeadFinderCompany[]
}

interface ScrapingJobHistory {
  id: string
  search_query: string
  location: string
  status: string
  companies_count: number
  created_at: string
}

// ── Constants ───────────────────────────────────────────

const SECTORS = [
  { value: 'personalizado', label: 'Personalizado' },
  { value: 'Transporte de carga general', label: 'Transporte de carga general' },
  { value: 'Construcción', label: 'Construcción' },
  { value: 'Agrícola', label: 'Agrícola' },
  { value: 'Alimentos', label: 'Alimentos' },
  { value: 'Petrolera', label: 'Petrolera' },
  { value: 'Petroquímica', label: 'Petroquímica' },
  { value: 'Refresquera', label: 'Refresquera' },
  { value: 'Portuaria', label: 'Portuaria' },
]

const STATUS_MESSAGES = [
  '🤖 Rastreando coordenadas industriales en Google Maps...',
  '🎯 Filtrando negocios irrelevantes con nuestro Pipeline Core...',
  '💼 Cruzando dominios web con directores en LinkedIn...',
  '📧 Extrayendo y verificando correos corporativos con Snov.io...',
]

const POLL_INTERVAL = 8000
const MESSAGE_ROTATE = 2500

// ── Helpers ─────────────────────────────────────────────

function priorityLabel(score: number): { label: string; color: string } {
  if (score >= 60) return { label: 'SQL Alta', color: 'bg-green-100 text-green-800 border-green-200' }
  if (score >= 30) return { label: 'MQL Media', color: 'bg-blue-100 text-blue-800 border-blue-200' }
  if (score > 0) return { label: 'Baja', color: 'bg-amber-100 text-amber-800 border-amber-200' }
  return { label: 'Descartado', color: 'bg-slate-100 text-slate-500 border-slate-200' }
}

function kanbanColumn(score: number): 'alta' | 'media' | 'baja' | 'descartado' {
  if (score >= 60) return 'alta'
  if (score >= 30) return 'media'
  if (score > 0) return 'baja'
  return 'descartado'
}

// ── Component ───────────────────────────────────────────

export default function LeadFinderPage() {
  const [searchQuery, setSearchQuery] = useState('Empresas de')
  const [selectedSector, setSelectedSector] = useState('Transporte de carga general')
  const [customQuery, setCustomQuery] = useState('')
  const [location, setLocation] = useState('')
  const [limit, setLimit] = useState(50)
  const [submitting, setSubmitting] = useState(false)

  // History state
  const [historyJobs, setHistoryJobs] = useState<ScrapingJobHistory[]>([])
  const [selectedHistoryJobId, setSelectedHistoryJobId] = useState<string>('')

  // Polling state
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<string | null>(null)
  const [jobResult, setJobResult] = useState<LeadFinderResult | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  // Animation state
  const [msgIndex, setMsgIndex] = useState(0)
  const [progress, setProgress] = useState(0)

  // Refs for cleanup
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const messageRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  // Rotating messages
  useEffect(() => {
    if (jobStatus !== 'processing' && jobStatus !== 'pending') {
      if (messageRef.current) clearInterval(messageRef.current)
      return
    }
    messageRef.current = setInterval(() => {
      setMsgIndex((prev) => (prev + 1) % STATUS_MESSAGES.length)
    }, MESSAGE_ROTATE)
    return () => {
      if (messageRef.current) clearInterval(messageRef.current)
    }
  }, [jobStatus])

  // Simulated progress
  useEffect(() => {
    if (jobStatus !== 'processing' && jobStatus !== 'pending') {
      if (progressRef.current) clearInterval(progressRef.current)
      return
    }
    setProgress(5)
    progressRef.current = setInterval(() => {
      setProgress((prev) => Math.min(prev + Math.random() * 6, 92))
    }, POLL_INTERVAL / 3)
    return () => {
      if (progressRef.current) clearInterval(progressRef.current)
    }
  }, [jobStatus])

  // Fetch job history
  const fetchHistory = useCallback(async () => {
    try {
      const jobs = await api.get<ScrapingJobHistory[]>('/scraping-jobs/', {
        job_type: 'MAPS_DISCOVERY',
      })
      if (mountedRef.current) {
        setHistoryJobs(jobs.filter((j) => j.status === 'completed' || j.id === jobId))
      }
    } catch {
      // silent
    }
  }, [jobId])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // Load historical job result
  const loadHistoryJob = useCallback(async (historyId: string) => {
    try {
      const job = await api.get<ScrapingJob>(`/scraping-jobs/${historyId}/`)
      if (!mountedRef.current) return
      setJobId(historyId)
      setJobStatus(job.status)
      if (job.status === 'completed' && job.result) {
        setJobResult(job.result)
        setProgress(100)
      } else {
        setErrorMessage('La búsqueda seleccionada no tiene resultados')
      }
    } catch {
      setErrorMessage('Error al cargar la búsqueda histórica')
    }
  }, [])

  // Polling
  const startPolling = useCallback((id: string, sq: string, loc: string) => {
    setJobId(id)
    setJobStatus('pending')
    setJobResult(null)
    setErrorMessage('')
    setMsgIndex(0)
    setProgress(0)
    setSelectedHistoryJobId(id)
    setHistoryJobs((prev) => {
      if (prev.some((j) => j.id === id)) return prev
      const entry: ScrapingJobHistory = {
        id,
        search_query: sq,
        location: loc,
        status: 'processing',
        companies_count: 0,
        created_at: new Date().toISOString(),
      }
      return [entry, ...prev].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    })
  }, [])

  useEffect(() => {
    if (!jobId) return

    pollingRef.current = setInterval(async () => {
      try {
        const job = await api.get<ScrapingJob>(`/scraping-jobs/${jobId}/`)
        if (!mountedRef.current) return

        setJobStatus(job.status)
        if (job.status === 'completed') {
          setJobResult(job.result)
          setProgress(100)
          if (pollingRef.current) clearInterval(pollingRef.current)
          if (messageRef.current) clearInterval(messageRef.current)
          if (progressRef.current) clearInterval(progressRef.current)
          setHistoryJobs((prev) =>
            prev.map((j) =>
              j.id === job.id
                ? {
                    ...j,
                    status: 'completed',
                    companies_count: job.result?.created ?? j.companies_count,
                    search_query: job.result?.search_query ?? j.search_query,
                    location: job.result?.location ?? j.location,
                  }
                : j,
            ),
          )
        } else if (job.status === 'error') {
          setErrorMessage(job.error_message || 'Error desconocido en el trabajo de scraping')
          if (pollingRef.current) clearInterval(pollingRef.current)
          if (messageRef.current) clearInterval(messageRef.current)
          if (progressRef.current) clearInterval(progressRef.current)
        }
      } catch (err) {
        if (!mountedRef.current) return
        console.error('Polling error:', err)
      }
    }, POLL_INTERVAL)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [jobId])

  const handleSubmit = useCallback(async () => {
    setSubmitting(true)
    setErrorMessage('')
    try {
      const effectiveQuery = selectedSector === 'personalizado'
        ? customQuery.trim()
        : searchQuery.includes(selectedSector)
          ? searchQuery
          : `${searchQuery.trim()} ${selectedSector}`

      const job = await api.post<ScrapingJob>('/scraping-jobs/lead_finder/', {
        search_query: effectiveQuery,
        location: location.trim(),
        limit,
      })
      startPolling(job.id, effectiveQuery, location.trim())
    } catch (err) {
      const apiErr = err as ApiError
      setErrorMessage(
        (apiErr?.data && typeof apiErr.data === 'object' && 'detail' in apiErr.data
          ? (apiErr.data as Record<string, unknown>).detail
          : apiErr?.message) as string || 'Error al iniciar la prospección'
      )
    } finally {
      setSubmitting(false)
    }
  }, [searchQuery, selectedSector, customQuery, location, limit, startPolling])

  const handleReset = useCallback(() => {
    setJobId(null)
    setJobStatus(null)
    setJobResult(null)
    setErrorMessage('')
    setProgress(0)
    if (pollingRef.current) clearInterval(pollingRef.current)
    if (messageRef.current) clearInterval(messageRef.current)
    if (progressRef.current) clearInterval(progressRef.current)
  }, [])

  // ── Render helpers ────────────────────────────────────

  const kanbanColumns: { key: string; label: string; color: string; icon: string }[] = [
    { key: 'alta', label: 'SQL Alta', color: 'border-green-400 bg-green-50', icon: '🔥' },
    { key: 'media', label: 'MQL Media', color: 'border-blue-400 bg-blue-50', icon: '🎯' },
    { key: 'baja', label: 'Baja Prioridad', color: 'border-amber-400 bg-amber-50', icon: '📌' },
    { key: 'descartado', label: 'Descartados', color: 'border-slate-300 bg-slate-50', icon: '⛔' },
  ]

  const groupedCompanies = jobResult?.companies
    ? {
        alta: jobResult.companies.filter((c) => kanbanColumn(c.score) === 'alta'),
        media: jobResult.companies.filter((c) => kanbanColumn(c.score) === 'media'),
        baja: jobResult.companies.filter((c) => kanbanColumn(c.score) === 'baja'),
        descartado: jobResult.companies.filter((c) => kanbanColumn(c.score) === 'descartado'),
      }
    : { alta: [], media: [], baja: [], descartado: [] }

  const isLoading = jobStatus === 'pending' || jobStatus === 'processing'
  const showForm = !jobId && !submitting
  const showResults = jobResult || errorMessage

  const validSectors = new Set(
    jobResult?.companies.map((c) => c.sector).filter(Boolean) ?? []
  )

  return (
    <DashboardLayout>
      {/* ── Header ── */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Lead Finder</h1>
            <p className="text-slate-500 mt-1">
              Autogenera carteras de clientes usando Google Maps + LinkedIn + Snov.io
            </p>
          </div>

          {/* History dropdown — visible during loading and results */}
          {historyJobs.length > 0 && !showForm && (
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-slate-500">
                Historial:
              </label>
              <select
                value={selectedHistoryJobId || jobId || ''}
                onChange={(e) => {
                  const val = e.target.value
                  setSelectedHistoryJobId(val)
                  if (val && val !== jobId) {
                    loadHistoryJob(val)
                  }
                }}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px] max-w-[300px]"
              >
                {historyJobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.search_query || 'S. buscar'} — {j.location || 'Sin ubicación'}
                    {' '}({j.status === 'processing' ? '⋯' : j.companies_count} emp.)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* ── FORM ── */}
      {showForm && !showResults && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8 max-w-3xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Sector */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Giro Industrial / Búsqueda
              </label>
              <select
                value={selectedSector}
                onChange={(e) => setSelectedSector(e.target.value)}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {SECTORS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              {selectedSector === 'personalizado' && (
                <input
                  type="text"
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  placeholder="Ej: Empresas de logística, Talleres mecánicos..."
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 mt-2"
                />
              )}
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Ubicación Geográfica
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Ej: Veracruz, Nuevo León, CDMX..."
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Limit slider */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Límite de empresas a buscar: <span className="text-blue-600 font-bold">{limit}</span>
            </label>
            <input
              type="range"
              min={10}
              max={500}
              step={10}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>10</span>
              <span>500</span>
            </div>
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={submitting || !location.trim()}
            className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-xl text-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
          >
            🔍 Autogenerar Cartera Industrial con IA
          </button>
        </div>
      )}

      {/* ── LOADING / POLLING ── */}
      {isLoading && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 mb-8 text-center max-w-2xl mx-auto animate-slide-up">
          <div className="flex justify-center mb-6">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 rounded-full border-4 border-blue-100" />
              <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-600 animate-spin" />
            </div>
          </div>

          <p className="text-lg font-semibold text-slate-800 mb-2 transition-all duration-500">
            {STATUS_MESSAGES[msgIndex]}
          </p>
          <p className="text-sm text-slate-400 mb-6">
            Escaneando {location} · {jobStatus === 'pending' ? 'Iniciando...' : 'Procesando...'}
          </p>

          {/* Progress bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-400 mt-2">
            {progress < 100 ? `${Math.round(progress)}% completado` : 'Finalizando...'}
          </p>
        </div>
      )}

      {/* ── RESULTS ── */}
      {showResults && !isLoading && (
        <div className="animate-slide-up">
          {/* Error state */}
          {errorMessage && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-8">
              <p className="text-red-700 font-medium mb-1">Error en la prospección</p>
              <p className="text-red-600 text-sm">{errorMessage}</p>
              <button
                onClick={handleReset}
                className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors"
              >
                Intentar de nuevo
              </button>
            </div>
          )}

          {/* Metrics row */}
          {jobResult && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <MetricCard
                  label="Empresas Encontradas"
                  value={jobResult.created}
                  sub={`${jobResult.total_raw} resultados crudos · ${jobResult.pipeline_relevant} relevantes`}
                  color="text-blue-600"
                  bg="bg-blue-50 border-blue-200"
                />
                <MetricCard
                  label="Contactos Descubiertos"
                  value={`${jobResult.snov_contacts_total} 📧`}
                  sub={`${jobResult.snov_enriched_count} dominios enriquecidos`}
                  color="text-emerald-600"
                  bg="bg-emerald-50 border-emerald-200"
                />
                <MetricCard
                  label="Sectores Validados"
                  value={`${validSectors.size}`}
                  sub="Sectores objetivo clasificados"
                  color="text-purple-600"
                  bg="bg-purple-50 border-purple-200"
                />
                <MetricCard
                  label="Créditos Consumidos"
                  value={`${jobResult.credits_consumed} 🪙`}
                  sub={`${jobResult.snov_enriched_count} enriquecimientos × 15 créditos`}
                  color="text-amber-600"
                  bg="bg-amber-50 border-amber-200"
                />
              </div>

              {/* Kanban Board */}
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900">
                  📋 Tablero de Prospección — {jobResult.location}
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {kanbanColumns.map((col) => {
                  const items = groupedCompanies[col.key as keyof typeof groupedCompanies]
                  return (
                    <div
                      key={col.key}
                      className={`rounded-2xl border-2 ${col.color} p-4 min-h-[300px]`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                          <span>{col.icon}</span>
                          <span>{col.label}</span>
                        </h3>
                        <span className="bg-white px-2.5 py-1 rounded-full text-xs font-bold text-slate-600 shadow-sm">
                          {items.length}
                        </span>
                      </div>

                      <div className="space-y-3">
                        {items.length === 0 && (
                          <p className="text-xs text-slate-400 text-center py-8">
                            No hay empresas en esta categoría
                          </p>
                        )}
                        {items.map((company) => (
                          <LeadCard
                            key={company.id}
                            company={company}
                          />
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* New search button */}
              <div className="mt-8 text-center">
                <button
                  onClick={handleReset}
                  className="px-6 py-3 bg-white border border-slate-300 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors shadow-sm"
                >
                  🔄 Nueva prospección
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Initial state - no form, no results (e.g. if submission just started) */}
      {submitting && !jobId && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}
    </DashboardLayout>
  )
}

// ── Sub-components ──────────────────────────────────────

function MetricCard({
  label,
  value,
  sub,
  color,
  bg,
}: {
  label: string
  value: string | number
  sub: string
  color: string
  bg: string
}) {
  return (
    <div className={`rounded-2xl border p-5 ${bg}`}>
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-slate-400 mt-1">{sub}</p>
    </div>
  )
}

function LeadCard({ company }: { company: LeadFinderCompany }) {
  const [expanded, setExpanded] = useState(false)
  const p = priorityLabel(company.score)
  const domain = company.website
    ? (() => {
        try {
          const u = new URL(company.website.startsWith('http') ? company.website : `https://${company.website}`)
          return u.hostname.replace('www.', '')
        } catch {
          return company.website
        }
      })()
    : ''

  const hasExpandedMaps = company.latitude || company.longitude ||
    company.google_rating != null || (company.maps_categories?.length ?? 0) > 0
  const primaryCategory = company.maps_categories?.[0] ?? null
  const starCount = company.google_rating != null ? Math.round(company.google_rating) : 0

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* ── Thumbnail row ── */}
      {company.main_photo_url && (
        <div className="relative w-full h-28 overflow-hidden bg-slate-100">
          <img
            src={company.main_photo_url}
            alt={company.name}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        </div>
      )}

      {/* ── Clickable header ── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4"
      >
        {/* Name + score badge */}
        <div className="flex items-start justify-between mb-1.5">
          <h4 className="text-sm font-semibold text-slate-900 leading-tight line-clamp-2 flex-1 min-w-0">
            {company.name}
          </h4>
          <span className={`ml-2 px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap shrink-0 ${p.color}`}>
            {company.score}
          </span>
        </div>

        {/* Google Rating — always visible */}
        {company.google_rating != null && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="flex items-center text-amber-400" aria-label={`${company.google_rating.toFixed(1)} de 5 estrellas`}>
              {[1, 2, 3, 4, 5].map((n) => (
                <svg
                  key={n}
                  className={`w-3.5 h-3.5 ${n <= starCount ? 'fill-amber-400' : 'fill-slate-200'}`}
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </span>
            <span className="text-xs font-semibold text-slate-700">
              {company.google_rating.toFixed(1)}
            </span>
            {company.google_reviews_count != null && (
              <span className="text-xs text-slate-400">
                ({company.google_reviews_count} reseña{company.google_reviews_count !== 1 ? 's' : ''})
              </span>
            )}
          </div>
        )}

        {/* Category badge */}
        {primaryCategory && (
          <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium mb-1.5">
            {primaryCategory}
          </span>
        )}

        {company.sector && !primaryCategory && (
          <p className="text-xs text-slate-500 mb-1 line-clamp-1">{company.sector}</p>
        )}

        {domain && (
          <p className="text-xs text-blue-600 truncate mb-1">{domain}</p>
        )}

        {/* Snov.io badge */}
        {company.contacts_count > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-100">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-lg">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {company.contacts_count} Contacto{company.contacts_count !== 1 ? 's' : ''} Directo{company.contacts_count !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        {hasExpandedMaps && (
          <p className="text-xs text-slate-400 mt-2">
            {expanded ? '▲ Ocultar detalles' : '▼ Más datos de Maps'}
          </p>
        )}
      </button>

      {/* ── Expanded section — extra Maps data ── */}
      {expanded && hasExpandedMaps && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-100 space-y-2">
          <div className="grid grid-cols-2 gap-2 text-xs">
            {company.google_rating != null && (
              <div className="bg-amber-50 rounded-lg p-2 text-center">
                <span className="text-amber-600 font-bold text-sm">
                  {'★'.repeat(starCount)}{'☆'.repeat(5 - starCount)}
                </span>
                <p className="text-slate-500 mt-0.5">{company.google_rating.toFixed(1)}</p>
              </div>
            )}
            {company.google_reviews_count != null && (
              <div className="bg-blue-50 rounded-lg p-2 text-center">
                <span className="text-blue-600 font-bold text-lg">{company.google_reviews_count}</span>
                <p className="text-slate-500">Reseñas</p>
              </div>
            )}
          </div>

          {(company.latitude != null && company.longitude != null) && (
            <div className="bg-slate-50 rounded-lg p-2 text-xs">
              <span className="text-slate-500 font-medium">Ubicación:</span>{' '}
              <span className="text-slate-700">
                {company.latitude.toFixed(5)}, {company.longitude.toFixed(5)}
              </span>
            </div>
          )}

          {(company.maps_categories?.length ?? 0) > 1 && (
            <div className="flex flex-wrap gap-1">
              {company.maps_categories!.slice(1).map((cat, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
