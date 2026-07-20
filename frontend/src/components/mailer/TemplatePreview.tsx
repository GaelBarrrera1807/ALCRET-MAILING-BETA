'use client'

interface TemplatePreviewProps {
  html: string
  context: Record<string, string>
}

function renderTemplate(template: string, context: Record<string, string>): string {
  let result = template
  for (const [key, value] of Object.entries(context)) {
    result = result.replaceAll(new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'gi'), value)
  }
  return result
}

export default function TemplatePreview({ html, context }: TemplatePreviewProps) {
  if (!html) {
    return (
      <div className="flex items-center justify-center h-48 bg-slate-50 rounded-lg border border-dashed border-slate-300">
        <p className="text-sm text-slate-400">Sin contenido para previsualizar</p>
      </div>
    )
  }

  const rendered = renderTemplate(html, context)

  return (
    <div
      className="w-full h-64 overflow-auto bg-white rounded-lg border border-slate-200 p-4"
      dangerouslySetInnerHTML={{ __html: rendered }}
    />
  )
}
