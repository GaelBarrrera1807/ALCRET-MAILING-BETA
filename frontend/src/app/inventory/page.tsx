'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import RichTemplateEditor from '@/components/mailer/RichTemplateEditor'
import TemplatePreview from '@/components/mailer/TemplatePreview'
import { getInventoryItems } from '@/lib/inventory-api'
import { useToast } from '@/contexts/ToastContext'
import type { InventoryItem, PaginatedResponse } from '@/lib/types'

const UNIT_VARIABLES = [
  'sku_o_vin',
  'nombre_unidad',
  'almacen_id',
  'producto_id',
  'cantidad_disponible',
  'tipo_movimiento',
]

const MAX_ITEMS = 2000

const DEFAULT_BODY = `
<h2>Ficha de la unidad</h2>
<p><strong>Unidad:</strong> {{ nombre_unidad }}</p>
<p><strong>VIN/SKU:</strong> {{ sku_o_vin }}</p>
<p><strong>Almacén:</strong> {{ almacen_id }}</p>
<p><strong>Producto:</strong> {{ producto_id }}</p>
<p><strong>Cantidad disponible:</strong> {{ cantidad_disponible }}</p>
<p><strong>Tipo de movimiento:</strong> {{ tipo_movimiento }}</p>
<p><em>Atentamente,<br>Equipo Comercial</em></p>
`

function unitContext(item: InventoryItem): Record<string, string> {
  return {
    sku_o_vin: item.sku_o_vin || '-',
    nombre_unidad: item.nombre_unidad || '-',
    almacen_id: item.almacen_id || '-',
    producto_id: item.producto_id || '-',
    cantidad_disponible: String(item.cantidad_disponible),
    tipo_movimiento: item.tipo_movimiento || '-',
  }
}

function formatDate(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<InventoryItem | null>(null)
  const [recipient, setRecipient] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [context, setContext] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const { addToast } = useToast()

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setItems([])
    try {
      const all: InventoryItem[] = []
      let page = 1
      for (;;) {
        const data: PaginatedResponse<InventoryItem> = await getInventoryItems({ page: String(page) })
        all.push(...data.results)
        if (all.length >= MAX_ITEMS || !data.next) break
        page += 1
      }
      setItems(all.slice(0, MAX_ITEMS))
    } catch {
      addToast('Error al cargar el inventario', 'error')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter((it) =>
      [it.nombre_unidad, it.sku_o_vin, it.almacen_id, it.producto_id, it.tipo_movimiento]
        .some((v) => (v || '').toLowerCase().includes(q))
    )
  }, [items, search])

  const openSheet = useCallback((item: InventoryItem) => {
    setSelected(item)
    setContext(unitContext(item))
    setSubject(item.sku_o_vin ? `Ficha ${item.nombre_unidad || item.sku_o_vin}` : 'Ficha de la unidad')
    setBody(DEFAULT_BODY)
    setRecipient('')
  }, [])

  const handleSend = () => {
    const email = recipient.trim()
    if (!email) {
      addToast('Ingresa el correo del destinatario', 'error')
      return
    }
    const previewContext = unitContext(selected as InventoryItem)
    let text = body
    for (const [k, v] of Object.entries(previewContext)) {
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
    addToast('Abriendo cliente de correo con la ficha', 'success')
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Inventario</h1>
          <p className="text-slate-500 mt-1">{items.length} unidades sincronizadas</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por unidad, VIN/SKU, almacén o producto..."
          className="px-4 py-2 border border-slate-300 rounded-lg text-sm w-full max-w-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
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
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Unidad</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">VIN/SKU</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Almacén</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Producto</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Cantidad</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Movimiento</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Actualizado</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400">
                    No hay unidades en el inventario.
                  </td>
                </tr>
              ) : (
                filtered.map((it) => (
                  <tr key={it.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{it.nombre_unidad || '-'}</td>
                    <td className="px-6 py-4">
                      {it.sku_o_vin ? (
                        <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-xs border border-slate-200">
                          {it.sku_o_vin}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-sm">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{it.almacen_id || '-'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{it.producto_id || '-'}</td>
                    <td className="px-6 py-4 text-center text-sm text-slate-700 font-medium">
                      {it.cantidad_disponible}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{it.tipo_movimiento || '-'}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">{formatDate(it.updated_at)}</td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => openSheet(it)}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium whitespace-nowrap"
                      >
                        Enviar Ficha
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-10 pb-10 bg-black/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Enviar Ficha por Correo</h2>
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
                <RichTemplateEditor
                  value={body}
                  onChange={setBody}
                  variables={UNIT_VARIABLES}
                />
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
                {sending ? 'Abriendo...' : 'Enviar Ficha'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}