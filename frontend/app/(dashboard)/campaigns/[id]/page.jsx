'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Target, TrendingUp, IndianRupee, PieChart } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { MetricCard } from '@/components/MetricCard'

export default function CampaignDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [campaign, setCampaign] = useState(null)
  const [offers, setOffers] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    if (!merchantId) {
      router.push('/login')
      return
    }

    async function fetchData() {
      try {
        const [campRes, offersRes, analyticsRes] = await Promise.all([
          fetch(`http://localhost:8000/campaigns/${params.id}?merchant_id=${merchantId}`),
          fetch(`http://localhost:8000/campaigns/${params.id}/offers?merchant_id=${merchantId}`),
          fetch(`http://localhost:8000/campaigns/${params.id}/analytics?merchant_id=${merchantId}`)
        ])

        if (!campRes.ok) throw new Error('Campaign not found')
        
        setCampaign(await campRes.json())
        const offersData = offersRes.ok ? await offersRes.json() : null;
        setOffers(offersData?.items || [])
        setAnalytics(analyticsRes.ok ? await analyticsRes.json() : null)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [params.id, router])

  if (loading) {
    return (
      <div className="space-y-6">
        <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500">
          <ArrowLeft size={16} className="mr-1" /> Back
        </Link>
        <LoadingSkeleton type="card" />
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="space-y-6">
        <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
          <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl font-medium">
          {error || 'Campaign not found'}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
      </Link>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-gray-200 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-bold text-gray-900 tracking-tight">
              {campaign.goal || campaign.campaign_name || "Untitled Campaign"}
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p className="text-gray-500 font-mono text-sm">ID: {campaign.campaign_id}</p>
        </div>
      </div>

      {/* Analytics KPI */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          title="Total Revenue" 
          value={`₹${analytics?.revenue || 0}`} 
          icon={IndianRupee} 
          color="green" 
        />
        <MetricCard 
          title="Conversion Rate" 
          value={`${(analytics?.conversion_rate || 0).toFixed(1)}%`} 
          icon={TrendingUp} 
          color="purple" 
        />
        <MetricCard 
          title="Verified Payments" 
          value={analytics?.verified_payments || 0} 
          icon={Target} 
          color="blue" 
        />
        <MetricCard 
          title="Total Offers Sent" 
          value={analytics?.total_offers || 0} 
          icon={PieChart} 
          color="gray" 
        />
      </div>

      {/* Offers & Segments */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden mt-8">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">Campaign Offers</h3>
          <p className="text-sm text-gray-500 mt-1">Offers provisioned to each segment and their conversion performance.</p>
        </div>
        
        {offers.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No offers found for this campaign.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider border-b border-gray-200">
                  <th className="p-4">Segment</th>
                  <th className="p-4">Discount</th>
                  <th className="p-4">Conversions</th>
                  <th className="p-4">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {offers.map((offer) => {
                  const segAnalytics = analytics?.segment_breakdown?.[offer.customer_segment] || {}
                  return (
                    <tr key={offer.offer_id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 font-semibold capitalize text-gray-900">
                        {offer.customer_segment.replace(/_/g, ' ')}
                      </td>
                      <td className="p-4">
                        <span className="bg-purple-100 text-purple-800 border border-purple-200 px-2.5 py-1 rounded-full text-xs font-bold">
                          {offer.discount_pct}% OFF
                        </span>
                      </td>
                      <td className="p-4 text-gray-900">
                        {segAnalytics.verified_payments || 0}
                        <span className="text-gray-400 text-xs ml-1">/ {segAnalytics.total_offers || 1}</span>
                      </td>
                      <td className="p-4 font-medium text-gray-900">
                        ₹{segAnalytics.revenue || 0}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
