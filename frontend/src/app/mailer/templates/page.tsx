'use client'

import { useEffect, useState, useCallback } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import TemplateEditor from '@/components/mailer/TemplateEditor'
import TemplatePreview from '@/components/mailer/TemplatePreview'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate, previewTemplate } from '@/lib/mailer-api'
import { useToast } from '@/contexts/ToastContext'
import type { EmailTemplate, PaginatedResponse } from '@/lib/types'

const TEMPLATE_TYPES = [
  { value: 'cold_outreach', label: 'Prospección en Frío' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'follow_up', label: 'Seguimiento' },
  { value: 'newsletter', label: 'Boletín' },
  { value: 'welcome', label: 'Bienvenida' },
  { value: 'custom', label: 'Personalizada' },
]

const DEFAULT_VARIABLES = ['first_name', 'company', 'sector']

interface FormData {
  name: string
  template_type: string
  subject: string
  body_html: string
  variables: string[]
}

const emptyForm: FormData = {
  name: '',
  template_type: 'cold_outreach',
  subject: '',
  body_html: '',
  variables: [...DEFAULT_VARIABLES],
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EmailTemplate | null>(null)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [previewHtml, setPreviewHtml] = useState('')
  const [previewContext, setPreviewContext] = useState<Record<string, string>>({
    first_name: 'Juan',
    company: 'Empresa Ejemplo',
    sector: 'Tecnología',
  })
  const { addToast } = useToast()

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getTemplates()
      setTemplates(data.results)
    } catch {
      addToast('Error al cargar plantillas', 'error')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    fetchTemplates()
  }, [fetchTemplates])

  const openCreate = () => {
    setEditing(null)
    setForm(emptyForm)
    setPreviewHtml('')
    setShowForm(true)
  }

  const openEdit = (t: EmailTemplate) => {
    setEditing(t)
    setForm({
      name: t.name,
      template_type: t.template_type,
      subject: t.subject,
      body_html: t.body_html,
      variables: t.variables.length > 0 ? t.variables : DEFAULT_VARIABLES,
    })
    setPreviewHtml(t.body_html)
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.subject.trim() || !form.body_html.trim()) {
      addToast('Nombre, asunto y cuerpo son obligatorios', 'error')
      return
    }
    setSaving(true)
    try {
      if (editing) {
        await updateTemplate(editing.id, form)
        addToast('Plantilla actualizada', 'success')
      } else {
        await createTemplate(form)
        addToast('Plantilla creada', 'success')
      }
      setShowForm(false)
      fetchTemplates()
    } catch {
      addToast('Error al guardar la plantilla', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar esta plantilla?')) return
    try {
      await deleteTemplate(id)
      addToast('Plantilla eliminada', 'success')
      fetchTemplates()
    } catch {
      addToast('Error al eliminar', 'error')
    }
  }

  const handlePreview = async () => {
    if (!editing) {
      setPreviewHtml(form.body_html)
      return
    }
    try {
      const result = await previewTemplate(editing.id, previewContext)
      setPreviewHtml(result.body_html)
    } catch {
      setPreviewHtml(form.body_html)
    }
  }

  useEffect(() => {
    if (showForm) handlePreview()
  }, [showForm, form.body_html])

  const typeLabel = (v: string) => TEMPLATE_TYPES.find((t) => t.value === v)?.label || v

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Plantillas</h1>
          <p className="text-slate-500 mt-1">{templates.length} plantillas</p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Nueva Plantilla
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-10 pb-10 bg-black/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{editing ? 'Editar Plantilla' : 'Nueva Plantilla'}</h2>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600 text-xl">✕</button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Nombre de la plantilla"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                  <select
                    value={form.template_type}
                    onChange={(e) => setForm({ ...form, template_type: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {TEMPLATE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Asunto</label>
                <input
                  value={form.subject}
                  onChange={(e) => setForm({ ...form, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Asunto del correo"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Cuerpo (HTML)</label>
                <TemplateEditor
                  value={form.body_html}
                  onChange={(v) => setForm({ ...form, body_html: v })}
                  variables={form.variables}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Vista previa</label>
                <div className="flex gap-2 mb-2 flex-wrap">
                  {Object.entries(previewContext).map(([k, v]) => (
                    <label key={k} className="text-xs text-slate-500 flex items-center gap-1">
                      <span className="font-mono">{k}:</span>
                      <input
                        value={v}
                        onChange={(e) => setPreviewContext({ ...previewContext, [k]: e.target.value })}
                        className="w-28 px-2 py-0.5 border border-slate-200 rounded text-xs"
                      />
                    </label>
                  ))}
                </div>
                <TemplatePreview html={form.body_html} context={previewContext} />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Guardando...' : editing ? 'Actualizar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">Tipo</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Usos</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Activa</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {templates.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-400">
                    No hay plantillas. Crea tu primera plantilla.
                  </td>
                </tr>
              ) : (
                templates.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{t.name}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{typeLabel(t.template_type)}</td>
                    <td className="px-6 py-4 text-center text-sm text-slate-600">{t.use_count}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${t.is_active ? 'bg-green-500' : 'bg-slate-300'}`} />
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => openEdit(t)}
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="text-sm text-red-500 hover:text-red-700 font-medium"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </DashboardLayout>
  )
}
