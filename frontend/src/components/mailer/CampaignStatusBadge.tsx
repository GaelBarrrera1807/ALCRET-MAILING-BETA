'use client'

interface CampaignStatusBadgeProps {
  status: string
}

const STYLES: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-600',
  scheduled: 'bg-blue-100 text-blue-800',
  sending: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-green-100 text-green-800',
  paused: 'bg-orange-100 text-orange-800',
  cancelled: 'bg-red-100 text-red-800',
}

const LABELS: Record<string, string> = {
  draft: 'Borrador',
  scheduled: 'Programada',
  sending: 'Enviando',
  sent: 'Enviada',
  paused: 'Pausada',
  cancelled: 'Cancelada',
}

export default function CampaignStatusBadge({ status }: CampaignStatusBadgeProps) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STYLES[status] || 'bg-slate-100 text-slate-600'}`}>
      {LABELS[status] || status}
    </span>
  )
}
