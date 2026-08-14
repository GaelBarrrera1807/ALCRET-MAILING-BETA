'use client'

import { Node, type NodeViewProps } from '@tiptap/core'
import { ReactNodeViewRenderer } from '@tiptap/react'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    variable: {
      insertVariable: (name: string) => ReturnType
    }
  }
}

export const VARIABLE_LABELS: Record<string, string> = {
  first_name: 'Nombre',
  last_name: 'Apellido',
  company_name: 'Empresa',
  sector: 'Sector',
  email: 'Email',
// Inventario
  sku_o_vin: 'VIN/SKU',
  vin: 'VIN',
  nombre_unidad: 'Unidad',
  almacen_id: 'Almacén',
  producto_id: 'Producto',
  cantidad_disponible: 'Cantidad',
  tipo_movimiento: 'Tipo de movimiento',
  // Oportunidades / Pipeline
  contact_name: 'Nombre de contacto',
  contact_email: 'Email de contacto',
  monto_total: 'Monto total',
  esquema: 'Esquema',
  unidad_interes: 'Unidad de interés',
  last_email_interaction: 'Última interacción',
}

export const SUPPORTED_VARIABLES = Object.keys(VARIABLE_LABELS)

export function preprocessLegacyVariables(html: string, variables: string[]): string {
  let result = html
  for (const v of variables) {
    const pattern = `{{ ${v} }}`
    result = result.replaceAll(pattern, `<span data-var="${v}">${pattern}</span>`)
  }
  return result
}

export function cleanupVariableOutput(html: string): string {
  return html.replace(/<span\s+data-var="(\w+)"[^>]*>(\{\{\s*\1\s*\}\})<\/span>/g, '$2')
}

function VariablePill(props: NodeViewProps) {
  const { node, selected, getPos, editor } = props
  const name = node.attrs.name as string
  const label = VARIABLE_LABELS[name] || name

  const handleClick = () => {
    const pos = getPos()
    if (typeof pos === 'number') {
      editor.commands.setNodeSelection(pos)
    }
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium select-none ${
        selected
          ? 'bg-blue-200 text-blue-800 ring-2 ring-blue-400'
          : 'bg-blue-50 text-blue-700 border border-blue-200'
      }`}
      data-var={name}
      contentEditable={false}
      onClick={handleClick}
      title={name}
    >
      <svg className="w-3 h-3 shrink-0" viewBox="0 0 16 16" fill="currentColor">
        <path d="M7 1.5L3 14.5h2L9 1.5H7zm4 0l-4 13h2l4-13h-2z" />
      </svg>
      <span>{label}</span>
    </span>
  )
}

export const Variable = Node.create({
  name: 'variable',

  group: 'inline',

  inline: true,

  atom: true,

  addAttributes() {
    return {
      name: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-var'),
        renderHTML: (attrs) => ({ 'data-var': attrs.name }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-var]' }]
  },

  renderHTML({ node }) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return ['span', { 'data-var': node.attrs.name, style: 'display:inline;' }, `{{ ${node.attrs.name} }}`] as any
  },

  addNodeView() {
    return ReactNodeViewRenderer(VariablePill)
  },

  addCommands() {
    return {
      insertVariable:
        (name: string) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { name },
          })
        },
    }
  },

  addKeyboardShortcuts() {
    return {
      Backspace: () => false,
      Delete: () => false,
    }
  },
})
