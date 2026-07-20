'use client'

import { useRef, useState, useEffect, useCallback } from 'react'
import { uploadTemplateImage } from '@/lib/mailer-api'
import { api } from '@/lib/api'

interface ImageItem {
  id: string
  url: string
  alt_text: string
  file_size: number
  created_at: string
}

interface ImageSelectorProps {
  open: boolean
  onClose: () => void
  onSelect: (src: string, alt: string) => void
  onError?: (msg: string) => void
}

export default function ImageSelector({ open, onClose, onSelect, onError }: ImageSelectorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [tab, setTab] = useState<'upload' | 'url' | 'library'>('upload')
  const [uploading, setUploading] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [altInput, setAltInput] = useState('')
  const [error, setError] = useState('')
  const [images, setImages] = useState<ImageItem[]>([])
  const [loadingLib, setLoadingLib] = useState(false)

  const showError = useCallback((msg: string) => {
    setError(msg)
    onError?.(msg)
  }, [onError])

  const reset = () => {
    setUrlInput('')
    setAltInput('')
    setError('')
    setTab('upload')
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const fetchImages = useCallback(async () => {
    setLoadingLib(true)
    try {
      const data = await api.get<{ results: ImageItem[] }>('/mailer/images/')
      setImages(data.results)
    } catch {
      showError('Error al cargar la biblioteca de imágenes')
    } finally {
      setLoadingLib(false)
    }
  }, [showError])

  useEffect(() => {
    if (open && tab === 'library') fetchImages()
  }, [open, tab, fetchImages])

  const insertImageFn = (src: string, alt: string) => {
    onSelect(src, alt || '')
    handleClose()
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      showError('Solo se permiten archivos de imagen')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      showError('La imagen no debe superar los 10MB')
      return
    }

    setUploading(true)
    setError('')
    try {
      const result = await uploadTemplateImage(file, altInput)
      insertImageFn(result.url, altInput || file.name)
    } catch {
      showError('Error al subir la imagen')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleUrlInsert = () => {
    const trimmed = urlInput.trim()
    if (!trimmed) {
      showError('Ingresa una URL de imagen')
      return
    }
    insertImageFn(trimmed, altInput)
  }

  if (!open) return null

  const tabClass = (t: string) =>
    `px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
      tab === t
        ? 'border-blue-500 text-blue-600'
        : 'border-transparent text-slate-500 hover:text-slate-700'
    }`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={handleClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Insertar imagen</h3>
          <button
            type="button"
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        <div className="flex border-b border-slate-200 mb-4">
          <button type="button" onClick={() => setTab('upload')} className={tabClass('upload')}>
            Subir archivo
          </button>
          <button type="button" onClick={() => setTab('url')} className={tabClass('url')}>
            Pegar URL
          </button>
          <button type="button" onClick={() => setTab('library')} className={tabClass('library')}>
            Biblioteca
          </button>
        </div>

        {tab === 'upload' && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Texto alternativo
              </label>
              <input
                type="text"
                value={altInput}
                onChange={(e) => setAltInput(e.target.value)}
                placeholder="Descripción de la imagen (opcional)"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
                id="image-upload-input"
              />
              <label htmlFor="image-upload-input" className="cursor-pointer flex flex-col items-center gap-2">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <span className="text-sm text-slate-500">
                  {uploading ? 'Subiendo...' : 'Haz clic para seleccionar una imagen'}
                </span>
                <span className="text-xs text-slate-400">PNG, JPG, GIF hasta 10MB</span>
              </label>
            </div>
          </div>
        )}

        {tab === 'url' && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                URL de la imagen
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://ejemplo.com/imagen.jpg"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Texto alternativo
              </label>
              <input
                type="text"
                value={altInput}
                onChange={(e) => setAltInput(e.target.value)}
                placeholder="Descripción de la imagen (opcional)"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        )}

        {tab === 'library' && (
          <div className="space-y-3">
            {loadingLib ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              </div>
            ) : images.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">
                No hay imágenes subidas. Sube una imagen desde la pestaña &quot;Subir archivo&quot;.
              </p>
            ) : (
              <div className="grid grid-cols-3 gap-3 max-h-60 overflow-y-auto">
                {images.map((img) => (
                  <button
                    key={img.id}
                    type="button"
                    onClick={() => insertImageFn(img.url, img.alt_text)}
                    className="group relative aspect-video rounded-lg border border-slate-200 overflow-hidden hover:border-blue-400 transition-colors"
                  >
                    <img
                      src={img.url}
                      alt={img.alt_text || 'Imagen'}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200"
          >
            Cancelar
          </button>
          {tab === 'url' && (
            <button
              type="button"
              onClick={handleUrlInsert}
              disabled={!urlInput.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Insertar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
