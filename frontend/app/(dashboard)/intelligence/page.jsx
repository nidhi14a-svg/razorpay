'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AIInsightCard } from '@/components/AIInsightCard'
import { EmptyState } from '@/components/EmptyState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { Sparkles, Activity } from 'lucide-react'

export default function IntelligencePage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasRun, setHasRun] = useState(false)

  const handleRunAgent = async () => {
    const merchantId = localStorage.getItem('merchantId')
    setLoading(true)
    setError(null)
    
    // Add a 60-second timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)
    
    try {
      const res = await fetch('http://localhost:8000/agent/run', {
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
    <div className="space-y-8 animate-in fade-in duration-500 max-w-4xl mx-auto">
      <div className="text-center space-y-4 py-8">
        <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
          <Sparkles className="w-8 h-8 text-purple-600" />
        </div>
        <h2 className="text-3xl font-bold text-gray-900 tracking-tight">AI Revenue Agent</h2>
        <p className="text-gray-500 max-w-2xl mx-auto">
          The Revenue Agent analyzes your historical campaign data, customer segments, and business rules to recommend the single most impactful action you can take right now.
        </p>
        
        {!loading && (
          <button 
            onClick={handleRunAgent}
            className="mt-6 bg-purple-600 hover:bg-purple-700 text-white font-semibold px-8 py-3 rounded-full shadow-md hover:shadow-lg transition flex items-center gap-2 mx-auto"
          >
            <Activity size={20} />
            {hasRun ? 'Run Agent Again' : 'Generate Growth Strategy'}
          </button>
        )}
      </div>

      {loading && (
        <div className="space-y-6 max-w-2xl mx-auto">
          <div className="bg-purple-50 p-6 rounded-xl border border-purple-100 text-center animate-pulse">
             <div className="flex justify-center mb-4">
               <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
             </div>
             <p className="font-semibold text-purple-900 mb-1">Analyzing Data Signals...</p>
             <p className="text-sm text-purple-700">Connecting segments, rules, and historical intelligence.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl text-center font-medium max-w-2xl mx-auto">
          {error}
        </div>
      )}

      {!loading && !error && hasRun && data && (
        <div className="max-w-3xl mx-auto">
          {data.status === 'FAILED' ? (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 p-8 rounded-xl text-center">
              <h3 className="text-xl font-bold mb-2">Analysis Failed</h3>
              <p>{data.reason}</p>
              <div className="mt-6 flex justify-center gap-4 text-sm font-medium">
                 <span className="bg-amber-100 px-3 py-1 rounded-full">Data Sufficiency: {data.data_sufficiency}</span>
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
              
              <div className="bg-white border border-gray-200 p-6 rounded-xl flex items-start gap-4">
                 <div className="flex-1">
                   <h4 className="font-bold text-gray-900 mb-1">Guardrail Status</h4>
                   <p className="text-gray-600 text-sm">{data.guardrail_result?.reason || 'Verified'}</p>
                 </div>
                 <div>
                   <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                     data.status === 'GENERATED' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
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
