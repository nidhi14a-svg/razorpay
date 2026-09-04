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
    
    if (!merchantId) {
      window.location.href = '/login'
      return
    }
    
    async function fetchCampaigns() {
      try {
        const res = await fetch(`http://localhost:8000/campaigns?merchant_id=${merchantId}`)
        if (!res.ok) {
          throw new Error(`Failed to fetch campaigns (Status: ${res.status})`)
        }
        const json = await res.json()
        setCampaigns(Array.isArray(json.items) ? json.items : [])
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
          <h2 className="text-2xl font-bold text-foreground">Campaigns</h2>
          <p className="text-muted">Loading your campaigns...</p>
        </div>
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">Campaigns</h2>
          <p className="text-muted mt-1">Manage and monitor all your marketing campaigns.</p>
        </div>
        <Link 
          href="/campaigns/create" 
          className="flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-sm"
        >
          <PlusCircle size={20} /> Create Campaign
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-xl">
          {error}
        </div>
      )}

      {campaigns.length === 0 && !error ? (
        <EmptyState 
          title="No campaigns yet" 
          description="You haven't launched any campaigns. Create your first AI-optimized campaign to start generating revenue."
          action={
            <Link href="/campaigns/create" className="bg-brand-primary hover:bg-brand-teal text-white px-6 py-3 rounded-xl font-medium transition-colors inline-block shadow-sm">
              Create Campaign
            </Link>
          }
        />
      ) : (
        <div className="bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
          {/* Search/Filter Bar */}
          <div className="p-5 border-b border-border bg-gray-50/50 dark:bg-gray-900/20 flex items-center">
            <div className="relative max-w-md w-full flex items-center">
              <Search className="w-5 h-5 text-muted absolute left-3" />
              <input 
                type="text"
                placeholder="Search campaigns by goal or status..."
                className="w-full pl-10 pr-4 py-2.5 bg-surface border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary/50 transition-shadow text-foreground"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50/50 dark:bg-gray-900/20 border-b border-border">
                  <th className="p-5 font-semibold text-muted text-sm uppercase tracking-wider">Campaign</th>
                  <th className="p-5 font-semibold text-muted text-sm uppercase tracking-wider">Status</th>
                  <th className="p-5 font-semibold text-muted text-sm uppercase tracking-wider">Target Segments</th>
                  <th className="p-5 font-semibold text-muted text-sm uppercase tracking-wider">Created</th>
                  <th className="p-5 font-semibold text-muted text-sm uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredCampaigns.map((campaign) => (
                  <tr key={campaign.campaign_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors group">
                    <td className="p-5">
                      <div className="font-semibold text-foreground text-base mb-1">
                        {campaign.campaign_name || 'Untitled Campaign'}
                      </div>
                      <div className="text-sm text-muted max-w-xs truncate" title={campaign.goal || campaign.campaign_description}>
                        {campaign.goal || campaign.campaign_description || 'No goal specified'}
                      </div>
                    </td>
                    <td className="p-5">
                      <StatusBadge status={campaign.status} />
                    </td>
                    <td className="p-5">
                      <div className="flex flex-wrap gap-1.5">
                        {(campaign.target_segments || []).map((seg, idx) => (
                          <span key={idx} className="bg-gray-100 dark:bg-gray-800 text-muted px-2.5 py-1 rounded-md text-xs font-medium capitalize">
                            {seg.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {(!campaign.target_segments || campaign.target_segments.length === 0) && (
                          <span className="text-muted text-sm italic">All segments</span>
                        )}
                      </div>
                    </td>
                    <td className="p-5">
                      <div className="flex items-center gap-2 text-sm text-muted">
                        <Calendar size={14} className="opacity-70" />
                        {new Date(campaign.created_at).toLocaleDateString(undefined, { 
                          month: 'short', 
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </div>
                    </td>
                    <td className="p-5 text-right">
                      <Link 
                        href={`/campaigns/${campaign.campaign_id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-brand-primary dark:text-brand-teal hover:text-brand-teal dark:hover:text-brand-primary transition-colors group-hover:translate-x-1 duration-200"
                      >
                        View Details <ChevronRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
                
                {filteredCampaigns.length === 0 && (
                  <tr>
                    <td colSpan="5" className="p-10 text-center text-muted">
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
