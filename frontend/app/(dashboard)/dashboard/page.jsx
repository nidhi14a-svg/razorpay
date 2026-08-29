'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { MetricCard } from '@/components/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { IndianRupee, MousePointerClick, Megaphone, Users, PlusCircle } from 'lucide-react'

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    
    async function fetchDashboard() {
      try {
        // Fetch intelligence for dashboard stats
        const res = await fetch(`http://localhost:8000/merchants/${merchantId}/intelligence`)
        if (!res.ok) throw new Error('Failed to fetch dashboard data')
        const json = await res.json()
        setData(json)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    if (merchantId) fetchDashboard()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard Overview</h2>
          <p className="text-gray-500">Loading your business metrics...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      </div>
    )
  }

  const summary = data?.summary || {
    total_campaigns: 0,
    total_customers: 0,
    revenue: 0,
    conversion_rate: 0
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Dashboard Overview</h2>
          <p className="text-gray-500 mt-1">Here's what's happening with your campaigns today.</p>
        </div>
        <Link 
          href="/campaigns/create" 
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition shadow-sm"
        >
          <PlusCircle size={20} /> New Campaign
        </Link>
      </div>

      {error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
          Failed to load dashboard data. Please try again.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title="Total Revenue" 
              value={`₹${summary.revenue?.toLocaleString() || 0}`} 
              icon={IndianRupee} 
              color="green" 
            />
            <MetricCard 
              title="Avg Conversion" 
              value={`${summary.conversion_rate?.toFixed(1) || 0}%`} 
              icon={MousePointerClick} 
              color="purple" 
            />
            <MetricCard 
              title="Total Campaigns" 
              value={summary.total_campaigns || 0} 
              icon={Megaphone} 
              color="blue" 
            />
            <MetricCard 
              title="Total Reach" 
              value={summary.total_customers || 0} 
              icon={Users} 
              color="amber" 
            />
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col items-center justify-center min-h-[300px] text-center">
              <h3 className="text-lg font-bold text-gray-800 mb-2">Need a Campaign Strategy?</h3>
              <p className="text-gray-500 mb-6 max-w-sm">Use our AI Revenue Agent to analyze your segments and recommend high-converting offers automatically.</p>
              <Link href="/intelligence" className="bg-gray-900 text-white hover:bg-gray-800 px-6 py-2.5 rounded-lg font-medium transition">
                Ask Revenue Agent
              </Link>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col items-center justify-center min-h-[300px] text-center">
               <h3 className="text-lg font-bold text-gray-800 mb-2">Optimize Existing Campaigns</h3>
               <p className="text-gray-500 mb-6 max-w-sm">Review AI recommendations for active campaigns to improve conversions and protect margins.</p>
               <Link href="/optimizations" className="bg-blue-50 text-blue-700 hover:bg-blue-100 px-6 py-2.5 rounded-lg font-medium transition border border-blue-200">
                 View Optimizations
               </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
