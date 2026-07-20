'use client'

import type { Editor } from '@tiptap/core'

interface EditorToolbarProps {
  editor: Editor
}

const COLORS = [
  { label: 'Negro', value: '#000000' },
  { label: 'Gris', value: '#64748b' },
  { label: 'Azul', value: '#2563eb' },
  { label: 'Verde', value: '#16a34a' },
  { label: 'Rojo', value: '#dc2626' },
  { label: 'Naranja', value: '#ea580c' },
]

type ToolbarBtn = {
  label: string
  icon: string
  action: () => void
  isActive: () => boolean
  title: string
}

function ToolbarButton({ btn, editor }: { btn: ToolbarBtn; editor: Editor }) {
  return (
    <button
      type="button"
      onClick={btn.action}
      title={btn.title}
      className={`w-8 h-8 flex items-center justify-center rounded text-sm transition-colors ${
        btn.isActive()
          ? 'bg-blue-100 text-blue-700'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'
      } ${!editor.isEditable ? 'opacity-50 cursor-not-allowed' : ''}`}
      disabled={!editor.isEditable}
    >
      <span dangerouslySetInnerHTML={{ __html: btn.icon }} />
    </button>
  )
}

function Divider() {
  return <span className="w-px h-5 bg-slate-200 mx-0.5 shrink-0" />
}

function ColorPicker({ editor }: { editor: Editor }) {
  const currentColor = editor.getAttributes('textStyle').color || '#000000'
  return (
    <div className="flex items-center gap-0.5">
      {COLORS.map((c) => (
        <button
          key={c.value}
          type="button"
          onClick={() => editor.chain().focus().setColor(c.value).run()}
          title={c.label}
          className={`w-6 h-6 rounded-full border-2 transition-all ${
            currentColor === c.value ? 'border-blue-500 scale-110' : 'border-transparent hover:scale-110'
          }`}
          style={{ backgroundColor: c.value }}
        />
      ))}
      {currentColor !== '#000000' && (
        <button
          type="button"
          onClick={() => editor.chain().focus().unsetColor().run()}
          title="Quitar color"
          className="w-6 h-6 flex items-center justify-center text-xs text-slate-400 hover:text-slate-600"
        >
          ✕
        </button>
      )}
    </div>
  )
}

export default function EditorToolbar({ editor }: EditorToolbarProps) {
  const HEADINGS = [
    { label: 'Texto', level: null as number | null },
    { label: 'H1', level: 1 },
    { label: 'H2', level: 2 },
    { label: 'H3', level: 3 },
  ]

  const currentHeading = HEADINGS.find((h) => h.level && editor.isActive('heading', { level: h.level }))
    ?.label || 'Texto'

  const buttons: ToolbarBtn[] = [
    {
      label: 'Undo',
      icon: '&#x21B6;',
      action: () => editor.chain().focus().undo().run(),
      isActive: () => false,
      title: 'Deshacer',
    },
    {
      label: 'Redo',
      icon: '&#x21B7;',
      action: () => editor.chain().focus().redo().run(),
      isActive: () => false,
      title: 'Rehacer',
    },
    {
      label: 'Bold',
      icon: '<b>B</b>',
      action: () => editor.chain().focus().toggleBold().run(),
      isActive: () => editor.isActive('bold'),
      title: 'Negritas',
    },
    {
      label: 'Italic',
      icon: '<i>I</i>',
      action: () => editor.chain().focus().toggleItalic().run(),
      isActive: () => editor.isActive('italic'),
      title: 'Cursivas',
    },
    {
      label: 'Underline',
      icon: '<u>U</u>',
      action: () => editor.chain().focus().toggleUnderline().run(),
      isActive: () => editor.isActive('underline'),
      title: 'Subrayado',
    },
    {
      label: 'BulletList',
      icon: '&#x2022; &#x2022;',
      action: () => editor.chain().focus().toggleBulletList().run(),
      isActive: () => editor.isActive('bulletList'),
      title: 'Lista con viñetas',
    },
    {
      label: 'OrderedList',
      icon: '1. 2.',
      action: () => editor.chain().focus().toggleOrderedList().run(),
      isActive: () => editor.isActive('orderedList'),
      title: 'Lista numerada',
    },
    {
      label: 'Link',
      icon: '&#x1F517;',
      action: () => {
        const prev = editor.getAttributes('link').href as string | undefined
        const url = window.prompt('URL del enlace:', prev || 'https://')
        if (url === null) return
        if (!url) {
          editor.chain().focus().unsetLink().run()
          return
        }
        editor.chain().focus().setLink({ href: url }).run()
      },
      isActive: () => editor.isActive('link'),
      title: 'Insertar enlace',
    },
  ]

  return (
    <div className="flex flex-wrap items-center gap-1 px-3 py-2 bg-white border border-b-0 border-slate-200 rounded-t-lg">
      <div className="flex items-center gap-0.5">
        <ToolbarButton btn={buttons[0]} editor={editor} />
        <ToolbarButton btn={buttons[1]} editor={editor} />
      </div>

      <Divider />

      <div className="flex items-center gap-0.5">
        <ToolbarButton btn={buttons[2]} editor={editor} />
        <ToolbarButton btn={buttons[3]} editor={editor} />
        <ToolbarButton btn={buttons[4]} editor={editor} />
      </div>

      <Divider />

      <ColorPicker editor={editor} />

      <Divider />

      <select
        value={currentHeading}
        onChange={(e) => {
          const level = parseInt(e.target.value)
          if (level) {
            editor.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 }).run()
          } else {
            editor.chain().focus().setParagraph().run()
          }
        }}
        className="px-2 py-1 text-sm border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
      >
        {HEADINGS.map((h) => (
          <option key={h.label} value={h.level || ''}>
            {h.label}
          </option>
        ))}
      </select>

      <Divider />

      <div className="flex items-center gap-0.5">
        <ToolbarButton btn={buttons[5]} editor={editor} />
        <ToolbarButton btn={buttons[6]} editor={editor} />
      </div>

      <Divider />

      <ToolbarButton btn={buttons[7]} editor={editor} />
    </div>
  )
}

export { EditorToolbar as Toolbar }
