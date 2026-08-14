'use client'

/**
 * RichTemplateEditor - Editor visual WYSIWYG para plantillas de email marketing.
 *
 * == Estrategia futura: Almacenamiento S3 compatible con SES ==
 * Actualmente TemplateImage almacena imágenes en media/mailer/images/%Y/%m/
 * vía ImageField de Django. Para escalar a SES + S3:
 *
 * 1. Configurar django-storages con backend S3:
 *    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
 *    AWS_S3_REGION_NAME = 'us-east-1'  # mismna región que SES
 *    AWS_S3_CUSTOM_DOMAIN = 'cdn.ejemplo.com'  # CloudFront/CDN opcional
 *
 * 2. Migrar imágenes existentes a S3 vía management command o script one-off.
 *    Las URLs en body_html de templates antiguos apuntarán a la instancia
 *    anterior; considerar un middleware de redirección o actualización batch.
 *
 * 3. Para SES, las imágenes DEBEN tener URLs absolutas públicas. S3 + CloudFront
 *    es la arquitectura recomendada. Las URLs generadas por TemplateImageSerializer
 *    ya construyen URLs absolutas via settings.BASE_URL, adaptarlas a S3.
 *
 * 4. No implementar hasta que el volumen de imágenes lo justifique.
 *    La arquitectura actual con ImageField + media local sirve para etapas
 *    tempranas y volúmenes moderados.
 *
 * == Estrategia futura: Versionado de plantillas ==
 * Actualmente EmailTemplate no tiene versionado. Estrategia recomendada:
 *
 * 1. Agregar modelo EmailTemplateVersion:
 *    - FK a EmailTemplate
 *    - subject, body_html, variables (snapshot)
 *    - version_number (auto-increment por template)
 *    - created_by (FK User)
 *    - change_summary (texto libre)
 *
 * 2. En el serializer de EmailTemplate, crear automáticamente una versión
 *    antes de cada update (vía signal pre_save o en perform_update).
 *
 * 3. En el frontend, agregar selector de versiones en el modal de edición
 *    (dropdown con fechas + resumen), permitiendo previsualizar y restaurar.
 *
 * 4. La restauración copia subject/body_html/variables de la versión al template.
 *    No eliminar versiones al eliminar el template (soft-delete o archivo).
 *
 * 5. No implementar hasta que los usuarios soliciten explícitamente la feature.
 *
 * == Fase futura: Validación con Gmail real ==
 * Después de implementar el editor visual, agregar workflow de prueba:
 *
 * 1. Botón "Enviar prueba" en el modal de creación/edición de template.
 * 2. Input para email(s) de prueba (máximo 5).
 * 3. Usar el mismo pipeline que Campaign Send pero para un destinatario único.
 * 4. Endpoint: POST /api/mailer/templates/{id}/test-send/ { emails: [] }
 * 5. Verificar en Gmail/Outlook/Yahoo que el renderizado es correcto.
 * 6. No reemplaza MailHog (dev) ni Preview (iteración rápida).
 */

import { useCallback, useRef, useState, useEffect } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import Document from '@tiptap/extension-document'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import Bold from '@tiptap/extension-bold'
import Italic from '@tiptap/extension-italic'
import Heading from '@tiptap/extension-heading'
import BulletList from '@tiptap/extension-bullet-list'
import OrderedList from '@tiptap/extension-ordered-list'
import ListItem from '@tiptap/extension-list-item'
import History from '@tiptap/extension-history'
import HardBreak from '@tiptap/extension-hard-break'
import Dropcursor from '@tiptap/extension-dropcursor'
import Gapcursor from '@tiptap/extension-gapcursor'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import ImageExt from '@tiptap/extension-image'
import { Table } from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import { TextStyle } from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import HorizontalRule from '@tiptap/extension-horizontal-rule'
import Placeholder from '@tiptap/extension-placeholder'
import { Variable, preprocessLegacyVariables, cleanupVariableOutput } from '@/extensions/Variable'
import EditorToolbar from './EditorToolbar'
import InsertMenu from './InsertMenu'
import VariableSelector from './VariableSelector'
import ImageSelector from './ImageSelector'

interface RichTemplateEditorProps {
  value: string
  onChange: (html: string) => void
  variables: string[]
}

export default function RichTemplateEditor({ value, onChange, variables }: RichTemplateEditorProps) {
  const [showImageModal, setShowImageModal] = useState(false)
  const processedValue = useRef<string | null>(cleanupVariableOutput(value))

  const editor = useEditor({
    extensions: [
      Document,
      Paragraph,
      Text,
      Bold,
      Italic,
      Underline,
      Heading.configure({ levels: [1, 2, 3] }),
      BulletList,
      OrderedList,
      ListItem,
      History.configure({ depth: 100 }),
      HardBreak,
      Dropcursor,
      Gapcursor,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' },
      }),
      ImageExt.configure({ inline: false, allowBase64: true }),
      Table.configure({ resizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      TextStyle,
      Color,
      HorizontalRule,
      Placeholder.configure({ placeholder: 'Empieza a escribir tu correo aquí...' }),
      Variable,
    ],
    content: preprocessLegacyVariables(value, variables),
    onUpdate: ({ editor }) => {
      const raw = editor.getHTML()
      const clean = cleanupVariableOutput(raw)
      processedValue.current = clean
      onChange(clean)
    },
    editorProps: {
      attributes: {
        class:
          'prose prose-sm max-w-none focus:outline-none min-h-[320px] px-4 py-3 text-slate-800',
      },
    },
  })

  useEffect(() => {
    if (!editor) return
    if (!value) return

    const current = cleanupVariableOutput(editor.getHTML())
    if (value === processedValue.current || value === current) return

    const content = preprocessLegacyVariables(value, variables)
    editor.commands.setContent(content)
    processedValue.current = value
  }, [editor, value, variables])

  const handleImageSelect = useCallback(
    (src: string, alt: string) => {
      editor?.chain().focus().setImage({ src, alt }).run()
      setShowImageModal(false)
    },
    [editor]
  )

  const handleVariableSelect = useCallback(
    (name: string) => {
      editor?.chain().focus().insertVariable(name).run()
    },
    [editor]
  )

  if (!editor) return null

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2 flex-wrap">
          <InsertMenu
            editor={editor}
            onInsertImage={() => setShowImageModal(true)}
          />
          <VariableSelector onSelect={handleVariableSelect} allowedVariables={variables} />
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowImageModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-50 rounded-lg border border-green-200 hover:bg-green-100 transition-colors"
          >
            🖼 Imagen
          </button>
        </div>
      </div>

      <EditorToolbar editor={editor} />

      <EditorContent editor={editor} />

      {showImageModal && (
        <ImageSelector
          open={showImageModal}
          onClose={() => setShowImageModal(false)}
          onSelect={handleImageSelect}
        />
      )}
    </div>
  )
}
