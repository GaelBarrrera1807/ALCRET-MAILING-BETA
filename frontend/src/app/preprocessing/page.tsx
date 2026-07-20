'use client'

import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api, getTokens, API_BASE } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { PreprocessingJob, PreprocessResponse, JobStats, PaginatedResponse } from '@/lib/types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface KanbanRecord {
  _index: number
  name: string
  description: string
  score: number
  prioridad: string
  industria_detectada: string
  sector_note: string
  justificacion_ia: string
  website: string
  email: string
  phone: string
  city: string
  state: string
}

// ─── Constants ───────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 1800
const MAX_POLL_ATTEMPTS = 200
const STATUS_MESSAGES = [
  'Limpiando y normalizando base de datos...',
  'Aplicando similitud léxica difusa...',
  'Clasificando sectores industriales objetivo...',
  'Analizando palabras clave de exclusión...',
  'Calculando puntuación de relevancia (scoring)...',
  'Evaluando contexto con Cerebras IA...',
  'Generando directorio limpio estructurado...',
]

const ALLOWED_EXTS = ['.csv', '.xlsx', '.xls']
const ALLOWED_EXTS_LABEL = '.csv, .xlsx, .xls'

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

// ─── CSV Parser ──────────────────────────────────────────────────────────────

function parseCSVLine(line: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQ = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (inQ) {
      if (c === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') { cur += '"'; i++ }
        else inQ = false
      } else cur += c
    } else {
      if (c === '"') inQ = true
      else if (c === ',') { out.push(cur.trim()); cur = '' }
      else cur += c
    }
  }
  out.push(cur.trim())
  return out
}

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0)
  if (lines.length < 2) return []
  const hd = parseCSVLine(lines[0])
  const result: Record<string, string>[] = []
  for (let i = 1; i < lines.length; i++) {
    const vals = parseCSVLine(lines[i])
    if (vals.length === 0) continue
    const row: Record<string, string> = {}
    hd.forEach((h, idx) => { row[h] = vals[idx] ?? '' })
    result.push(row)
  }
  return result
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isValidFile(f: File): boolean {
  const dot = f.name.lastIndexOf('.')
  if (dot === -1) return false
  return ALLOWED_EXTS.includes(f.name.slice(dot).toLowerCase())
}

