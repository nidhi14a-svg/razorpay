'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Check if merchant is already logged in
    const merchantId = localStorage.getItem('merchantId')
    
    if (merchantId) {
      // If logged in, go to dashboard
      router.push('/dashboard')
    } else {
      // If not logged in, go to login page
      router.push('/login')
    }
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-xl">Redirecting...</p>
    </div>
  )
}