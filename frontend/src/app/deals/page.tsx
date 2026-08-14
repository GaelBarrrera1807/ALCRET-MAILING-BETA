'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import RichTemplateEditor from '@/components/mailer/RichTemplateEditor'
import TemplatePreview from '@/components/mailer/TemplatePreview'
import { getLeads, updateLeadStage } from '@/lib/leads-api'
import { useToast } from '@/contexts/ToastContext'
import { Mail, User } from 'lucide-react'
import type { Lead, PaginatedResponse } from '@/lib/types'

const MAX_LEADS = 2000

const STAGES = [
  { value: 'nuevo_lead', label: 'Nuevo Lead', dot: 'bg-slate-400' },
  { value: 'cotizacion_enviada', label: 'Cotización Enviada', dot: 'bg-blue-500' },
  { value: 'mesa_credito', label: 'Expediente / Mesa de Crédito', dot: 'bg-amber-500' },
  { value: 'credito_aprobado', label: 'Crédito Aprobado', dot: 'bg-purple-500' },
  { value: 'ganado', label: 'Venta / Entrega Completada', dot: 'bg-green-500' },
  { value: 'perdido', label: 'Perdido / Rechazado', dot: 'bg-red-500' },
]

const DEAL_VARIABLES = [
  'contact_name',
  'company_name',
  'sector',
  'unidad_interes',
  'monto_total',
  'esquema',
  'last_email_interaction',
]

const DEFAULT_BODY = `
<p>Estimado(a) <strong>{{ contact_name }}</strong>,</p>
<p>Damos seguimiento a la oportunidad de <strong>{{ unidad_interes }}</strong> para <strong>{{ company_name }}</strong>.</p>
<br>
<p><strong>Unidad de interés:</strong> {{ unidad_interes }}</p>
<p><strong>Monto total de la operación:</strong> {{ monto_total }}</p>
<p><strong>Esquema:</strong> {{ esquema }}</p>
<p><strong>Última interacción:</strong> {{ last_email_interaction }}</p>
<br>
<p>Quedamos atentos a cualquier duda.</p>
<p>Atentamente,<br>Equipo Comercial</p>
`

function formatMoney(value: string | null | undefined) {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  if (Number.isNaN(n)) return value
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  }).format(n)
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return null
  return new Date(iso).toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function dealContext(lead: Lead): Record<string, string> {
  return {
    contact_name: lead.contact_name || 'Sr./Sra.',
    company_name: lead.company_name || '-',
    sector: lead.detected_sector || '-',
    unidad_interes: lead.unidad_interes || '-',
    monto_total: formatMoney(lead.monto_total) || '-',
    esquema: lead.esquema_display || lead.esquema || '-',
    last_email_interaction: formatDate(lead.last_email_interaction) || '-',
  }
}