function formatTime(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function truncate(text: string, max: number): string {
  if (!text || text.length <= max) return text
  return text.slice(0, max) + '…'
}

// ─── Tab definitions (table view) ────────────────────────────────────────────

interface TabDef {
  id: string
  label: string
  shortLabel: string
  count: number
  color: string
  badgeBg: string
  badgeText: string
  header: string
  description: string
  body: string
}

function buildTabs(stats: JobStats): TabDef[] {
  const alta = stats.by_priority?.alta ?? 0
  const media = stats.by_priority?.media ?? 0
  const baja = stats.by_priority?.baja ?? 0
  const discarded = stats.discarded ?? 0

  return [
    {
      id: 'sql',
      label: `SQL — Alta Prioridad`,
      shortLabel: 'SQL',
      count: alta,
      color: 'text-green-600',
      badgeBg: 'bg-green-100',
      badgeText: 'text-green-700',
      header: 'Sales Qualified Leads',
      description: 'Prospectos con intención comercial financiera explícita (arrendamiento, crédito, leasing) y puntuación ≥ 60',
      body: 'Estos leads muestran intención financiera directa. Son candidatos ideales para contacto comercial inmediato. Descarga el directorio limpio para ver los detalles completos de cada empresa.',
    },
    {
      id: 'mql',
      label: `MQL — Media Prioridad`,
      shortLabel: 'MQL',
      count: media,
      color: 'text-blue-600',
      badgeBg: 'bg-blue-100',
      badgeText: 'text-blue-700',
      header: 'Marketing Qualified Leads',
      description: 'Prospectos del sector transporte sin intención financiera inmediata detectada. Puntuación ≥ 30',
      body: 'Empresas del sector transporte con potencial de desarrollo. Requieren nurturing antes de estar listas para venta directa. Incluye flotillas, logística y operadores de carga.',
    },
    {
      id: 'baja',
      label: `Otras Relevantes`,
      shortLabel: 'Baja',
      count: baja,
      color: 'text-amber-600',
      badgeBg: 'bg-amber-100',
      badgeText: 'text-amber-700',
      header: 'Otras Relevantes (Baja Prioridad)',
      description: 'Empresas con puntuación positiva pero por debajo de los umbrales de prioridad comercial',
      body: 'Registros que no alcanzan los umbrales de prioridad pero pueden ser relevantes para campañas futuras o análisis complementarios.',
    },
    {
      id: 'descartados',
      label: `Descartados`,
      shortLabel: 'Desc.',
      count: discarded,
      color: 'text-slate-400',
      badgeBg: 'bg-slate-100',
      badgeText: 'text-slate-600',
      header: 'Registros Descartados',
      description: 'Empresas filtradas por reglas de exclusión o sin relevancia industrial o logística',
      body: 'Incluye comercios locales, retail, servicios no industriales, y empresas sin actividad logística, de transporte o industrial relevante según el análisis semántico.',
    },
  ]
}

// ─── Kanban column definitions ───────────────────────────────────────────────

interface ColumnDef {
  id: string
  title: string
  icon: string
  accent: string
  accentBorder: string
  badgeBg: string
  badgeText: string
  cardBorder: string
  gradientFrom: string
}

const KANBAN_COLUMNS: ColumnDef[] = [
  {
    id: 'sql',
    title: 'SQL — Alta Prioridad',
    icon: '🔥',
    accent: 'text-green-700',
    accentBorder: 'border-green-500',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
    cardBorder: 'border-l-green-500',
    gradientFrom: 'from-green-500',
  },
  {
    id: 'mql',
    title: 'MQL — Media Prioridad',
    icon: '📊',
    accent: 'text-blue-700',
    accentBorder: 'border-blue-500',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
    cardBorder: 'border-l-blue-500',
    gradientFrom: 'from-blue-500',
  },
  {
    id: 'baja',
    title: 'Baja Prioridad',
    icon: '📋',
    accent: 'text-amber-700',
    accentBorder: 'border-amber-500',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
    cardBorder: 'border-l-amber-500',
    gradientFrom: 'from-amber-500',
  },
  {
    id: 'descartados',
    title: 'Descartados',
    icon: '🚫',
    accent: 'text-slate-500',
    accentBorder: 'border-slate-300',
    badgeBg: 'bg-slate-100',
    badgeText: 'text-slate-600',
    cardBorder: 'border-l-slate-300',
    gradientFrom: 'from-slate-400',
  },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function PreprocessingPage() {
  // Upload area
  const [file, setFile] = useState<File | null>(null)
  const [threshold, setThreshold] = useState(30)
  const [useAiFallback, setUseAiFallback] = useState(false)
  const [autoEnrichSql, setAutoEnrichSql] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Processing
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [msgIndex, setMsgIndex] = useState(0)
  const pollingRef = useRef(false)

  // Results
  const [jobResult, setJobResult] = useState<PreprocessingJob | null>(null)
  const [activeTab, setActiveTab] = useState('sql')
  const [viewMode, setViewMode] = useState<'table' | 'kanban'>('table')

  // Kanban data (parsed from CSV)
  const [kanbanRecords, setKanbanRecords] = useState<KanbanRecord[]>([])
  const [kanbanLoading, setKanbanLoading] = useState(false)
  const [enrichingIds, setEnrichingIds] = useState<Set<number>>(new Set())

  // History
  const [jobs, setJobs] = useState<PreprocessingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')

  const { addToast } = useToast()

  // ── Rotate status messages & progress during processing ──

  useEffect(() => {
    if (!processing) return
    const t = setInterval(() => {
      setMsgIndex(i => (i + 1) % STATUS_MESSAGES.length)
      setProgress(p => Math.min(82, p + 1.8))
    }, 2800)
    return () => clearInterval(t)
  }, [processing])

  // ── Poll job status ──

  const pollJob = useCallback(
    async (id: string): Promise<PreprocessingJob> => {
      pollingRef.current = true
      for (let i = 0; i < MAX_POLL_ATTEMPTS; i++) {
        if (!pollingRef.current) break
        await new Promise(r => setTimeout(r, POLL_INTERVAL_MS))
        try {
          const resp = await api.get<PreprocessingJob>(`/preprocess-jobs/${id}/`)
          if (resp.status === 'completed' || resp.status === 'error') return resp
          setProgress(p => Math.min(82, p + 0.4))
        } catch {
          /* retry */
        }
      }
      throw new Error('Tiempo de espera agotado para el job de prospección')
    },
    [],
  )

  // ── Fetch & parse cleaned CSV for Kanban ──

  const fetchKanbanData = useCallback(
    async (job: PreprocessingJob) => {
      if (!job.cleaned_file) {
        setKanbanRecords([])
        return
      }
      setKanbanLoading(true)
      try {
        const { access } = await getTokens()
        if (!access) return
        const res = await fetch(
          `${API_BASE}/preprocess-jobs/${job.id}/download/`,
          { headers: { Authorization: `Bearer ${access}` } },
        )
        if (!res.ok) throw new Error('Error al descargar CSV')
        const text = await res.text()
        const raw = parseCSV(text)
        const records: KanbanRecord[] = raw.map((r, idx) => ({
          _index: idx,
          name: r.name || '',
          description: r.description || r.giro || '',
          score: Number(r.score) || 0,
          prioridad: (r.prioridad || '').toLowerCase(),
          industria_detectada: r.industria_detectada || '',
          sector_note: r.sector_note || '',
          justificacion_ia: r.justificacion_ia || '',
          website: r.website || '',
          email: r.email || '',
          phone: r.phone || '',
          city: r.city || '',
          state: r.state || '',
        }))
        setKanbanRecords(records)
      } catch {
        setKanbanRecords([])
      } finally {
        setKanbanLoading(false)
      }
    },
    [],
  )

  // Lazy-load Kanban data on demand when user switches to that view
  const handleViewModeChange = useCallback((mode: 'table' | 'kanban') => {
    setViewMode(mode)
    if (
      mode === 'kanban' &&
      jobResult?.status === 'completed' &&
      jobResult?.cleaned_file &&
      kanbanRecords.length === 0 &&
      !kanbanLoading
    ) {
      fetchKanbanData(jobResult)
    }
  }, [jobResult, kanbanRecords.length, kanbanLoading, fetchKanbanData])

  // ── Group Kanban records by priority ──

  const groupedKanban = useMemo(() => {
    const sql: KanbanRecord[] = []
    const mql: KanbanRecord[] = []
    const baja: KanbanRecord[] = []

    for (const r of kanbanRecords) {
      const p = r.prioridad
      const s = r.score
      if (p === 'alta' || s >= 60) sql.push(r)
      else if (p === 'media' || s >= 30) mql.push(r)
      else if (p === 'baja' || s > 0) baja.push(r)
    }

    return { sql, mql, baja }
  }, [kanbanRecords])

  // ── Submit file for processing ──

  const handleProcess = useCallback(
    async (f: File) => {
      if (!isValidFile(f)) {
        addToast(`Formato no soportado. Usa ${ALLOWED_EXTS_LABEL}`, 'error')
        return
      }

      pollingRef.current = true
      setFile(f)
      setProcessing(true)
      setJobResult(null)
      setKanbanRecords([])
      setProgress(5)
      setMsgIndex(0)
      setActiveTab('sql')

      const fd = new FormData()
      fd.append('file', f)
      fd.append('threshold', String(threshold))
      fd.append('use_ai_fallback', String(useAiFallback))
      fd.append('auto_enrich_sql', String(autoEnrichSql))

      try {
        const { job_id } = await api.upload<PreprocessResponse>('/preprocess/', fd)
        setProgress(12)
        const result = await pollJob(job_id)

        if (result.status === 'completed') {
          setJobResult(result)
          setProgress(100)
          const s = result.stats_json
          addToast(
            `Prospección completada: ${s?.relevant ?? 0} prospectos de ${s?.total ?? 0} registros`,
            'success',
          )
        } else {
          addToast(result.error_message || 'Error durante la prospección', 'error')
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al procesar el archivo'
        addToast(msg, 'error')
      } finally {
        pollingRef.current = false
        setProcessing(false)
      }
    },
    [threshold, useAiFallback, autoEnrichSql, pollJob, addToast],
  )

  // ── File selection ──

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) handleProcess(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleProcess(f)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  // ── Download cleaned file ──

  const handleDownload = async () => {
    if (!jobResult?.cleaned_file) {
      addToast('No hay archivo limpio disponible para descargar', 'error')
      return
    }
    try {
      const { access } = await getTokens()
      if (!access) {
        addToast('Sesión expirada. Inicia sesión de nuevo.', 'error')
        return
      }
      const res = await fetch(
        `${API_BASE}/preprocess-jobs/${jobResult.id}/download/`,
        { headers: { Authorization: `Bearer ${access}` } },
      )
      if (!res.ok) throw new Error('Error en descarga')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `prospeccion_${jobResult.original_filename}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      addToast('Descarga iniciada', 'success')
    } catch {
      addToast('Error al descargar el archivo', 'error')
    }
  }

  // ── Enrich a prospect with AI (create company + analyze) ──

  const handleEnrich = useCallback(
    async (rec: KanbanRecord) => {
      setEnrichingIds(prev => new Set(prev).add(rec._index))
      try {
        const company = await api.post<{ id: string }>('/companies/', {
          name: rec.name,
          description: rec.description,
          website: rec.website || '',
          email: rec.email || '',
          phone: rec.phone || '',
          city: rec.city || '',
          state: rec.state || '',
        })
        await api.post(`/companies/${company.id}/analyze/`)
        addToast(`${rec.name} enviada a análisis con IA`, 'success')
      } catch {
        addToast(`Error al enriquecer ${rec.name}`, 'error')
      } finally {
        setEnrichingIds(prev => {
          const next = new Set(prev)
          next.delete(rec._index)
          return next
        })
      }
    },
    [addToast],
  )

  // ── Load a past job's results ──

  const loadPastJob = useCallback(
    async (id: string) => {
      try {
        const detail = await api.get<PreprocessingJob>(`/preprocess-jobs/${id}/`)
        setJobResult(detail)
        setActiveTab('sql')
        addToast('Resultados cargados del historial', 'info')
      } catch {
        addToast('Error al cargar resultados del trabajo', 'error')
      }
    },
    [addToast],
  )

  // ── Fetch history ──

  useEffect(() => {
    let cancelled = false
    const fn = async () => {
      setLoading(true)
      try {
        const params: Record<string, string> = { page: String(page) }
        if (statusFilter) params.status = statusFilter
        const data = await api.get<PaginatedResponse<PreprocessingJob>>('/preprocess-jobs/', params)
        if (cancelled) return
        setJobs(data.results)
        setTotal(data.count)
      } catch {
        /* silent */
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fn()
    return () => { cancelled = true }
  }, [page, statusFilter])

  // ── Derived data ──

  const stats = jobResult?.stats_json
  const tabs = stats ? buildTabs(stats) : []

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <DashboardLayout>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prospección Inteligente</h1>
          <p className="text-sm text-slate-500 mt-1">
            Sube un directorio empresarial (CSV o Excel) y la IA lo analiza, clasifica y prioriza automáticamente
          </p>
        </div>
      </div>

      {/* ── Main grid: upload + results side by side on lg ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ════════ LEFT COLUMN: Upload ════════ */}
        <div className="lg:col-span-1 space-y-4">
          {/* ── Drop zone ── */}
          <div
            role="button"
            tabIndex={0}
            onKeyDown={e => {
              if (!processing && (e.key === 'Enter' || e.key === ' '))
                fileInputRef.current?.click()
            }}
            className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-all cursor-pointer select-none
              ${dragOver
                ? 'border-blue-500 bg-blue-50 shadow-lg shadow-blue-100/40 scale-[1.01]'
                : processing
                  ? 'border-slate-200 bg-slate-50 cursor-not-allowed'
                  : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/40'
              }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => !processing && fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileSelect}
              className="hidden"
              disabled={processing}
            />

            {!file && !processing && (
              <>
                <div className="mx-auto w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  Arrastra tu archivo aquí o <span className="text-blue-600">selecciona</span>
                </p>
                <p className="text-xs text-slate-400 mt-1">{ALLOWED_EXTS_LABEL} &middot; Máx 10 MB</p>
              </>
            )}

            {file && !processing && (
              <>
                <div className="mx-auto w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-slate-800 truncate px-2">{file.name}</p>
                <p className="text-xs text-slate-400 mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB &middot; Haz clic para cambiar</p>
              </>
            )}

            {processing && (
              <>
                <div className="mx-auto w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mb-3">
                  <div className="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
                </div>
                <p className="text-sm font-semibold text-slate-500">Procesando...</p>
                <p className="text-xs text-slate-400 mt-1">{file?.name ?? ''}</p>
              </>
            )}
          </div>

          {/* ── Configuration card ── */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-700">Configuración</h3>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-slate-500">Threshold de Relevancia</label>
                <span className="text-sm font-bold text-blue-600 font-mono">{threshold}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={threshold}
                onChange={e => setThreshold(Number(e.target.value))}
                disabled={processing}
                className="w-full h-2 accent-blue-600 rounded-lg appearance-none cursor-pointer bg-slate-200"
              />
              <p className="text-xs text-slate-400 mt-1">Solo empresas con score &ge; {threshold} serán consideradas prospectos</p>
            </div>

            <label className="flex items-start gap-2.5 cursor-pointer select-none group">
              <input
                type="checkbox"
                checked={useAiFallback}
                onChange={e => setUseAiFallback(e.target.checked)}
                disabled={processing}
                className="mt-0.5 rounded border-slate-300 accent-blue-600"
              />
              <div>
                <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">Usar IA para dudosos</span>
                <p className="text-xs text-slate-400 mt-0.5">
                  Cerebras evaluará casos fronterizos (score entre 1 y {threshold - 1}) y podría rescatarlos
                </p>
              </div>
            </label>

            <label className="flex items-start gap-2.5 cursor-pointer select-none group">
              <input
                type="checkbox"
                checked={autoEnrichSql}
                onChange={e => setAutoEnrichSql(e.target.checked)}
                disabled={processing}
                className="mt-0.5 rounded border-slate-300 accent-blue-600"
              />
              <div>
                <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">🤖 Enriquecimiento Automático SQL (Apify + Snov.io)</span>
                <p className="text-xs text-slate-400 mt-0.5">
                  Los prospectos de alto valor (score &ge; 60) serán enriquecidos en segundo plano sin intervención
                </p>
              </div>
            </label>

            <button
              onClick={() => file && handleProcess(file)}
              disabled={!file || processing}
              className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all duration-200
                ${file && !processing
                  ? 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-sm shadow-blue-200'
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                }`}
            >
              {processing ? 'Prospección en curso…' : file ? 'Iniciar Prospección Inteligente' : 'Selecciona un archivo primero'}
            </button>
          </div>

          {/* ── File info when results visible ── */}
          {jobResult && !processing && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Último análisis</h3>
              <p className="text-sm font-medium text-slate-800 truncate">{jobResult.original_filename}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Threshold: {jobResult.scoring_threshold} &middot;{' '}
                {jobResult.processing_time != null ? formatTime(jobResult.processing_time) : ''}
              </p>
              {jobResult.cleaned_file && (
                <button
                  onClick={handleDownload}
                  className="mt-3 w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  <svg className="w-3.5 h-3.5 inline mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Descargar Directorio Limpio
                </button>
              )}
            </div>
          )}
        </div>

        {/* ════════ RIGHT COLUMN: Results ════════ */}
        <div className="lg:col-span-2 space-y-4">
          {/* ── Processing state ── */}
          {processing && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full border-[3px] border-blue-100 border-t-blue-600 animate-spin shrink-0" />
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-slate-800">Analizando directorio...</h3>
                  <p className="text-xs text-slate-400 truncate">{STATUS_MESSAGES[msgIndex]}</p>
                </div>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{file?.name ?? ''} &middot; Threshold {threshold}</span>
                <span className="font-mono">{Math.round(progress)}%</span>
              </div>
            </div>
          )}

          {/* ── Empty state ── */}
          {!processing && !jobResult && (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <div className="mx-auto w-16 h-16 rounded-xl bg-slate-50 flex items-center justify-center mb-4 border border-slate-200">
                <svg className="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-slate-700">Sin resultados aún</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto leading-relaxed">
                Sube un directorio empresarial en la columna izquierda para que la IA lo analice, clasifique por industrias objetivo y genere prospectos calificados.
              </p>
            </div>
          )}

          {/* ── Results view ── */}
          {jobResult && stats && !processing && (
            <>
              {/* Metric cards */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                {[
                  { label: 'Registros totales', value: stats.total, color: 'text-slate-800' },
                  { label: 'Prospectos', value: stats.relevant, color: 'text-green-600' },
                  { label: 'Descartados', value: stats.discarded, color: 'text-red-400' },
                  { label: 'Score promedio', value: stats.avg_score, color: 'text-blue-600' },
                  { label: 'Créditos Consumidos', value: stats.credits_consumed ?? 0, color: 'text-amber-600', icon: '🪙' },
                ].map(m => (
                  <div key={m.label} className={`bg-white rounded-xl border border-slate-200 p-4 ${'icon' in m ? 'relative' : ''}`}>
                    <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">{m.label}</p>
                    <p className={`text-2xl font-bold mt-1 flex items-center gap-1.5 ${m.color}`}>
                      {'icon' in m && <span className="text-lg">{m.icon}</span>}
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* View toggle */}
              <div className="flex items-center justify-between">
                <div className="bg-slate-100 rounded-lg p-0.5 inline-flex">
                  {(['table', 'kanban'] as const).map(mode => (
                    <button
                      key={mode}
                      onClick={() => handleViewModeChange(mode)}
                      className={`px-4 py-1.5 text-xs font-medium rounded-md transition-all duration-200
                        ${viewMode === mode
                          ? 'bg-white text-slate-800 shadow-sm border border-slate-200'
                          : 'text-slate-500 hover:text-slate-700'
                        }`}
                    >
                      {mode === 'table' ? (
                        <span className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          Vista Tabla
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                          </svg>
                          Tablero Kanban
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleDownload}
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors shadow-sm"
                >
                  <svg className="w-3.5 h-3.5 inline mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Descargar CSV
                </button>
              </div>

              {/* ── TABLE VIEW ── */}
              {viewMode === 'table' && (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                  <div className="border-b border-slate-200">
                    <nav className="flex overflow-x-auto">
                      {tabs.map(t => (
                        <button
                          key={t.id}
                          onClick={() => setActiveTab(t.id)}
                          className={`flex items-center gap-1.5 px-4 py-3 text-xs font-medium border-b-2 transition-all whitespace-nowrap
                            ${activeTab === t.id
                              ? 'border-blue-600 text-blue-700 bg-blue-50/60'
                              : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                            }`}
                        >
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${t.badgeBg} ${t.badgeText}`}>{t.count}</span>
                          <span className="hidden sm:inline">{t.label}</span>
                          <span className="sm:hidden">{t.shortLabel}</span>
                        </button>
                      ))}
                    </nav>
                  </div>

                  <div className="p-5">
                    {tabs.map(t => {
                      if (t.id !== activeTab) return null
                      return (
                        <div key={t.id}>
                          <div className="flex items-start justify-between gap-4 mb-4">
                            <div className="min-w-0">
                              <h3 className="text-sm font-semibold text-slate-800">{t.header}</h3>
                              <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{t.description}</p>
                            </div>
                            <span className={`shrink-0 px-3 py-1 rounded-full text-xs font-bold ${t.badgeBg} ${t.badgeText}`}>
                              {t.count} registro{t.count !== 1 ? 's' : ''}
                            </span>
                          </div>
                          <div className={`rounded-lg border p-4 text-sm ${
                            t.id === 'sql' ? 'bg-green-50 border-green-200 text-green-800'
                            : t.id === 'mql' ? 'bg-blue-50 border-blue-200 text-blue-800'
                            : t.id === 'baja' ? 'bg-amber-50 border-amber-200 text-amber-800'
                            : 'bg-slate-50 border-slate-200 text-slate-600'
                          }`}>
                            <p className="font-medium">{t.body}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div className="border-t border-slate-200 px-5 py-3 flex items-center justify-between bg-slate-50/80">
                    <p className="text-xs text-slate-400 truncate mr-4">
                      Archivo: <span className="font-medium text-slate-600">{jobResult.original_filename}</span>
                    </p>
                  </div>
                </div>
              )}

              {/* ── KANBAN VIEW ── */}
              {viewMode === 'kanban' && (
                <div className="overflow-x-auto pb-2 -mx-1 px-1">
                  {kanbanLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
                        <span className="text-sm text-slate-400">Cargando registros del directorio limpio...</span>
                      </div>
                    </div>
                  ) : kanbanRecords.length === 0 && !jobResult.cleaned_file ? (
                    <div className="flex items-center justify-center py-16">
                      <div className="text-center">
                        <svg className="w-10 h-10 text-slate-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p className="text-sm text-slate-400">No hay datos individuales disponibles para vista Kanban</p>
                        <p className="text-xs text-slate-300 mt-1">Usa la vista Tabla para ver el resumen o descarga el CSV</p>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-4 gap-4 min-w-[900px]">
                      {KANBAN_COLUMNS.map(col => {
                        let records: KanbanRecord[] = []
                        let count = 0
                        let isDiscarded = false

                        if (col.id === 'sql') { records = groupedKanban.sql; count = records.length }
                        else if (col.id === 'mql') { records = groupedKanban.mql; count = records.length }
                        else if (col.id === 'baja') { records = groupedKanban.baja; count = records.length }
                        else { isDiscarded = true; count = stats.discarded }

                        return (
                          <div key={col.id} className="flex flex-col min-h-[320px]">
                            {/* Column header */}
                            <div className={`flex items-center justify-between mb-3 px-3 py-2 rounded-lg border-l-4 ${col.accentBorder} bg-white border border-slate-200 shadow-sm`}>
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="text-sm">{col.icon}</span>
                                <span className={`text-xs font-semibold ${col.accent} truncate`}>{col.title}</span>
                              </div>
                              <span className={`shrink-0 ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold ${col.badgeBg} ${col.badgeText}`}>
                                {count}
                              </span>
                            </div>

                            {/* Column body */}
                            <div className="flex-1 space-y-2.5 overflow-y-auto max-h-[520px] pr-0.5">
                              {!isDiscarded && records.map(rec => (
                                <div
                                  key={rec._index}
                                  className={`bg-white rounded-lg border border-slate-200 border-l-4 ${col.cardBorder} p-3 shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 group`}
                                >
                                  {/* Company name */}
                                  <h4 className="text-sm font-bold text-slate-800 truncate">{rec.name || 'Sin nombre'}</h4>

                                  {/* Description / giro */}
                                  {rec.description && (
                                    <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                                      {truncate(rec.description, 70)}
                                    </p>
                                  )}

                                  {/* Score badge */}
                                  <div className="flex items-center gap-2 mt-2">
                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold
                                      ${rec.score >= 60 ? 'bg-green-100 text-green-700'
                                        : rec.score >= 30 ? 'bg-blue-100 text-blue-700'
                                        : rec.score > 0 ? 'bg-amber-100 text-amber-700'
                                        : 'bg-slate-100 text-slate-500'
                                      }`}>
                                      <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                      </svg>
                                      Score: {rec.score}/100
                                    </span>

                                    {rec.industria_detectada && (
                                      <span className="text-[10px] text-slate-400 truncate max-w-[100px]">
                                        {truncate(rec.industria_detectada, 18)}
                                      </span>
                                    )}
                                  </div>

                                  {/* Location */}
                                  {(rec.city || rec.state) && (
                                    <p className="text-[10px] text-slate-400 mt-1">
                                      {[rec.city, rec.state].filter(Boolean).join(', ')}
                                    </p>
                                  )}

                                  {/* Enrich button */}
                                  <button
                                    onClick={() => handleEnrich(rec)}
                                    disabled={enrichingIds.has(rec._index)}
                                    className={`mt-2.5 w-full py-1.5 rounded-md text-[10px] font-semibold transition-all duration-150
                                      ${enrichingIds.has(rec._index)
                                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 hover:from-blue-100 hover:to-indigo-100 hover:border-blue-300 active:scale-[0.98]'
                                      }`}
                                  >
                                    {enrichingIds.has(rec._index) ? (
                                      <span className="flex items-center justify-center gap-1.5">
                                        <div className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                                        Analizando…
                                      </span>
                                    ) : (
                                      <span className="flex items-center justify-center gap-1.5">
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                        Enriquecer con IA
                                      </span>
                                    )}
                                  </button>

                                  {/* AI Reason */}
                                  {rec.justificacion_ia && (
                                    <div className="mt-2 text-[10px] text-slate-500 italic leading-relaxed bg-slate-50 p-1.5 rounded border border-slate-100">
                                      <span className="not-italic font-semibold text-xs text-slate-600">🤖 IA: </span>
                                      {rec.justificacion_ia}
                                    </div>
                                  )}
                                </div>
                              ))}

                              {/* Discarded column content */}
                              {isDiscarded && (
                                <div className="bg-white rounded-lg border border-slate-200 p-4 text-center">
                                  <div className="mx-auto w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center mb-2 border border-slate-200">
                                    <svg className="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                    </svg>
                                  </div>
                                  <p className="text-sm font-semibold text-slate-500">{count} registro{count !== 1 ? 's' : ''} descartado{count !== 1 ? 's' : ''}</p>
                                  <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                                    Empresas sin relevancia industrial o con keywords de exclusión
                                  </p>
                                  <div className="mt-3 text-left space-y-1">
                                    {[
                                      { label: 'Comercios locales / retail', icon: '🏪' },
                                      { label: 'Servicios no industriales', icon: '🔧' },
                                      { label: 'Sin actividad logística', icon: '📦' },
                                      { label: 'Excluidos por reglas', icon: '🚫' },
                                    ].map(item => (
                                      <div key={item.label} className="flex items-center gap-2 text-[10px] text-slate-400">
                                        <span>{item.icon}</span>
                                        <span>{item.label}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Empty column */}
                              {!isDiscarded && records.length === 0 && (
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                  <svg className="w-8 h-8 text-slate-200 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                                  </svg>
                                  <p className="text-[11px] text-slate-300">Sin registros</p>
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ════════ HISTORY TABLE ════════ */}
      <div className="mt-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Historial de Prospecciones</h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {total} trabajo{total !== 1 ? 's' : ''} realizado{total !== 1 ? 's' : ''}
            </p>
          </div>
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
          >
            <option value="">Todos los estados</option>
            {Object.entries(statusLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 text-sm text-slate-400">
              No hay trabajos de prospección aún. Sube un archivo para comenzar.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Archivo</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">Fecha</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Total</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Prospectos</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Descartados</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Score Prom.</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Tiempo</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(job => (
                    <tr key={job.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-3.5 text-sm font-medium text-slate-900 truncate max-w-[180px]">{job.original_filename}</td>
                      <td className="px-5 py-3.5 text-sm text-slate-500 whitespace-nowrap">
                        {new Date(job.created_at).toLocaleDateString('es-MX', {
                          day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </td>
                      <td className="px-5 py-3.5 text-center text-sm font-mono text-slate-700">{job.total_records}</td>
                      <td className="px-5 py-3.5 text-center text-sm font-mono font-semibold text-green-600">{job.relevant_records}</td>
                      <td className="px-5 py-3.5 text-center text-sm font-mono text-slate-400">{job.filtered_records}</td>
                      <td className="px-5 py-3.5 text-center text-sm font-mono text-slate-600">{job.stats_json?.avg_score ?? '—'}</td>
                      <td className="px-5 py-3.5 text-center text-sm font-mono text-slate-400">{formatTime(job.processing_time)}</td>
                      <td className="px-5 py-3.5 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${statusStyles[job.status] || 'bg-slate-100 text-slate-600'}`}>
                          {statusLabels[job.status] || job.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        {job.status === 'completed' && (
                          <button
                            onClick={() => loadPastJob(job.id)}
                            className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
                          >
                            Ver resultados
                          </button>
                        )}
                        {job.status === 'error' && (
                          <span className="text-xs text-red-400">
                            {job.error_message ? (job.error_message.length > 30 ? job.error_message.slice(0, 30) + '…' : job.error_message) : 'Error'}
                          </span>
                        )}
                        {job.status === 'pending' && <span className="text-xs text-slate-400">—</span>}
                        {job.status === 'processing' && <span className="text-xs text-blue-400">En curso</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {total > 25 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200 bg-slate-50">
              <p className="text-xs text-slate-500">
                {Math.min((page - 1) * 25 + 1, total)}–{Math.min(page * 25, total)} de {total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed bg-white hover:bg-slate-50 transition-colors"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * 25 >= total}
                  className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed bg-white hover:bg-slate-50 transition-colors"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
