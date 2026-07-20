'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { getCampaigns } from '@/lib/mailer-api'
import type { EmailCampaign } from '@/lib/types'

export default function MailerDashboardPage() {
  const [campaigns, setCampaigns] = useState<EmailCampaign[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCampaigns()
      .then((data) => setCampaigns(data.results))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const totalSent = campaigns.reduce((s, c) => s + c.sent_count, 0)
  const totalOpens = campaigns.reduce((s, c) => s + c.open_count, 0)
  const totalClicks = campaigns.reduce((s, c) => s + c.click_count, 0)
  const openRate = totalSent > 0 ? ((totalOpens / totalSent) * 100).toFixed(1) : '0.0'
  const clickRate = totalSent > 0 ? ((totalClicks / totalSent) * 100).toFixed(1) : '0.0'

  const StatCard = ({ label, value, color }: { label: string; value: string | number; color: string }) => (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <p className="text-sm text-slate-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  )

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-600',
      scheduled: 'bg-blue-100 text-blue-800',
      sending: 'bg-yellow-100 text-yellow-800',
      sent: 'bg-green-100 text-green-800',
      paused: 'bg-orange-100 text-orange-800',
      cancelled: 'bg-red-100 text-red-800',
    }
    const labels: Record<string, string> = {
      draft: 'Borrador',
      scheduled: 'Programada',
      sending: 'Enviando',
      sent: 'Enviada',
      paused: 'Pausada',
      cancelled: 'Cancelada',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-slate-100'}`}>
        {labels[status] || status}
      </span>
    )
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Email Marketing</h1>
          <p className="text-slate-500 mt-1">Campañas de correo electrónico</p>
        </div>
        <Link
          href="/mailer/campaigns"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Nueva Campaña
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Campañas" value={campaigns.length} color="text-slate-900" />
            <StatCard label="Emails Enviados" value={totalSent} color="text-blue-600" />
            <StatCard label="Tasa Apertura" value={`${openRate}%`} color="text-green-600" />
            <StatCard label="Tasa Clicks" value={`${clickRate}%`} color="text-purple-600" />
          </div>

          <nav className="flex gap-3 mb-8">
            <Link
              href="/mailer/templates"
              className="px-5 py-3 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors flex-1 text-center"
            >
              <p className="text-lg font-bold text-slate-900">📄</p>
              <p className="text-sm font-medium text-slate-700 mt-1">Plantillas</p>
            </Link>
            <Link
              href="/mailer/recipients"
              className="px-5 py-3 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors flex-1 text-center"
            >
              <p className="text-lg font-bold text-slate-900">👥</p>
              <p className="text-sm font-medium text-slate-700 mt-1">Destinatarios</p>
            </Link>
            <Link
              href="/mailer/campaigns"
              className="px-5 py-3 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors flex-1 text-center"
            >
              <p className="text-lg font-bold text-slate-900">📨</p>
              <p className="text-sm font-medium text-slate-700 mt-1">Campañas</p>
            </Link>
          </nav>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-900">Campañas Recientes</h2>
            </div>
            {campaigns.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                No hay campañas aún. Crea tu primera campaña de email marketing.
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Estado</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Enviados</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Aperturas</th>
                    <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => (
                    <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <Link href={`/mailer/campaigns/${c.id}`} className="font-medium text-slate-900 hover:text-blue-600">
                          {c.name}
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-center">{statusBadge(c.status)}</td>
                      <td className="px-6 py-4 text-center text-sm text-slate-600">{c.sent_count}</td>
                      <td className="px-6 py-4 text-center text-sm text-slate-600">{c.open_count}</td>
                      <td className="px-6 py-4 text-center text-sm text-slate-600">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </DashboardLayout>
  )
}
