'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function Dashboard() {
  const [merchantId, setMerchantId] = useState('')
  const [businessName, setBusinessName] = useState('')
  const router = useRouter()

  useEffect(() => {
    // Get merchant info from storage
    const id = localStorage.getItem('merchantId')
    const name = localStorage.getItem('businessName')
    
    if (!id) {
      // Not logged in, redirect to login
      router.push('/login')
    } else {
      setMerchantId(id)
      setBusinessName(name || 'Your Business')
    }
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem('merchantId')
    localStorage.removeItem('businessName')
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <nav className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">🚀 AI Revenue Agent</h1>
            <p className="text-blue-100 text-sm">{businessName}</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded text-white font-semibold"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-8">
        <h2 className="text-3xl font-bold mb-8 text-gray-800">Dashboard</h2>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Create Campaign */}
          <Link href="/dashboard/create-campaign">
            <div className="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl cursor-pointer transition">
              <h3 className="text-2xl font-bold mb-2">🚀 Create Campaign</h3>
              <p className="text-gray-600">
                Set a goal and let AI create a personalized campaign to achieve it.
              </p>
              <div className="mt-4 text-blue-500 font-semibold">
                Get Started →
              </div>
            </div>
          </Link>

          {/* Card 2: Monitor Campaigns */}
          <Link href="/dashboard/monitor">
            <div className="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl cursor-pointer transition">
              <h3 className="text-2xl font-bold mb-2">📊 Monitor Campaigns</h3>
              <p className="text-gray-600">
                Track real-time performance of your active campaigns.
              </p>
              <div className="mt-4 text-blue-500 font-semibold">
                View Stats →
              </div>
            </div>
          </Link>

          {/* Card 3: Business Rules */}
          <Link href="/dashboard/rules">
            <div className="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl cursor-pointer transition">
              <h3 className="text-2xl font-bold mb-2">⚙️ Business Rules</h3>
              <p className="text-gray-600">
                Set guardrails: max discount, min margin, budget limits.
              </p>
              <div className="mt-4 text-blue-500 font-semibold">
                Configure →
              </div>
            </div>
          </Link>

          {/* Card 4: Reports */}
          <Link href="/dashboard/reports">
            <div className="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl cursor-pointer transition">
              <h3 className="text-2xl font-bold mb-2">📈 Reports</h3>
              <p className="text-gray-600">
                View detailed analytics and campaign performance.
              </p>
              <div className="mt-4 text-blue-500 font-semibold">
                Analyze →
              </div>
            </div>
          </Link>
        </div>

        {/* Quick Stats Section */}
        <div className="mt-12 bg-white p-6 rounded-lg shadow-lg">
          <h3 className="text-2xl font-bold mb-6 text-gray-800">Quick Stats</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm">Active Campaigns</p>
              <p className="text-3xl font-bold text-blue-600">0</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm">Total Revenue</p>
              <p className="text-3xl font-bold text-green-600">₹0</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm">Avg Conversion</p>
              <p className="text-3xl font-bold text-purple-600">0%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}