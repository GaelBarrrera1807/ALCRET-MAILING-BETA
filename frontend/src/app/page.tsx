'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getTokens } from '@/lib/api'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    getTokens().then(({ access }) => {
      if (access) {
        router.push('/dashboard')
      } else {
        router.push('/login')
      }
    })
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  )
}
