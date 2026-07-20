'use client'

import { useState, useRef } from 'react'
import dynamic from 'next/dynamic'
import { uploadTemplateImage } from '@/lib/mailer-api'

const RichTemplateEditor = dynamic(
  () => import('./RichTemplateEditor'),
  { ssr: false, loading: () => <div className="h-64 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-center text-sm text-slate-400">Cargando editor...</div> }
)

interface TemplateEditorProps {
  value: string
  onChange: (value: string) => void
  variables: string[]
}

export default function TemplateEditor({ value, onChange, variables }: TemplateEditorProps) {
  const [showHtml, setShowHtml] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showImageModal, setShowImageModal] = useState(false)
  const [imageTab, setImageTab] = useState<'upload' | 'url'>('upload')
  const [uploading, setUploading] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [altInput, setAltInput] = useState('')
  const [error, setError] = useState('')

  const insertAtCursor = (text: string) => {
    const textarea = textareaRef.current
    if (!textarea) return
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = value.slice(0, start)
    const after = value.slice(end)
    const newValue = before + text + after
    onChange(newValue)
    requestAnimationFrame(() => {
      textarea.focus()
      const cursorPos = start + text.length
      textarea.setSelectionRange(cursorPos, cursorPos)
    })
  }

  const insertVariable = (variable: string) => {
    insertAtCursor(`{{ ${variable} }}`)
  }

  const insertImage = (src: string, alt: string) => {
    const altAttr = alt ? ` alt="${alt.replace(/"/g, '&quot;')}"` : ''
    const imgTag = `<img src="${src}"${altAttr} style="max-width:600px;height:auto;" />`
    insertAtCursor(imgTag)
    setShowImageModal(false)
    setUrlInput('')
    setAltInput('')
    setError('')
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) { setError('Solo se permiten archivos de imagen'); return }
    if (file.size > 10 * 1024 * 1024) { setError('La imagen no debe superar los 10MB'); return }
    setUploading(true); setError('')
    try {
      const result = await uploadTemplateImage(file, altInput)
      insertImage(result.url, altInput || file.name)
    } catch { setError('Error al subir la imagen') }
    finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = '' }
  }

  const handleUrlInsert = () => {
    const trimmed = urlInput.trim()
    if (!trimmed) { setError('Ingresa una URL de imagen'); return }
    insertImage(trimmed, altInput)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {showHtml && (
            <div className="flex flex-wrap items-center gap-1.5">
              {variables.map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => insertVariable(v)}
                  className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded border border-blue-200 hover:bg-blue-100 font-mono"
                >{`{{ ${v} }}`}</button>
              ))}
              <span className="w-px h-5 bg-slate-300 mx-1" />
              <button
                type="button"
                onClick={() => setShowImageModal(true)}
                className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded border border-green-200 hover:bg-green-100"
              >🖼 Insertar imagen</button>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setShowHtml(!showHtml)}
          className={`text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
            showHtml
              ? 'text-blue-600 bg-blue-50 border-blue-200 hover:bg-blue-100'
              : 'text-slate-500 bg-slate-50 border-slate-200 hover:bg-slate-100'
          }`}
        >
          {showHtml ? 'Volver al Editor Visual' : 'Ver HTML'}
        </button>
      </div>

      {showHtml ? (
        <>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full h-64 px-4 py-3 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
            placeholder="Escribe el HTML del template aquí..."
          />

          {showImageModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
              <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-800">Insertar imagen</h3>
                  <button type="button" onClick={() => { setShowImageModal(false); setError(''); setUrlInput(''); setAltInput('') }} className="text-slate-400 hover:text-slate-600 text-xl leading-none">&times;</button>
                </div>
                <div className="flex border-b border-slate-200 mb-4">
                  <button type="button" onClick={() => setImageTab('upload')} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${imageTab === 'upload' ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>Subir archivo</button>
                  <button type="button" onClick={() => setImageTab('url')} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${imageTab === 'url' ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>Pegar URL</button>
                </div>
                {imageTab === 'upload' ? (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Texto alternativo</label>
                      <input type="text" value={altInput} onChange={(e) => setAltInput(e.target.value)} placeholder="Descripción de la imagen (opcional)" className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" id="image-upload-input-legacy" />
                      <label htmlFor="image-upload-input-legacy" className="cursor-pointer flex flex-col items-center gap-2">
                        <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        <span className="text-sm text-slate-500">{uploading ? 'Subiendo...' : 'Haz clic para seleccionar una imagen'}</span>
                        <span className="text-xs text-slate-400">PNG, JPG, GIF hasta 10MB</span>
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">URL de la imagen</label>
                      <input type="url" value={urlInput} onChange={(e) => setUrlInput(e.target.value)} placeholder="https://ejemplo.com/imagen.jpg" className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Texto alternativo</label>
                      <input type="text" value={altInput} onChange={(e) => setAltInput(e.target.value)} placeholder="Descripción de la imagen (opcional)" className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                  </div>
                )}
                {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" onClick={() => { setShowImageModal(false); setError(''); setUrlInput(''); setAltInput('') }} className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200">Cancelar</button>
                  {imageTab === 'url' && <button type="button" onClick={handleUrlInsert} disabled={!urlInput.trim()} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">Insertar</button>}
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <RichTemplateEditor
          value={value}
          onChange={onChange}
          variables={variables}
        />
      )}
    </div>
  )
}
