'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import type { DashboardSummary } from '@/lib/types'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<DashboardSummary>('/summary/')
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const StatCard = ({ label, value, color }: { label: string; value: string | number; color: string }) => (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <p className="text-sm text-slate-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  )

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">Resumen general de tu prospección industrial</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Empresas" value={data.total_companies} color="text-slate-900" />
            <StatCard label="Analizadas" value={data.total_analyzed} color="text-green-600" />
            <StatCard label="Leads" value={data.total_leads} color="text-blue-600" />
            <StatCard label="Score Promedio" value={data.avg_score.toFixed(1)} color="text-purple-600" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Empresas por Sector</h2>
              {data.by_sector.length > 0 ? (
                <div className="space-y-3">
                  {data.by_sector.slice(0, 8).map((item) => (
                    <div key={item.detected_sector} className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">{item.detected_sector || 'Sin sector'}</span>
                      <span className="text-sm font-semibold text-slate-900">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No hay datos suficientes</p>
              )}
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Leads por Prioridad</h2>
              {data.by_priority.length > 0 ? (
                <div className="space-y-3">
                  {data.by_priority.map((item) => (
                    <div key={item.priority} className="flex items-center justify-between">
                      <span className="text-sm text-slate-600 capitalize">{item.priority}</span>
                      <span className="text-sm font-semibold text-slate-900">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No hay datos suficientes</p>
              )}
            </div>
          </div>
        </>
      ) : (
        <p className="text-slate-500">Error al cargar datos del dashboard</p>
      )}
    </DashboardLayout>
  )
}
