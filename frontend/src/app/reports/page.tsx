'use client'

import { useEffect, useState, useCallback } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import type { Report, PaginatedResponse } from '@/lib/types'

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [form, setForm] = useState({ title: '', report_type: 'leads', file_type: 'pdf' })

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<PaginatedResponse<Report>>('/reports/')
      setReports(data.results)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  const generateReport = async () => {
    if (!form.title) return
    setGenerating(true)
    try {
      await api.post('/reports/', form)
      setForm({ title: '', report_type: 'leads', file_type: 'pdf' })
      fetchReports()
    } catch (err) {
      console.error(err)
      alert('Error al generar reporte')
    } finally {
      setGenerating(false)
    }
  }

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      generating: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
    }
    const labels: Record<string, string> = {
      generating: 'Generando',
      completed: 'Completado',
      error: 'Error',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || ''}`}>
        {labels[status] || status}
      </span>
    )
  }

  const reportTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      leads: 'Leads',
      scoring: 'Scoring',
      commercial: 'Comercial',
      processing: 'Procesamiento',
      custom: 'Personalizado',
    }
    return labels[type] || type
  }

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Reportes</h1>
        <p className="text-slate-500 mt-1">Genera y descarga reportes de prospección</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Generar Reporte</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Título</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Nombre del reporte"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                <select
                  value={form.report_type}
                  onChange={(e) => setForm((f) => ({ ...f, report_type: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg"
                >
                  <option value="leads">Reporte de Leads</option>
                  <option value="scoring">Reporte de Scoring</option>
                  <option value="commercial">Métricas Comerciales</option>
                  <option value="processing">Procesamiento</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Formato</label>
                <select
                  value={form.file_type}
                  onChange={(e) => setForm((f) => ({ ...f, file_type: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg"
                >
                  <option value="pdf">PDF</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
              <button
                onClick={generateReport}
                disabled={generating || !form.title}
                className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {generating ? 'Generando...' : 'Generar reporte'}
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <h2 className="text-lg font-semibold text-slate-900 px-6 py-4 border-b border-slate-200">
              Reportes Generados
            </h2>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : reports.length === 0 ? (
              <p className="text-center py-12 text-slate-400">No hay reportes generados aún</p>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Título</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Tipo</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <tr key={report.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <p className="font-medium text-slate-900">{report.title}</p>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {reportTypeLabel(report.report_type)}
                      </td>
                      <td className="px-6 py-4 text-center">{statusBadge(report.status)}</td>
                      <td className="px-6 py-4 text-center text-sm text-slate-600">
                        {new Date(report.created_at).toLocaleDateString('es-MX')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
