'use client'

import { useState, useRef, useEffect } from 'react'
import { VARIABLE_LABELS } from '@/extensions/Variable'

interface VariableSelectorProps {
  onSelect: (name: string) => void
  allowedVariables: string[]
}

export default function VariableSelector({ onSelect, allowedVariables }: VariableSelectorProps) {
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

  const variables = allowedVariables.filter((v) => VARIABLE_LABELS[v])

  if (variables.length === 0) return null

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg border border-indigo-200 hover:bg-indigo-100 transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
          <path d="M7 1.5L3 14.5h2L9 1.5H7zm4 0l-4 13h2l4-13h-2z" />
        </svg>
        Insertar Variable
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
          <div className="px-3 py-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
            Variables disponibles
          </div>
          {variables.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => {
                onSelect(v)
                setOpen(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <span className="font-mono text-xs">{`{{ ${v} }}`}</span>
              <span className="text-xs text-slate-400">{VARIABLE_LABELS[v]}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
