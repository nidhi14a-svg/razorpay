'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

export default function MonitorCampaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate fetching campaigns
    // In real app, this would fetch from backend
    setLoading(false)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Back Button */}
      <div className="bg-white border-b p-4">
        <Link href="/dashboard" className="text-blue-600 hover:text-blue-800 font-semibold">
          ← Back to Dashboard
        </Link>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-2 text-gray-800">📊 Monitor Campaigns</h1>
        <p className="text-gray-600 mb-8">
          Track real-time performance of your active campaigns.
        </p>

        {/* No Campaigns */}
        {!loading && campaigns.length === 0 && (
          <div className="bg-white p-12 rounded-lg shadow-lg text-center">
            <p className="text-gray-600 text-lg mb-4">
              No active campaigns yet.
            </p>
            <Link href="/dashboard/create-campaign">
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold">
                Create Your First Campaign
              </button>
            </Link>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="bg-white p-12 rounded-lg shadow-lg text-center">
            <p className="text-gray-600">Loading campaigns...</p>
          </div>
        )}

        {/* Campaigns List */}
        {campaigns.length > 0 && (
          <div className="space-y-6">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="bg-white p-6 rounded-lg shadow-lg">
                <h3 className="text-xl font-bold text-gray-800 mb-4">{campaign.goal}</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-gray-600 text-sm">Conversions</p>
                    <p className="text-2xl font-bold text-blue-600">{campaign.conversions}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 text-sm">Revenue</p>
                    <p className="text-2xl font-bold text-green-600">₹{campaign.revenue}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 text-sm">Conversion Rate</p>
                    <p className="text-2xl font-bold text-purple-600">{campaign.conversionRate}%</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}