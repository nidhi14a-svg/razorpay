'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { EmptyState } from '@/components/EmptyState'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { PlusCircle, Search, Calendar, ChevronRight } from 'lucide-react'

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    
    async function fetchCampaigns() {
      try {
        const res = await fetch(`http://localhost:8000/campaigns?merchant_id=${merchantId}`)
        if (!res.ok) {
          throw new Error(`Failed to fetch campaigns (Status: ${res.status})`)
        }
        const json = await res.json()
        setCampaigns(json.items || [])
      } catch (err) {
        console.error("Campaigns fetch error:", err)
        setError(err.message || "Failed to load campaigns")
      } finally {
        setLoading(false)
      }
    }
    
    if (merchantId) fetchCampaigns()
  }, [])

  const filteredCampaigns = campaigns.filter(c => 
    (c.goal || c.campaign_name || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.status || '').toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Campaigns</h2>
          <p className="text-gray-500">Loading your campaigns...</p>
        </div>
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Campaigns</h2>
          <p className="text-gray-500 mt-1">Manage and monitor all your marketing campaigns.</p>
        </div>
        <Link 
          href="/campaigns/create" 
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition shadow-sm"
        >
          <PlusCircle size={20} /> Create Campaign
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
          {error}
        </div>
      )}

      {campaigns.length === 0 && !error ? (
        <EmptyState 
          title="No campaigns yet" 
          description="You haven't launched any campaigns. Create your first AI-optimized campaign to start generating revenue."
          action={
            <Link href="/campaigns/create" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium transition">
              Create Campaign
            </Link>
          }
        />
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          {/* Search/Filter Bar */}
          <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex items-center">
            <div className="relative max-w-md w-full flex items-center">
              <Search className="w-5 h-5 text-gray-400 absolute left-3" />
              <input 
                type="text"
                placeholder="Search campaigns by goal or status..."
                className="w-full pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-sm font-medium border-b border-gray-200">
                  <th className="p-4 font-semibold uppercase tracking-wider">Campaign</th>
                  <th className="p-4 font-semibold uppercase tracking-wider">Status</th>
                  <th className="p-4 font-semibold uppercase tracking-wider">Segments Targeted</th>
                  <th className="p-4 font-semibold uppercase tracking-wider">ID</th>
                  <th className="p-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredCampaigns.map((campaign) => (
                  <tr key={campaign.campaign_id} className="hover:bg-blue-50/30 transition-colors group">
                    <td className="p-4">
                      <div className="font-semibold text-gray-900 mb-1">
                        {campaign.goal || campaign.campaign_name || "Untitled Campaign"}
                      </div>
                      <div className="flex items-center text-xs text-gray-500">
                        <Calendar size={14} className="mr-1" /> Created recently
                      </div>
                    </td>
                    <td className="p-4">
                      <StatusBadge status={campaign.status} />
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                       {campaign.target_segments?.length || 0} Segments
                    </td>
                    <td className="p-4 text-xs font-mono text-gray-400">
                      {campaign.campaign_id.slice(0, 8)}...
                    </td>
                    <td className="p-4 text-right">
                      <Link 
                        href={`/campaigns/${campaign.campaign_id}`}
                        className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        View Details <ChevronRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
                {filteredCampaigns.length === 0 && (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-gray-500">
                      No campaigns match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
