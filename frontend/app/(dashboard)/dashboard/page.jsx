'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { MetricCard } from '@/components/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { IndianRupee, MousePointerClick, Megaphone, Users, PlusCircle, Brain, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    
    if (!merchantId) {
      window.location.href = '/login'
      return
    }
    
    async function fetchDashboard() {
      try {
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
          <h2 className="text-2xl font-bold text-foreground">Dashboard Overview</h2>
          <p className="text-muted">Loading your business metrics...</p>
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-6">
        <div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">Dashboard Overview</h2>
          <p className="text-muted mt-1 text-sm">Here's what's happening with your revenue today.</p>
        </div>
        <Link 
          href="/campaigns/create" 
          className="flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white px-5 py-2.5 rounded-xl font-semibold transition-all duration-300 shadow-sm hover:shadow-md hover:-translate-y-0.5"
        >
          <PlusCircle size={20} /> New Campaign
        </Link>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-xl">
          Failed to load dashboard data. Please try again.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title="Total Revenue" 
              value={`₹${summary.revenue?.toLocaleString() || 0}`} 
              icon={IndianRupee} 
              color="primary" 
            />
            <MetricCard 
              title="Avg Conversion" 
              value={`${summary.conversion_rate?.toFixed(1) || 0}%`} 
              icon={MousePointerClick} 
              color="coral" 
            />
            <MetricCard 
              title="Total Campaigns" 
              value={summary.total_campaigns || 0} 
              icon={Megaphone} 
              color="teal" 
            />
            <MetricCard 
              title="Total Reach" 
              value={summary.total_customers || 0} 
              icon={Users} 
              color="primary" 
            />
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-surface border border-border rounded-2xl p-8 shadow-soft flex flex-col items-start justify-between min-h-[300px] hover:border-brand-primary/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none group-hover:bg-brand-primary/10 transition-colors duration-500 -translate-y-1/2 translate-x-1/3"></div>
              <div>
                <div className="w-14 h-14 bg-brand-primary/10 dark:bg-brand-primary/20 rounded-xl flex items-center justify-center mb-6 text-brand-primary dark:text-brand-teal border border-brand-primary/20 shadow-sm group-hover:scale-105 transition-transform">
                  <Brain size={28} className="animate-pulse-slow" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-3 tracking-tight">AI Revenue Agent</h3>
                <p className="text-muted mb-8 max-w-sm leading-relaxed">Instantly analyze your customer segments and let RAZZZ recommend high-converting offers with proven strategies.</p>
              </div>
              <Link href="/intelligence" className="bg-brand-primary text-white hover:bg-brand-teal px-8 py-3.5 rounded-xl font-semibold transition-all duration-300 shadow-sm hover:shadow-md flex items-center gap-2">
                Generate Strategy
                <span className="text-white/70">→</span>
              </Link>
            </div>
            
            <div className="bg-surface border border-border rounded-2xl p-8 shadow-soft flex flex-col items-start justify-between min-h-[300px] hover:border-brand-coral/30 transition-all duration-300 relative overflow-hidden group">
               <div className="absolute bottom-0 right-0 w-64 h-64 bg-brand-coral/5 rounded-full blur-3xl pointer-events-none group-hover:bg-brand-coral/10 transition-colors duration-500 translate-y-1/3 translate-x-1/4"></div>
               <div>
                 <div className="w-14 h-14 bg-brand-peach/50 dark:bg-amber-900/20 rounded-xl flex items-center justify-center mb-6 text-brand-coral dark:text-amber-500 border border-brand-coral/20 shadow-sm group-hover:scale-105 transition-transform">
                   <TrendingUp size={28} />
                 </div>
                 <h3 className="text-2xl font-bold text-foreground mb-3 tracking-tight">Active Optimizations</h3>
                 <p className="text-muted mb-8 max-w-sm leading-relaxed">Review AI recommendations for your active campaigns to improve conversions and protect your margins automatically.</p>
               </div>
               <Link href="/optimizations" className="bg-surface text-foreground border border-border hover:border-brand-coral/50 hover:bg-brand-peach/10 dark:hover:bg-amber-900/10 px-8 py-3.5 rounded-xl font-semibold transition-all duration-300 shadow-sm flex items-center gap-2">
                 View Optimizations
                 <span className="text-muted">→</span>
               </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
