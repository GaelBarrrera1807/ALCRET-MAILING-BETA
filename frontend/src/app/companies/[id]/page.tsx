'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { api } from '@/lib/api'
import { useToast } from '@/contexts/ToastContext'
import type { CompanyDetail, CompanyContact } from '@/lib/types'

export default function CompanyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { addToast } = useToast()
  const [company, setCompany] = useState<CompanyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!params.id) return
    setLoading(true)
    api.get<CompanyDetail>(`/companies/${params.id}/`)
      .then((data) => {
        setCompany(data)
        setForm({
          name: data.name,
          business_name: data.business_name,
          rfc: data.rfc,
          description: data.description,
          website: data.website,
          email: data.email,
          phone: data.phone,
          address: data.address,
          city: data.city,
          state: data.state,
          country: data.country,
          postal_code: data.postal_code,
          notes: data.notes,
        })
      })
      .catch(() => {
        addToast('Error al cargar la empresa.', 'error')
        router.push('/companies')
      })
      .finally(() => setLoading(false))
  }, [params.id, addToast, router])

  const handleSave = async () => {
    try {
      const updated = await api.patch<CompanyDetail>(`/companies/${params.id}/`, form)
      setCompany(updated)
      setEditing(false)
      addToast('Empresa actualizada correctamente.', 'success')
    } catch {
      addToast('Error al guardar los cambios.', 'error')
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </DashboardLayout>
    )
  }

  if (!company) return null

  const scoreColor = company.score >= 70 ? 'text-green-600' : company.score >= 40 ? 'text-yellow-600' : 'text-slate-400'
  const priorityColor: Record<string, string> = {
    urgente: 'text-red-600 bg-red-50',
    alta: 'text-orange-600 bg-orange-50',
    media: 'text-blue-600 bg-blue-50',
    baja: 'text-slate-500 bg-slate-50',
  }

  return (
    <DashboardLayout>
      <div className="mb-6">
        <Link href="/companies" className="text-sm text-blue-600 hover:text-blue-800 mb-2 inline-block">
          ← Volver a empresas
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{company.name}</h1>
            <p className="text-slate-500 mt-1">{company.business_name || 'Sin razón social'}</p>
          </div>
          <div className="flex gap-3">
            {editing ? (
              <>
                <button
                  onClick={() => { setEditing(false); setCompany(company) }}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                >
                  Guardar
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Editar
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Información General</h2>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nombre" value={company.name} editable={editing} name="name" form={form} setForm={setForm} />
              <Field label="Razón Social" value={company.business_name} editable={editing} name="business_name" form={form} setForm={setForm} />
              <Field label="RFC" value={company.rfc} editable={editing} name="rfc" form={form} setForm={setForm} />
              <Field label="Sitio Web" value={company.website} editable={editing} name="website" form={form} setForm={setForm} />
              <Field label="Email" value={company.email} editable={editing} name="email" form={form} setForm={setForm} />
              <Field label="Teléfono" value={company.phone} editable={editing} name="phone" form={form} setForm={setForm} />
              <Field label="Ciudad" value={company.city} editable={editing} name="city" form={form} setForm={setForm} />
              <Field label="Estado" value={company.state} editable={editing} name="state" form={form} setForm={setForm} />
              <Field label="País" value={company.country} editable={editing} name="country" form={form} setForm={setForm} />
              <Field label="Código Postal" value={company.postal_code} editable={editing} name="postal_code" form={form} setForm={setForm} />
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-500 mb-1">Descripción</label>
                {editing ? (
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    rows={3}
                  />
                ) : (
                  <p className="text-sm text-slate-700">{company.description || 'Sin descripción'}</p>
                )}
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-500 mb-1">Dirección</label>
                {editing ? (
                  <textarea
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    rows={2}
                  />
                ) : (
                  <p className="text-sm text-slate-700">{company.address || 'Sin dirección'}</p>
                )}
              </div>
            </div>
          </div>

          {company.status === 'analyzed' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Resultado del Análisis (Cerebras AI)</h2>
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Productos Recomendados</p>
                  <div className="flex flex-wrap gap-2">
                    {company.analysis_products.length > 0 ? company.analysis_products.map((p: string) => (
                      <span key={p} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                        {p}
                      </span>
                    )) : <span className="text-sm text-slate-400">Ninguno</span>}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Prioridad</p>
                  <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${priorityColor[company.analysis_priority] || 'text-slate-500 bg-slate-50'}`}>
                    {company.analysis_priority || 'No asignada'}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Resumen del Análisis</p>
                  <p className="text-sm text-slate-700">{company.analysis_summary || 'Sin resumen'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Motivo</p>
                  <p className="text-sm text-slate-700">{company.analysis_reason || 'Sin motivo registrado'}</p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Notas</h2>
            {editing ? (
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                rows={4}
              />
            ) : (
              <p className="text-sm text-slate-700">{company.notes || 'Sin notas'}</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center">
            <p className="text-sm text-slate-500 mb-2">Score</p>
            <p className={`text-4xl font-bold ${scoreColor}`}>{company.score}</p>
            <p className="text-xs text-slate-400 mt-2">
              {company.status === 'analyzed' ? 'Analizado por Cerebras' : company.status === 'pending' ? 'Pendiente' : company.status === 'error' ? 'Error' : 'Analizando...'}
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="text-sm font-semibold text-slate-500 uppercase mb-3">Clasificación</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-400">Sector Detectado</p>
                <p className="text-sm font-medium text-slate-700">{company.detected_sector || company.sector_name || 'No detectado'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Es Cliente</p>
                <p className="text-sm font-medium text-slate-700">{company.is_client ? 'Sí' : 'No'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Es Lead</p>
                <p className="text-sm font-medium text-slate-700">{company.is_lead ? 'Sí' : 'No'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Origen</p>
                <p className="text-sm font-medium text-slate-700">{company.source || 'Desconocido'}</p>
              </div>
            </div>
          </div>

          {company.contacts.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase mb-3">Contactos ({company.contacts.length})</h3>
              <div className="space-y-3">
                {company.contacts.map((contact: CompanyContact) => (
                  <div key={contact.id} className="text-sm">
                    <p className="font-medium text-slate-700">{contact.name}</p>
                    {contact.position && <p className="text-xs text-slate-400">{contact.position}</p>}
                    {contact.email && <p className="text-xs text-slate-400">{contact.email}</p>}
                    {contact.phone && <p className="text-xs text-slate-400">{contact.phone}</p>}
                    {contact.is_primary && <span className="text-xs text-blue-600 font-medium">Principal</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

function Field({
  label, value, editable, name, form, setForm,
}: {
  label: string
  value: string
  editable: boolean
  name: string
  form: Record<string, string>
  setForm: (f: Record<string, string>) => void
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-500 mb-1">{label}</label>
      {editable ? (
        <input
          type="text"
          value={form[name] || ''}
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
        />
      ) : (
        <p className="text-sm text-slate-700">{value || '-'}</p>
      )}
    </div>
  )
}
