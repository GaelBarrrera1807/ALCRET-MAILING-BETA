'use client'

import { useState, useRef, useEffect } from 'react'
import type { Editor } from '@tiptap/core'

interface InsertMenuProps {
  editor: Editor
  onInsertImage: () => void
}

export default function InsertMenu({ editor, onInsertImage }: InsertMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const insertCTA = () => {
    editor
      .chain()
      .focus()
      .insertContent(
        `<table border="0" cellpadding="0" cellspacing="0" style="margin:16px auto;"><tr><td align="center" style="background-color:#2563eb;border-radius:8px;padding:12px 32px;"><a href="https://" target="_blank" style="color:#ffffff;text-decoration:none;font-size:16px;font-weight:600;">&gt;&gt; Contáctanos &lt;&lt;</a></td></tr></table>`
      )
      .run()
    setOpen(false)
  }

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
    setOpen(false)
  }

  const insertSeparator = () => {
    editor.chain().focus().setHorizontalRule().run()
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-emerald-700 bg-emerald-50 rounded-lg border border-emerald-200 hover:bg-emerald-100 transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 3a1 1 0 011 1v3h3a1 1 0 110 2H9v3a1 1 0 11-2 0V9H4a1 1 0 110-2h3V4a1 1 0 011-1z" />
        </svg>
        Insertar
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-52 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
          <button
            type="button"
            onClick={insertCTA}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span className="w-6 h-6 flex items-center justify-center rounded bg-blue-100 text-blue-600 text-xs font-bold">
              CTA
            </span>
            <span>Botón CTA</span>
          </button>
          <button
            type="button"
            onClick={() => { onInsertImage(); setOpen(false) }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span className="w-6 h-6 flex items-center justify-center rounded bg-green-100 text-green-600 text-xs">
              🖼
            </span>
            <span>Imagen</span>
          </button>
          <button
            type="button"
            onClick={insertTable}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span className="w-6 h-6 flex items-center justify-center rounded bg-orange-100 text-orange-600 text-xs">
              ⊞
            </span>
            <span>Tabla</span>
          </button>
          <button
            type="button"
            onClick={insertSeparator}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span className="w-6 h-6 flex items-center justify-center rounded bg-slate-100 text-slate-600 text-xs">
              —
            </span>
            <span>Separador</span>
          </button>
        </div>
      )}
    </div>
  )
}
