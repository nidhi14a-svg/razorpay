'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { MetricCard } from '@/components/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { 
  IndianRupee, 
  Users, 
  ShoppingBag, 
  ShoppingCart, 
  PlusCircle, 
  Brain, 
  TrendingUp, 
  PieChart, 
  Filter 
} from 'lucide-react'

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
        const res = await fetch(`http://localhost:8000/merchants/${merchantId}/dashboard-summary`)
        if (!res.ok) throw new Error('Failed to fetch dashboard metrics')
        const json = await res.json()
        setData(json)
      } catch (err) {
        console.error("Dashboard fetch error:", err)
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      </div>
    )
  }

  const summary = data || {
    total_customers: 0,
    total_revenue: 0,
    average_order_value: 0,
    total_orders: 0,
    segment_distribution: {}
  }

  const segmentEntries = Object.entries(summary.segment_distribution || {})
  const totalInSegments = Object.values(summary.segment_distribution || {}).reduce((a, b) => a + b, 0) || summary.total_customers || 1

  const getSegmentColor = (seg) => {
    const s = seg.toLowerCase()
    if (s.includes('vip')) return 'bg-amber-500 text-amber-950 dark:text-amber-100 border-amber-300'
    if (s.includes('loyal')) return 'bg-emerald-500 text-emerald-950 dark:text-emerald-100 border-emerald-300'
    if (s.includes('risk')) return 'bg-rose-500 text-rose-950 dark:text-rose-100 border-rose-300'
    if (s.includes('inactive') || s.includes('dormant')) return 'bg-slate-400 text-slate-950 dark:text-slate-100 border-slate-300'
    return 'bg-brand-primary text-white border-brand-primary/30'
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-6">
        <div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">Dashboard Overview</h2>
          <p className="text-muted mt-1 text-sm">Here is a real-time behavioral overview of your customer dataset.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link 
            href="/customers" 
            className="flex items-center gap-2 bg-surface hover:bg-surface/80 border border-border text-foreground px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 shadow-sm"
          >
            <Users size={16} /> View Customers
          </Link>
          <Link 
            href="/campaigns/create" 
            className="flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white px-5 py-2.5 rounded-xl font-semibold transition-all duration-300 shadow-sm hover:shadow-md hover:-translate-y-0.5"
          >
            <PlusCircle size={20} /> New Campaign
          </Link>
        </div>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-xl">
          Failed to load dashboard metrics. Please ensure you have completed customer onboarding.
        </div>
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title="Total Customers" 
              value={summary.total_customers?.toLocaleString() || 0} 
              icon={Users} 
              color="primary" 
            />
            <MetricCard 
              title="Total Lifetime Value" 
              value={`₹${summary.total_revenue?.toLocaleString() || 0}`} 
              icon={IndianRupee} 
              color="emerald" 
            />
            <MetricCard 
              title="Average Order Value" 
              value={`₹${summary.average_order_value?.toLocaleString() || 0}`} 
              icon={ShoppingBag} 
              color="coral" 
            />
            <MetricCard 
              title="Total Purchases / Orders" 
              value={summary.total_orders?.toLocaleString() || 0} 
              icon={ShoppingCart} 
              color="teal" 
            />
          </div>

          {/* Segment Distribution Section */}
          <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8 shadow-soft">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-primary/10 text-brand-primary flex items-center justify-center">
                  <PieChart size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground tracking-tight">Customer Segment Distribution</h3>
                  <p className="text-xs text-muted">Deterministic segmentation based on behavioral recency, frequency, and monetary spend.</p>
                </div>
              </div>
              <Link href="/customers" className="text-xs font-semibold text-brand-primary hover:underline flex items-center gap-1">
                Explore Segment Data →
              </Link>
            </div>

            {segmentEntries.length === 0 ? (
              <p className="text-sm text-muted">No segment data calculated yet.</p>
            ) : (
              <div className="space-y-4">
                {/* Visual Progress Bar */}
                <div className="w-full h-4 rounded-full bg-background overflow-hidden flex shadow-inner">
                  {segmentEntries.map(([seg, count]) => {
                    const pct = (count / totalInSegments) * 100
                    return (
                      <div 
                        key={seg}
                        style={{ width: `${Math.max(pct, 1)}%` }}
                        className={`${getSegmentColor(seg)} h-full transition-all duration-500`}
                        title={`${seg}: ${count.toLocaleString()} (${pct.toFixed(1)}%)`}
                      />
                    )
                  })}
                </div>

                {/* Badges Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 pt-2">
                  {segmentEntries.map(([seg, count]) => {
                    const pct = ((count / totalInSegments) * 100).toFixed(1)
                    return (
                      <div key={seg} className="p-3 rounded-xl bg-background border border-border flex flex-col justify-between">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-xs font-bold uppercase tracking-wider text-muted truncate">
                            {seg.replace('_', ' ')}
                          </span>
                          <span className="text-[10px] font-semibold text-brand-primary">{pct}%</span>
                        </div>
                        <div className="text-lg font-extrabold text-foreground">{count.toLocaleString()}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
          
          {/* Action CTAs */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-surface border border-border rounded-2xl p-8 shadow-soft flex flex-col items-start justify-between min-h-[280px] hover:border-brand-primary/30 transition-all duration-300 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none group-hover:bg-brand-primary/10 transition-colors duration-500 -translate-y-1/2 translate-x-1/3"></div>
              <div>
                <div className="w-14 h-14 bg-brand-primary/10 dark:bg-brand-primary/20 rounded-xl flex items-center justify-center mb-6 text-brand-primary dark:text-brand-teal border border-brand-primary/20 shadow-sm group-hover:scale-105 transition-transform">
                  <Brain size={28} className="animate-pulse-slow" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-3 tracking-tight">AI Revenue Agent</h3>
                <p className="text-muted mb-8 max-w-sm leading-relaxed">
                  Analyze your customer segments and guardrails to automatically recommend personalized, margin-safe offers.
                </p>
              </div>
              <Link href="/intelligence" className="bg-brand-primary text-white hover:bg-brand-teal px-8 py-3.5 rounded-xl font-semibold transition-all duration-300 shadow-sm hover:shadow-md flex items-center gap-2">
                Generate Strategy
                <span className="text-white/70">→</span>
              </Link>
            </div>
            
            <div className="bg-surface border border-border rounded-2xl p-8 shadow-soft flex flex-col items-start justify-between min-h-[280px] hover:border-brand-coral/30 transition-all duration-300 relative overflow-hidden group">
               <div className="absolute bottom-0 right-0 w-64 h-64 bg-brand-coral/5 rounded-full blur-3xl pointer-events-none group-hover:bg-brand-coral/10 transition-colors duration-500 translate-y-1/3 translate-x-1/4"></div>
               <div>
                 <div className="w-14 h-14 bg-brand-peach/50 dark:bg-amber-900/20 rounded-xl flex items-center justify-center mb-6 text-brand-coral dark:text-amber-500 border border-brand-coral/20 shadow-sm group-hover:scale-105 transition-transform">
                   <TrendingUp size={28} />
                 </div>
                 <h3 className="text-2xl font-bold text-foreground mb-3 tracking-tight">Active Optimizations</h3>
                 <p className="text-muted mb-8 max-w-sm leading-relaxed">
                   Review continuous AI recommendations for your active campaigns to improve conversions and protect your margins.
                 </p>
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
