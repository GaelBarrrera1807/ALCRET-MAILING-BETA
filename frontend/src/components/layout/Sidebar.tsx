'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
  LayoutDashboard,
  Rocket,
  Search,
  Building2,
  Target,
  Mail,
  FileText,
  History,
  LogOut,
} from 'lucide-react'

const iconMap: Record<string, React.ReactNode> = {
  Dashboard: <LayoutDashboard size={18} />,
  'Lead Finder': <Rocket size={18} />,
  Preprocesamiento: <Search size={18} />,
  Empresas: <Building2 size={18} />,
  Leads: <Target size={18} />,
  'Email Marketing': <Mail size={18} />,
  Reportes: <FileText size={18} />,
  'Historial de Búsquedas': <History size={18} />,
}

const navItems = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/lead-finder', label: 'Lead Finder' },
  { href: '/preprocessing', label: 'Preprocesamiento' },
  { href: '/companies', label: 'Empresas' },
  { href: '/leads', label: 'Leads' },
  { href: '/mailer', label: 'Email Marketing' },
  { href: '/reports', label: 'Reportes' },
  { href: '/historial-busquedas', label: 'Historial de Búsquedas' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { logout } = useAuth()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col">
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-lg font-bold">Prospección IA</h1>
        <p className="text-sm text-slate-400 mt-1">Industrial B2B</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <span className="flex-shrink-0">{iconMap[item.label]}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t border-slate-700">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <LogOut size={18} />
          <span>Cerrar sesión</span>
        </button>
      </div>
    </aside>
  )
}
