'use client'

interface CampaignStatsCardsProps {
  stats: {
    sent: number
    opens: number
    clicks: number
    bounces: number
    unsubscribes: number
  }
}

export default function CampaignStatsCards({ stats }: CampaignStatsCardsProps) {
  const cards = [
    { label: 'Enviados', value: stats.sent, color: 'text-blue-600' },
    { label: 'Abiertos', value: stats.opens, color: 'text-green-600' },
    { label: 'Clicks', value: stats.clicks, color: 'text-purple-600' },
    { label: 'Rebotes', value: stats.bounces, color: 'text-orange-600' },
    { label: 'Bajas', value: stats.unsubscribes, color: 'text-red-600' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map((card) => (
        <div key={card.label} className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center">
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
          <p className="text-xs text-slate-500 mt-1">{card.label}</p>
        </div>
      ))}
    </div>
  )
}
