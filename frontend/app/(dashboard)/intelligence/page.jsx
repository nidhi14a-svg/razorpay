'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { AIInsightCard } from '@/components/AIInsightCard'
import { EmptyState } from '@/components/EmptyState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { Sparkles, Activity, FileSearch, ShieldCheck, Users, Target, TrendingUp } from 'lucide-react'
import { getApiUrl } from '@/lib/api'

export default function IntelligencePage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasRun, setHasRun] = useState(false)

  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    if (!merchantId) {
      window.location.href = '/login'
    }
  }, [])

  const handleRunAgent = async () => {
    const merchantId = localStorage.getItem('merchantId')
    setLoading(true)
    setError(null)
    
    // Add a 120-second timeout to allow the backend fallback to resolve
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000)
    
    try {
      const res = await fetch(getApiUrl('/agent/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: merchantId }),
        signal: controller.signal
      })
      
      let json
      try {
        json = await res.json()
      } catch (e) {
        throw new Error(`Failed to parse backend response (Status: ${res.status})`)
      }
      
      if (!res.ok) {
        const errMsg = Array.isArray(json.detail) 
          ? json.detail.map(d => d.msg).join(', ') 
          : (json.detail || 'Failed to run revenue agent')
        throw new Error(errMsg)
      }
      
      setData(json)
      setHasRun(true)
    } catch (err) {
      console.error("Agent run error:", err)
      if (err.name === 'AbortError') {
        setError('The AI agent took too long to respond. Please try again.')
      } else {
        setError(err.message || 'An unexpected error occurred.')
      }
    } finally {
      clearTimeout(timeoutId)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto pb-12">
      {/* Hero Section */}
      <div className="relative bg-surface rounded-3xl overflow-hidden shadow-soft border border-border mb-12 group transition-all duration-500">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-primary/5 via-brand-teal/5 to-transparent pointer-events-none"></div>
        
        {/* Animated ambient background */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-primary/10 rounded-full blur-[100px] pointer-events-none translate-x-1/3 -translate-y-1/3 group-hover:bg-brand-primary/15 transition-colors duration-700"></div>

        <div className="relative z-10 flex flex-col items-center text-center p-12 md:p-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/20 dark:text-brand-teal text-sm font-bold tracking-wide uppercase mb-8 border border-brand-primary/20">
            <Sparkles size={16} className="animate-pulse" />
            Decision Engine
          </div>
          
          <h2 className="text-4xl md:text-6xl font-extrabold text-foreground tracking-tight leading-tight mb-6 max-w-3xl mx-auto">
            Your AI-Powered <br className="hidden md:block"/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-primary to-brand-teal">Revenue Strategist</span>
          </h2>
          
          <p className="text-muted text-lg md:text-xl leading-relaxed max-w-2xl mb-12">
            RAZZZ analyzes your customer segments and historical data to recommend high-converting offers with proven strategies.
          </p>
          
          {!loading && (
            <button 
              onClick={handleRunAgent}
              className="bg-brand-primary hover:bg-brand-teal text-white font-bold px-10 py-5 rounded-2xl shadow-sm hover:shadow-soft transition-all duration-300 flex items-center gap-3 text-lg hover:-translate-y-1"
            >
              <Activity size={24} />
              {hasRun ? 'Run New Analysis' : 'Generate Strategy'}
            </button>
          )}
        </div>
      </div>

      {/* Feature Columns */}
      {!hasRun && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 px-4">
          <div className="flex flex-col items-center text-center group">
            <div className="w-20 h-20 bg-surface border border-border shadow-soft text-brand-primary rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Users size={32} strokeWidth={1.5} />
            </div>
            <h3 className="font-bold text-foreground text-xl mb-3">Understand Customers</h3>
            <p className="text-muted text-base leading-relaxed max-w-xs">Identify high-value segments and discover hidden revenue opportunities.</p>
          </div>
          <div className="flex flex-col items-center text-center group">
            <div className="w-20 h-20 bg-surface border border-border shadow-soft text-brand-teal rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Target size={32} strokeWidth={1.5} />
            </div>
            <h3 className="font-bold text-foreground text-xl mb-3">Launch Smart Campaigns</h3>
            <p className="text-muted text-base leading-relaxed max-w-xs">Personalize offers that drive engagement and maximize sales automatically.</p>
          </div>
          <div className="flex flex-col items-center text-center group">
            <div className="w-20 h-20 bg-surface border border-border shadow-soft text-emerald-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <TrendingUp size={32} strokeWidth={1.5} />
            </div>
            <h3 className="font-bold text-foreground text-xl mb-3">Optimize & Grow</h3>
            <p className="text-muted text-base leading-relaxed max-w-xs">Continuously refine your strategies for maximum revenue impact.</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="space-y-6 max-w-3xl mx-auto">
          <div className="bg-surface p-8 rounded-2xl border border-brand-teal/20 text-center shadow-sm relative overflow-hidden">
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-primary via-brand-teal to-brand-coral animate-pulse"></div>
             <div className="flex justify-center mb-6">
               <div className="w-10 h-10 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin"></div>
             </div>
             <h3 className="text-xl font-bold text-foreground mb-2">Analyzing Data Signals</h3>
             <p className="text-muted flex items-center justify-center gap-2">
               <FileSearch size={16} /> Connecting segments, rules, and historical intelligence...
             </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-6 rounded-2xl text-center font-medium max-w-3xl mx-auto flex items-center justify-center gap-2">
          {error}
        </div>
      )}

      {!loading && !error && hasRun && data && (
        <div className="max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
          {data.status === 'GUARDRAILS_MISSING' || data.status === 'MISSING_GUARDRAILS' ? (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-400 p-8 rounded-3xl text-center shadow-sm max-w-2xl mx-auto">
              <h3 className="text-2xl font-bold mb-3">Revenue Guardrails Required</h3>
              <p className="text-base text-amber-700 dark:text-amber-300 mb-6">{data.reason || 'Complete your merchant guardrails (max discount & min margin) before generating AI intelligence.'}</p>
              <Link
                href="/onboarding?step=guardrails"
                className="inline-flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white font-bold px-6 py-3 rounded-xl transition-all shadow-sm"
              >
                Configure Guardrails
              </Link>
            </div>
          ) : (data.status === 'INSUFFICIENT_CUSTOMER_DATA' || data.status === 'NO_CUSTOMER_DATA') ? (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 p-8 rounded-3xl text-center shadow-sm max-w-2xl mx-auto">
              <h3 className="text-2xl font-bold mb-3">No Customer Data Uploaded</h3>
              <p className="text-base text-blue-700 dark:text-blue-300 mb-6">{data.reason || 'Please upload your customer dataset to enable segmentation and personalized offers.'}</p>
              <Link
                href="/onboarding?step=data"
                className="inline-flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white font-bold px-6 py-3 rounded-xl transition-all shadow-sm"
              >
                Upload Customer Dataset
              </Link>
            </div>
          ) : data.status === 'INSUFFICIENT_BEHAVIORAL_DATA' ? (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 p-8 rounded-3xl text-center shadow-sm max-w-2xl mx-auto">
              <h3 className="text-2xl font-bold mb-3">Insufficient Behavioral Data</h3>
              <p className="text-base text-amber-700 dark:text-amber-300 mb-6 leading-relaxed">
                {data.reason || 'Customer records exist, but purchase history could not be calculated because the uploaded CSV does not contain valid transaction amount, quantity/price, or order information.'}
              </p>
              <Link
                href="/onboarding?step=data"
                className="inline-flex items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white font-bold px-6 py-3 rounded-xl transition-all shadow-sm"
              >
                Upload Valid Transactional Dataset
              </Link>
            </div>
          ) : data.status === 'FAILED' ? (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-400 p-8 rounded-2xl text-center shadow-sm">
              <h3 className="text-2xl font-bold mb-3">Analysis Failed</h3>
              <p className="text-lg">{data.reason}</p>
              <div className="mt-6 flex justify-center gap-4 text-sm font-medium">
                 <span className="bg-amber-100 dark:bg-amber-900/40 px-4 py-2 rounded-lg border border-amber-200 dark:border-amber-800">
                   Data Sufficiency: {data.data_sufficiency}
                 </span>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <AIInsightCard 
                title={`Strategy: ${data.recommendation?.action || 'Unknown'}`}
                recommendation={data.recommendation?.offer || 'N/A'}
                reason={data.reason}
                evidence={data.evidence}
                confidence={data.confidence}
                limitations={data.recommendation?.limitations}
              />
              
              <div className="bg-surface border border-border p-6 rounded-2xl flex items-start gap-4 shadow-sm">
                 <div className="p-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-lg">
                   <ShieldCheck size={24} />
                 </div>
                 <div className="flex-1">
                   <h4 className="font-bold text-foreground mb-1">Guardrail Status</h4>
                   <p className="text-muted text-sm">{data.guardrail_result?.reason || 'Verified'}</p>
                 </div>
                 <div>
                   <span className={`px-4 py-1.5 rounded-lg text-sm font-bold border ${
                     data.status === 'GENERATED' 
                      ? 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800' 
                      : 'bg-brand-peach/50 text-brand-coral border-brand-coral/20 dark:bg-brand-peach/20 dark:text-brand-coral dark:border-brand-coral/30'
                   }`}>
                     {data.status}
                   </span>
                 </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
