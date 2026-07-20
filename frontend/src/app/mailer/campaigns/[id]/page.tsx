'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import CampaignStatusBadge from '@/components/mailer/CampaignStatusBadge'
import CampaignStatsCards from '@/components/mailer/CampaignStatsCards'
import TemplatePreview from '@/components/mailer/TemplatePreview'
import {
  getCampaign,
  updateCampaign,
  sendCampaign,
  getCampaignStats,
} from '@/lib/mailer-api'
import { useToast } from '@/contexts/ToastContext'
import type { EmailCampaign, CampaignStats } from '@/lib/types'

const SOURCE_FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'internal', label: 'Internos' },
  { value: 'external', label: 'Externos' },
  { value: 'manual', label: 'Manual' },
]

export default function CampaignDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { addToast } = useToast()

  const [campaign, setCampaign] = useState<EmailCampaign | null>(null)
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [saving, setSaving] = useState(false)
  const [showSendConfirm, setShowSendConfirm] = useState(false)
  const [sending, setSending] = useState(false)

  const previewContext = {
    first_name: 'Juan',
    company: 'Empresa Ejemplo',
    sector: 'Tecnología',
  }

  const fetchData = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        getCampaign(id),
        getCampaignStats(id).catch(() => null),
      ])
      setCampaign(c)
      setStats(s)
      setSubject(c.subject)
      setBodyHtml(c.body_html)
      setSourceFilter(c.source_filter)
    } catch {
      addToast('Error al cargar la campaña', 'error')
    } finally {
      setLoading(false)
    }
  }, [id, addToast])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateCampaign(id, { subject, body_html: bodyHtml, source_filter: sourceFilter })
      setEditing(false)
      addToast('Campaña actualizada', 'success')
      fetchData()
    } catch {
      addToast('Error al guardar', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleSend = async () => {
    setSending(true)
    try {
      await sendCampaign(id)
      addToast('Campaña enviada correctamente', 'success')
      setShowSendConfirm(false)
      fetchData()
    } catch {
      addToast('Error al enviar la campaña', 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <DashboardLayout>
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : !campaign ? (
        <p className="text-slate-500">Campaña no encontrada</p>
      ) : (
        <>
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <Link href="/mailer/campaigns" className="text-sm text-slate-400 hover:text-slate-600">Campañas</Link>
                <span className="text-slate-300">/</span>
                <h1 className="text-2xl font-bold text-slate-900">{campaign.name}</h1>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <CampaignStatusBadge status={campaign.status} />
                {campaign.template_name && (
                  <span className="text-sm text-slate-500">
                    Plantilla: {campaign.template_name}
                  </span>
                )}
              </div>
            </div>
            {campaign.status === 'draft' && (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (editing) handleSave()
                    else setEditing(true)
                  }}
                  disabled={saving}
                  className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : editing ? 'Guardar' : 'Editar'}
                </button>
                <button
                  onClick={() => setShowSendConfirm(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Enviar
                </button>
              </div>
            )}
          </div>

          {/* Stats */}
          {stats && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-3">Estadísticas</h2>
              <CampaignStatsCards stats={stats} />
            </div>
          )}

          {editing ? (
            /* Edit mode */
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6 space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">Editar Campaña</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Asunto</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Filtrar destinatarios</label>
                  <select
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    {SOURCE_FILTERS.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Cuerpo (HTML)</label>
                <textarea
                  value={bodyHtml}
                  onChange={(e) => setBodyHtml(e.target.value)}
                  className="w-full h-48 px-4 py-3 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Vista previa</label>
                <TemplatePreview html={bodyHtml} context={previewContext} />
              </div>
            </div>
          ) : (
            /* View mode */
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Detalles</h2>
                <dl className="space-y-3">
                  <div className="flex justify-between">
                    <dt className="text-sm text-slate-500">Asunto</dt>
                    <dd className="text-sm text-slate-900 font-medium">{campaign.subject || '(sin asunto)'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm text-slate-500">Filtro</dt>
                    <dd className="text-sm text-slate-900 font-medium capitalize">{campaign.source_filter}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm text-slate-500">Destinatarios</dt>
                    <dd className="text-sm text-slate-900 font-medium">{campaign.total_recipients}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm text-slate-500">Creada</dt>
                    <dd className="text-sm text-slate-900 font-medium">
                      {new Date(campaign.created_at).toLocaleString()}
                    </dd>
                  </div>
                  {campaign.sent_at && (
                    <div className="flex justify-between">
                      <dt className="text-sm text-slate-500">Enviada</dt>
                      <dd className="text-sm text-slate-900 font-medium">
                        {new Date(campaign.sent_at).toLocaleString()}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Vista previa</h2>
                <TemplatePreview html={campaign.body_html} context={previewContext} />
              </div>
            </div>
          )}

          {/* Send confirmation modal */}
          {showSendConfirm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
                <h2 className="text-lg font-semibold mb-2">¿Enviar campaña?</h2>
                <p className="text-sm text-slate-600 mb-6">
                  Se enviará a <strong>{campaign.total_recipients}</strong> destinatarios.
                  {campaign.source_filter !== 'all' && (
                    <> Filtro: <strong>{campaign.source_filter}</strong>.</>
                  )}
                  Esta acción no se puede deshacer.
                </p>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setShowSendConfirm(false)}
                    className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleSend}
                    disabled={sending}
                    className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {sending ? 'Enviando...' : 'Confirmar envío'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </DashboardLayout>
  )
}