export default function DealsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Lead | null>(null)
  const [recipient, setRecipient] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [context, setContext] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const { addToast } = useToast()

  const fetchLeads = useCallback(async () => {
    setLoading(true)
    setLeads([])
    try {
      const all: Lead[] = []
      let page = 1
      for (;;) {
        const data: PaginatedResponse<Lead> = await getLeads({ page: String(page) })
        all.push(...data.results)
        if (all.length >= MAX_LEADS || !data.next) break
        page += 1
      }
      setLeads(all.slice(0, MAX_LEADS))
    } catch {
      addToast('Error al cargar el pipeline', 'error')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    fetchLeads()
  }, [fetchLeads])

  const byStage = useMemo(() => {
    const map = new Map<string, Lead[]>()
    for (const s of STAGES) map.set(s.value, [])
    for (const lead of leads) {
      const list = map.get(lead.stage)
      if (list) list.push(lead)
      else map.get('nuevo_lead')?.push(lead)
    }
    return map
  }, [leads])

  const handleMove = async (id: string, from: string, to: string) => {
    if (from === to) return
    const prev = leads
    setLeads((cur) => cur.map((l) => (l.id === id ? { ...l, stage: to } : l)))
    try {
      const updated = await updateLeadStage(id, to)
      setLeads((cur) => cur.map((l) => (l.id === id ? { ...l, stage: updated.stage } : l)))
      addToast('Etapa actualizada', 'success')
    } catch {
      setLeads(prev)
      addToast('Error al actualizar la etapa', 'error')
    }
  }

  const onDragStart = (e: React.DragEvent, id: string) => {
    setDraggingId(id)
    e.dataTransfer.setData('text/plain', id)
    e.dataTransfer.effectAllowed = 'move'
  }

  const onDrop = (e: React.DragEvent, stage: string) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('text/plain')
    const lead = leads.find((l) => l.id === id)
    setDraggingId(null)
    if (lead) handleMove(id, lead.stage, stage)
  }

  const openEmail = (lead: Lead) => {
    setSelected(lead)
    setContext(dealContext(lead))
    setRecipient(lead.contact_email || '')
    setSubject(lead.company_name ? `Seguimiento - ${lead.company_name}` : 'Seguimiento')
    setBody(DEFAULT_BODY)
  }

  const handleSend = () => {
    const email = recipient.trim()
    if (!email) {
      addToast('Ingresa el correo del destinatario', 'error')
      return
    }
    const ctx = dealContext(selected as Lead)
    let text = body
    for (const [k, v] of Object.entries(ctx)) {
      text = text.replaceAll(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'gi'), v)
    }
    const plain = text
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n')
      .replace(/<\/h[1-6]>/gi, '\n')
      .replace(/<\/tr>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .replace(/&nbsp;/gi, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
    const mailto = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(plain)}`
    setSending(true)
    window.location.href = mailto
    setSending(false)
    setSelected(null)
    addToast('Abriendo cliente de correo con el seguimiento', 'success')
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pipeline de Ventas</h1>
          <p className="text-slate-500 mt-1">{leads.length} oportunidades</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STAGES.map((stage) => {
            const cards = byStage.get(stage.value) || []
            return (
              <div
                key={stage.value}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => onDrop(e, stage.value)}
                className={`w-72 shrink-0 flex flex-col rounded-xl bg-slate-200/60 border border-slate-200 min-h-[60vh] ${
                  draggingId ? 'ring-2 ring-blue-200' : ''
                }`}
              >
                <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
                  <span className={`w-2.5 h-2.5 rounded-full ${stage.dot}`} />
                  <span className="text-sm font-semibold text-slate-800 flex-1">{stage.label}</span>
                  <span className="text-xs font-medium text-slate-400 bg-white border border-slate-200 rounded-full px-2 py-0.5">
                    {cards.length}
                  </span>
                </div>
                <div className="flex-1 p-3 space-y-3 overflow-y-auto max-h-[75vh]">
                  {cards.length === 0 ? (
                    <div className="text-center text-xs text-slate-400 py-8">Sin oportunidades</div>
                  ) : (
                    cards.map((lead) => (
                      <div
                        key={lead.id}
                        draggable
                        onDragStart={(e) => onDragStart(e, lead.id)}
                        onDragEnd={() => setDraggingId(null)}
                        className={`bg-white rounded-lg shadow-sm border border-slate-200 p-4 hover:shadow-md cursor-grab active:cursor-grabbing transition-shadow ${
                          draggingId === lead.id ? 'opacity-40' : ''
                        }`}
                      >
                        <Link
                          href={`/leads/${lead.id}`}
                          className="block font-semibold text-slate-900 text-sm hover:text-blue-600"
                        >
                          {lead.company_name || 'Sin empresa'}
                        </Link>
                        {lead.unidad_interes && (
                          <p className="text-xs text-slate-500 mt-1">{lead.unidad_interes}</p>
                        )}
                        <div className="flex items-center gap-2 mt-3">
                          <span className="text-sm font-bold text-slate-800">
                            {formatMoney(lead.monto_total) || '—'}
                          </span>
                          {lead.esquema_display && (
                            <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs">
                              {lead.esquema_display}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <User size={14} />
                            {lead.assigned_to_name || 'Sin vendedor'}
                          </span>
                          {lead.last_email_interaction && (
                            <span className="flex items-center gap-1 text-slate-400">
                              <Mail size={14} />
                              {formatDate(lead.last_email_interaction)}
                            </span>
                          )}
                        </div>
                        <div className="mt-3 pt-3 border-t border-slate-100">
                          <button
                            onClick={() => openEmail(lead)}
                            className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg border border-blue-200 hover:bg-blue-100 transition-colors"
                          >
                            <Mail size={14} />
                            Enviar Correo de Seguimiento
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-10 pb-10 bg-black/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Enviar Correo de Seguimiento</h2>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600 text-xl">✕</button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Para (correo)</label>
                  <input
                    value={recipient}
                    onChange={(e) => setRecipient(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="correo@empresa.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Asunto</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Cuerpo</label>
                <RichTemplateEditor value={body} onChange={setBody} variables={DEAL_VARIABLES} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Vista previa</label>
                <TemplatePreview html={body} context={context} />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setSelected(null)}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSend}
                disabled={sending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {sending ? 'Abriendo...' : 'Enviar Seguimiento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}