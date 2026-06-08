'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '📊' },
  { href: '/preprocessing', label: 'Preprocesamiento', icon: '🔍' },
  { href: '/companies', label: 'Empresas', icon: '🏢' },
  { href: '/leads', label: 'Leads', icon: '🎯' },
  { href: '/reports', label: 'Reportes', icon: '📄' },
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
              <span>{item.icon}</span>
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
          <span>🚪</span>
          <span>Cerrar sesión</span>
        </button>
      </div>
    </aside>
  )
}
