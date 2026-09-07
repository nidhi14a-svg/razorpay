'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { getApiUrl } from '@/lib/api'

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  
  const [status, setStatus] = useState('verifying') // verifying, success, error
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided in the URL.')
      return
    }

    const verifyToken = async () => {
      try {
        const response = await fetch(getApiUrl('/auth/verify-email'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })
        const data = await response.json()
        
        if (response.ok) {
          setStatus('success')
          setMessage('Your email has been successfully verified! You can now log in.')
        } else {
          setStatus('error')
          setMessage(data.detail || 'Verification failed. The token may be expired or invalid.')
        }
      } catch (err) {
        setStatus('error')
        setMessage('Network error. Could not connect to the server.')
      }
    }

    verifyToken()
  }, [token])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center items-center gap-2 mb-4">
          <div className="w-10 h-10 bg-teal-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-xl">R</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">RAZZZ</h1>
        </div>
        
        <div className="bg-white py-8 px-4 shadow-sm border border-slate-200 sm:rounded-xl sm:px-10 text-center mt-8">
          
          {status === 'verifying' && (
            <div className="flex flex-col items-center">
              <Loader2 className="h-12 w-12 text-teal-600 animate-spin mb-4" />
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Verifying your email...</h2>
              <p className="text-slate-600">Please wait while we validate your token.</p>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center">
              <div className="h-16 w-16 rounded-full bg-teal-100 flex items-center justify-center mb-4">
                <CheckCircle2 className="h-8 w-8 text-teal-600" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Email Verified</h2>
              <p className="text-slate-600 mb-6">{message}</p>
              <Link
                href="/login"
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 transition-colors"
              >
                Log In to RAZZZ
              </Link>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-col items-center">
              <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
                <XCircle className="h-8 w-8 text-red-600" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Verification Failed</h2>
              <p className="text-slate-600 mb-6">{message}</p>
              <Link
                href="/login"
                className="w-full flex justify-center py-2.5 px-4 border border-slate-300 rounded-lg shadow-sm text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 transition-colors"
              >
                Return to Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function VerifyEmail() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  )
}
