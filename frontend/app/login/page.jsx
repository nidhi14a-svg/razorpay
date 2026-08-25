'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('merchantId', data.merchant_id)
        localStorage.setItem('businessName', data.business_name)
        router.push('/dashboard')
      } else {
        setError(data.detail || 'Login failed')
      }
    } catch (error) {
      setError('Error: ' + error.message)
    }

    setLoading(false)
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600">
      <div className="bg-white p-8 rounded-lg shadow-2xl w-96">
        <h1 className="text-3xl font-bold mb-2 text-center text-gray-800">
          🚀 AI Revenue Agent
        </h1>
        <p className="text-center text-gray-600 mb-6">Grow your business with AI</p>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {error && (
            <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 rounded-lg transition disabled:opacity-50"
          >
            {loading ? '⏳ Logging in...' : '🔓 Login'}
          </button>
        </form>

        <div className="mt-6 p-4 bg-gray-100 rounded-lg text-sm">
          <p className="font-semibold text-gray-700 mb-2">Demo Credentials:</p>
          <p className="text-gray-600">Email: <code className="bg-white px-2 py-1">demo@example.com</code></p>
          <p className="text-gray-600">Password: <code className="bg-white px-2 py-1">demo123</code></p>
        </div>
      </div>
    </div>
  )
}